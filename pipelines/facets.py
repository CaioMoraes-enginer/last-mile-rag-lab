"""Facetas de evidencia e cobertura (KAN-9).

A decisao de rota depende de evidencias DISPERSAS em cinco categorias, cada uma
num documento do corpus. Em vez de uma consulta unica (P2), o P3 gera uma consulta
por faceta e depois verifica se todas as facetas necessarias foram recuperadas
ANTES de gerar (se faltar, sinaliza insuficiencia em vez de alucinar).

As facetas espelham as cinco categorias de evidencia do escopo (secao 8):
  pedido, malha, eventos (incidentes/clima), acesso e SLA.
"""
from dataclasses import dataclass

from domain.models import Order


@dataclass(frozen=True)
class Facet:
    key: str
    documents: tuple[str, ...]   # documentos que cobrem esta faceta


# Mapa faceta -> documento(s) do corpus (categorias de evidencia).
FACETS: tuple[Facet, ...] = (
    Facet("pedido", ("DOC-01",)),
    Facet("malha", ("DOC-02",)),
    Facet("eventos", ("DOC-03",)),
    Facet("acesso", ("DOC-04",)),
    Facet("sla", ("DOC-05",)),
)

# Facetas obrigatorias para uma decisao valida (todas, na v1).
REQUIRED_FACETS: tuple[str, ...] = tuple(f.key for f in FACETS)

# Documento -> faceta (para medir cobertura a partir dos chunks recuperados).
_DOC_TO_FACET = {doc: f.key for f in FACETS for doc in f.documents}


def build_faceted_queries(order: Order) -> dict[str, str]:
    """Uma consulta por faceta, derivada do pedido (sem gabarito)."""
    base = f"pedido {order.order_id} zona {order.zona} modal {order.modal} estado {order.state}"
    return {
        "pedido": f"{base}: estado do pedido, eventos do turno e linha do tempo operacional.",
        "malha": f"{base}: mapa da malha, segmentos, custos base e versao da rede.",
        "eventos": f"{base}: incidentes ativos, bloqueios de segmento e boletins de clima com penalidades.",
        "acesso": f"{base}: politicas de acesso, corredores controlados, avisos e janelas temporais por modal.",
        "sla": f"{base}: regras de SLA, prazo, calculo de folga e classe de risco.",
    }


def facet_of(document_id: str) -> str | None:
    """Faceta coberta por um documento (ou None se desconhecido)."""
    return _DOC_TO_FACET.get(document_id)


def coverage(document_ids: list[str]) -> dict[str, bool]:
    """Quais facetas estao presentes no conjunto de documentos recuperados."""
    presentes = {facet_of(d) for d in document_ids}
    return {f.key: (f.key in presentes) for f in FACETS}


def missing_facets(document_ids: list[str]) -> list[str]:
    """Facetas obrigatorias que NAO foram recuperadas."""
    cov = coverage(document_ids)
    return [f for f in REQUIRED_FACETS if not cov.get(f, False)]
