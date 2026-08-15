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
from pipelines.embeddings import HashingEmbeddingProvider, OllamaEmbeddingProvider
from pipelines.full_context import FullContextPipeline
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


def _build_pipeline(args):
    if args.pipeline == "full_context":
        return FullContextPipeline()

    embedder = _build_embedder(args)
    if args.store == "pgvector":
        from db.client import connect
        from db.repository import ChunkRepository
        store = PgVectorStore(ChunkRepository(connect()), embedding_model=args.embedding_model)
    else:
        store = InMemoryVectorStore.from_chunks(load_corpus(), embedder)
    return VectorPipeline(store, embedder, top_k=args.top_k)


def _serialize(result) -> dict:
    """Artefato reproduzivel (sem o texto integral do contexto, so o hash)."""
    return {
        "pipeline": {"name": result.pipeline_name, "version": result.pipeline_version},
        "provenance": result.provenance,
        "decision": json.loads(result.decision.model_dump_json()),
        "telemetry": dataclasses.asdict(result.telemetry),
        "engine_validation": result.engine_validation,
        "retrieval": result.retrieval,
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
    parser.add_argument("--pipeline", choices=["full_context", "vector"], default="full_context")
    parser.add_argument("--provider", choices=["ollama", "mock"], default="ollama")
    parser.add_argument("--model", default="llama3.1", help="modelo do LLM (Ollama)")
    parser.add_argument("--embedding-model", default="nomic-embed-text")
    parser.add_argument("--store", choices=["memory", "pgvector"], default="memory")
    parser.add_argument("--top-k", type=int, default=8)
    parser.add_argument("--host", default="http://localhost:11434")
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--out", default=None, help="caminho do artefato (default: output/<ts>.json)")
    args = parser.parse_args()

    config = PipelineConfig(
        provider_model=args.model, temperature=args.temperature, seed=args.seed,
        prompt_version="vector_v1" if args.pipeline == "vector" else "full_context_v1",
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
