"""Motor de decisao deterministico (KAN-4).

Recebe o pedido, as rotas candidatas e as evidencias, aplica as regras e devolve
o contrato DecisionResponse. Nenhuma regra especifica do ORD-042: mude as
evidencias ou o pedido e o resultado muda junto.

`evaluate_route` avalia UMA rota (validade + ETA/slack/risco); `decide` avalia
todas e escolhe a melhor valida. Os pipelines (KAN-7+) usam `evaluate_route` como
fonte de verdade para validar a rota que o LLM propos.
"""
from dataclasses import dataclass
from datetime import datetime

from domain.decision import Citation, DecisionResponse, RejectedRoute
from domain.enums import DecisionStatus, RiskClass, SegmentClass
from domain.evidence import AccessNotice, AccessPolicy, Incident, Segment, WeatherBulletin
from domain.models import Order, RouteCandidate
from engine.rules import (
    active_notice,
    blocking_incident,
    controlled_access_reason,
    is_active,
    weather_penalty_minutes,
)
from engine.sla import classify_risk, compute_slack_minutes

# Familias de restricao verificadas em toda decisao (para o campo constraints_checked).
CONSTRAINTS = ["vigencia", "bloqueio-incidente", "penalidade-chuva", "acesso-controlado", "sla"]


@dataclass
class RouteEvaluation:
    """Resultado deterministico da avaliacao de UMA rota."""
    route_id: str
    valid: bool
    estimated_minutes: int | None
    slack_minutes: int | None
    risk_class: RiskClass | None
    reject_reason: str | None
    controlled_segments: int


def evaluate_route(
    route: RouteCandidate,
    order: Order,
    segment_class: dict[str, SegmentClass],
    incidents: list[Incident],
    bulletin: WeatherBulletin | None,
    notices: list[AccessNotice],
    policy: AccessPolicy,
) -> RouteEvaluation:
    """Aplica as regras a uma unica rota e devolve validade + numeros do motor."""
    at = order.decision_at

    # 1) rota que passa por segmento bloqueado por incidente ativo -> invalida
    incident = blocking_incident(route, incidents, at)
    if incident is not None:
        return RouteEvaluation(
            route_id=route.route_id, valid=False,
            estimated_minutes=None, slack_minutes=None, risk_class=None,
            reject_reason=f"{incident.segment_id} bloqueado pelo incidente {incident.incident_id} (v{incident.version})",
            controlled_segments=0,
        )

    # 2) corredor controlado sem permissao (aviso + politica) -> invalida
    reason = controlled_access_reason(route, order, segment_class, notices, policy, at)
    if reason is not None:
        return RouteEvaluation(
            route_id=route.route_id, valid=False,
            estimated_minutes=None, slack_minutes=None, risk_class=None,
            reject_reason=reason, controlled_segments=0,
        )

    # 3) rota valida: ETA = custo nominal + penalidade de chuva
    eta = route.nominal_cost_minutes + weather_penalty_minutes(route, segment_class, bulletin, at)
    slack = compute_slack_minutes(order.decision_at, order.promised_at, eta)
    controlled = sum(1 for s in route.segments if segment_class.get(s) == SegmentClass.CT_BIKE)
    return RouteEvaluation(
        route_id=route.route_id, valid=True,
        estimated_minutes=eta, slack_minutes=slack, risk_class=classify_risk(slack),
        reject_reason=None, controlled_segments=controlled,
    )


def decide(
    order: Order,
    routes: list[RouteCandidate],
    segments: list[Segment],
    incidents: list[Incident],
    bulletin: WeatherBulletin | None,
    notices: list[AccessNotice],
    policy: AccessPolicy,
) -> DecisionResponse:
    """Aplica as regras deterministicas a todas as rotas e devolve a decisao completa."""
    at = order.decision_at
    segment_class = {s.segment_id: s.segment_class for s in segments}
    route_by_id = {r.route_id: r for r in routes}

    evaluations = [
        evaluate_route(route, order, segment_class, incidents, bulletin, notices, policy)
        for route in routes
    ]
    rejected = [
        RejectedRoute(route_id=e.route_id, reason=e.reject_reason or "")
        for e in evaluations if not e.valid
    ]
    valid = [e for e in evaluations if e.valid]

    if not valid:
        return DecisionResponse(
            order_id=order.order_id,
            decision_timestamp=at,
            valid=False,
            status=DecisionStatus.INSUFFICIENT_EVIDENCE,
            recommended_action="Nenhuma rota valida; escalar para decisao manual.",
            constraints_checked=CONSTRAINTS,
            rejected_routes=rejected,
            confidence=1.0,
        )

    # melhor rota valida: menor ETA; desempate por menos segmentos controlados
    valid.sort(key=lambda e: (e.estimated_minutes, e.controlled_segments))
    best = valid[0]
    best_route = route_by_id[best.route_id]

    return DecisionResponse(
        order_id=order.order_id,
        decision_timestamp=at,
        selected_route=best.route_id,
        valid=True,
        estimated_minutes=best.estimated_minutes,
        slack_minutes=best.slack_minutes,
        risk_class=best.risk_class,
        recommended_action=f"Seguir pela rota {best.route_id} (ETA {best.estimated_minutes} min, slack {best.slack_minutes} min).",
        constraints_checked=CONSTRAINTS,
        rejected_routes=rejected,
        citations=_build_citations(best_route, order, segment_class, notices, bulletin, at),
        confidence=1.0,
        status=DecisionStatus.SUCCESS,
    )


def _build_citations(
    route: RouteCandidate,
    order: Order,
    segment_class: dict[str, SegmentClass],
    notices: list[AccessNotice],
    bulletin: WeatherBulletin | None,
    at: datetime,
) -> list[Citation]:
    """Evidencias que sustentam a rota escolhida (rastreabilidade).

    Nota: no motor puro as citacoes referenciam o ID da evidencia; a pagina e o
    chunk exato do PDF entram quando o motor for alimentado pela ingestao (KAN-6).
    """
    citations: list[Citation] = []
    for seg_id in route.segments:
        if segment_class.get(seg_id) == SegmentClass.CT_BIKE:
            notice = active_notice(seg_id, order.zona, notices, at)
            if notice is not None:
                citations.append(Citation(
                    document_id="DOC-04",
                    chunk_id=notice.notice_id,
                    version=notice.version,
                    snippet=f"Aviso autoriza {seg_id} na {notice.zona}.",
                ))
    if bulletin is not None and is_active(bulletin.effective_from, bulletin.effective_to, at):
        citations.append(Citation(
            document_id="DOC-03",
            chunk_id=bulletin.bulletin_id,
            snippet="Penalidades de chuva por classe de segmento.",
        ))
    return citations
