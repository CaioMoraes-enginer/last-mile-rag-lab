"""Testes da API (KAN-11).

Usam o TestClient do FastAPI: rodam a app em processo, sem subir servidor nem
rede. Provider real (ollama) e sempre simulado por monkeypatch.
"""
import time

from fastapi.testclient import TestClient

from api.main import app

client = TestClient(app)


def test_health_nao_chama_llm():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_lista_pipelines():
    r = client.get("/v1/pipelines")
    assert set(r.json()["pipelines"]) == {"full_context", "vector", "advanced"}


def test_openapi_disponivel():
    r = client.get("/openapi.json")
    assert r.status_code == 200
    assert "/v1/decide" in r.json()["paths"]


def test_decide_fixture_sucesso():
    r = client.post("/v1/decide", json={"pipeline": "vector", "provider": "mock"})
    body = r.json()
    assert r.status_code == 200
    assert body["source"] == "fixture"
    assert body["decision"]["selected_route"] == "C"      # gabarito do caso canonico
    assert body["run_id"]


def test_os_tres_pipelines_mesmo_contrato():
    for p in ("full_context", "vector", "advanced"):
        r = client.post("/v1/decide", json={"pipeline": p, "provider": "mock"})
        assert r.status_code == 200, p
        body = r.json()
        assert body["pipeline"] == p
        assert "selected_route" in body["decision"]        # mesmo schema (KAN-3)


def test_pipeline_invalido_da_422():
    r = client.post("/v1/decide", json={"pipeline": "foobar", "provider": "mock"})
    assert r.status_code == 422                             # Literal rejeita


def test_modal_invalido_da_422():
    r = client.post("/v1/decide", json={"modal": "HELICOPTERO"})
    assert r.status_code == 422                             # enum do KAN-3 rejeita


def test_provedor_indisponivel_da_504(monkeypatch):
    """Ollama fora do ar (simulado) -> 504 com corpo estavel."""
    from pipelines import embeddings
    import api.factory as factory

    def boom(self, texts):
        raise ConnectionError("ollama offline")

    monkeypatch.setattr(embeddings.OllamaEmbeddingProvider, "embed", boom)
    factory._stores.cache_clear()

    r = client.post("/v1/decide", json={"pipeline": "vector", "provider": "ollama"})
    assert r.status_code == 504
    body = r.json()
    assert body["error"]["code"] == "provider_unavailable"
    assert "run_id" in body
    assert "traceback" not in str(body).lower()            # nao vaza detalhe interno


def test_timeout_da_504(monkeypatch):
    import api.routes.decide as decide_route
    monkeypatch.setattr(decide_route, "TIMEOUT_SECONDS", 0.05)
    monkeypatch.setattr(decide_route, "run_decision", lambda req, run_id: time.sleep(1) or {})
    r = client.post("/v1/decide", json={"pipeline": "vector", "provider": "mock"})
    assert r.status_code == 504
    assert r.json()["error"]["code"] == "provider_unavailable"
