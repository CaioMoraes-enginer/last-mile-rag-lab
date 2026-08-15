"""Ponto de entrada do pipeline P1 (KAN-7).

Roda o caso canonico ORD-042 pelo pipeline de contexto completo e persiste um
artefato reproduzivel (config + proveniencia + decisao + telemetria), sem segredos.

Exemplos (da raiz do projeto):
    python -m pipelines.cli --provider mock            # offline, deterministico
    python -m pipelines.cli --provider ollama --model llama3.1
"""
import argparse
import dataclasses
import json
from datetime import datetime
from pathlib import Path

from pipelines.base import PipelineConfig
from pipelines.cases import canonical_routes, make_order
from pipelines.full_context import FullContextPipeline
from pipelines.providers import MockProvider, OllamaProvider

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


def _build_provider(args):
    if args.provider == "ollama":
        return OllamaProvider(host=args.host)
    return MockProvider(text=_MOCK_JSON)


def _serialize(result) -> dict:
    """Artefato reproduzivel (sem o texto integral do contexto, so o hash)."""
    return {
        "pipeline": {"name": result.pipeline_name, "version": result.pipeline_version},
        "provenance": result.provenance,
        "decision": json.loads(result.decision.model_dump_json()),
        "telemetry": dataclasses.asdict(result.telemetry),
        "engine_validation": result.engine_validation,
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
    parser = argparse.ArgumentParser(description="Pipeline P1 - contexto completo (KAN-7)")
    parser.add_argument("--provider", choices=["ollama", "mock"], default="ollama")
    parser.add_argument("--model", default="llama3.1", help="modelo do Ollama")
    parser.add_argument("--host", default="http://localhost:11434")
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--out", default=None, help="caminho do artefato (default: output/<ts>.json)")
    args = parser.parse_args()

    config = PipelineConfig(
        provider_model=args.model, temperature=args.temperature, seed=args.seed,
    )
    provider = _build_provider(args)
    result = FullContextPipeline().run(make_order(), canonical_routes(), provider, config)

    artifact = _serialize(result)
    print(json.dumps(artifact["decision"], ensure_ascii=False, indent=2))
    print("\nvalidacao do motor:", json.dumps(result.engine_validation, ensure_ascii=False))
    if result.errors:
        print("erros:", result.errors)

    OUTPUT_DIR.mkdir(exist_ok=True)
    out_path = Path(args.out) if args.out else OUTPUT_DIR / f"full_context_{_stamp()}.json"
    out_path.write_text(json.dumps(artifact, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nartefato -> {out_path}")
    return 0


def _stamp() -> str:
    return datetime.now().strftime("%Y%m%dT%H%M%S")


if __name__ == "__main__":
    raise SystemExit(main())
