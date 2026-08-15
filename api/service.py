"""Servico de aplicacao (KAN-11): orquestra uma decisao.

Gera/propaga o run_id, monta o provedor, roda o pipeline e mapeia o resultado.
Sem regra de negocio: o motor e os pipelines fazem o trabalho. Erros de infra
sao traduzidos para ApiError (sem vazar detalhes internos).
"""
import json
import logging

from engine.decider import decide
from pipelines.base import PipelineConfig
from pipelines.providers import MockProvider, OllamaProvider

from api.errors import corpus_unavailable, provider_unavailable
from api.factory import build_pipeline, build_scenario

log = logging.getLogger("api")


def _fixture_provider(scenario: dict) -> MockProvider:
    """Provedor simulado (source='fixture'): o motor calcula a rota ouro do cenario."""
    gold = decide(**scenario).selected_route
    payload = {
        "selected_route": gold, "status": "SUCCESS" if gold else "INSUFFICIENT_EVIDENCE",
        "confidence": 0.8, "recommended_action": f"rota {gold}", "citations": [],
    }
    return MockProvider(text=json.dumps(payload, ensure_ascii=False))


def run_decision(req, run_id: str) -> dict:
    """Executa uma decisao e devolve o corpo da resposta."""
    try:
        scenario = build_scenario(req)
        pipeline = build_pipeline(req.pipeline, req.provider, scenario)
    except FileNotFoundError as exc:
        raise corpus_unavailable(f"corpus/indice indisponivel: {exc}")
    except ConnectionError as exc:          # ex.: embeddings do Ollama fora do ar
        raise provider_unavailable(str(exc))

    provider = OllamaProvider() if req.provider == "ollama" else _fixture_provider(scenario)
    config = PipelineConfig(provider_model="llama3", temperature=0.0, seed=42)

    log.info("decide start run_id=%s pipeline=%s provider=%s", run_id, req.pipeline, req.provider)
    try:
        result = pipeline.run(scenario["order"], scenario["routes"], provider, config)
    except ConnectionError as exc:          # LLM fora do ar
        raise provider_unavailable(str(exc))
    log.info("decide done run_id=%s status=%s latency_ms=%.0f",
             run_id, result.decision.status, result.telemetry.latency_ms)

    return {
        "run_id": run_id,
        "pipeline": req.pipeline,
        "source": "live" if req.provider == "ollama" else "fixture",
        "decision": json.loads(result.decision.model_dump_json()),
        "retrieval": result.retrieval,
        "engine_validation": result.engine_validation,
        "telemetry": vars(result.telemetry),
        "errors": result.errors,
    }
