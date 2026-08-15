"""Fabrica de pipelines injetavel (KAN-11).

Constroi os indices uma vez por provedor (caros) e devolve o pipeline pedido por
nome, ja com o cenario do pedido. O healthcheck NAO chama nada disto.
"""
from functools import lru_cache

from pipelines.advanced import AdvancedConfig, AdvancedPipeline
from pipelines.cases import canonical_scenario, make_order
from pipelines.context import load_corpus
from pipelines.embeddings import HashingEmbeddingProvider, OllamaEmbeddingProvider
from pipelines.full_context import FullContextPipeline
from pipelines.lexical import InMemoryBM25Store
from pipelines.vector import VectorPipeline
from pipelines.vectorstore import InMemoryVectorStore

from api.errors import pipeline_not_found

PIPELINES = ("full_context", "vector", "advanced")


@lru_cache(maxsize=2)
def _stores(provider: str):
    """Indices construidos 1x por provedor e reutilizados."""
    emb = OllamaEmbeddingProvider() if provider == "ollama" else HashingEmbeddingProvider()
    chunks = load_corpus()
    return emb, InMemoryVectorStore.from_chunks(chunks, emb), InMemoryBM25Store(chunks)


def build_scenario(req) -> dict:
    """Cenario do pedido = canonico + overrides do request (modal/estado/horario)."""
    scenario = canonical_scenario()
    over = {"modal": req.modal, "state": req.state}
    if req.decision_at:
        over["decision_at"] = req.decision_at
    if req.promised_at:
        over["promised_at"] = req.promised_at
    scenario["order"] = make_order(**over)
    return scenario


def build_pipeline(name: str, provider: str, scenario: dict):
    """Instancia o pipeline pedido, com o cenario (verdade do motor) injetado."""
    if name not in PIPELINES:
        raise pipeline_not_found(name)
    if name == "full_context":
        return FullContextPipeline(scenario=scenario)
    emb, vec, lex = _stores(provider)
    if name == "vector":
        return VectorPipeline(vec, emb, scenario=scenario)
    return AdvancedPipeline(
        vec, emb, lex,
        config=AdvancedConfig(final_k=8, max_per_document=2), scenario=scenario,
    )
