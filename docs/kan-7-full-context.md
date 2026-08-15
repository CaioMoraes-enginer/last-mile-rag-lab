# Pipeline P1 — Contexto completo sem recuperação (KAN-7)

> Entregável da tarefa **[KAN-7 / EP01-T06]**. Baseline de força bruta dos três
> pipelines da v1: manda o corpus inteiro ao LLM, sem etapa de recuperação.

## Papel no experimento

O P1 é o **grupo de controle**. Sem seleção de contexto, ele estabelece a régua de
qualidade, latência, custo e tokens de "mandar tudo". Os pipelines com recuperação
(P2 vetorial — KAN-8; P3 avançado — KAN-9) serão comparados contra ele no harness
(KAN-10). Todos produzem o **mesmo contrato** (`DecisionResponse`); só muda *como
recuperam* o contexto.

## Arquitetura

```
pedido ORD-042 + rotas A/B/C
        │
        ▼
FullContextPipeline.run()               (template em pipelines/base.py)
        │
        ├─ retrieve()      → todos os chunks aprovados (pipelines/context.py)
        ├─ build_prompt()  → prompt versionado (pipelines/prompts.py)
        ├─ provider.complete() → LLM (Ollama real ou Mock)  (pipelines/providers.py)
        └─ parse_and_validate() → JSON → contrato + validação do motor
        ▼
PipelineResult (decisão + telemetria + proveniência + validação do motor)
```

### Fronteira LLM × motor (escopo §6)

- O **LLM sugere** a rota, justifica e redige as citações.
- O **motor determinístico (KAN-4) é a fonte de verdade**: valida a rota escolhida
  e calcula `estimated_minutes`, `slack_minutes` e `risk_class`. O LLM nunca
  calcula números nem sobrescreve o motor.
- A validação do motor é registrada **à parte** (`engine_validation`), preservando
  a interpretação experimental (requisito 9 do card).

### Anti-vazamento (escopo §11)

O contexto usa **somente** os chunks de `data/corpus/chunks.jsonl` cujos documentos
constam no `manifest.json`. `README`, `docs/`, o escopo e os testes-ouro **nunca**
entram no índice. As evidências estruturadas do motor (incidentes, política, etc.)
**não** vão ao LLM — ele precisa derivá-las do texto.

### Anti-overfitting

Não há nenhuma lógica que force a rota "C". A decisão emerge do motor sobre o caso
(`pipelines/cases.py`); um teste de guarda de deriva garante que o caso canônico
continua batendo com a resposta ouro do KAN-5.

## Como rodar

### Offline (mock determinístico) — não precisa de nada instalado

```bash
python -m pipelines.cli --provider mock
```

### Real (Ollama local, grátis)

Pré-requisitos: [Ollama](https://ollama.com) instalado, servidor no ar e um modelo baixado.

```bash
ollama serve            # inicia o servidor (se ainda não estiver rodando)
ollama pull llama3.1    # baixa o modelo (uma vez)
python -m pipelines.cli --provider ollama --model llama3.1
```

Cada execução imprime a decisão e grava um artefato reproduzível em
`output/full_context_<timestamp>.json` (config + proveniência + decisão +
telemetria + validação do motor + resposta crua). Sem segredos (Ollama é local).

## Configuração e reprodutibilidade

`PipelineConfig` (em `pipelines/base.py`) versiona os parâmetros:

| Parâmetro | Default | Papel |
|---|---|---|
| `provider_model` | `llama3.1` | modelo do Ollama |
| `temperature` | `0.0` | mínima variabilidade |
| `seed` | `42` | semente registrada na proveniência |
| `max_output_tokens` | `1536` | teto da resposta (detecta truncamento) |
| `prompt_version` | `full_context_v1` | versão do prompt registrada |

## Tratamento de falhas (sem mascarar)

| Situação | Comportamento |
|---|---|
| JSON inválido/ausente | `status = ERROR`, erro registrado |
| JSON cercado por texto | reparo único (recorta o `{...}`), `repair_applied = True` |
| Resposta truncada | erro registrado (`truncada`) |
| Rota inexistente | `status = ERROR`, erro registrado |
| Rota proposta é inválida | `status = ERROR` + motivo do motor |
| Citação para chunk inexistente | descartada + erro registrado |
| LLM declara `INSUFFICIENT_EVIDENCE` | abstenção propagada |

## Limitações (v1)

- **Caso único:** roda o ORD-042 canônico. Contrafactuais e multi-caso entram no
  harness (KAN-10), que pode injetar outro cenário via `FullContextPipeline(scenario=...)`.
- **Qualidade depende do modelo local:** modelos pequenos podem errar a rota ou
  emitir JSON fora do formato — por isso o parser é tolerante e o motor valida.
- **Contexto integral:** corpus grande pode estourar a janela do modelo. Como o
  corpus v1 é pequeno (~66 chunks), cabe; medir isso é justamente o ponto do baseline.
- **Custo:** `estimated_cost_usd = 0` (Ollama local). O campo existe para quando o
  harness comparar com provedores pagos.
```
