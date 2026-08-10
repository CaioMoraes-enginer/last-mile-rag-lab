"""Teste de idempotencia do loader JSONL."""

from pathlib import Path

from db.client import connect
from db.loader import load_jsonl
from db.repository import ChunkRepository


FIXTURE = Path(__file__).resolve().parent / "fixtures" / "chunks.sample.jsonl"
DOCUMENT_ID = "SAMPLE-DOC"


def main() -> int:
    with connect() as connection:
        repository = ChunkRepository(connection)

        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM chunks WHERE document_id = %s", (DOCUMENT_ID,))

        first_total = load_jsonl(FIXTURE, repository, batch_size=1)
        second_total = load_jsonl(FIXTURE, repository, batch_size=1)

        rows = repository.filter_chunks(document_id=DOCUMENT_ID)

        print("Primeira carga processou:", first_total)
        print("Segunda carga processou:", second_total)
        print("Linhas armazenadas apos duas cargas:", len(rows))

        assert first_total == 2
        assert second_total == 2
        assert [row["chunk_id"] for row in rows] == [
            "LOADER-SAMPLE-1",
            "LOADER-SAMPLE-2",
        ]

        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM chunks WHERE document_id = %s", (DOCUMENT_ID,))

    print("\nOK! Loader JSONL idempotente e banco limpo.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
