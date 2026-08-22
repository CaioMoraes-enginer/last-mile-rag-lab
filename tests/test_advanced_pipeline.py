"""Testes do pipeline P3 - RAG avancado (KAN-9).

Embeddings deterministicos + indices em memoria + LLM mock: sem Ollama/Postgres.
Cobrem busca lexical de codigos, fusao, cobertura, filtro temporal, ablacoes,
integracao do motor como ferramenta e ausencia de regra especial para escolher C.
"""
import json
from functools import lru_cache

from datetime import datetime

from pipelines.base import PipelineConfig
from pipelines.cases import canonical_routes, canonical_scenario, make_order
from pipelines.context import load_corpus
from pipelines.embeddings import HashingEmbeddingProvider
from pipelines.advanced import AdvancedPipeline, AdvancedConfig
from pipelines.filters import apply_temporal_filter
from pipelines.fusion import FusedChunk
from pipelines.lexical import InMemoryBM25Store
from pipelines.providers import MockProvider
from pipelines.vectorstore import InMemoryVectorStore

CONFIG = PipelineConfig(prompt_version="advanced_v1")
EMBEDDER = HashingEmbeddingProvider(dim=256)


@lru_cache(maxsize=1)
def _corpus():
    return tuple(load_corpus())


def _stores():
    chunks = list(_corpus())
    return InMemoryVectorStore.from_chunks(chunks, EMBEDDER), InMemoryBM25Store(chunks)


def _pipeline(cfg=None, scenario=None):
    vec, lex = _stores()
    return AdvancedPipeline(vec, EMBEDDER, lex, config=cfg or AdvancedConfig(), scenario=scenario)


def _mock(route="C", status="SUCCESS", chunk_id=None):
    citations = [{"document_id": "DOC-04", "chunk_id": chunk_id}] if chunk_id else []
    return MockProvider(text=json.dumps({
        "selected_route": route, "status": status, "confidence": 0.8,
        "recommended_action": "acao", "rejected_routes": [{"route_id": "A", "reason": "bloqueado"}],
        "citations": citations,
    }, ensure_ascii=False))


# ---- componentes --------------------------------------------------------------

def test_bm25_recovers_exact_code():
    _, lex = _stores()
    top = lex.search("ACCESS-Z03-017", top_k=3)
    assert top and all(c.document_id == "DOC-04" for c in top)   # codigo exato -> doc de acesso


def test_temporal_filter_drops_expired():
    vigente = FusedChunk("A", "DOC-03", 1, "1", "txt", 0.1)
    expirado = FusedChunk("B", "DOC-03", 2, "1", "txt", 0.1,
                          effective_to="2026-08-08T18:00:00-03:00")  # antes das 19:15
    mantidos, descartados = apply_temporal_filter(
        [vigente, expirado], datetime.fromisoformat("2026-08-08T19:15:00-03:00"))
    assert [c.chunk_id for c in mantidos] == ["A"]
    assert descartados[0]["chunk_id"] == "B" and descartados[0]["reason"] == "expirado"


# ---- pipeline ----------------------------------------------------------------

def test_hybrid_retrieval_covers_all_facets_and_records_trace():
    pipe = _pipeline(AdvancedConfig(final_k=8, max_per_document=2))
    pipe.retrieve(make_order(), canonical_routes())
    assert pipe._missing == []                                   # cobertura completa
    assert any("lexical:" in r for r in pipe._trace["retrievers"])
    assert any("vetorial:" in r for r in pipe._trace["retrievers"])
    assert pipe.retrieval_records()[0]["contributions"]          # fusao rastreavel


def test_end_to_end_with_tools_and_engine_validation():
    pipe = _pipeline(AdvancedConfig(final_k=8, max_per_document=2))
    retrieved = pipe.retrieve(make_order(), canonical_routes()).chunk_ids
    result = pipe.run(make_order(), canonical_routes(), _mock(chunk_id=retrieved[0]), CONFIG)

    assert result.decision.selected_route == "C"
    assert result.decision.estimated_minutes == 13              # numero do motor (ferramenta)
    assert result.engine_validation["route_agreement"] is True
    nomes = [t["name"] for t in result.trace["tool_calls"]]
    assert "gold_decision" in nomes and "validate_route" in nomes   # motor chamado como ferramenta


def test_coverage_gate_triggers_on_missing_document():
    """Documento ausente do corpus (evidencia inexistente) -> insuficiencia, nao alucinacao."""
    sem_malha = [c for c in _corpus() if c["document_id"] != "DOC-02"]  # remove a malha (DOC-02)
    vec = InMemoryVectorStore.from_chunks(sem_malha, EMBEDDER)
    lex = InMemoryBM25Store(sem_malha)
    pipe = AdvancedPipeline(vec, EMBEDDER, lex, config=AdvancedConfig(final_k=8, max_per_document=2))
    result = pipe.run(make_order(), canonical_routes(), _mock(), CONFIG)
    assert result.decision.status == "INSUFFICIENT_EVIDENCE"
    assert "malha" in result.trace["missing_facets"]


def test_ablation_no_lexical_removes_lexical_retrievers():
    pipe = _pipeline(AdvancedConfig(use_lexical=False))
    pipe.retrieve(make_order(), canonical_routes())
    assert all("lexical:" not in r for r in pipe._trace["retrievers"])


def test_ablation_no_tools_leaves_numbers_unvalidated():
    pipe = _pipeline(AdvancedConfig(use_tools=False, final_k=8, max_per_document=2))
    result = pipe.run(make_order(), canonical_routes(), _mock(), CONFIG)
    assert result.decision.estimated_minutes is None            # sem motor, sem numero
    assert any("ablacao" in e for e in result.errors)


def test_no_hardcoded_c_counterfactual():
    """Modal MOTO invalida a rota C; se o LLM insistir em C, o motor reprova."""
    s = canonical_scenario()
    s["order"] = make_order(modal="MOTO")
    pipe = _pipeline(AdvancedConfig(final_k=8, max_per_document=2), scenario=s)
    result = pipe.run(make_order(modal="MOTO"), canonical_routes(), _mock(route="C"), CONFIG)

    assert result.engine_validation["gold_route"] == "B"            # ouro NAO e C aqui
    assert result.decision.valid is False                           # motor reprova C p/ MOTO
    assert result.decision.status == "ERROR"


def test_engine_validation_uses_shared_gold_contract():
    """O P3 deve usar a MESMA chave `gold_route` dos demais pipelines (KAN-17).

    Regressao: o P3 gerava `gold_selected_route`, quebrando a API e a interface
    (KAN-12), que leem `gold_route`. As chaves gold_* devem casar com o contrato
    compartilhado (decision._gold_record).
    """
    from domain.decision import DecisionResponse
    from pipelines.decision import _gold_record

    shared_keys = set(_gold_record(DecisionResponse(
        order_id="ORD-042", decision_timestamp="2026-08-08T19:15:00-03:00",
    )))
    result = _pipeline(AdvancedConfig(final_k=8, max_per_document=2)).run(
        make_order(), canonical_routes(), _mock(), CONFIG)
    ev = result.engine_validation
    assert shared_keys <= set(ev)                 # todas as chaves gold_* do contrato
    assert "gold_route" in ev
    assert "gold_selected_route" not in ev        # a chave antiga/errada nao volta


def test_reproducible():
    a = _pipeline(AdvancedConfig(final_k=8, max_per_document=2)).run(
        make_order(), canonical_routes(), _mock(), CONFIG)
    b = _pipeline(AdvancedConfig(final_k=8, max_per_document=2)).run(
        make_order(), canonical_routes(), _mock(), CONFIG)
    assert a.decision.model_dump_json() == b.decision.model_dump_json()
    assert a.retrieval == b.retrieval
