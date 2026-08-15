"""Testes do pipeline P2 - RAG vetorial simples (KAN-8).

Usam embeddings DETERMINISTICOS (HashingEmbeddingProvider) e indice em memoria,
mais o MockProvider de LLM: a suite nao depende de Ollama nem de Postgres.
"""
import json
from functools import lru_cache

from pipelines.base import PipelineConfig
from pipelines.cases import canonical_routes, make_order
from pipelines.context import load_corpus
from pipelines.embeddings import HashingEmbeddingProvider
from pipelines.providers import MockProvider
from pipelines.query import build_retrieval_query
from pipelines.vector import VectorPipeline
from pipelines.vectorstore import InMemoryVectorStore

CONFIG = PipelineConfig(prompt_version="vector_v1")
EMBEDDER = HashingEmbeddingProvider(dim=256)


@lru_cache(maxsize=1)
def _store() -> InMemoryVectorStore:
    return InMemoryVectorStore.from_chunks(load_corpus(), EMBEDDER)


def _mock(route="C", status="SUCCESS", chunk_id=None, confidence=0.8):
    citations = [{"document_id": "DOC-04", "chunk_id": chunk_id}] if chunk_id else []
    return MockProvider(text=json.dumps({
        "selected_route": route, "status": status, "confidence": confidence,
        "recommended_action": "acao de teste",
        "rejected_routes": [{"route_id": "A", "reason": "bloqueado"}],
        "citations": citations,
    }, ensure_ascii=False))


# ---- indice / retriever ------------------------------------------------------

def test_store_returns_ranked_topk_with_metadata():
    query_emb = EMBEDDER.embed([build_retrieval_query(make_order())])[0]
    results = _store().search(query_emb, top_k=3)

    assert len(results) == 3
    assert [r.rank for r in results] == [1, 2, 3]                 # rank sequencial
    assert results[0].score >= results[1].score >= results[2].score  # score decrescente
    for r in results:                                            # metadados presentes
        assert r.chunk_id and r.document_id and r.content


def test_empty_index_returns_nothing():
    vazio = InMemoryVectorStore()
    assert vazio.search([0.1] * 256, top_k=5) == []


def test_dedup_by_chunk_id():
    chunk = load_corpus()[0]
    store = InMemoryVectorStore.from_chunks([chunk, dict(chunk)], EMBEDDER)  # duplicado
    results = store.search(EMBEDDER.embed(["qualquer consulta"])[0], top_k=5)
    assert len([r for r in results if r.chunk_id == chunk["chunk_id"]]) == 1


def test_topk_is_configurable():
    query_emb = EMBEDDER.embed([build_retrieval_query(make_order())])[0]
    assert len(_store().search(query_emb, top_k=2)) == 2
    assert len(_store().search(query_emb, top_k=6)) == 6


# ---- pipeline ----------------------------------------------------------------

def _pipeline(top_k=6):
    return VectorPipeline(_store(), EMBEDDER, top_k=top_k)


def test_pipeline_end_to_end_with_mock():
    pipe = _pipeline()
    retrieved_first = pipe.retrieve(make_order(), canonical_routes()).chunk_ids
    result = pipe.run(make_order(), canonical_routes(), _mock(chunk_id=retrieved_first[0]), CONFIG)

    assert result.decision.selected_route == "C"
    assert result.decision.estimated_minutes == 13          # numero do motor
    assert result.engine_validation["route_agreement"] is True
    assert len(result.retrieval) == 6                        # ranking no artefato
    assert result.retrieval[0]["rank"] == 1
    assert "score" in result.retrieval[0]
    assert len(result.decision.citations) == 1              # citacao do chunk recuperado


def test_generator_only_cites_retrieved_chunks():
    """Citar um chunk fora do conjunto recuperado e descartado."""
    pipe = _pipeline(top_k=3)
    retrieved = set(pipe.retrieve(make_order(), canonical_routes()).chunk_ids)
    fora = next(c["chunk_id"] for c in load_corpus() if c["chunk_id"] not in retrieved)

    result = pipe.run(make_order(), canonical_routes(), _mock(chunk_id=fora), CONFIG)
    assert result.decision.citations == []
    assert any("descartadas" in e for e in result.errors)


def test_pipeline_is_reproducible():
    a = _pipeline().run(make_order(), canonical_routes(), _mock(), CONFIG)
    b = _pipeline().run(make_order(), canonical_routes(), _mock(), CONFIG)
    assert a.decision.model_dump_json() == b.decision.model_dump_json()
    assert a.retrieval == b.retrieval                        # ranking deterministico
