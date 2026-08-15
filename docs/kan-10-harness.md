# Harness de avaliação comparativa (KAN-10)

> Entregável da tarefa **[KAN-10 / EP01-T09]**. Executa os três pipelines sobre os
> mesmos casos, avalia por uma rubrica comum e gera artefatos comparativos.

## Por que existe

O valor do projeto está na **comparação honesta**. Medir só "a saída contém rota C"
esconderia respostas alucinadas, evidência expirada e citações irrelevantes. O
harness mede se cada pipeline acerta **pelos motivos certos**.

## Arquitetura

```
casos (canônico + contrafactuais)          eval/cases.py   (gabarito = motor, nunca fixo)
      │
      ▼
runner: os 3 pipelines pela MESMA interface  eval/runner.py  (mock/fixture ou Ollama real)
      │
      ▼
rubrica determinística por dimensão          eval/rubric.py
      │
      ▼
relatório (JSON + Markdown + matriz de falhas)  eval/report.py
```

## Dimensões da rubrica (100% automáticas)

| Dimensão | O que mede |
|---|---|
| Acerto de rota | `selected_route == gold` |
| Validade operacional | a rota escolhida é válida no motor |
| **Correto pelos motivos certos** | rota certa **E** válida **E** com citações **E** cobertura ≥ 0.6 **E** precisão de citação = 1 |
| Cobertura de evidências | facetas citadas ÷ 5 |
| Precisão de citação | citações válidas ÷ emitidas |
| Eficiência | latência, tokens, contexto, custo |
| Confiabilidade | contagem por status (SUCCESS / INSUFFICIENT / ERROR), erros |

> A dimensão central é **"correto pelos motivos certos"**: a rota certa **sem**
> evidência não recebe nota máxima (escopo §9). Isso impede que um acerto sortudo
> ou alucinado seja premiado.

## Justiça experimental

- Mesma entrada, mesmo contrato, mesmo corpus, mesma seed — registrados na proveniência.
- O **gabarito nunca entra no contexto** dos pipelines (só a rubrica o usa).
- **Falhas contam no denominador** (não são removidas da média).
- Distingue resposta inválida × evidência insuficiente × erro.
- Toda medição é automática; **não há LLM-as-judge** (se houvesse, seria separado e versionado).

## Casos

Canônico (ORD-042 → C) + contrafactuais de **nível de pedido** que mudam o
gabarito: modal MOTO → B, estado ASSIGNED → B, decisão às 20:05 (aviso expirado) → B.
Contrafactuais de nível de evento (remover incidente/clima) são testados no motor
em KAN-5 — como o corpus é um snapshot fixo, não se refletem no texto recuperado.

## Como rodar

```bash
python -m eval.run --provider mock                  # offline, determinístico (testa o avaliador)
python -m eval.run --provider ollama --repeats 3    # real, com variabilidade
python -m eval.run --provider ollama --ablations    # inclui ablações do avançado
```

Gera `output/benchmark_<ts>.json` (máquina) e `.md` (humano) com a tabela lado a
lado, a matriz por caso e a análise de falhas.

## Modo fixture

Com `--provider mock`, respostas determinísticas exercitam o harness e o avaliador
**sem API**. A fixture cita poucos chunks de propósito — o relatório mostra rota
correta com "motivos certos" baixo, ilustrando que **acerto de rota ≠ nota máxima**.

## Limitações (v1)

- Rubrica determinística; grounding textual profundo ficaria para um LLM-judge
  (separado e versionado) — fora do escopo da v1.
- Conjunto de casos focado no ORD-042; ampliar o corpus/multi-caso é roadmap.
- Custo `= 0` no Ollama local; o campo existe para comparar com provedores pagos.
```
