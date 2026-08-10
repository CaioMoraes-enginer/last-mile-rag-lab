"""Teste de idempotencia do ChunkRepository."""

from db.client import connect
from db.repository import ChunkRepository


TEST_CHUNK_ID = "REPOSITORY-SMOKE-1"


def main() -> int:
    primeiro_chunk = {
        "chunk_id": TEST_CHUNK_ID,
        "document_id": "REPOSITORY-SMOKE-DOC",
        "document_title": "Documento de teste",
        "document_type": "smoke_test",
        "page": 1,
        "section": "Teste inicial",
        "version": "1.0",
        "zona": "ZONA-03",
        "entity_ids": ["ORD-042", "SG-BD"],
        "content": "Conteudo original do chunk.",
        "source_hash": "repository-smoke",
    }

    chunk_atualizado = {
        **primeiro_chunk,
        "version": "2.0",
        "content": "Conteudo atualizado pelo segundo upsert.",
    }

    with connect() as connection:
        repository = ChunkRepository(connection)

        # Remove qualquer sobra de uma execucao anterior.
        with connection.cursor() as cursor:
            cursor.execute(
                "DELETE FROM chunks WHERE chunk_id = %s",
                (TEST_CHUNK_ID,),
            )

        # Primeira chamada: insere o chunk.
        repository.upsert_many([primeiro_chunk])

        # Segunda chamada: deve atualizar, e nao duplicar.
        repository.upsert_many([chunk_atualizado])

        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT COUNT(*), MAX(version), MAX(content)
                FROM chunks
                WHERE chunk_id = %s
                """,
                (TEST_CHUNK_ID,),
            )
            quantidade, version, content = cursor.fetchone()

        print("Quantidade encontrada:", quantidade)
        print("Versao armazenada:", version)
        print("Conteudo armazenado:", content)

        assert quantidade == 1, "o upsert criou registros duplicados"
        assert version == "2.0", "a versao nao foi atualizada"
        assert content == "Conteudo atualizado pelo segundo upsert."

        # Limpa o registro de teste.
        with connection.cursor() as cursor:
            cursor.execute(
                "DELETE FROM chunks WHERE chunk_id = %s",
                (TEST_CHUNK_ID,),
            )

    print("\nOK! Repository idempotente: inseriu e atualizou sem duplicar.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())