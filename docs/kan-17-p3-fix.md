# KAN-17 — Correções no pipeline avançado (P3)

Origem: ao comparar os três pipelines pela interface (KAN-12) com provedores reais
(Ollama `llama3` e OpenAI `gpt-4o-mini`), o **P3 (avançado)** aparecia com resultado
"curiosamente ruim". A investigação separou **dois problemas independentes**.

---

## Bug 1 — `engine_validation` do P3 fora do contrato (CORRIGIDO)

### Sintoma
Na interface, a **ROTA OURO** do P3 aparecia como `—`, enquanto P1/P2 mostravam `C`.

### Causa
O P3 montava as chaves dinamicamente:

```python
engine_validation = {f"gold_{k}": v for k, v in gold.items()}   # -> gold_selected_route
```

Como `ToolRunner.gold_decision()` devolve `selected_route`, a chave virava
`gold_selected_route`. Mas o contrato compartilhado (`pipelines/decision._gold_record`,
usado por P1/P2), a API e a interface (KAN-12) leem **`gold_route`**. A rota ouro
do motor **era calculada corretamente (C)** — só ficava rotulada com a chave errada,
e por isso a UI não a encontrava.

### Correção
`pipelines/advanced.py` passa a emitir exatamente as mesmas chaves `gold_*` do
contrato compartilhado (`gold_route`, `gold_valid`, `gold_estimated_minutes`,
`gold_slack_minutes`, `gold_risk_class`, `gold_status`).

### Testes
- `test_no_hardcoded_c_counterfactual` atualizado para `gold_route`.
- `test_engine_validation_uses_shared_gold_contract` (novo) trava o contrato:
  as chaves `gold_*` do P3 devem casar com `decision._gold_record` e a chave antiga
  `gold_selected_route` não pode voltar.

Verificado na API: `POST /v1/decide {pipeline: advanced}` → `engine_validation.gold_route = "C"`.

---

## Bug 2 — P3 propõe rota inválida por não recuperar a evidência decisiva (LIMITAÇÃO DOCUMENTADA)

### Sintoma
Com provedor real (tanto `llama3` quanto `gpt-4o-mini`), o P3 escolhe a **rota A**,
que o motor reprova (`SG-BD` bloqueado pelo incidente `INC-Z03-042`) → status **ERROR**.
O baseline P1 (contexto completo) e o P2 (vetorial) acertam a rota **C**.

### Causa raiz — recall, não geração
A evidência que sustenta a decisão está em:

| Chunk | Conteúdo |
|-------|----------|
| `DOC-03-P03-C01` | "INCIDENTE CRÍTICO — Interdição do segmento B-D · Boletim INC-Z03-042 v2.1" |
| `DOC-03-P03-C02` | "SG-BD deve ser removido de qualquer cálculo entre 18:40–21:30" |

Mas esse chunk **não é recuperado** pelo P3. Medições (cenário ORD-042, embeddings de
hashing offline):

- Rank do chunk decisivo nos recuperadores da faceta *eventos*:
  **32º no lexical (BM25)** e **46º no vetorial** — muito além do `top_k=10`.
- **Nenhum ajuste de recall** o traz para o contexto:

  | Config | DOC-03 no contexto | Chunk decisivo presente? |
  |--------|--------------------|--------------------------|
  | atual (top_k=10, final_k=8, cap=2) | `P02` (cabeçalho) | ❌ |
  | top_k=20, final_k=10, cap=3 | `P05` (distrator) | ❌ |
  | top_k=30, final_k=12, cap=3 | `P04, P05, P02` | ❌ |
  | top_k=50, final_k=12, cap=4 | `P04, P05` | ❌ |

- Incluir os segmentos das rotas candidatas na query **não resolve**: o mapa da malha
  (`DOC-02`) cita todos os segmentos e dilui o sinal, e o incidente usa "B-D" enquanto
  as rotas usam "SG-BD".

O corpus foi construído com **distratores propositais** na mesma faceta:
`DOC-03-P05` ("DISTRATORES REGIONAIS — incidentes em outras zonas"), `DOC-03-P06`
(boletins históricos/substituídos), `DOC-03-P02` (só o cabeçalho "ESCOPO DA FONTE").
Eles casam com a query genérica de *eventos* melhor do que o incidente real e ocupam
as vagas do documento.

O **gate de cobertura** (`facets.coverage`) mede presença por **documento**: como um
chunk qualquer de `DOC-03` está presente, a faceta *eventos* é dada como "coberta" e o
P3 **não sinaliza insuficiência** — entrega ao LLM um contexto sem a prova do bloqueio,
e qualquer modelo escolhe a rota A (mais rápida). O motor então reprova A (rede de
segurança funcionando: falha **visível**, com status ERROR, não silenciosa).

### Por que NÃO foi "corrigido" aqui
Qualquer ajuste que force o P3 a achar `C` **neste** cenário é *overfit* no ORD-042 —
seria gamar o próprio benchmark que o corpus adversarial existe para testar. Distinguir
o chunk decisivo dos distratores sem conhecer a resposta (a rota ouro) exigiria vazar
gabarito. Portanto, a decisão consciente é **documentar como limitação conhecida** em vez
de aplicar um hack.

### Encaminhamento (card de follow-up, a criar)
1. **Medir**: recall@k do chunk decisivo por faceta, em vários cenários, pelo harness
   (KAN-10) — transformar "está ruim" em métrica.
2. **Recuperação estruturada / por ferramenta**: para os segmentos das rotas candidatas,
   buscar deterministicamente o incidente **autoritativo e vigente** (versão corrente,
   zona correta) e injetá-lo no contexto — coerente com a tese "motor/ferramentas como
   fonte de verdade", em vez de depender de recuperação fuzzy contra distratores.
3. **Gate honesto**: enquanto a evidência decisiva não for confirmada para os segmentos
   em jogo, o P3 deveria **abster-se** (`INSUFFICIENT_EVIDENCE`) em vez de propor rota.

### Observação
A interface (KAN-12) está **correta**: ela reportou fielmente o comportamento real dos
pipelines (a divergência, o ERROR do motor, a telemetria). O problema é de recuperação
no P3 (KAN-9), não de apresentação.
