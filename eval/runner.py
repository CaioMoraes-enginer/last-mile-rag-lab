"""Runner do harness (KAN-10).

Executa os tres pipelines (e, opcionalmente, ablacoes do avancado) pela MESMA
interface, sobre os MESMOS casos, e coleta (resultado, score). Justica
experimental: mesma entrada, mesmo contrato, mesmo corpus, seeds registradas;
falhas contam no denominador (nao sao removidas).

Modos:
  - fixture (mock): respostas deterministicas, sem API — testa o avaliador.
  - ollama: LLM e embeddings reais, locais.
"""
import json
from dataclasses import dataclass, field

from eval.cases import EvalCase, build_cases
from eval.rubric import CaseScore, evaluate
from pipelines.advanced import AdvancedConfig, AdvancedPipeline
from pipelines.base import PipelineConfig
from pipelines.context import load_corpus
from pipelines.embeddings import HashingEmbeddingProvider, OllamaEmbeddingProvider
from pipelines.full_context import FullContextPipeline
from pipelines.lexical import InMemoryBM25Store
from pipelines.providers import MockProvider, OllamaProvider
from pipelines.vector import VectorPipeline
from pipelines.vectorstore import InMemoryVectorStore


@dataclass
class RunConfig:
    provider: str = "mock"                 # "mock" | "ollama"
    model: str = "llama3"
    embedding_model: str = "nomic-embed-text"
    host: str = "http://localhost:11434"
    n_repeats: int = 1
    include_ablations: bool = False
    top_k: int = 8
    final_k: int = 8
    max_per_doc: int = 2
    seed: int = 42


@dataclass
class _Ctx:
    embedder: object
    vector_store: object
    lexical_store: object
    cfg: RunConfig


@dataclass
class RunRecord:
    case_id: str
    pipeline: str
    repeat: int
    score: CaseScore
    engine_validation: dict
    provenance: dict


@dataclass
class HarnessOutput:
    config: dict
    records: list[RunRecord] = field(default_factory=list)


def _build_ctx(cfg: RunConfig) -> _Ctx:
    if cfg.provider == "ollama":
        embedder = OllamaEmbeddingProvider(cfg.embedding_model, cfg.host)
    else:
        embedder = HashingEmbeddingProvider()
    chunks = load_corpus()
    return _Ctx(embedder, InMemoryVectorStore.from_chunks(chunks, embedder),
                InMemoryBM25Store(chunks), cfg)


def _pipelines(case: EvalCase, ctx: _Ctx) -> dict:
    cfg = ctx.cfg
    pack = {
        "full_context": FullContextPipeline(scenario=case.scenario),
        "vector": VectorPipeline(ctx.vector_store, ctx.embedder, top_k=cfg.top_k, scenario=case.scenario),
        "advanced": AdvancedPipeline(
            ctx.vector_store, ctx.embedder, ctx.lexical_store,
            config=AdvancedConfig(final_k=cfg.final_k, max_per_document=cfg.max_per_doc),
            scenario=case.scenario),
    }
    if cfg.include_ablations:
        for flag in ("use_lexical", "use_reranker", "use_tools"):
            ac = AdvancedConfig(final_k=cfg.final_k, max_per_document=cfg.max_per_doc, **{flag: False})
            pack[f"advanced_no_{flag[4:]}"] = AdvancedPipeline(
                ctx.vector_store, ctx.embedder, ctx.lexical_store, config=ac, scenario=case.scenario)
    return pack


def _fixture_provider(pipeline, case: EvalCase) -> MockProvider:
    """Resposta fixa e DETERMINISTICA: escolhe o gabarito e cita um chunk recuperado.

    So para exercitar o harness/avaliador sem API — nao mede qualidade real.
    """
    gold_route = case.gold.selected_route
    if gold_route is None:
        payload = {"selected_route": None, "status": "INSUFFICIENT_EVIDENCE",
                   "confidence": 0.5, "recommended_action": "abster", "citations": []}
        return MockProvider(text=json.dumps(payload, ensure_ascii=False))
    # descobre um chunk realmente recuperado por este pipeline para citar
    bundle = pipeline.retrieve(case.order, case.routes)
    cited = bundle.chunk_ids[0] if bundle.chunk_ids else None
    citations = [{"document_id": "DOC-XX", "chunk_id": cited}] if cited else []
    payload = {
        "selected_route": gold_route, "status": "SUCCESS", "confidence": 0.8,
        "recommended_action": f"rota {gold_route}",
        "rejected_routes": [], "citations": citations,
    }
    return MockProvider(text=json.dumps(payload, ensure_ascii=False))


def run_harness(cfg: RunConfig | None = None, cases: list[EvalCase] | None = None) -> HarnessOutput:
    cfg = cfg or RunConfig()
    cases = cases or build_cases()
    ctx = _build_ctx(cfg)
    pconfig = PipelineConfig(provider_model=cfg.model, temperature=0.0, seed=cfg.seed)

    out = HarnessOutput(config={
        "provider": cfg.provider, "model": cfg.model, "embedding_model": cfg.embedding_model,
        "n_repeats": cfg.n_repeats, "seed": cfg.seed, "include_ablations": cfg.include_ablations,
    })

    for case in cases:
        for name, pipeline in _pipelines(case, ctx).items():
            for rep in range(cfg.n_repeats):
                if cfg.provider == "ollama":
                    provider = OllamaProvider(host=cfg.host)
                else:
                    provider = _fixture_provider(pipeline, case)
                result = pipeline.run(case.order, case.routes, provider, pconfig)
                score = evaluate(case, result, name)
                out.records.append(RunRecord(
                    case_id=case.case_id, pipeline=name, repeat=rep, score=score,
                    engine_validation=result.engine_validation or {},
                    provenance={k: result.provenance.get(k) for k in ("model", "seed", "prompt_version", "corpus_hash")},
                ))
    return out
