"""Busca lexical (KAN-9).

Complementa a busca vetorial: recupera TERMOS e CODIGOS exatos (SG-BD, ORD-042,
ACCESS-Z03-017) que o embedding semantico costuma diluir. Dois backends por tras
do mesmo Protocol:

  - InMemoryBM25Store: BM25 em Python puro. A tokenizacao preserva hifens, entao
    codigos viram um unico termo e casam de forma exata.
  - PgLexicalStore: reusa ChunkRepository.lexical_search (full-text portugues do
    KAN-15) para a execucao real.
"""
import math
import re
from collections import Counter
from typing import Protocol, runtime_checkable

from pipelines.vectorstore import RetrievedChunk

# Preserva hifen e digitos: "ACCESS-Z03-017" e "ORD-042" viram um token so.
_TOKEN_RE = re.compile(r"[a-z0-9][a-z0-9\-]*")

BM25_K1 = 1.5
BM25_B = 0.75


def _tokenize(text: str) -> list[str]:
    return _TOKEN_RE.findall(text.lower())


@runtime_checkable
class LexicalStore(Protocol):
    """Fronteira da busca lexical (mesma forma da vetorial)."""

    def search(self, query: str, top_k: int) -> list[RetrievedChunk]:
        ...


class InMemoryBM25Store:
    """Indice BM25 em memoria. Reproduzivel, sem servico externo (testes/offline)."""

    def __init__(self, chunks: list[dict]):
        self._chunks = chunks
        self._docs_tokens = [_tokenize(c["content"]) for c in chunks]
        self._doc_len = [len(t) for t in self._docs_tokens]
        self._avgdl = (sum(self._doc_len) / len(self._doc_len)) if self._doc_len else 0.0
        self._tf = [Counter(toks) for toks in self._docs_tokens]
        self._df = Counter()
        for toks in self._docs_tokens:
            for termo in set(toks):
                self._df[termo] += 1
        self._n = len(chunks)

    def _idf(self, termo: str) -> float:
        # IDF do BM25 (Robertson), com piso >= 0 para termos muito comuns.
        n_qi = self._df.get(termo, 0)
        return max(0.0, math.log((self._n - n_qi + 0.5) / (n_qi + 0.5) + 1.0))

    def _score(self, query_tokens: list[str], idx: int) -> float:
        tf = self._tf[idx]
        dl = self._doc_len[idx]
        total = 0.0
        for termo in query_tokens:
            f = tf.get(termo, 0)
            if f == 0:
                continue
            denom = f + BM25_K1 * (1 - BM25_B + BM25_B * (dl / (self._avgdl or 1)))
            total += self._idf(termo) * (f * (BM25_K1 + 1)) / denom
        return total

    def search(self, query: str, top_k: int) -> list[RetrievedChunk]:
        if top_k < 1:
            raise ValueError("top_k deve ser >= 1")
        query_tokens = _tokenize(query)
        scored = [(self._score(query_tokens, i), i) for i in range(self._n)]
        scored = [(s, i) for s, i in scored if s > 0]
        scored.sort(key=lambda it: (-it[0], self._chunks[it[1]]["chunk_id"]))
        resultado: list[RetrievedChunk] = []
        for pos, (score, i) in enumerate(scored[:top_k], start=1):
            c = self._chunks[i]
            resultado.append(RetrievedChunk(
                chunk_id=c["chunk_id"], document_id=c["document_id"],
                page=c.get("page"), version=c.get("version"),
                content=c["content"], score=round(score, 6), rank=pos,
                effective_from=c.get("effective_from"), effective_to=c.get("effective_to"),
            ))
        return resultado


class PgLexicalStore:
    """Indice lexical real: reusa ChunkRepository.lexical_search (KAN-15)."""

    def __init__(self, repository):
        self.repository = repository

    def search(self, query: str, top_k: int) -> list[RetrievedChunk]:
        if top_k < 1:
            raise ValueError("top_k deve ser >= 1")
        rows = self.repository.lexical_search(query, limit=top_k)
        return [
            RetrievedChunk(
                chunk_id=row["chunk_id"], document_id=row["document_id"],
                page=row.get("page"), version=row.get("version"),
                content=row["content"], score=round(float(row["score"]), 6), rank=pos,
            )
            for pos, row in enumerate(rows, start=1)
        ]
