"""Teste das consultas reutilizaveis do ChunkRepository."""

from datetime import datetime

from db.client import connect
from db.repository import ChunkRepository


PREFIX = "QUERY-SMOKE-"
DECISION_AT = datetime.fromisoformat("2026-08-08T19:15:00-03:00")
DIM = 768


def one_hot(position: int) -> list[float]:
    embedding = [0.0] * DIM
    embedding[position] = 1.0
    return embedding


def main() -> int:
    chunks = [
        {
            "chunk_id": f"{PREFIX}1",
            "document_id": "QUERY-DOC-03",
            "page": 1,
            "section": "Bloqueio",
            "version": "2.1",
            "effective_from": "2026-08-08T18:40:00-03:00",
            "effective_to": "2026-08-08T21:30:00-03:00",
            "zona": "ZONA-03",
            "entity_ids": ["SG-BD"],
            "content": "Bloqueio total no segmento SG-BD.",
            "embedding": one_hot(0),
        },
        {
            "chunk_id": f"{PREFIX}2",
            "document_id": "QUERY-DOC-03",
            "page": 2,
            "section": "Chuva expirada",
            "version": "1.0",
            "effective_from": "2026-08-08T18:00:00-03:00",
            "effective_to": "2026-08-08T19:00:00-03:00",
            "zona": "ZONA-03",
            "entity_ids": ["SG-CF"],
            "content": "Desvio pelo corredor arterial SG-CF.",
            "embedding": one_hot(1),
        },
        {
            "chunk_id": f"{PREFIX}3",
            "document_id": "QUERY-DOC-04",
            "page": 3,
            "section": "Acesso controlado",
            "version": "3.0",
            "effective_from": "2026-08-08T18:00:00-03:00",
            "effective_to": "2026-08-08T20:00:00-03:00",
            "zona": "ZONA-03",
            "entity_ids": ["SG-CE"],
            "content": "Corredor controlado SG-CE liberado para bicicleta.",
            "embedding": one_hot(2),
        },
    ]

    with connect() as connection:
        repository = ChunkRepository(connection)

        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM chunks WHERE chunk_id LIKE %s", (f"{PREFIX}%",))

        repository.upsert_many(chunks)

        vector_results = repository.vector_search(
            one_hot(2),
            limit=1,
            zona="ZONA-03",
            as_of=DECISION_AT,
        )
        assert vector_results[0]["chunk_id"] == f"{PREFIX}3"
        assert vector_results[0]["document_id"] == "QUERY-DOC-04"
        assert vector_results[0]["page"] == 3
        assert float(vector_results[0]["distance"]) == 0.0
        print("[1] busca vetorial pelo repository: OK")

        lexical_results = repository.lexical_search(
            "SG-BD",
            zona="ZONA-03",
            as_of=DECISION_AT,
        )
        assert [row["chunk_id"] for row in lexical_results] == [f"{PREFIX}1"]
        print("[2] busca lexical pelo repository: OK")

        active_results = repository.filter_chunks(
            zona="ZONA-03",
            as_of=DECISION_AT,
        )
        assert [row["chunk_id"] for row in active_results] == [
            f"{PREFIX}1",
            f"{PREFIX}3",
        ]

        version_results = repository.filter_chunks(version="3.0")
        assert [row["chunk_id"] for row in version_results] == [f"{PREFIX}3"]

        entity_results = repository.filter_chunks(entity_id="SG-CE")
        assert [row["chunk_id"] for row in entity_results] == [f"{PREFIX}3"]
        print("[3] filtros de zona, vigencia, versao e entidade: OK")

        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM chunks WHERE chunk_id LIKE %s", (f"{PREFIX}%",))

    print("\nOK! Consultas do ChunkRepository funcionando e banco limpo.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
