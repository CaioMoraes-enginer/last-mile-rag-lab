"""Contrato estruturado da decisao de rota (KAN-3).

Este e o formato UNICO de resposta que os tres pipelines (contexto completo,
RAG vetorial e RAG avancado) precisam preencher. Um contrato so permite
comparar os pipelines de forma justa no benchmark.
"""
from datetime import datetime

from pydantic import BaseModel, Field

from domain.enums import DecisionStatus, RiskClass


class Citation(BaseModel):
    """Uma evidencia rastreavel: aponta para o trecho exato que sustenta a decisao.

    Regra do projeto: citacao NAO pode ser "segundo o documento". Ela precisa
    levar ate o documento, a pagina e o chunk usado.
    """
    document_id: str                 # ex: "DOC-04"
    chunk_id: str                    # ex: "DOC-04-P01-C02"
    page: int | None = None          # pagina no PDF
    version: str | None = None       # versao do documento/evento citado
    snippet: str | None = None       # trecho curto do texto citado


class RejectedRoute(BaseModel):
    """Uma rota descartada, com o motivo (para auditoria)."""
    route_id: str                    # ex: "A"
    reason: str                      # ex: "SG-BD bloqueado pelo incidente INC-Z03-042"


class DecisionResponse(BaseModel):
    """A resposta completa de uma decisao de rota."""

    order_id: str
    decision_timestamp: datetime

    # Resultado principal (fica None quando status = INSUFFICIENT_EVIDENCE)
    selected_route: str | None = None
    valid: bool = False

    # Numeros calculados pelo motor deterministico (a KAN-4, mais pra frente)
    estimated_minutes: int | None = None
    slack_minutes: int | None = None
    risk_class: RiskClass | None = None

    recommended_action: str = ""

    # Rastreabilidade
    constraints_checked: list[str] = Field(default_factory=list)
    rejected_routes: list[RejectedRoute] = Field(default_factory=list)
    citations: list[Citation] = Field(default_factory=list)

    confidence: float = 0.0
    status: DecisionStatus = DecisionStatus.SUCCESS


if __name__ == "__main__":
    # Demonstracao: monta a decisao do ORD-042 e mostra ela virando JSON.
    exemplo = DecisionResponse(
        order_id="ORD-042",
        decision_timestamp="2026-08-08T19:15:00-03:00",
        selected_route="C",
        valid=True,
        estimated_minutes=17,
        slack_minutes=0,
        risk_class="AT_RISK",
        recommended_action="Seguir pela rota C (corredor controlado SG-CE).",
        constraints_checked=["incidente", "clima", "politica-acesso", "sla"],
        rejected_routes=[
            RejectedRoute(route_id="A", reason="SG-BD bloqueado pelo incidente INC-Z03-042"),
            RejectedRoute(route_id="B", reason="Desvio mais lento; penalidade de chuva no SG-CF"),
        ],
        citations=[
            Citation(document_id="DOC-04", chunk_id="DOC-04-P01-C02", page=1, version="3.0"),
        ],
        confidence=0.9,
        status="SUCCESS",
    )
    print(exemplo.model_dump_json(indent=2))