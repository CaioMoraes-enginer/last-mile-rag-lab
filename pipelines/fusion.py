"""Fusao de rankings e diversificacao (KAN-9).

Combina varios rankings (lexical + vetorial, por faceta) num unico ranking com
Reciprocal Rank Fusion (RRF), um metodo deterministico e documentado:

    score(chunk) = soma_sobre_rankings( 1 / (k + rank_do_chunk_naquele_ranking) )

RRF nao depende da escala dos scores de cada recuperador (so do rank), o que evita
ter que normalizar BM25 contra cosseno. A contribuicao de cada recuperador fica
registrada para auditoria (por que o chunk subiu).
"""
from dataclasses import dataclass, field

from pipelines.vectorstore import RetrievedChunk

RRF_K = 60


@dataclass
class FusedChunk:
    chunk_id: str
    document_id: str
    page: int | None
    version: str | None
    content: str
    rrf_score: float
    rank: int = 0
    contributions: dict[str, int] = field(default_factory=dict)  # recuperador -> rank de origem
    effective_from: str | None = None
    effective_to: str | None = None


def reciprocal_rank_fusion(
    rankings: dict[str, list[RetrievedChunk]], k: int = RRF_K,
) -> list[FusedChunk]:
    """Funde rankings nomeados em um so. Cada chave e um recuperador (ex.: 'vetorial:acesso')."""
    fused: dict[str, FusedChunk] = {}
    for retriever, ranking in rankings.items():
        for item in ranking:
            fc = fused.get(item.chunk_id)
            if fc is None:
                fc = FusedChunk(
                    chunk_id=item.chunk_id, document_id=item.document_id,
                    page=item.page, version=item.version, content=item.content,
                    rrf_score=0.0,
                    effective_from=item.effective_from, effective_to=item.effective_to,
                )
                fused[item.chunk_id] = fc
            fc.rrf_score += 1.0 / (k + item.rank)
            fc.contributions[retriever] = item.rank

    ordenados = sorted(fused.values(), key=lambda c: (-c.rrf_score, c.chunk_id))
    for pos, fc in enumerate(ordenados, start=1):
        fc.rrf_score = round(fc.rrf_score, 6)
        fc.rank = pos
    return ordenados


def diversify(chunks: list[FusedChunk], max_per_document: int) -> list[FusedChunk]:
    """Evita que um unico documento domine o contexto (cap por documento)."""
    if max_per_document < 1:
        return chunks
    por_doc: dict[str, int] = {}
    resultado: list[FusedChunk] = []
    for fc in chunks:
        usados = por_doc.get(fc.document_id, 0)
        if usados >= max_per_document:
            continue
        por_doc[fc.document_id] = usados + 1
        resultado.append(fc)
    # reindexa o rank apos a diversificacao
    for pos, fc in enumerate(resultado, start=1):
        fc.rank = pos
    return resultado
