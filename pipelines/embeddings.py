"""Provedores de embedding (KAN-8).

Abstrai a geracao de vetores atras de um Protocol, do mesmo jeito que o LLM:

  - OllamaEmbeddingProvider: modelo real de embedding via Ollama (padrao
    nomic-embed-text, 768 dimensoes — casa com a coluna vector(768) do KAN-15).
  - HashingEmbeddingProvider: embedding DETERMINISTICO (hashing trick) para os
    testes. Nao usa rede e nao depende de PYTHONHASHSEED (usa hashlib), entao a
    mesma frase gera sempre o mesmo vetor. Chunks que compartilham termos com a
    consulta ficam mais proximos — suficiente para exercitar ordenacao e top-k.

So a stdlib (urllib/hashlib/math) — sem dependencia nova.
"""
import hashlib
import json
import math
import re
import urllib.error
import urllib.request

_TOKEN_RE = re.compile(r"[a-z0-9\-]+")


def _l2_normalize(vec: list[float]) -> list[float]:
    norma = math.sqrt(sum(x * x for x in vec))
    if norma == 0:
        return vec
    return [x / norma for x in vec]


class HashingEmbeddingProvider:
    """Embedding deterministico por hashing de tokens (para testes/offline)."""

    def __init__(self, dim: int = 768):
        self.dim = dim
        self.model = f"hashing-{dim}d"

    def _embed_one(self, text: str) -> list[float]:
        vec = [0.0] * self.dim
        for token in _TOKEN_RE.findall(text.lower()):
            h = int(hashlib.md5(token.encode("utf-8")).hexdigest(), 16)
            idx = h % self.dim
            sinal = 1.0 if (h // self.dim) % 2 == 0 else -1.0
            vec[idx] += sinal
        return _l2_normalize(vec)

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [self._embed_one(t) for t in texts]


class OllamaEmbeddingProvider:
    """Embedding real via API do Ollama (local, gratis)."""

    def __init__(
        self, model: str = "nomic-embed-text",
        host: str = "http://localhost:11434", timeout: float = 120.0,
    ):
        self.model = model
        self.host = host.rstrip("/")
        self.timeout = timeout

    def embed(self, texts: list[str]) -> list[list[float]]:
        payload = {"model": self.model, "input": texts}
        req = urllib.request.Request(
            f"{self.host}/api/embed",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                body = json.loads(resp.read().decode("utf-8"))
        except urllib.error.URLError as exc:
            raise ConnectionError(
                f"Falha ao gerar embeddings no Ollama em {self.host}. Servidor no ar e "
                f"modelo '{self.model}' baixado (ollama pull {self.model})? Detalhe: {exc}"
            ) from exc
        return body.get("embeddings", [])
