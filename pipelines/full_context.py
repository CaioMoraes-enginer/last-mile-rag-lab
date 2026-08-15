"""Pipeline P1: contexto completo sem recuperacao (KAN-7).

Estrategia de recuperacao = "mandar tudo": todos os chunks aprovados entram no
prompt, sem busca, top-k ou filtro. E o baseline de forca bruta contra o qual os
pipelines com recuperacao (P2/P3) serao comparados.

Fluxo (herdado de RagPipeline.run): recupera -> prompt -> LLM -> parse/valida.
Na validacao, o motor deterministico (KAN-4) e a FONTE DE VERDADE: ele calcula os
numeros da rota escolhida pelo LLM e a decisao ouro, registradas em separado.
"""
from domain.decision import DecisionResponse
from domain.enums import DecisionStatus
from domain.models import Order, RouteCandidate
from engine.decider import CONSTRAINTS, decide, evaluate_route
from pipelines.base import ContextBundle, LLMResponse, PipelineConfig, RagPipeline
from pipelines.cases import canonical_scenario
from pipelines.context import build_chunk_index, full_context_bundle, load_corpus
from pipelines.parsing import (
    ParseError,
    parse_proposal,
    parse_rejected_routes,
    resolve_citations,
)
from pipelines.prompts import render_full_context


class FullContextPipeline(RagPipeline):
    """P1 — contexto completo, sem recuperacao."""

    name = "full_context"
    version = "1.0.0"

    def __init__(self, scenario: dict | None = None):
        # o "mundo" estruturado (verdade do motor). Default = caso canonico ORD-042.
        # KAN-10 pode injetar contrafactuais aqui sem tocar no pipeline.
        self.scenario = scenario or canonical_scenario()
        self._chunk_index: dict[str, dict] = {}

    def retrieve(self, order: Order, routes: list[RouteCandidate]) -> ContextBundle:
        """Monta o contexto integral e guarda o indice para resolver citacoes."""
        self._chunk_index = build_chunk_index(load_corpus())
        return full_context_bundle()

    def build_prompt(
        self, context: ContextBundle, order: Order, routes: list[RouteCandidate],
        config: PipelineConfig,
    ) -> str:
        return render_full_context(order, routes, context.text)

    def parse_and_validate(
        self, llm: LLMResponse, order: Order, routes: list[RouteCandidate],
    ) -> tuple[DecisionResponse, dict | None, bool, list[str]]:
        errors: list[str] = []
        gold = decide(**self.scenario)
        engine_validation = _gold_record(gold)

        # 1) interpretar a resposta do LLM (com reparo unico e mensuravel)
        try:
            proposal, repair_applied = parse_proposal(llm.text)
        except ParseError as exc:
            errors.append(f"parse: {exc}")
            decision = _error_decision(order, "Resposta do LLM ilegivel; sem decisao.")
            return decision, engine_validation, False, errors

        if llm.truncated:
            errors.append("resposta truncada no limite de tokens (max_output_tokens)")

        # 2) rota proposta pelo LLM
        route_by_id = {r.route_id: r for r in routes}
        llm_route = proposal.get("selected_route")
        llm_status = str(proposal.get("status", "")).upper()

        citations, dropped = resolve_citations(proposal.get("citations", []), self._chunk_index)
        if dropped:
            errors.append(f"citacoes descartadas (chunk inexistente): {dropped}")
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
        segment_class = {s.segment_id: s.segment_class for s in self.scenario["segments"]}
        ev = evaluate_route(
            route_obj, order, segment_class,
            self.scenario["incidents"], self.scenario["bulletin"],
            self.scenario["notices"], self.scenario["policy"],
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
