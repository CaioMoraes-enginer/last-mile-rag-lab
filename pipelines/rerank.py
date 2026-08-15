"""Reranking dos candidatos (KAN-9).

Reordena os candidatos fundidos por relevancia a consulta, atras de uma interface
substituivel (um cross-encoder real poderia entrar no lugar sem mexer no pipeline).

  - IdentityReranker: mantem a ordem (usado na ablacao "sem reranker").
  - LexicalOverlapReranker: reranker LOCAL/simulado, deterministico — pontua pela
    sobreposicao de termos entre consulta e chunk. Suficiente para exercitar a
    etapa nos testes sem baixar um modelo de reranking.
"""
import re
from typing import Protocol, runtime_checkable

from pipelines.fusion import FusedChunk

_TOKEN_RE = re.compile(r"[a-z0-9][a-z0-9\-]*")


@runtime_checkable
class Reranker(Protocol):
    """Recebe candidatos e devolve um ranking rastreavel (reordenado)."""

    name: str

    def rerank(self, query: str, candidates: list[FusedChunk]) -> list[FusedChunk]:
        ...


class IdentityReranker:
    """Nao reordena (ablacao 'sem reranker')."""

    name = "identity"

    def rerank(self, query: str, candidates: list[FusedChunk]) -> list[FusedChunk]:
        for pos, fc in enumerate(candidates, start=1):
            fc.rank = pos
        return candidates


class LexicalOverlapReranker:
    """Reranker local: pontua pela sobreposicao de termos consulta x chunk."""

    name = "lexical_overlap"

    def rerank(self, query: str, candidates: list[FusedChunk]) -> list[FusedChunk]:
        termos = set(_TOKEN_RE.findall(query.lower()))

        def overlap(fc: FusedChunk) -> float:
            doc_termos = set(_TOKEN_RE.findall(fc.content.lower()))
            if not doc_termos:
                return 0.0
            return len(termos & doc_termos) / len(termos or {""})

        # desempate estavel: overlap, depois rrf_score, depois chunk_id
        reordenados = sorted(
            candidates, key=lambda fc: (-overlap(fc), -fc.rrf_score, fc.chunk_id)
        )
        for pos, fc in enumerate(reordenados, start=1):
            fc.rank = pos
        return reordenados
