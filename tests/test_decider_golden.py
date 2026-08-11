"""Testes ouro do motor deterministico (KAN-5).

Cada caso parte do cenario canonico ORD-042 e altera UMA variavel (um
contrafactual), verificando que a decisao muda como esperado. Isso prova que o
motor decide pelas REGRAS — e nao devolve "C" por acidente.

Rode da raiz do projeto:
    python -m pytest -v
"""
from domain.evidence import AccessNotice, AccessPolicy, Incident, Segment, WeatherBulletin
from domain.models import Order, RouteCandidate
from engine.decider import decide


def make_order(**overrides) -> Order:
    """Constroi o pedido base do ORD-042, permitindo trocar campos por caso."""
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


def base_scenario() -> dict:
    """Cenario canonico ORD-042 (a resposta ouro e a rota C)."""
    return {
        "order": make_order(),
        "routes": [
            RouteCandidate(route_id="A", segments=["SG-BD"], nominal_cost_minutes=10),
            RouteCandidate(route_id="B", segments=["SG-BC", "SG-CF", "SG-FD"], nominal_cost_minutes=16),
            RouteCandidate(route_id="C", segments=["SG-BC", "SG-CE"], nominal_cost_minutes=12),
        ],
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


def test_canonico_escolhe_c():
    """Cenario completo -> a melhor rota valida e a C."""
    d = decide(**base_scenario())
    assert d.selected_route == "C"
    assert d.valid is True
    assert d.risk_class == "AT_RISK"
    assert d.estimated_minutes == 13


def test_bloqueio_removido_escolhe_a():
    """Sem o incidente, a rota A (mais curta) volta a valer e vence."""
    s = base_scenario()
    s["incidents"] = []
    assert decide(**s).selected_route == "A"


def test_aviso_expirado_cai_para_b():
    """Sem aviso de acesso ativo, a rota C perde o corredor controlado."""
    s = base_scenario()
    s["notices"] = []
    assert decide(**s).selected_route == "B"


def test_modal_errado_cai_para_b():
    """Moto nao pode usar o corredor CT-BIKE -> rota C invalida."""
    s = base_scenario()
    s["order"] = make_order(modal="MOTO")
    assert decide(**s).selected_route == "B"


def test_estado_errado_cai_para_b():
    """Pedido ainda nao despachado nao cumpre a politica do corredor."""
    s = base_scenario()
    s["order"] = make_order(state="ASSIGNED")
    assert decide(**s).selected_route == "B"


def test_chuva_encerrada_mantem_c_mais_rapida():
    """Sem chuva, C continua a escolha, mas com ETA menor (so o custo nominal)."""
    s = base_scenario()
    s["bulletin"] = None
    d = decide(**s)
    assert d.selected_route == "C"
    assert d.estimated_minutes == 12


def test_sem_rota_valida_abstem():
    """Todas as rotas invalidas -> o motor se abstem (INSUFFICIENT_EVIDENCE)."""
    s = base_scenario()
    s["order"] = make_order(modal="MOTO")  # rota C fora (modal nao permitido)
    s["incidents"] = [
        Incident(incident_id="INC-A", segment_id="SG-BD", version="1",
                 effective_from="2026-08-08T18:00:00-03:00", effective_to="2026-08-08T22:00:00-03:00"),
        Incident(incident_id="INC-B", segment_id="SG-CF", version="1",
                 effective_from="2026-08-08T18:00:00-03:00", effective_to="2026-08-08T22:00:00-03:00"),
    ]  # rotas A e B bloqueadas
    d = decide(**s)
    assert d.valid is False
    assert d.status == "INSUFFICIENT_EVIDENCE"
    assert d.selected_route is None
