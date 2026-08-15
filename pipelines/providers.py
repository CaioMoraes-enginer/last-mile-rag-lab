"""Adaptadores de provedor de LLM (KAN-7).

Duas implementacoes do Protocol LLMProvider:

  - OllamaProvider: chamada real a um modelo local via API do Ollama
    (http://localhost:11434). Gratis, offline e reprodutivel — coerente com o lab.
  - MockProvider: devolve um texto fixo, sem rede. E o que os testes usam, para
    que a suite NAO dependa de uma chamada real ao provedor (criterio de aceite).

Usa apenas a stdlib (urllib) — sem dependencia nova.
"""
import json
import time
import urllib.error
import urllib.request

from pipelines.base import LLMResponse, PipelineConfig


class OllamaProvider:
    """Provedor real: fala com o servidor local do Ollama.

    Requer o Ollama rodando e o modelo baixado (`ollama pull <modelo>`). Fixa
    temperatura e seed vindos da config para tornar a geracao reprodutivel e pede
    saida em JSON (`format=json`).
    """

    def __init__(self, host: str = "http://localhost:11434", timeout: float = 120.0):
        self.host = host.rstrip("/")
        self.timeout = timeout

    def complete(self, prompt: str, config: PipelineConfig) -> LLMResponse:
        payload = {
            "model": config.provider_model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
            "format": "json",
            "options": {
                "temperature": config.temperature,
                "seed": config.seed,
                "num_predict": config.max_output_tokens,
            },
        }
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            f"{self.host}/api/chat",
            data=data,
            headers={"Content-Type": "application/json"},
        )
        inicio = time.perf_counter()
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                body = json.loads(resp.read().decode("utf-8"))
        except urllib.error.URLError as exc:
            raise ConnectionError(
                f"Falha ao contatar o Ollama em {self.host}. O servidor esta rodando "
                f"e o modelo '{config.provider_model}' foi baixado? Detalhe: {exc}"
            ) from exc
        latency_ms = (time.perf_counter() - inicio) * 1000

        return LLMResponse(
            text=body.get("message", {}).get("content", ""),
            model=body.get("model", config.provider_model),
            input_tokens=body.get("prompt_eval_count", 0),
            output_tokens=body.get("eval_count", 0),
            latency_ms=latency_ms,
            truncated=body.get("done_reason") == "length",
        )


class MockProvider:
    """Provedor simulado: devolve um texto pre-definido. Nao usa rede.

    Serve aos testes (respostas deterministicas) e a demonstracoes offline. Pode
    simular truncamento e contagem de tokens para exercitar a telemetria.
    """

    def __init__(
        self, text: str, *,
        input_tokens: int = 1000, output_tokens: int = 120,
        latency_ms: float = 0.0, truncated: bool = False,
        model: str = "mock",
    ):
        self._text = text
        self._input_tokens = input_tokens
        self._output_tokens = output_tokens
        self._latency_ms = latency_ms
        self._truncated = truncated
        self._model = model

    def complete(self, prompt: str, config: PipelineConfig) -> LLMResponse:
        return LLMResponse(
            text=self._text,
            model=self._model,
            input_tokens=self._input_tokens,
            output_tokens=self._output_tokens,
            latency_ms=self._latency_ms,
            truncated=self._truncated,
        )
