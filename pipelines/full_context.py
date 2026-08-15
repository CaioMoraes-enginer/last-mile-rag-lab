"""Pipeline P1: contexto completo sem recuperacao (KAN-7).

Estrategia de recuperacao = "mandar tudo": todos os chunks aprovados entram no
prompt, sem busca, top-k ou filtro. E o baseline de forca bruta contra o qual os
pipelines com recuperacao (P2/P3) serao comparados.

A montagem/validacao da decisao e compartilhada (pipelines/decision.py); aqui so
mora a estrategia de recuperacao (retrieve) e o prompt.
"""
from domain.decision import DecisionResponse
from domain.models import Order, RouteCandidate
from pipelines.base import ContextBundle, LLMResponse, PipelineConfig, RagPipeline
from pipelines.cases import canonical_scenario
from pipelines.context import build_chunk_index, full_context_bundle, load_corpus
from pipelines.decision import build_decision
from pipelines.prompts import render_decision_prompt


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
        return render_decision_prompt(order, routes, context.text)

    def parse_and_validate(
        self, llm: LLMResponse, order: Order, routes: list[RouteCandidate],
    ) -> tuple[DecisionResponse, dict | None, bool, list[str]]:
        return build_decision(llm, order, routes, self.scenario, self._chunk_index)
