"""Motor de decisao deterministico (KAN-4).

Recebe o pedido, as rotas candidatas e as evidencias, aplica as regras e devolve
o contrato DecisionResponse. Nenhuma regra especifica do ORD-042: mude as
evidencias ou o pedido e o resultado muda junto.
"""
from datetime import datetime

from domain.decision import Citation, DecisionResponse, RejectedRoute
from domain.enums import DecisionStatus, SegmentClass
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


def decide(
    order: Order,
    routes: list[RouteCandidate],
    segments: list[Segment],
    incidents: list[Incident],
    bulletin: WeatherBulletin | None,
    notices: list[AccessNotice],
    policy: AccessPolicy,
) -> DecisionResponse:
    """Aplica as regras deterministicas e devolve a decisao completa."""
    at = order.decision_at
    segment_class = {s.segment_id: s.segment_class for s in segments}

    rejected: list[RejectedRoute] = []
    valid: list[tuple[RouteCandidate, int, int]] = []  # (rota, eta, slack)

    for route in routes:
        # 1) rota que passa por segmento bloqueado por incidente ativo -> invalida
        incident = blocking_incident(route, incidents, at)
        if incident is not None:
            rejected.append(RejectedRoute(
                route_id=route.route_id,
                reason=f"{incident.segment_id} bloqueado pelo incidente {incident.incident_id} (v{incident.version})",
            ))
            continue

        # 2) corredor controlado sem permissao (aviso + politica) -> invalida
        reason = controlled_access_reason(route, order, segment_class, notices, policy, at)
        if reason is not None:
            rejected.append(RejectedRoute(route_id=route.route_id, reason=reason))
            continue

        # 3) rota valida: ETA = custo nominal + penalidade de chuva
        eta = route.nominal_cost_minutes + weather_penalty_minutes(route, segment_class, bulletin, at)
        slack = compute_slack_minutes(order.decision_at, order.promised_at, eta)
        valid.append((route, eta, slack))

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
    def controlled_count(route: RouteCandidate) -> int:
        return sum(1 for s in route.segments if segment_class.get(s) == SegmentClass.CT_BIKE)

    valid.sort(key=lambda item: (item[1], controlled_count(item[0])))
    best_route, best_eta, best_slack = valid[0]

    return DecisionResponse(
        order_id=order.order_id,
        decision_timestamp=at,
        selected_route=best_route.route_id,
        valid=True,
        estimated_minutes=best_eta,
        slack_minutes=best_slack,
        risk_class=classify_risk(best_slack),
        recommended_action=f"Seguir pela rota {best_route.route_id} (ETA {best_eta} min, slack {best_slack} min).",
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
