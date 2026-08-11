"""Regras deterministicas do motor de decisao (KAN-4).

Funcoes puras sobre as evidencias: dizem se uma evidencia esta ativa, se uma
rota esta bloqueada, quanto a chuva penaliza e se um corredor controlado esta
liberado. Zero LLM, tudo auditavel.
"""
from datetime import datetime

from domain.enums import SegmentClass
from domain.evidence import AccessNotice, AccessPolicy, Incident, WeatherBulletin
from domain.models import Order, RouteCandidate


def is_active(effective_from: datetime, effective_to: datetime, at: datetime) -> bool:
    """A evidencia vale no instante `at`? (janela de vigencia, extremos inclusivos)."""
    return effective_from <= at <= effective_to


def blocking_incident(
    route: RouteCandidate,
    incidents: list[Incident],
    at: datetime,
) -> Incident | None:
    """Primeiro incidente ATIVO que bloqueia um segmento da rota (ou None)."""
    for incident in incidents:
        if incident.segment_id in route.segments and is_active(
            incident.effective_from, incident.effective_to, at
        ):
            return incident
    return None


def active_notice(
    segment_id: str,
    zona: str,
    notices: list[AccessNotice],
    at: datetime,
) -> AccessNotice | None:
    """Aviso de acesso ativo para o segmento na zona, no instante `at`."""
    for notice in notices:
        if (
            notice.segment_id == segment_id
            and notice.zona == zona
            and is_active(notice.effective_from, notice.effective_to, at)
        ):
            return notice
    return None


def weather_penalty_minutes(
    route: RouteCandidate,
    segment_class: dict[str, SegmentClass],
    bulletin: WeatherBulletin | None,
    at: datetime,
) -> int:
    """Minutos extras da chuva: soma a penalidade da classe de cada segmento."""
    if bulletin is None or not is_active(bulletin.effective_from, bulletin.effective_to, at):
        return 0
    total = 0
    for seg_id in route.segments:
        classe = segment_class.get(seg_id)
        if classe is not None:
            total += bulletin.penalties_by_class.get(classe, 0)
    return total


def controlled_access_reason(
    route: RouteCandidate,
    order: Order,
    segment_class: dict[str, SegmentClass],
    notices: list[AccessNotice],
    policy: AccessPolicy,
    at: datetime,
) -> str | None:
    """Motivo pelo qual a rota NAO pode usar um corredor controlado (ou None se ok).

    Para cada segmento CT-BIKE da rota, exige: aviso ativo para o segmento na
    zona do pedido e o pedido cumprindo a politica (modal e estado).
    """
    for seg_id in route.segments:
        if segment_class.get(seg_id) != SegmentClass.CT_BIKE:
            continue
        if active_notice(seg_id, order.zona, notices, at) is None:
            return f"{seg_id} e corredor controlado sem aviso de acesso ativo"
        if order.modal != policy.required_modal:
            return f"{seg_id} exige modal {policy.required_modal} (pedido: {order.modal})"
        if order.state != policy.required_state:
            return f"{seg_id} exige estado {policy.required_state} (pedido: {order.state})"
    return None
