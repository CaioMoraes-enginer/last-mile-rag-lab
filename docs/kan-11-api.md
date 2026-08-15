# API versionada (KAN-11)

> Entregável da tarefa **[KAN-11 / EP01-T10]**. Fronteira HTTP fina sobre os três
> pipelines. A interface (KAN-12) e o Arduino (KAN-13) consomem esta API **sem
> importar código interno**.

## Arquitetura

```
POST /v1/decide
   → routes/decide.py   (run_id, timeout, executor)
   → service.py         (orquestra: monta cenário, provedor, roda, mapeia)
   → factory.py         (fábrica de pipelines + índices em cache)
   → pipelines/…        (KAN-7/8/9)  +  engine/…  (fonte de verdade)
```

A API **não duplica regra** nenhuma: escolhe o pipeline por nome, chama o `.run()`
e mapeia o `PipelineResult` para JSON.

## Endpoints

| Método | Rota | O que faz |
|---|---|---|
| GET | `/health` | Saúde — **não chama LLM** nem constrói índice |
| GET | `/v1/pipelines` | Lista os pipelines disponíveis |
| POST | `/v1/decide` | Roda uma decisão e devolve o contrato + evidências + telemetria |
| GET | `/openapi.json`, `/docs` | Especificação OpenAPI + Swagger UI (automáticos) |

### `POST /v1/decide` — corpo

```json
{ "pipeline": "advanced", "provider": "mock",
  "modal": "BICICLETA", "state": "DISPATCHED",
  "decision_at": null, "promised_at": null }
```

`pipeline` ∈ `full_context | vector | advanced` · `provider` ∈ `mock | ollama`.
`modal`/`state` e overrides opcionais permitem contrafactuais (o gabarito muda).

### Resposta (resumo)

```json
{ "run_id": "…", "pipeline": "advanced", "source": "fixture",
  "decision": { "selected_route": "C", "valid": true, "estimated_minutes": 13, … },
  "retrieval": [ { "rank": 1, "rrf_score": …, "chunk_id": "…", "contributions": {…} } ],
  "telemetry": { "latency_ms": …, "input_tokens": …, "context_chars": … },
  "engine_validation": { "gold_selected_route": "C", "route_agreement": true },
  "errors": [] }
```

`source` deixa **explícito** se veio de `fixture` (mock) ou `live` (Ollama).

## Erros

Corpo estável, **sem stack trace nem credenciais**:

```json
{ "error": { "code": "provider_unavailable", "message": "…" }, "run_id": "…" }
```

| Situação | HTTP | `code` |
|---|--:|---|
| Entrada inválida (enum/Literal) | 422 | *(validação do FastAPI)* |
| Pipeline inexistente | 404 | `pipeline_not_found` |
| Corpus/índice indisponível | 503 | `corpus_unavailable` |
| Conflito de evidências | 409 | `evidence_conflict` |
| Timeout / provedor fora | 504 | `provider_unavailable` |
| Saída do modelo inválida | 502 | `model_output_invalid` |

> **Evidência insuficiente = 200** (com `status: INSUFFICIENT_EVIDENCE`) — é um
> resultado válido do pipeline (abstenção), não um erro de infraestrutura.

## Como rodar

```bash
.venv\Scripts\python.exe -m uvicorn api.main:app --reload --port 8000
```

Exemplos executáveis:

```bash
curl http://localhost:8000/health

curl -X POST http://localhost:8000/v1/decide \
  -H "Content-Type: application/json" \
  -d '{"pipeline":"advanced","provider":"mock"}'

# real (Ollama local no ar):
curl -X POST http://localhost:8000/v1/decide \
  -H "Content-Type: application/json" \
  -d '{"pipeline":"vector","provider":"ollama"}'
```

Abra `http://localhost:8000/docs` para a UI do Swagger.

## Configuração (ambiente)

| Variável | Default | Papel |
|---|---|---|
| `API_TIMEOUT_S` | `180` | timeout por requisição de decisão |
| `API_CORS_ORIGINS` | `localhost:5173,localhost:3000` | origens liberadas p/ a UI local |

## Observabilidade

Cada requisição gera um `run_id` (uuid) que aparece **na resposta, nos logs e no
corpo de erro** — o fio que conecta tudo na auditoria. Logs estruturados com
`run_id`, pipeline, status e latência.

## Testes

`tests/test_api.py` (TestClient, sem rede): health sem LLM, OpenAPI, os 3 pipelines
no mesmo contrato, decisão em fixture, pipeline/modal inválidos (422), provedor
indisponível (504) e timeout (504). Suíte total: **49 passed**.

## Limitações (v1)

- Sem autenticação/multiusuário (fora de escopo do card).
- Endpoint de benchmark (KAN-10) não exposto ainda — a UI pode chamar `eval.run`
  localmente; expor via `/v1/benchmark` é evolução simples.
