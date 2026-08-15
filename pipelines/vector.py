"""Pipeline P2: RAG vetorial simples (KAN-8).

Recuperacao = similaridade vetorial pura: embeda a consulta derivada do pedido,
busca os top-k chunks mais proximos e monta o contexto SO com eles. Sem BM25,
filtros temporais, fusao ou reranking (isso e o P3/KAN-9).

Herda de RagPipeline: reaproveita run(), o prompt e a validacao/parse (KAN-7).
A unica diferenca em relacao ao P1 e o retrieve() abaixo.
"""
from domain.decision import DecisionResponse
from domain.models import Order, RouteCandidate
from pipelines.base import ContextBundle, LLMResponse, PipelineConfig, RagPipeline
from pipelines.cases import canonical_scenario
from pipelines.decision import build_decision
from pipelines.prompts import render_decision_prompt
from pipelines.query import build_retrieval_query
from pipelines.vectorstore import RetrievedChunk, VectorStore


class VectorPipeline(RagPipeline):
    """P2 — RAG vetorial simples (top-k por similaridade)."""

    name = "vector"
    version = "1.0.0"

    def __init__(
        self, store: VectorStore, embedder, *,
        top_k: int = 8, scenario: dict | None = None,
    ):
        self.store = store
        self.embedder = embedder
        self.top_k = top_k
        self.scenario = scenario or canonical_scenario()
        self._chunk_index: dict[str, dict] = {}
        self._retrieved: list[RetrievedChunk] = []

    def retrieve(self, order: Order, routes: list[RouteCandidate]) -> ContextBundle:
        query = build_retrieval_query(order)
        query_embedding = self.embedder.embed([query])[0]
        self._retrieved = self.store.search(query_embedding, self.top_k)

        # so os chunks recuperados podem ser vistos e citados pelo gerador
        self._chunk_index = {
            r.chunk_id: {
                "chunk_id": r.chunk_id, "document_id": r.document_id,
                "page": r.page, "version": r.version, "content": r.content,
            }
            for r in self._retrieved
        }
        text = "\n\n".join(_render_retrieved(r) for r in self._retrieved)
        return ContextBundle(
            text=text,
            chunk_ids=[r.chunk_id for r in self._retrieved],
            corpus_hash=self.store.index_hash(),
        )

    def retrieval_records(self) -> list:
        """Ranking recuperado para o artefato (chunk_id, rank, score, doc, page)."""
        return [
            {
                "rank": r.rank, "score": r.score, "chunk_id": r.chunk_id,
                "document_id": r.document_id, "page": r.page,
            }
            for r in self._retrieved
        ]

    def build_prompt(
        self, context: ContextBundle, order: Order, routes: list[RouteCandidate],
        config: PipelineConfig,
    ) -> str:
        return render_decision_prompt(order, routes, context.text)

    def parse_and_validate(
        self, llm: LLMResponse, order: Order, routes: list[RouteCandidate],
    ) -> tuple[DecisionResponse, dict | None, bool, list[str]]:
        return build_decision(llm, order, routes, self.scenario, self._chunk_index)


def _render_retrieved(r: RetrievedChunk) -> str:
    cab = (
        f"[rank={r.rank} | score={r.score} | chunk_id={r.chunk_id} "
        f"| doc={r.document_id} | page={r.page}]"
    )
    return f"{cab}\n{r.content}"
