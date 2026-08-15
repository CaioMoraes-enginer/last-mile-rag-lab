"""Casos de avaliacao (KAN-10).

Cada caso e um mundo estruturado (cenario do motor) + o gabarito CALCULADO pelo
motor (nunca fixo). O gabarito e usado so pela rubrica; o pipeline recebe apenas
o pedido, as rotas e o corpus.

Foco em contrafactuais de NIVEL DE PEDIDO (modal, estado, horario): eles alteram o
pedido entregue ao LLM e mudam o gabarito, entao medem se o pipeline se adapta.
Contrafactuais de nivel de evento (remover incidente/clima) sao testados no motor
em KAN-5 — como o corpus e um snapshot fixo, nao se refletem no texto recuperado.
"""
from dataclasses import dataclass

from domain.decision import DecisionResponse
from domain.models import Order, RouteCandidate
from engine.decider import decide
from pipelines.cases import canonical_scenario, make_order


@dataclass
class EvalCase:
    case_id: str
    description: str
    scenario: dict
    gold: DecisionResponse

    @property
    def order(self) -> Order:
        return self.scenario["order"]

    @property
    def routes(self) -> list[RouteCandidate]:
        return self.scenario["routes"]


def _case(case_id: str, description: str, **order_overrides) -> EvalCase:
    scenario = canonical_scenario()
    if order_overrides:
        scenario["order"] = make_order(**order_overrides)
    return EvalCase(case_id, description, scenario, decide(**scenario))


def build_cases() -> list[EvalCase]:
    """Caso canonico + contrafactuais de nivel de pedido (gabarito muda)."""
    return [
        _case("canonico", "ORD-042 canonico (bike, DISPATCHED, 19:15) -> C"),
        _case("modal_moto", "Modal MOTO invalida o corredor CT-BIKE -> B", modal="MOTO"),
        _case("estado_assigned", "Estado ASSIGNED nao cumpre a politica -> B", state="ASSIGNED"),
        _case(
            "horario_apos_20h", "Decisao 20:05: aviso de acesso expirado -> B",
            decision_at="2026-08-08T20:05:00-03:00",
            promised_at="2026-08-08T20:30:00-03:00",
        ),
    ]
