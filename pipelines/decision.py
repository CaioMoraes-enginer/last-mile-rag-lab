"""Montagem e validacao da decisao — compartilhada entre os pipelines (KAN-7/8).

Extraida do full-context (KAN-7) para ser reutilizada pelo RAG vetorial (KAN-8)
sem duplicar logica: interpreta a resposta do LLM, resolve citacoes contra os
chunks que o gerador VIU (chunk_index) e valida com o motor deterministico.

Fronteira (escopo secao 6): o LLM sugere a rota; o motor e a fonte de verdade dos
numeros e da validade. A validacao do motor volta registrada A PARTE (requisito 9).
"""
from domain.decision import DecisionResponse
from domain.enums import DecisionStatus
from domain.models import Order, RouteCandidate
from engine.decider import CONSTRAINTS, decide, evaluate_route
from pipelines.base import LLMResponse
from pipelines.parsing import (
    ParseError,
    parse_proposal,
    parse_rejected_routes,
    resolve_citations,
)


def build_decision(
    llm: LLMResponse,
    order: Order,
    routes: list[RouteCandidate],
    scenario: dict,
    chunk_index: dict[str, dict],
) -> tuple[DecisionResponse, dict | None, bool, list[str]]:
    """Converte a resposta crua no contrato e valida com o motor.

    Retorna (decisao, registro_da_validacao_do_motor, houve_reparo, erros).
    `chunk_index` e o conjunto de chunks que o gerador viu: citacoes fora dele
    sao descartadas (garante que so se cita fonte realmente usada).
    """
    errors: list[str] = []
    gold = decide(**scenario)
    engine_validation = _gold_record(gold)

    # 1) interpretar a resposta do LLM (com reparo unico e mensuravel)
    try:
        proposal, repair_applied = parse_proposal(llm.text)
    except ParseError as exc:
        errors.append(f"parse: {exc}")
        return _error_decision(order, "Resposta do LLM ilegivel; sem decisao."), engine_validation, False, errors

    if llm.truncated:
        errors.append("resposta truncada no limite de tokens (max_output_tokens)")

    # 2) rota proposta pelo LLM
    route_by_id = {r.route_id: r for r in routes}
    llm_route = proposal.get("selected_route")
    llm_status = str(proposal.get("status", "")).upper()

    citations, dropped = resolve_citations(proposal.get("citations", []), chunk_index)
    if dropped:
        errors.append(f"citacoes descartadas (chunk nao recuperado/inexistente): {dropped}")
    rejected = parse_rejected_routes(proposal.get("rejected_routes", []))
    confidence = _clamp01(proposal.get("confidence", 0.0))
    action = str(proposal.get("recommended_action", ""))

    # 3) abstencao declarada pelo LLM
    if llm_route in (None, "", "null") or llm_status == "INSUFFICIENT_EVIDENCE":
        decision = DecisionResponse(
            order_id=order.order_id, decision_timestamp=order.decision_at,
            selected_route=None, valid=False,
            recommended_action=action or "Evidencia insuficiente para decidir.",
            constraints_checked=CONSTRAINTS, rejected_routes=rejected,
            citations=citations, confidence=confidence,
            status=DecisionStatus.INSUFFICIENT_EVIDENCE,
        )
        return decision, engine_validation, repair_applied, errors

    # 4) rota inexistente -> erro, sem mascarar
    route_obj = route_by_id.get(str(llm_route))
    if route_obj is None:
        errors.append(f"LLM escolheu rota inexistente: {llm_route!r}")
        decision = _error_decision(order, f"Rota {llm_route!r} nao existe entre as candidatas.")
        decision.rejected_routes = rejected
        decision.citations = citations
        return decision, engine_validation, repair_applied, errors

    # 5) motor valida a rota escolhida (fonte de verdade dos numeros)
    segment_class = {s.segment_id: s.segment_class for s in scenario["segments"]}
    ev = evaluate_route(
        route_obj, order, segment_class,
        scenario["incidents"], scenario["bulletin"],
        scenario["notices"], scenario["policy"],
    )
    engine_validation["llm_route"] = str(llm_route)
    engine_validation["llm_route_valid"] = ev.valid
    engine_validation["route_agreement"] = str(llm_route) == gold.selected_route

    decision = DecisionResponse(
        order_id=order.order_id, decision_timestamp=order.decision_at,
        selected_route=str(llm_route), valid=ev.valid,
        estimated_minutes=ev.estimated_minutes, slack_minutes=ev.slack_minutes,
        risk_class=ev.risk_class,
        recommended_action=action or (
            f"Seguir pela rota {llm_route}." if ev.valid
            else f"Rota {llm_route} invalida: {ev.reject_reason}"
        ),
        constraints_checked=CONSTRAINTS, rejected_routes=rejected,
        citations=citations, confidence=confidence,
        status=DecisionStatus.SUCCESS if ev.valid else DecisionStatus.ERROR,
    )
    if not ev.valid:
        errors.append(f"rota {llm_route} proposta pelo LLM e invalida: {ev.reject_reason}")
    return decision, engine_validation, repair_applied, errors


def _gold_record(gold: DecisionResponse) -> dict:
    """Decisao ouro do motor, registrada A PARTE da proposta do LLM (requisito 9)."""
    return {
        "gold_route": gold.selected_route,
        "gold_valid": gold.valid,
        "gold_estimated_minutes": gold.estimated_minutes,
        "gold_slack_minutes": gold.slack_minutes,
        "gold_risk_class": str(gold.risk_class) if gold.risk_class else None,
        "gold_status": str(gold.status),
    }


def _error_decision(order: Order, action: str) -> DecisionResponse:
    return DecisionResponse(
        order_id=order.order_id, decision_timestamp=order.decision_at,
        selected_route=None, valid=False,
        recommended_action=action, constraints_checked=CONSTRAINTS,
        confidence=0.0, status=DecisionStatus.ERROR,
    )


def _clamp01(value) -> float:
    try:
        return max(0.0, min(1.0, float(value)))
    except (TypeError, ValueError):
        return 0.0
