"""Operacoes de armazenamento dos chunks no PostgreSQL + pgvector."""

from collections.abc import Iterable, Mapping
from datetime import datetime
from typing import Any

from pgvector import Vector
from psycopg import Connection
from psycopg.rows import dict_row


UPSERT_CHUNK_SQL = """
INSERT INTO chunks (
    chunk_id,
    document_id,
    document_title,
    document_type,
    page,
    section,
    version,
    effective_from,
    effective_to,
    zona,
    entity_ids,
    content,
    embedding,
    source_hash
)
VALUES (
    %(chunk_id)s,
    %(document_id)s,
    %(document_title)s,
    %(document_type)s,
    %(page)s,
    %(section)s,
    %(version)s,
    %(effective_from)s,
    %(effective_to)s,
    %(zona)s,
    %(entity_ids)s,
    %(content)s,
    %(embedding)s,
    %(source_hash)s
)
ON CONFLICT (chunk_id)
DO UPDATE SET
    document_id = EXCLUDED.document_id,
    document_title = EXCLUDED.document_title,
    document_type = EXCLUDED.document_type,
    page = EXCLUDED.page,
    section = EXCLUDED.section,
    version = EXCLUDED.version,
    effective_from = EXCLUDED.effective_from,
    effective_to = EXCLUDED.effective_to,
    zona = EXCLUDED.zona,
    entity_ids = EXCLUDED.entity_ids,
    content = EXCLUDED.content,
    embedding = EXCLUDED.embedding,
    source_hash = EXCLUDED.source_hash,
    ingested_at = now()
"""


class ChunkRepository:
    """Centraliza as operacoes da aplicacao sobre a tabela chunks."""

    def __init__(self, connection: Connection) -> None:
        self.connection = connection

    @staticmethod
    def _prepare_chunk(chunk: Mapping[str, Any]) -> dict[str, Any]:
        """Valida e converte um chunk para o formato aceito pelo banco."""

        required_fields = ("chunk_id", "document_id", "content")

        for field in required_fields:
            if chunk.get(field) in (None, ""):
                raise ValueError(f"Campo obrigatorio ausente: {field}")

        embedding = chunk.get("embedding")

        if embedding is not None and not isinstance(embedding, Vector):
            embedding = Vector(embedding)

        entity_ids = chunk.get("entity_ids")

        if isinstance(entity_ids, str):
            entity_ids = [entity_ids]
        elif entity_ids is not None:
            entity_ids = list(entity_ids)

        effective_from = ChunkRepository._parse_datetime(
            chunk.get("effective_from"),
            "effective_from",
        )
        effective_to = ChunkRepository._parse_datetime(
            chunk.get("effective_to"),
            "effective_to",
        )

        return {
            "chunk_id": chunk["chunk_id"],
            "document_id": chunk["document_id"],
            "document_title": chunk.get("document_title"),
            "document_type": chunk.get("document_type"),
            "page": chunk.get("page"),
            "section": chunk.get("section"),
            "version": chunk.get("version"),
            "effective_from": effective_from,
            "effective_to": effective_to,
            "zona": chunk.get("zona"),
            "entity_ids": entity_ids,
            "content": chunk["content"],
            "embedding": embedding,
            "source_hash": chunk.get("source_hash"),
        }

    @staticmethod
    def _parse_datetime(value: Any, field: str) -> datetime | None:
        """Aceita datetime ou timestamp ISO-8601 e devolve datetime."""

        if value is None or isinstance(value, datetime):
            return value

        if isinstance(value, str):
            try:
                return datetime.fromisoformat(value.replace("Z", "+00:00"))
            except ValueError as exc:
                raise ValueError(
                    f"Timestamp invalido no campo {field}: {value}"
                ) from exc

        raise ValueError(f"Tipo invalido no campo {field}: {type(value).__name__}")

    @staticmethod
    def _build_filters(
        *,
        document_id: str | None = None,
        zona: str | None = None,
        version: str | None = None,
        as_of: datetime | str | None = None,
        entity_id: str | None = None,
    ) -> tuple[str, list[Any]]:
        """Monta apenas filtros SQL previamente definidos e seus parametros."""

        clauses: list[str] = []
        params: list[Any] = []

        if document_id is not None:
            clauses.append("document_id = %s")
            params.append(document_id)

        if zona is not None:
            clauses.append("zona = %s")
            params.append(zona)

        if version is not None:
            clauses.append("version = %s")
            params.append(version)

        if as_of is not None:
            parsed_as_of = ChunkRepository._parse_datetime(as_of, "as_of")
            clauses.append("(effective_from IS NULL OR effective_from <= %s)")
            params.append(parsed_as_of)
            clauses.append("(effective_to IS NULL OR effective_to >= %s)")
            params.append(parsed_as_of)

        if entity_id is not None:
            clauses.append("%s = ANY(COALESCE(entity_ids, ARRAY[]::TEXT[]))")
            params.append(entity_id)

        if not clauses:
            return "", params

        return " AND " + " AND ".join(clauses), params

    def upsert_many(self, chunks: Iterable[Mapping[str, Any]]) -> int:
        """Insere chunks novos e atualiza chunks que ja possuem o mesmo ID."""

        prepared_chunks = [
            self._prepare_chunk(chunk)
            for chunk in chunks
        ]

        if not prepared_chunks:
            return 0

        with self.connection.cursor() as cursor:
            cursor.executemany(UPSERT_CHUNK_SQL, prepared_chunks)

        return len(prepared_chunks)

    def vector_search(
        self,
        embedding: list[float] | Vector,
        *,
        limit: int = 5,
        document_id: str | None = None,
        zona: str | None = None,
        version: str | None = None,
        as_of: datetime | str | None = None,
    ) -> list[dict[str, Any]]:
        """Retorna os chunks mais proximos pela distancia cosseno."""

        if limit < 1:
            raise ValueError("O limite da busca deve ser maior que zero")

        query_vector = embedding if isinstance(embedding, Vector) else Vector(embedding)
        filter_sql, filter_params = self._build_filters(
            document_id=document_id,
            zona=zona,
            version=version,
            as_of=as_of,
        )

        query = f"""
            SELECT
                chunk_id,
                document_id,
                page,
                section,
                version,
                effective_from,
                effective_to,
                zona,
                entity_ids,
                content,
                embedding <=> %s AS distance
            FROM chunks
            WHERE embedding IS NOT NULL
              {filter_sql}
            ORDER BY distance ASC, chunk_id ASC
            LIMIT %s
        """

        with self.connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute(query, [query_vector, *filter_params, limit])
            return cursor.fetchall()

    def lexical_search(
        self,
        text: str,
        *,
        limit: int = 5,
        document_id: str | None = None,
        zona: str | None = None,
        version: str | None = None,
        as_of: datetime | str | None = None,
    ) -> list[dict[str, Any]]:
        """Busca termos no indice full-text em portugues."""

        if not text.strip():
            raise ValueError("O texto da busca lexical nao pode ser vazio")

        if limit < 1:
            raise ValueError("O limite da busca deve ser maior que zero")

        filter_sql, filter_params = self._build_filters(
            document_id=document_id,
            zona=zona,
            version=version,
            as_of=as_of,
        )

        query = f"""
            WITH lexical_query AS (
                SELECT plainto_tsquery('portuguese', %s) AS value
            )
            SELECT
                chunk_id,
                document_id,
                page,
                section,
                version,
                effective_from,
                effective_to,
                zona,
                entity_ids,
                content,
                ts_rank_cd(content_tsv, lexical_query.value) AS score
            FROM chunks
            CROSS JOIN lexical_query
            WHERE content_tsv @@ lexical_query.value
              {filter_sql}
            ORDER BY score DESC, chunk_id ASC
            LIMIT %s
        """

        with self.connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute(query, [text, *filter_params, limit])
            return cursor.fetchall()

    def filter_chunks(
        self,
        *,
        document_id: str | None = None,
        zona: str | None = None,
        version: str | None = None,
        as_of: datetime | str | None = None,
        entity_id: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Lista chunks por documento, zona, versao, vigencia ou entidade."""

        if limit < 1:
            raise ValueError("O limite da busca deve ser maior que zero")

        filter_sql, filter_params = self._build_filters(
            document_id=document_id,
            zona=zona,
            version=version,
            as_of=as_of,
            entity_id=entity_id,
        )

        query = f"""
            SELECT
                chunk_id,
                document_id,
                page,
                section,
                version,
                effective_from,
                effective_to,
                zona,
                entity_ids,
                content,
                source_hash,
                ingested_at
            FROM chunks
            WHERE TRUE
              {filter_sql}
            ORDER BY document_id ASC, page ASC NULLS LAST, chunk_id ASC
            LIMIT %s
        """

        with self.connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute(query, [*filter_params, limit])
            return cursor.fetchall()
