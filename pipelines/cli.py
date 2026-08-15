"""Ponto de entrada dos pipelines de decisao (KAN-7/8).

Roda o caso canonico ORD-042 por um dos pipelines e persiste um artefato
reproduzivel (config + proveniencia + ranking + decisao + telemetria), sem segredos.

Exemplos (da raiz do projeto):
    python -m pipelines.cli --pipeline full_context --provider mock
    python -m pipelines.cli --pipeline vector --provider mock            # offline
    python -m pipelines.cli --pipeline vector --provider ollama --top-k 8
    python -m pipelines.cli --pipeline vector --provider ollama --store pgvector
"""
import argparse
import dataclasses
import json
from datetime import datetime
from pathlib import Path

from pipelines.base import PipelineConfig
from pipelines.cases import canonical_routes, make_order
from pipelines.context import load_corpus
from pipelines.advanced import AdvancedConfig, AdvancedPipeline
from pipelines.embeddings import HashingEmbeddingProvider, OllamaEmbeddingProvider
from pipelines.full_context import FullContextPipeline
from pipelines.lexical import InMemoryBM25Store, PgLexicalStore
from pipelines.providers import MockProvider, OllamaProvider
from pipelines.vector import VectorPipeline
from pipelines.vectorstore import InMemoryVectorStore, PgVectorStore

# Resposta simulada valida para o modo offline (cita um chunk real do DOC-04).
_MOCK_JSON = json.dumps({
    "selected_route": "C",
    "status": "SUCCESS",
    "confidence": 0.8,
    "recommended_action": "Seguir pela rota C pelo corredor controlado SG-CE.",
    "rejected_routes": [
        {"route_id": "A", "reason": "SG-BD bloqueado pelo incidente INC-Z03-042"},
        {"route_id": "B", "reason": "Desvio arterial com penalidade de chuva"},
    ],
    "citations": [{"document_id": "DOC-04", "chunk_id": "DOC-04-P01-C01"}],
}, ensure_ascii=False)

OUTPUT_DIR = Path("output")


def _build_llm(args):
    if args.provider == "ollama":
        return OllamaProvider(host=args.host)
    return MockProvider(text=_MOCK_JSON)


def _build_embedder(args):
    if args.provider == "ollama":
        return OllamaEmbeddingProvider(model=args.embedding_model, host=args.host)
    return HashingEmbeddingProvider()


def _build_stores(args, embedder):
    """(vector_store, lexical_store) conforme o backend escolhido."""
    if args.store == "pgvector":
        from db.client import connect
        from db.repository import ChunkRepository
        repo = ChunkRepository(connect())
        return PgVectorStore(repo, embedding_model=args.embedding_model), PgLexicalStore(repo)
    chunks = load_corpus()
    return InMemoryVectorStore.from_chunks(chunks, embedder), InMemoryBM25Store(chunks)


def _build_pipeline(args):
    if args.pipeline == "full_context":
        return FullContextPipeline()

    embedder = _build_embedder(args)
    vector_store, lexical_store = _build_stores(args, embedder)

    if args.pipeline == "vector":
        return VectorPipeline(vector_store, embedder, top_k=args.top_k)

    cfg = AdvancedConfig(
        use_lexical=not args.no_lexical, use_filters=not args.no_filters,
        use_reranker=not args.no_reranker, use_tools=not args.no_tools,
        top_k_retriever=args.top_k, final_k=args.final_k, max_per_document=args.max_per_doc,
    )
    return AdvancedPipeline(vector_store, embedder, lexical_store, config=cfg)


def _serialize(result) -> dict:
    """Artefato reproduzivel (sem o texto integral do contexto, so o hash)."""
    return {
        "pipeline": {"name": result.pipeline_name, "version": result.pipeline_version},
        "provenance": result.provenance,
        "decision": json.loads(result.decision.model_dump_json()),
        "telemetry": dataclasses.asdict(result.telemetry),
        "engine_validation": result.engine_validation,
        "retrieval": result.retrieval,
        "trace": result.trace,
        "context_summary": {
            "chunk_count": len(result.context.chunk_ids),
            "char_count": result.context.char_count,
            "corpus_hash": result.context.corpus_hash,
        },
        "repair_applied": result.repair_applied,
        "errors": result.errors,
        "llm_raw": result.llm_raw,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Pipelines de decisao (KAN-7/8)")
    parser.add_argument("--pipeline", choices=["full_context", "vector", "advanced"], default="full_context")
    parser.add_argument("--provider", choices=["ollama", "mock"], default="ollama")
    parser.add_argument("--model", default="llama3.1", help="modelo do LLM (Ollama)")
    parser.add_argument("--embedding-model", default="nomic-embed-text")
    parser.add_argument("--store", choices=["memory", "pgvector"], default="memory")
    parser.add_argument("--top-k", type=int, default=8, help="candidatos por recuperador (advanced) / top-k (vector)")
    parser.add_argument("--final-k", type=int, default=8, help="chunks no contexto (advanced)")
    parser.add_argument("--max-per-doc", type=int, default=3, help="cap de diversificacao (advanced)")
    # ablacoes do pipeline avancado
    parser.add_argument("--no-lexical", action="store_true")
    parser.add_argument("--no-filters", action="store_true")
    parser.add_argument("--no-reranker", action="store_true")
    parser.add_argument("--no-tools", action="store_true")
    parser.add_argument("--host", default="http://localhost:11434")
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--out", default=None, help="caminho do artefato (default: output/<ts>.json)")
    args = parser.parse_args()

    config = PipelineConfig(
        provider_model=args.model, temperature=args.temperature, seed=args.seed,
        prompt_version={"vector": "vector_v1", "advanced": "advanced_v1"}.get(
            args.pipeline, "full_context_v1"),
    )
    pipeline = _build_pipeline(args)
    result = pipeline.run(make_order(), canonical_routes(), _build_llm(args), config)

    artifact = _serialize(result)
    print(json.dumps(artifact["decision"], ensure_ascii=False, indent=2))
    if result.retrieval:
        print("\nranking recuperado:", json.dumps(result.retrieval, ensure_ascii=False))
    print("\nvalidacao do motor:", json.dumps(result.engine_validation, ensure_ascii=False))
    if result.errors:
        print("erros:", result.errors)

    OUTPUT_DIR.mkdir(exist_ok=True)
    out_path = Path(args.out) if args.out else OUTPUT_DIR / f"{args.pipeline}_{_stamp()}.json"
    out_path.write_text(json.dumps(artifact, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nartefato -> {out_path}")
    return 0


def _stamp() -> str:
    return datetime.now().strftime("%Y%m%dT%H%M%S")


if __name__ == "__main__":
    raise SystemExit(main())
