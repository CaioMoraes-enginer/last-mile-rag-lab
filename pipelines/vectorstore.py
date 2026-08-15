"""Indice vetorial e busca por similaridade (KAN-8).

Dois backends por tras de um Protocol comum:

  - InMemoryVectorStore: cosseno em Python puro. Reproduzivel e sem servico
    externo — usado nos testes e no modo offline.
  - PgVectorStore: reusa ChunkRepository.vector_search (Postgres + pgvector, HNSW
    cosseno do KAN-15) para a execucao real.

Ambos devolvem RetrievedChunk com rank e score, e aplicam a mesma politica de
recuperacao: similaridade pura (sem BM25/filtro), dedup por chunk_id, desempate
estavel por chunk_id, corte em top-k.
"""
import math
from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@dataclass
class RetrievedChunk:
    """Um chunk recuperado, com rastreabilidade da busca (rank + score)."""
    chunk_id: str
    document_id: str
    page: int | None
    version: str | None
    content: str
    score: float          # 0..1 (1 = identico); cosseno normalizado
    rank: int             # posicao no ranking (1 = melhor)


def _cosine(a: list[float], b: list[float]) -> float:
    num = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return 0.0
    return num / (na * nb)


@runtime_checkable
class VectorStore(Protocol):
    """Fronteira do indice vetorial. O pipeline nao conhece o backend concreto."""

    def search(self, query_embedding: list[float], top_k: int) -> list[RetrievedChunk]:
        """Top-k chunks mais similares, ja com rank e score."""
        ...

    def index_hash(self) -> str:
        """Hash reproduzivel do indice (corpus + modelo de embedding)."""
        ...


def _dedup_rank(scored: list[tuple[float, dict]], top_k: int) -> list[RetrievedChunk]:
    """Ordena por score desc (desempate por chunk_id), remove repetidos, corta em top-k."""
    scored.sort(key=lambda item: (-item[0], item[1]["chunk_id"]))
    vistos: set[str] = set()
    resultado: list[RetrievedChunk] = []
    for score, chunk in scored:
        cid = chunk["chunk_id"]
        if cid in vistos:
            continue
        vistos.add(cid)
        resultado.append(RetrievedChunk(
            chunk_id=cid,
            document_id=chunk["document_id"],
            page=chunk.get("page"),
            version=chunk.get("version"),
            content=chunk["content"],
            score=round(score, 6),
            rank=len(resultado) + 1,
        ))
        if len(resultado) >= top_k:
            break
    return resultado


class InMemoryVectorStore:
    """Indice em memoria: cosseno em Python puro. Reproduzivel, sem servico externo."""

    def __init__(self):
        self._items: list[tuple[dict, list[float]]] = []
        self._embedding_model = "unknown"

    @classmethod
    def from_chunks(cls, chunks: list[dict], embedder, *, batch: int = 32) -> "InMemoryVectorStore":
        """Indexa chunks (dicts do chunks.jsonl) gerando embeddings do conteudo."""
        store = cls()
        store._embedding_model = getattr(embedder, "model", "unknown")
        for inicio in range(0, len(chunks), batch):
            lote = chunks[inicio : inicio + batch]
            vetores = embedder.embed([c["content"] for c in lote])
            for chunk, vetor in zip(lote, vetores):
                store._items.append((chunk, vetor))
        return store

    def search(self, query_embedding: list[float], top_k: int) -> list[RetrievedChunk]:
        if top_k < 1:
            raise ValueError("top_k deve ser >= 1")
        scored = [(_cosine(query_embedding, vetor), chunk) for chunk, vetor in self._items]
        return _dedup_rank(scored, top_k)

    def index_hash(self) -> str:
        import hashlib
        h = hashlib.sha256(self._embedding_model.encode("utf-8"))
        for chunk, _ in sorted(self._items, key=lambda it: it[0]["chunk_id"]):
            h.update(chunk["chunk_id"].encode("utf-8"))
            h.update(chunk.get("source_hash", "").encode("utf-8"))
        return h.hexdigest()

    def __len__(self) -> int:
        return len(self._items)


class PgVectorStore:
    """Indice real: reusa ChunkRepository.vector_search (Postgres + pgvector)."""

    def __init__(self, repository, *, embedding_model: str = "nomic-embed-text"):
        self.repository = repository
        self.embedding_model = embedding_model

    def search(self, query_embedding: list[float], top_k: int) -> list[RetrievedChunk]:
        if top_k < 1:
            raise ValueError("top_k deve ser >= 1")
        rows = self.repository.vector_search(query_embedding, limit=top_k)
        resultado: list[RetrievedChunk] = []
        for pos, row in enumerate(rows, start=1):
            # pgvector devolve distancia cosseno (0 = identico); score = 1 - distancia
            score = round(1.0 - float(row["distance"]), 6)
            resultado.append(RetrievedChunk(
                chunk_id=row["chunk_id"], document_id=row["document_id"],
                page=row.get("page"), version=row.get("version"),
                content=row["content"], score=score, rank=pos,
            ))
        return resultado

    def index_hash(self) -> str:
        # o indice vive no banco; identificamos pelo modelo de embedding usado.
        import hashlib
        return hashlib.sha256(f"pgvector:{self.embedding_model}".encode("utf-8")).hexdigest()
