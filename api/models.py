"""Contratos de request/response da API (KAN-11).

A entrada reaproveita os enums do dominio (KAN-3): modal/estado invalidos viram
422 automatico. `pipeline` e `provider` sao Literal -> valor invalido tambem e 422,
e aparecem como enum no OpenAPI.
"""
from typing import Literal

from pydantic import BaseModel, Field

from domain.enums import Modal, OrderState

PipelineName = Literal["full_context", "vector", "advanced"]
ProviderName = Literal["mock", "ollama"]


class DecideRequest(BaseModel):
    """Pedido de decisao. Overrides opcionais permitem contrafactuais."""
    pipeline: PipelineName = "advanced"
    provider: ProviderName = "mock"
    modal: Modal = Modal.BICICLETA
    state: OrderState = OrderState.DISPATCHED
    decision_at: str | None = None
    promised_at: str | None = None

    model_config = {
        "json_schema_extra": {
            "examples": [{"pipeline": "advanced", "provider": "mock"}]
        }
    }


class DecideResponse(BaseModel):
    """Resposta: o contrato de decisao (KAN-3) + rastreabilidade e telemetria."""
    run_id: str
    pipeline: str
    source: Literal["fixture", "live"]     # explicito quando veio de mock (criterio do card)
    decision: dict                         # DecisionResponse serializado (schema KAN-3)
    retrieval: list = Field(default_factory=list)
    telemetry: dict
    engine_validation: dict | None = None
    errors: list[str] = Field(default_factory=list)


class ErrorResponse(BaseModel):
    """Formato estavel de erro (documentado no OpenAPI)."""
    error: dict
    run_id: str
