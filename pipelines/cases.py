"""Caso canonico ORD-042 para os pipelines (KAN-7).

Separa duas coisas que NUNCA se misturam:

  - a PERGUNTA (order + routes): o pedido e as rotas candidatas. Isso vai ao LLM.
  - o MUNDO estruturado (segments/incidents/bulletin/notices/policy): a verdade
    que o motor deterministico usa para validar. Isso NAO vai ao LLM — ele precisa
    derivar os fatos do texto do corpus (anti-vazamento, escopo secao 11).

Os valores espelham o cenario ouro do KAN-5 (test_decider_golden). Um teste de
consistencia (test_full_context_pipeline) garante que os dois nao divirjam.
"""
from domain.evidence import AccessNotice, AccessPolicy, Incident, Segment, WeatherBulletin
from domain.models import Order, RouteCandidate


def make_order(**overrides) -> Order:
    """Pedido base do ORD-042; `overrides` troca campos para contrafactuais."""
    dados = dict(
        order_id="ORD-042",
        zona="ZONA-03",
        modal="BICICLETA",
        state="DISPATCHED",
        decision_at="2026-08-08T19:15:00-03:00",
        promised_at="2026-08-08T19:32:00-03:00",
    )
    dados.update(overrides)
    return Order(**dados)


def canonical_routes() -> list[RouteCandidate]:
    """As tres rotas candidatas do caso canonico (a pergunta)."""
    return [
        RouteCandidate(route_id="A", segments=["SG-BD"], nominal_cost_minutes=10),
        RouteCandidate(route_id="B", segments=["SG-BC", "SG-CF", "SG-FD"], nominal_cost_minutes=16),
        RouteCandidate(route_id="C", segments=["SG-BC", "SG-CE"], nominal_cost_minutes=12),
    ]


def canonical_scenario() -> dict:
    """Cenario completo do ORD-042 no formato aceito por engine.decide().

    A resposta ouro deste cenario e a rota C (validade + ETA 13 min).
    """
    return {
        "order": make_order(),
        "routes": canonical_routes(),
        "segments": [
            Segment(segment_id="SG-BD", segment_class="LOCAL"),
            Segment(segment_id="SG-BC", segment_class="LOCAL"),
            Segment(segment_id="SG-CF", segment_class="ARTERIAL"),
            Segment(segment_id="SG-FD", segment_class="LOCAL"),
            Segment(segment_id="SG-CE", segment_class="CT-BIKE"),
        ],
        "incidents": [
            Incident(
                incident_id="INC-Z03-042", segment_id="SG-BD", version="2.1",
                effective_from="2026-08-08T18:40:00-03:00", effective_to="2026-08-08T21:30:00-03:00",
            ),
        ],
        "bulletin": WeatherBulletin(
            bulletin_id="WTH-Z03-018",
            effective_from="2026-08-08T18:55:00-03:00", effective_to="2026-08-08T20:10:00-03:00",
            penalties_by_class={"LOCAL": 1, "ARTERIAL": 6, "EXPRESS": 2, "CT-BIKE": 0},
        ),
        "notices": [
            AccessNotice(
                notice_id="ACCESS-Z03-017", segment_id="SG-CE", zona="ZONA-03", version="3.0",
                effective_from="2026-08-08T18:00:00-03:00", effective_to="2026-08-08T20:00:00-03:00",
            ),
        ],
        "policy": AccessPolicy(
            policy_id="POL-MODAL-CT-3.0", version="3.0",
            required_modal="BICICLETA", required_state="DISPATCHED",
        ),
    }
