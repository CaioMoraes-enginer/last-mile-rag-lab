"""Pipeline P3: RAG avancado (KAN-9).

Orquestra recuperacao hibrida e auditavel:

  facetas -> [lexical BM25 + vetorial] por faceta -> fusao RRF -> filtro de
  vigencia -> diversificacao -> reranking -> checagem de cobertura -> LLM ->
  motor COMO FERRAMENTA (validado, auditavel) -> decisao.

Todas as etapas sao registradas no trace (permite reconstruir por que cada chunk
chegou ao contexto). As ablacoes (sem lexical / sem filtro / sem reranker / sem
ferramenta) sao configuraveis, sem alterar codigo.
"""
from dataclasses import dataclass

from domain.decision import DecisionResponse
from domain.enums import DecisionStatus
from domain.models import Order, RouteCandidate
from engine.decider import CONSTRAINTS
from pipelines.base import ContextBundle, LLMResponse, PipelineConfig, RagPipeline
from pipelines.cases import canonical_scenario
from pipelines.facets import (
    REQUIRED_FACETS,
    build_faceted_queries,
    coverage,
    facet_of,
    missing_facets,
)
from pipelines.filters import apply_temporal_filter
from pipelines.fusion import FusedChunk, diversify, reciprocal_rank_fusion
from pipelines.parsing import ParseError, parse_proposal, parse_rejected_routes, resolve_citations
from pipelines.prompts import render_decision_prompt
from pipelines.query import build_retrieval_query
from pipelines.rerank import IdentityReranker, LexicalOverlapReranker
from pipelines.tools import ToolRunner


@dataclass
class AdvancedConfig:
    """Flags de ablacao + parametros de recuperacao (registrados no trace)."""
    use_lexical: bool = True
    use_filters: bool = True
    use_reranker: bool = True
    use_tools: bool = True
    top_k_retriever: int = 10   # candidatos por recuperador/faceta
    final_k: int = 8            # chunks que entram no contexto
    max_per_document: int = 3   # cap da diversificacao


class AdvancedPipeline(RagPipeline):
    """P3 — RAG avancado (hibrido + filtros + reranking + ferramentas)."""

    name = "advanced"
    version = "1.0.0"

    def __init__(
        self, vector_store, embedder, lexical_store, *,
        reranker=None, config: AdvancedConfig | None = None, scenario: dict | None = None,
    ):
        self.vector_store = vector_store
        self.embedder = embedder
        self.lexical_store = lexical_store
        self.reranker = reranker or LexicalOverlapReranker()
        self.cfg = config or AdvancedConfig()
        self.scenario = scenario or canonical_scenario()
        self._chunk_index: dict[str, dict] = {}
        self._final: list[FusedChunk] = []
        self._backfilled: list[str] = []
        self._trace: dict = {}
        self._tool_calls: list[dict] = []
        self._missing: list[str] = []

    # ---- recuperacao (a fronteira do P3) ------------------------------------

    def retrieve(self, order: Order, routes: list[RouteCandidate]) -> ContextBundle:
        cfg = self.cfg
        faceted = build_faceted_queries(order)

        rankings: dict[str, list] = {}
        candidate_counts: dict[str, int] = {}
        for facet, q in faceted.items():
            vres = self.vector_store.search(self.embedder.embed([q])[0], cfg.top_k_retriever)
            rankings[f"vetorial:{facet}"] = vres
            candidate_counts[f"vetorial:{facet}"] = len(vres)
            if cfg.use_lexical:
                lres = self.lexical_store.search(q, cfg.top_k_retriever)
                rankings[f"lexical:{facet}"] = lres
                candidate_counts[f"lexical:{facet}"] = len(lres)

        fused = reciprocal_rank_fusion(rankings)

        dropped_by_filter: list[dict] = []
        if cfg.use_filters:
            fused, dropped_by_filter = apply_temporal_filter(fused, order.decision_at)

        diversified = diversify(fused, cfg.max_per_document)

        reranker = self.reranker if cfg.use_reranker else IdentityReranker()
        reranked = reranker.rerank(build_retrieval_query(order), diversified)

        final = reranked[: cfg.final_k]
        # backfill de cobertura: garante representacao de cada faceta cujo documento
        # FOI recuperado. O gate so dispara quando a evidencia nem existe no pool.
        selecionados = {c.chunk_id for c in final}
        cobertas = {facet_of(c.document_id) for c in final}
        backfilled: list[str] = []
        for facet in REQUIRED_FACETS:
            if facet in cobertas:
                continue
            cand = next(
                (c for c in reranked
                 if c.chunk_id not in selecionados and facet_of(c.document_id) == facet),
                None,
            )
            if cand is not None:
                final.append(cand)
                selecionados.add(cand.chunk_id)
                cobertas.add(facet)
                backfilled.append(cand.chunk_id)
        for pos, fc in enumerate(final, start=1):
            fc.rank = pos

        self._final = final
        self._backfilled = backfilled
        self._missing = missing_facets([c.document_id for c in self._final])

        self._chunk_index = {
            c.chunk_id: {
                "chunk_id": c.chunk_id, "document_id": c.document_id,
                "page": c.page, "version": c.version, "content": c.content,
            }
            for c in self._final
        }
        self._trace = {
            "faceted_queries": faceted,
            "retrievers": list(rankings.keys()),
            "candidate_counts": candidate_counts,
            "filter_dropped": dropped_by_filter,
            "reranker": reranker.name,
            "backfilled": self._backfilled,
            "coverage": coverage([c.document_id for c in self._final]),
            "missing_facets": self._missing,
            "ablations": {
                "use_lexical": cfg.use_lexical, "use_filters": cfg.use_filters,
                "use_reranker": cfg.use_reranker, "use_tools": cfg.use_tools,
            },
        }
        text = "\n\n".join(_render(c) for c in self._final)
        return ContextBundle(
            text=text,
            chunk_ids=[c.chunk_id for c in self._final],
            corpus_hash=self.vector_store.index_hash(),
        )

    def retrieval_records(self) -> list:
        return [
            {
                "rank": c.rank, "rrf_score": c.rrf_score, "chunk_id": c.chunk_id,
                "document_id": c.document_id, "page": c.page, "contributions": c.contributions,
            }
            for c in self._final
        ]

    def trace_record(self) -> dict:
        return {**self._trace, "tool_calls": self._tool_calls}

    def build_prompt(
        self, context: ContextBundle, order: Order, routes: list[RouteCandidate],
        config: PipelineConfig,
    ) -> str:
        return render_decision_prompt(order, routes, context.text)

    # ---- validacao com o motor como ferramenta ------------------------------

    def parse_and_validate(
        self, llm: LLMResponse, order: Order, routes: list[RouteCandidate],
    ) -> tuple[DecisionResponse, dict | None, bool, list[str]]:
        errors: list[str] = []
        runner = ToolRunner(self.scenario)
        gold = runner.gold_decision()
        # MESMO contrato dos demais pipelines (decision._gold_record): a chave da
        # rota ouro e `gold_route`, nao `gold_selected_route`. Sem isso a API e a
        # interface (KAN-12) nao encontram a rota ouro do P3 e mostram vazio.
        engine_validation = {
            "gold_route": gold["selected_route"],
            "gold_valid": gold["valid"],
            "gold_estimated_minutes": gold["estimated_minutes"],
            "gold_slack_minutes": gold["slack_minutes"],
            "gold_risk_class": gold["risk_class"],
            "gold_status": gold["status"],
        }

        # gate de cobertura: faltando faceta essencial -> insuficiencia (antes de confiar no LLM)
        if self._missing:
            errors.append(f"cobertura insuficiente: faltam facetas {self._missing}")
            engine_validation["coverage_gate"] = True
            engine_validation["missing_facets"] = self._missing
            self._tool_calls = runner.audit()
            decision = _insufficient(order, f"Faltam evidencias das facetas {self._missing}.")
            return decision, engine_validation, False, errors

        # interpreta a resposta do LLM
        try:
            proposal, repair_applied = parse_proposal(llm.text)
        except ParseError as exc:
            errors.append(f"parse: {exc}")
            self._tool_calls = runner.audit()
            return _error(order, "Resposta do LLM ilegivel."), engine_validation, False, errors

        if llm.truncated:
            errors.append("resposta truncada no limite de tokens")

        citations, dropped = resolve_citations(proposal.get("citations", []), self._chunk_index)
        if dropped:
            errors.append(f"citacoes descartadas (fora do recuperado): {dropped}")
        rejected = parse_rejected_routes(proposal.get("rejected_routes", []))
        confidence = _clamp01(proposal.get("confidence", 0.0))
        action = str(proposal.get("recommended_action", ""))
        llm_route = proposal.get("selected_route")
        llm_status = str(proposal.get("status", "")).upper()

        if llm_route in (None, "", "null") or llm_status == "INSUFFICIENT_EVIDENCE":
            self._tool_calls = runner.audit()
            decision = DecisionResponse(
                order_id=order.order_id, decision_timestamp=order.decision_at,
                selected_route=None, valid=False,
                recommended_action=action or "Evidencia insuficiente para decidir.",
                constraints_checked=CONSTRAINTS, rejected_routes=rejected,
                citations=citations, confidence=confidence,
                status=DecisionStatus.INSUFFICIENT_EVIDENCE,
            )
            return decision, engine_validation, repair_applied, errors

        engine_validation["llm_route"] = str(llm_route)
        engine_validation["route_agreement"] = str(llm_route) == gold.get("selected_route")

        # ablacao "sem ferramenta": aceita a rota do LLM SEM validar (saida degradada)
        if not self.cfg.use_tools:
            errors.append("ablacao: motor nao chamado; numeros nao validados")
            self._tool_calls = runner.audit()
            decision = DecisionResponse(
                order_id=order.order_id, decision_timestamp=order.decision_at,
                selected_route=str(llm_route), valid=False,
                recommended_action=action or f"Rota {llm_route} (sem validacao do motor).",
                constraints_checked=CONSTRAINTS, rejected_routes=rejected,
                citations=citations, confidence=confidence, status=DecisionStatus.SUCCESS,
            )
            return decision, engine_validation, repair_applied, errors

        # ferramenta: motor valida a rota escolhida (fonte de verdade)
        val = runner.validate_route(llm_route)
        self._tool_calls = runner.audit()
        if not val.get("ok"):
            errors.append(f"validate_route: {val.get('error')}")
            decision = _error(order, f"Rota {llm_route!r}: {val.get('error')}")
            decision.rejected_routes = rejected
            decision.citations = citations
            return decision, engine_validation, repair_applied, errors

        engine_validation["llm_route_valid"] = val["valid"]
        decision = DecisionResponse(
            order_id=order.order_id, decision_timestamp=order.decision_at,
            selected_route=str(llm_route), valid=val["valid"],
            estimated_minutes=val["estimated_minutes"], slack_minutes=val["slack_minutes"],
            risk_class=val["risk_class"],
            recommended_action=action or (
                f"Seguir pela rota {llm_route}." if val["valid"]
                else f"Rota {llm_route} invalida: {val['reject_reason']}"
            ),
            constraints_checked=CONSTRAINTS, rejected_routes=rejected,
            citations=citations, confidence=confidence,
            status=DecisionStatus.SUCCESS if val["valid"] else DecisionStatus.ERROR,
        )
        if not val["valid"]:
            errors.append(f"rota {llm_route} proposta pelo LLM e invalida: {val['reject_reason']}")
        return decision, engine_validation, repair_applied, errors


def _render(c: FusedChunk) -> str:
    cab = (
        f"[rank={c.rank} | rrf={c.rrf_score} | chunk_id={c.chunk_id} "
        f"| doc={c.document_id} | page={c.page} | via={list(c.contributions)}]"
    )
    return f"{cab}\n{c.content}"


def _insufficient(order: Order, action: str) -> DecisionResponse:
    return DecisionResponse(
        order_id=order.order_id, decision_timestamp=order.decision_at,
        selected_route=None, valid=False, recommended_action=action,
        constraints_checked=CONSTRAINTS, confidence=0.0,
        status=DecisionStatus.INSUFFICIENT_EVIDENCE,
    )


def _error(order: Order, action: str) -> DecisionResponse:
    return DecisionResponse(
        order_id=order.order_id, decision_timestamp=order.decision_at,
        selected_route=None, valid=False, recommended_action=action,
        constraints_checked=CONSTRAINTS, confidence=0.0, status=DecisionStatus.ERROR,
    )


def _clamp01(value) -> float:
    try:
        return max(0.0, min(1.0, float(value)))
    except (TypeError, ValueError):
        return 0.0
