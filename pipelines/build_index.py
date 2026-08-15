"""Constroi o indice vetorial no Postgres + pgvector (KAN-8).

Le a saida aprovada da ingestao (chunks.jsonl), gera os embeddings via Ollama e
faz upsert na tabela chunks (KAN-15). Reproduzivel: a mesma entrada + mesmo modelo
produzem o mesmo indice.

Pre-requisitos: Docker do Postgres no ar (porta 5433) e Ollama com o modelo de
embedding baixado (ollama pull nomic-embed-text).

Rode da raiz do projeto:
    python -m pipelines.build_index --embedding-model nomic-embed-text
"""
import argparse

from pipelines.context import load_corpus
from pipelines.embeddings import OllamaEmbeddingProvider


def build(embedding_model: str, host: str, batch: int) -> int:
    from db.client import connect
    from db.repository import ChunkRepository

    chunks = load_corpus()
    embedder = OllamaEmbeddingProvider(model=embedding_model, host=host)

    total = 0
    with connect() as conn:
        repo = ChunkRepository(conn)
        for inicio in range(0, len(chunks), batch):
            lote = chunks[inicio : inicio + batch]
            vetores = embedder.embed([c["content"] for c in lote])
            enriquecidos = [{**chunk, "embedding": vetor} for chunk, vetor in zip(lote, vetores)]
            total += repo.upsert_many(enriquecidos)
            print(f"  {total}/{len(chunks)} chunks indexados...", flush=True)
        conn.commit()

    print(f"OK! {total} chunks com embedding ({embedding_model}) no pgvector.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Constroi o indice vetorial (KAN-8)")
    parser.add_argument("--embedding-model", default="nomic-embed-text")
    parser.add_argument("--host", default="http://localhost:11434")
    parser.add_argument("--batch", type=int, default=16)
    args = parser.parse_args()
    return build(args.embedding_model, args.host, args.batch)


if __name__ == "__main__":
    raise SystemExit(main())
