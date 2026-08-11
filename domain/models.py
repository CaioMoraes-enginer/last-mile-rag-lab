"""Modelos de entrada do dominio: o pedido e as rotas a avaliar (KAN-3).

Enquanto o DecisionResponse (decision.py) e a SAIDA, estes sao a ENTRADA:
descrevem a pergunta que o motor de decisao precisa responder.
"""
from datetime import datetime

from pydantic import BaseModel, Field

from domain.enums import Modal, OrderState


class Order(BaseModel):
    """Um pedido de entrega a ser roteado."""
    order_id: str
    zona: str
    modal: Modal
    state: OrderState
    decision_at: datetime          # momento em que a decisao e tomada
    promised_at: datetime          # horario prometido de entrega (SLA)


class RouteCandidate(BaseModel):
    """Uma rota candidata: por quais segmentos passa e seu custo nominal."""
    route_id: str
    segments: list[str] = Field(default_factory=list)   # ex: ["SG-BC", "SG-CE"]
    nominal_cost_minutes: int                            # tempo nominal, sem penalidades


if __name__ == "__main__":
    # Cenario canonico do ORD-042: o pedido + as 3 rotas candidatas.
    # (segmentos e custos aqui sao ILUSTRATIVOS; o mapa real vem do DOC-02 na KAN-6)
    pedido = Order(
        order_id="ORD-042",
        zona="ZONA-03",
        modal="BICICLETA",
        state="DISPATCHED",
        decision_at="2026-08-08T19:15:00-03:00",
        promised_at="2026-08-08T19:32:00-03:00",
    )
    rotas = [
        RouteCandidate(route_id="A", segments=["SG-BD"], nominal_cost_minutes=12),
        RouteCandidate(route_id="B", segments=["SG-BC", "SG-CF", "SG-FD"], nominal_cost_minutes=20),
        RouteCandidate(route_id="C", segments=["SG-BC", "SG-CE"], nominal_cost_minutes=17),
    ]

    print("PEDIDO:")
    print(pedido.model_dump_json(indent=2))
    print("\nROTAS CANDIDATAS:")
    for rota in rotas:
        print(rota.model_dump_json())