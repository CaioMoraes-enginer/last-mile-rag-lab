"""Testes do pipeline P1 - contexto completo (KAN-7).

Usam SEMPRE o MockProvider: a suite nao depende de chamada real ao LLM (criterio
de aceite). Cobrem o caminho feliz, a validacao pelo motor, a resolucao de
citacoes e o tratamento de falhas sem mascara-las.
"""
import json

from engine.decider import decide
from pipelines.base import PipelineConfig
from pipelines.cases import canonical_routes, canonical_scenario, make_order
from pipelines.context import load_corpus
from pipelines.full_context import FullContextPipeline
from pipelines.providers import MockProvider

CONFIG = PipelineConfig()


def _run(mock_text: str, **mock_kwargs):
    pipeline = FullContextPipeline()
    provider = MockProvider(text=mock_text, **mock_kwargs)
    return pipeline.run(make_order(), canonical_routes(), provider, CONFIG)


def _mock_decision(route="C", status="SUCCESS", chunk_id="DOC-04-P01-C01", confidence=0.8):
    return json.dumps({
        "selected_route": route,
        "status": status,
        "confidence": confidence,
        "recommended_action": "acao de teste",
        "rejected_routes": [{"route_id": "A", "reason": "bloqueado"}],
        "citations": [{"document_id": "DOC-04", "chunk_id": chunk_id}],
    }, ensure_ascii=False)


def test_canonical_scenario_matches_gold():
    """Guarda de deriva: o caso canonico ainda produz a resposta ouro (rota C, 13 min)."""
    gold = decide(**canonical_scenario())
    assert gold.selected_route == "C"
    assert gold.valid is True
    assert gold.estimated_minutes == 13


def test_pipeline_selects_route_and_engine_validates():
    """Caminho feliz: LLM escolhe C, motor confirma e preenche os numeros."""
    real_chunk = load_corpus()[0]["chunk_id"]
    result = _run(_mock_decision(chunk_id=real_chunk))

    assert result.decision.selected_route == "C"
    assert result.decision.valid is True
    assert result.decision.estimated_minutes == 13         # numero do motor, nao do LLM
    assert result.decision.risk_class == "AT_RISK"
    assert result.engine_validation["route_agreement"] is True
    assert result.telemetry.input_tokens > 0               # telemetria coletada
    assert result.telemetry.context_chars > 0
    assert len(result.decision.citations) == 1             # citacao resolvida


def test_citation_to_unknown_chunk_is_dropped():
    """Citacao para chunk inexistente e descartada e registrada como erro."""
    result = _run(_mock_decision(chunk_id="DOC-99-P99-C99"))
    assert result.decision.citations == []
    assert any("descartadas" in e for e in result.errors)


def test_invalid_json_is_not_masked():
    """Resposta ilegivel -> status ERROR e erro registrado (falha nao mascarada)."""
    result = _run("Desculpe, nao consigo responder isso.")
    assert result.decision.status == "ERROR"
    assert result.errors
    assert result.decision.selected_route is None


def test_abstention_when_llm_declares_insufficient():
    """LLM declara evidencia insuficiente -> abstencao propagada."""
    result = _run(_mock_decision(route=None, status="INSUFFICIENT_EVIDENCE"))
    assert result.decision.status == "INSUFFICIENT_EVIDENCE"
    assert result.decision.selected_route is None
    assert result.decision.valid is False


def test_nonexistent_route_is_error():
    """LLM escolhe uma rota que nao existe -> ERROR, sem inventar validacao."""
    result = _run(_mock_decision(route="Z"))
    assert result.decision.status == "ERROR"
    assert any("inexistente" in e for e in result.errors)


def test_repair_extracts_json_from_prose():
    """Reparo unico: JSON cercado por texto ainda e recuperado e sinalizado."""
    texto = "Claro! Aqui esta a analise:\n" + _mock_decision() + "\nEspero ter ajudado."
    result = _run(texto)
    assert result.repair_applied is True
    assert result.decision.selected_route == "C"


def test_truncation_is_reported():
    """Resposta truncada no limite de tokens vira erro registrado."""
    result = _run(_mock_decision(), truncated=True)
    assert any("truncada" in e for e in result.errors)


def test_result_is_reproducible():
    """Mesma entrada + mesmo mock -> mesma decisao (determinismo)."""
    a = _run(_mock_decision())
    b = _run(_mock_decision())
    assert a.decision.model_dump_json() == b.decision.model_dump_json()
