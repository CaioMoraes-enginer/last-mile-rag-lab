# Escopo executável — Last Mile RAG Lab v1

> Entregável da tarefa **[KAN-2 / EP01-T01]**. Este documento congela o escopo técnico da v1
> antes de qualquer implementação. Ele é a fonte de verdade para o contrato de domínio (KAN-3),
> o motor determinístico (KAN-4), os pipelines (KAN-6..KAN-9) e a avaliação (KAN-10).

| Campo | Valor |
|---|---|
| Épico | [KAN-1] Last Mile RAG Lab v1 — Benchmark de decisão de rotas com RAG |
| Versão do escopo | 1.0.0 |
| Status | Congelado (baseline v1) |
| Corpus alvo | `last-mile-rag-lab-v0.1` (5 PDFs, 42 páginas) |
| Autor | Caio Leandro de Moraes |
| Repositório | https://github.com/CaioMoraes-enginer/last-mile-rag-lab |

---

## 1. Objetivo da v1

Demonstrar, de forma **reproduzível e auditável**, se três arquiteturas de RAG conseguem tomar uma
**decisão logística operacionalmente válida, temporalmente correta e sustentada por evidências
fragmentadas** — e a que custo, latência e cobertura de citações cada uma chega lá.

A v1 **não** busca provar que o RAG avançado sempre vence. Busca **medir** em que condições cada
pipeline acerta a rota *pelos motivos certos*.

## 2. Pergunta operacional oficial

> Dado o estado atual do pedido, o modal, a malha vigente, os incidentes ativos, as políticas de
> acesso temporárias e o SLA, **qual é a rota operacionalmente válida que minimiza o tempo estimado
> de entrega** — e quais evidências sustentam essa decisão?

## 3. Instante canônico e regra de temporalidade

- **Caso de referência:** pedido sintético `ORD-042`, `ZONA-03`, modal `BICICLETA`, estado `DISPATCHED`.
- **Instante de decisão (`decision_at`):** **19:15** (referência canônica da v1).
- **Horário prometido (`promised_at`):** **19:32**.
- **Regra geral de temporalidade:**
  1. Toda avaliação de validade usa `decision_at` como relógio.
  2. Só valem documentos/avisos **vigentes** em `decision_at` (`effective_from ≤ decision_at ≤ effective_to`
     ou versão explicitamente marcada como vigente).
  3. Em conflito entre versões, vence a **versão vigente mais recente**; versões revogadas são ignoradas.
  4. Eventos são ordenados pelo **timestamp do evento**, não pelo de ingestão; duplicados e eventos
     fora de ordem são reduzidos deterministicamente.

## 4. Caso de referência ORD-042 (resultado esperado)

O caso canônico avalia três rotas candidatas. O resultado abaixo é o **esperado**, porém **não pode
ser codificado como constante**: ele precisa emergir da aplicação das regras sobre os documentos.

| Rota | Segmento | Veredito esperado | Justificativa (composição de evidências) |
|---|---|---|---|
| A | `SG-BD` | ❌ Inválida | Incidente `INC-Z03-042` v2.1 bloqueia B–D entre 18:40–21:30 (todos os modais) → ativo às 19:15. |
| B | `SG-CF` (arterial) | ✅ Válida, mais lenta | Desvio B–C–F–D + chuva `WTH-Z03-018` (18:55–20:10) = penalidade arterial **+6 min**. |
| C | `SG-CE` (CT-BIKE) | ✅ **Melhor rota válida** | `POL-MODAL-CT-3.0` + aviso `ACCESS-Z03-017` v3.0 autorizam SG-CE para bike + DISPATCHED + entrega, janela 18:00–20:00; classe CT-BIKE não sofre penalidade de chuva. |

> **Regra anti-overfitting:** é proibido qualquer código com lógica específica para retornar "C".
> A rota selecionada deve ser produto do motor determinístico sobre os dados recuperados. Alterar
> horário, modal, estado do pedido, política ou aviso deve poder mudar o resultado.

## 5. Os três pipelines (fronteiras claras, mesmo contrato)

Todos recebem a mesma pergunta e produzem o **mesmo contrato de saída** (seção 7). A diferença está
apenas em **como recuperam** o contexto entregue ao raciocínio.

| # | Pipeline | O que faz | Fronteira |
|---|---|---|---|
| P1 | Contexto completo sem recuperação | Envia os 5 documentos (ou o máximo cabível) ao modelo | Baseline de força bruta; sem seleção |
| P2 | RAG vetorial simples | Chunking + embeddings + busca por similaridade | Uma consulta semântica; sem filtros temporais/lexicais |
| P3 | RAG avançado | Vetorial + BM25 + fusão (RRF) + filtros (zona/versão/validade) + reranking + recuperação por categoria de evidência + ferramentas determinísticas | Recupera separadamente pedido, malha, incidentes/clima, política de acesso e SLA |

**Objetivo de decisão comum aos três:** selecionar a melhor rota **válida**, com ETA, slack, risco e
citações verificáveis — ou abster-se com `INSUFFICIENT_EVIDENCE`.

## 6. Fronteira: raciocínio probabilístico × validação determinística

| Camada | Responsabilidade | **Nunca** faz |
|---|---|---|
| LLM (probabilístico) | Interpretar a pergunta, decompor consultas, organizar a explicação, redigir citações | Calcular ETA/slack, decidir se um evento está ativo, escolher a versão vigente |
| Motor determinístico | Reduzir eventos, selecionar versão vigente, validar segmentos, aplicar bloqueios/penalidades, calcular ETA/slack, classificar risco, selecionar a rota | Depender de SDK de LLM ou "inventar" valores |

O motor é a **fonte de verdade dos números e da validade**. O LLM nunca é autorizado a sobrescrever o motor.

## 7. Contrato de saída estruturado

Único para os três pipelines. Valores numéricos são **calculados pelo motor** — nunca fixos.

```json
{
  "order_id": "ORD-042",
  "decision_timestamp": "<ISO-8601, = decision_at>",
  "selected_route": "<A|B|C|null>",
  "valid": "<bool>",
  "estimated_minutes": "<number, calculado pelo motor>",
  "slack_minutes": "<number, calculado pelo motor>",
  "risk_class": "<STANDARD|ATTENTION|AT_RISK|BREACH>",
  "recommended_action": "<string>",
  "constraints_checked": ["<lista de regras aplicadas>"],
  "rejected_routes": [{"route": "A", "reason": "<motivo com evidência>"}],
  "citations": [{"document_id": "DOC-04", "page": 3, "section": "<...>", "version": "3.0", "snippet": "<trecho>"}],
  "evidence_coverage": "<0..1>",
  "confidence": "<0..1>",
  "status": "<SUCCESS|INSUFFICIENT_EVIDENCE|ERROR>"
}
```

### 7.1. Método de decisão (definido no DOC-05)

```text
slack_minutes = promised_at − decision_at − estimated_route_minutes
```

| Classe de risco | Condição |
|---|---|
| `STANDARD` | slack > 15 min |
| `ATTENTION` | 8 ≤ slack ≤ 15 |
| `AT_RISK` | 1 ≤ slack ≤ 7 |
| `BREACH` | slack ≤ 0 |

**Desempate entre rotas válidas:** (1) maior slack; depois (2) menor quantidade de segmentos controlados.
**Abstenção:** se a cobertura mínima de evidências não for atingida → `status = INSUFFICIENT_EVIDENCE`.

## 8. Métricas obrigatórias

| Métrica | Significado | Unidade/escala | Regra de cálculo |
|---|---|---|---|
| Acerto de rota | Escolheu a rota esperada | booleano / % | `selected_route == gold_route` |
| Validade operacional | A rota escolhida era de fato válida | booleano / % | Motor valida a rota escolhida contra as regras vigentes |
| Cobertura de evidências | Recuperou as 5 categorias necessárias | 0..1 | nº de categorias obrigatórias presentes ÷ 5 |
| Correção de citações | As citações apontam para trecho real e vigente | 0..1 | citações válidas ÷ citações emitidas |
| Grounding | A conclusão é sustentada pelas citações | 0..1 | asserções sustentadas ÷ asserções feitas |
| Validade temporal | Não usou versão revogada/fora de vigência | booleano / % | nenhuma citação com `effective` inválido em `decision_at` |
| Exatidão de cálculo | ETA/slack/risco batem com o motor | booleano / % | comparação campo a campo com o motor |
| Abstenção correta | Absteve quando (e só quando) faltava evidência | booleano / % | `INSUFFICIENT_EVIDENCE` iff cobertura < mínimo |
| Latência | Tempo de ponta a ponta | ms | `t_fim − t_início` |
| Tokens | Entrada + saída consumidos | tokens | soma reportada pelo provedor |
| Tamanho de contexto | Volume enviado ao modelo | tokens/chars | medido antes da chamada |
| Custo estimado | Custo monetário da execução | USD | tokens × preço por token do modelo |
| Estabilidade | Consistência entre execuções | 0..1 | variância do resultado em N execuções |

## 9. Definição de correção (regra central)

> Uma resposta só é considerada **correta** quando **rota**, **validade** e **evidências** são coerentes
> entre si. Escolher a rota certa citando uma política revogada, sem cobertura mínima de evidências ou
> com cálculo errado é considerado **falha**.

Cascata de avaliação:

```text
Escolheu a rota esperada?
      → A rota era realmente válida?
            → As evidências recuperadas eram suficientes?
                  → As citações sustentam a conclusão?
                        → Os cálculos estão corretos?
```

## 10. Cenários contrafactuais mínimos (v1)

Impedem que a implementação force a resposta "C". Conjunto mínimo:

1. Horário após 20:00 → janela de `ACCESS-Z03-017` expirada → C inválida.
2. Estado ≠ DISPATCHED → C inválida.
3. Modal ≠ BICICLETA → C inválida.
4. Bloqueio `INC-Z03-042` removido/expirado → A volta a ser candidata válida.
5. Chuva `WTH-Z03-018` encerrada → B deixa de sofrer +6 min.
6. Documento obrigatório ausente → `INSUFFICIENT_EVIDENCE`.
7. Versão revogada presente no corpus → não pode ser citada como vigente.
8. Eventos recebidos fora de ordem → resultado idêntico ao da ordem correta.

## 11. Política de citação e anti-vazamento

- Toda citação deve permitir chegar a **`document_id` + página + seção/trecho + versão**. "Segundo o
  documento" não é citação válida.
- **Escopo de recuperação:** apenas `data/corpus/documents/*.pdf` (conforme `manifest.json`).
- **Nunca** entram no índice do corpus: `README.md`, `docs/`, `assets/`, resultados de avaliação, este
  documento de escopo e qualquer artefato que contenha a resposta esperada. (Risco de vazamento.)

## 12. Requisitos

### 12.1. Funcionais

| ID | Requisito |
|---|---|
| RF-01 | Ingerir os 5 PDFs em chunks com metadados rastreáveis (doc, página, seção, versão, vigência, região, IDs). |
| RF-02 | Executar os três pipelines sobre o mesmo caso e produzir o contrato da seção 7. |
| RF-03 | Motor determinístico calcula validade, ETA, slack, risco e seleção de rota. |
| RF-04 | Harness de avaliação roda os casos (canônico + contrafactuais) e emite as métricas da seção 8. |
| RF-05 | API versionada expõe decisão, evidências, rotas descartadas, rastreamento e telemetria. |
| RF-06 | Interface (React) compara os três pipelines lado a lado. |
| RF-07 | Adaptador serial envia a rota selecionada ao Arduino, que a sinaliza fisicamente. |

### 12.2. Não funcionais

| ID | Requisito |
|---|---|
| RNF-01 | **Reprodutibilidade:** dependências fixadas, prompts versionados, temperatura fixada, seeds registradas. |
| RNF-02 | **Determinismo do motor:** mesmo input → mesmo output, sem dependência de LLM. |
| RNF-03 | **Telemetria:** latência, tokens, contexto e custo medidos por execução. |
| RNF-04 | **Integridade do corpus:** hashes SHA-256 validados antes de cada run (`validate_corpus.py`). |
| RNF-05 | **Rastreabilidade:** cada resultado carrega versão do corpus + versão do pipeline. |
| RNF-06 | **Portabilidade:** geradores e código não devem depender de caminhos absolutos de fontes do Windows. |

## 13. Interface (v1 = React)

Painel comparativo mostrando, por pipeline: rota selecionada, validade, ETA, slack, risco, evidências
recuperadas, documentos ausentes, citações, latência, tokens, custo, erros e abstenções.

## 14. Hardware (Arduino) — camada de visualização

O Arduino **não participa do raciocínio**. O computador decide e envia por serial:

```text
ROUTE:A | ROUTE:B | ROUTE:C | ROUTE:OFF
```

O Arduino acende **um** LED (A/B/C), apaga os demais, devolve `ACK` e mantém estado seguro para
comandos inválidos ou perda de conexão. O protocolo serial é versionado.

## 15. Incluído × Fora de escopo × Futuro

**Incluído na v1:** contrato de domínio; motor determinístico; ingestão + chunking + citações; os três
pipelines; harness de avaliação; caso canônico + contrafactuais; API versionada; interface React;
integração Arduino; testes, documentação, CI e hardening.

**Fora de escopo (v1):** dados reais ou de pessoas; integração oficial com iFood/Bosch/qualquer
plataforma; otimização logística de produção; alterar os PDFs sem justificativa aprovada; escolher o
fornecedor **definitivo** de LLM/embeddings (a v1 abstrai atrás de interface, com um padrão).

**Futuro (roadmap):** corpus maior e multi-caso; múltiplas zonas; avaliação com juízes/LLM-as-judge;
deploy público; observabilidade avançada; novos modais.

## 16. Decisões arquiteturais aprovadas

- Separação estrita LLM × motor determinístico (motor é a fonte de verdade).
- Contrato de saída único para os três pipelines.
- Backlog **completo** entregue na v1 (sem corte de escopo), ritmo ~1 card/dia.
- Interface em **React**; Arduino **incluído** como camada final.
- Corpus congelado em `v0.1` durante a v1 (mudança exige atualização intencional de hashes).

## 17. Perguntas em aberto (resolver até KAN-3)

- Fornecedor de LLM e de embeddings **para desenvolvimento** (padrão atrás de uma interface abstrata).
- Vector store (ex.: FAISS/Chroma) e reranker.
- Método de contabilização de custo por modelo.
- Estratégia de deploy da interface React (fica no roadmap se não couber).

## 18. Definição de pronto do épico (DoD)

O épico KAN-1 está pronto quando:

- [ ] Os três pipelines rodam o caso canônico e todos os contrafactuais da seção 10.
- [ ] Todas as métricas obrigatórias (seção 8) são emitidas por pipeline.
- [ ] Nenhuma resposta correta se apoia em versão revogada ou sem cobertura mínima.
- [ ] Não existe código que force a rota "C".
- [ ] Toda decisão traz citações rastreáveis (doc + página + trecho + versão).
- [ ] A API expõe decisão, evidências e telemetria; a interface React compara os três lado a lado.
- [ ] O Arduino sinaliza a rota via serial com `ACK` e estado seguro.
- [ ] Testes, documentação e CI passam; o corpus valida por hash; o benchmark é reproduzível.

## 19. Plano de execução — 13 cards, ~1 card/dia

| Dia | Card | Entrega |
|---:|---|---|
| 1 | **KAN-2** | Este escopo congelado *(em andamento)* |
| 2 | KAN-3 | Modelo de domínio + contrato estruturado de decisão |
| 3 | KAN-4 | Motor determinístico (validade, ETA, slack, risco, seleção) |
| 4 | KAN-5 | Testes ouro + cenários contrafactuais do ORD-042 |
| 5 | KAN-6 | Ingestão dos 5 PDFs com chunking e citações rastreáveis |
| 6 | KAN-7 | Baseline P1 — contexto completo sem recuperação |
| 7 | KAN-8 | Baseline P2 — RAG vetorial simples |
| 8 | KAN-9 ⚠️ | RAG avançado (híbrido + filtros + reranking + ferramentas) — *card pesado* |
| 9 | KAN-10 | Harness de avaliação comparativa dos três pipelines |
| 10 | KAN-11 ⚠️ | API versionada — *card pesado* |
| 11 | KAN-12 ⚠️ | Interface React comparativa — *card pesado* |
| 12 | KAN-13 | Integração Arduino Uno por serial |
| 13 | KAN-14 | Testes, documentação, CI, reprodutibilidade e hardening |

> ⚠️ Cards mais pesados que um dia típico: **KAN-9, KAN-11, KAN-12**. Vale reservar buffer ou usar os
> dias de "card leve" (KAN-13 é pequeno) para compensar.
