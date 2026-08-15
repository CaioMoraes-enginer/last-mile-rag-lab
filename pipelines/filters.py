"""Filtros de vigencia e versao (KAN-9).

Aplica a regra temporal do escopo (secao 3): so vale evidencia VIGENTE no instante
da decisao (`decision_at`, com fuso explicito). Chunks expirados ou ainda nao
vigentes sao removidos do contexto (mas registrados para auditoria).

Limite honesto: a ingestao (KAN-6) so carrega versao no nivel do documento; a
vigencia por chunk (`effective_from/to`) so existe quando a fonte a fornece. Onde
nao ha metadado de vigencia, o filtro e um no-op seguro — a corretude temporal
final e garantida pelo motor (KAN-4), que ignora versoes revogadas.
"""
from datetime import datetime

from pipelines.fusion import FusedChunk


def _parse(value: str | None) -> datetime | None:
    if value is None:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None


def apply_temporal_filter(
    chunks: list[FusedChunk], decision_at: datetime,
) -> tuple[list[FusedChunk], list[dict]]:
    """Separa chunks vigentes dos fora de vigencia em `decision_at`.

    Retorna (mantidos, descartados). Cada descartado registra o motivo.
    Chunks sem metadado de vigencia sao mantidos (no-op seguro).
    """
    mantidos: list[FusedChunk] = []
    descartados: list[dict] = []
    for fc in chunks:
        ef = _parse(fc.effective_from)
        et = _parse(fc.effective_to)
        if et is not None and decision_at > et:
            descartados.append({"chunk_id": fc.chunk_id, "reason": "expirado", "effective_to": fc.effective_to})
            continue
        if ef is not None and decision_at < ef:
            descartados.append({"chunk_id": fc.chunk_id, "reason": "ainda-nao-vigente", "effective_from": fc.effective_from})
            continue
        mantidos.append(fc)
    return mantidos, descartados
