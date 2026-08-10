"""Carrega artefatos JSONL de chunks no PostgreSQL de forma idempotente."""

import argparse
import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any

from db.client import connect
from db.repository import ChunkRepository


def iter_jsonl(path: Path) -> Iterator[dict[str, Any]]:
    """Le objetos JSON, um por linha, informando erros com numero da linha."""

    if not path.is_file():
        raise FileNotFoundError(f"Arquivo JSONL nao encontrado: {path}")

    with path.open("r", encoding="utf-8") as source:
        for line_number, raw_line in enumerate(source, start=1):
            line = raw_line.strip()

            if not line:
                continue

            try:
                record = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"JSON invalido em {path}, linha {line_number}: {exc.msg}"
                ) from exc

            if not isinstance(record, dict):
                raise ValueError(
                    f"A linha {line_number} de {path} deve conter um objeto JSON"
                )

            yield record


def load_jsonl(
    path: Path,
    repository: ChunkRepository,
    *,
    batch_size: int = 100,
) -> int:
    """Carrega um JSONL em lotes; o commit pertence ao chamador."""

    if batch_size < 1:
        raise ValueError("batch_size deve ser maior que zero")

    total = 0
    batch: list[dict[str, Any]] = []

    for record in iter_jsonl(path):
        batch.append(record)

        if len(batch) >= batch_size:
            total += repository.upsert_many(batch)
            batch.clear()

    if batch:
        total += repository.upsert_many(batch)

    return total


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Carrega chunks JSONL no PostgreSQL + pgvector.",
    )
    parser.add_argument("path", type=Path, help="Caminho do arquivo JSONL")
    parser.add_argument(
        "--batch-size",
        type=int,
        default=100,
        help="Quantidade de chunks por lote (padrao: 100)",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()

    with connect() as connection:
        repository = ChunkRepository(connection)
        total = load_jsonl(
            args.path,
            repository,
            batch_size=args.batch_size,
        )

    print(f"OK! {total} chunks processados por upsert a partir de {args.path}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
