"""Teste do motor no cenario canonico ORD-042 e num contrafactual (KAN-4).

Monta o pedido, as 3 rotas, o mapa de segmentos e as evidencias, roda o motor e
verifica que a decisao correta EMERGE DAS REGRAS (nao de um valor fixo):
  - rota A: invalida (SG-BD bloqueado pelo incidente ativo)
  - rota B: valida, porem lenta (desvio + penalidade de chuva no arterial)
  - rota C: melhor rota valida (corredor CT-BIKE liberado, sem penalidade de chuva)

Rode da raiz do projeto:
    python -m engine.decider_smoke_test
"""
from domain.evidence import AccessNotice, AccessPolicy, Incident, Segment, WeatherBulletin
from domain.models import Order, RouteCandidate
from engine.decider import decide


def cenario_ord_042():
    order = Order(
        order_id="ORD-042",
        zona="ZONA-03",
        modal="BICICLETA",
        state="DISPATCHED",
        decision_at="2026-08-08T19:15:00-03:00",
        promised_at="2026-08-08T19:32:00-03:00",
    )
    routes = [
        RouteCandidate(route_id="A", segments=["SG-BD"], nominal_cost_minutes=10),
        RouteCandidate(route_id="B", segments=["SG-BC", "SG-CF", "SG-FD"], nominal_cost_minutes=16),
        RouteCandidate(route_id="C", segments=["SG-BC", "SG-CE"], nominal_cost_minutes=12),
    ]
    segments = [
        Segment(segment_id="SG-BD", segment_class="LOCAL"),
        Segment(segment_id="SG-BC", segment_class="LOCAL"),
        Segment(segment_id="SG-CF", segment_class="ARTERIAL"),
        Segment(segment_id="SG-FD", segment_class="LOCAL"),
        Segment(segment_id="SG-CE", segment_class="CT-BIKE"),
    ]
    incidents = [
        Incident(
            incident_id="INC-Z03-042",
            segment_id="SG-BD",
            version="2.1",
            effective_from="2026-08-08T18:40:00-03:00",
            effective_to="2026-08-08T21:30:00-03:00",
        ),
    ]
    bulletin = WeatherBulletin(
        bulletin_id="WTH-Z03-018",
        effective_from="2026-08-08T18:55:00-03:00",
        effective_to="2026-08-08T20:10:00-03:00",
        penalties_by_class={"LOCAL": 1, "ARTERIAL": 6, "EXPRESS": 2, "CT-BIKE": 0},
    )
    notices = [
        AccessNotice(
            notice_id="ACCESS-Z03-017",
            segment_id="SG-CE",
            zona="ZONA-03",
            version="3.0",
            effective_from="2026-08-08T18:00:00-03:00",
            effective_to="2026-08-08T20:00:00-03:00",
        ),
    ]
    policy = AccessPolicy(
        policy_id="POL-MODAL-CT-3.0",
        version="3.0",
        required_modal="BICICLETA",
        required_state="DISPATCHED",
    )
    return order, routes, segments, incidents, bulletin, notices, policy


def main() -> int:
    order, routes, segments, incidents, bulletin, notices, policy = cenario_ord_042()

    decisao = decide(order, routes, segments, incidents, bulletin, notices, policy)
    print(decisao.model_dump_json(indent=2))

    assert decisao.selected_route == "C", f"esperava rota C, veio {decisao.selected_route}"
    assert decisao.valid is True, "a decisao deveria ser valida"
    assert decisao.risk_class == "AT_RISK", f"risco inesperado: {decisao.risk_class}"
    rejeitadas = {r.route_id for r in decisao.rejected_routes}
    assert "A" in rejeitadas, "rota A deveria ter sido rejeitada (bloqueio)"
    assert decisao.citations, "deveria haver ao menos uma citacao sustentando a rota"
    print("\nOK! Motor escolheu a rota C no cenario canonico ORD-042.")

    # Contrafactual: sem o aviso de acesso, a rota C perde a permissao do corredor.
    sem_aviso = decide(order, routes, segments, incidents, bulletin, [], policy)
    assert sem_aviso.selected_route != "C", "sem aviso ativo, a rota C nao poderia vencer"
    print(f"Contrafactual (sem aviso): rota {sem_aviso.selected_route}, status {sem_aviso.status}.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
