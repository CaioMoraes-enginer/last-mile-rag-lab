# Pipeline P3 — RAG avançado (KAN-9)

> Entregável da tarefa **[KAN-9 / EP01-T08]**. Terceiro e mais completo pipeline:
> busca híbrida, filtros de vigência, fusão, reranking, cobertura e o motor como
> ferramenta determinística.

## Papel no experimento

O P3 não é "aumentar o top-k". Ele recupera **certo**: códigos exatos, evidência
vigente, e as cinco categorias necessárias — delegando as regras duras ao motor.
Comparado ao P2 no harness (KAN-10), mostra o ganho de *recuperar bem*.

## Pipeline

```
consulta → facetas (5 categorias)
        → [BM25 lexical + vetorial] por faceta
        → fusão RRF (contribuição de cada recuperador registrada)
        → filtro de vigência (decision_at)
        → diversificação (cap por documento)
        → reranking (interface substituível)
        → backfill + checagem de cobertura das facetas
        → LLM → motor COMO FERRAMENTA (validado, auditável) → decisão
```

Cada etapa vai para o **trace** (reconstrói por que cada chunk chegou ao contexto).

## Componentes

| Módulo | Papel |
|---|---|
| `pipelines/facets.py` | 5 facetas (pedido, malha, eventos, acesso, SLA), consultas por faceta, cobertura |
| `pipelines/lexical.py` | BM25 em memória (códigos exatos) + `PgLexicalStore` (full-text do KAN-15) |
| `pipelines/fusion.py` | RRF determinístico + diversificação (cap por documento) |
| `pipelines/filters.py` | filtro de vigência no instante do pedido |
| `pipelines/rerank.py` | `Reranker` (interface) + local `LexicalOverlapReranker` + `IdentityReranker` |
| `pipelines/tools.py` | motor (KAN-4) como ferramenta tipada e auditável |
| `pipelines/advanced.py` | orquestrador + ablações + trace |

## Decisões de projeto

- **Fusão por RRF**: soma de `1/(k+rank)` por recuperador. Não depende da escala do
  score (BM25 × cosseno), então dispensa normalização. A contribuição de cada
  recuperador fica registrada.
- **Cobertura + backfill**: após o reranking, cada faceta cujo documento *foi
  recuperado* recebe ao menos um chunk (backfill). O **gate** só dispara quando a
  evidência **não existe** no corpus (ex.: documento ausente) → `INSUFFICIENT_EVIDENCE`,
  nunca alucinação.
- **Motor como ferramenta**: o P3 não pede números ao LLM. Chama `gold_decision` e
  `validate_route` (schemas tipados, entrada validada, chamadas auditadas). O LLM
  sugere a rota; o motor valida e calcula. Divergência é registrada, nunca
  sobrescreve o determinístico.
- **Vigência**: o filtro usa `decision_at`. Chunks expirados são descartados (mas
  registrados). *Limite honesto:* a ingestão (KAN-6) só carrega versão no nível do
  documento; a corretude temporal final é garantida pelo motor.

## Ablações (sem alterar código)

```bash
python -m pipelines.cli --pipeline advanced --provider mock                 # completo
python -m pipelines.cli --pipeline advanced --provider mock --no-lexical    # sem BM25
python -m pipelines.cli --pipeline advanced --provider mock --no-reranker   # sem rerank
python -m pipelines.cli --pipeline advanced --provider mock --no-filters    # sem filtro
python -m pipelines.cli --pipeline advanced --provider mock --no-tools      # sem motor
```

## Como rodar (real, Ollama)

```bash
ollama serve && ollama pull nomic-embed-text && ollama pull llama3.1
python -m pipelines.cli --pipeline advanced --provider ollama --final-k 8
# com pgvector (BM25 e vetorial no Postgres do KAN-15):
python -m pipelines.build_index
python -m pipelines.cli --pipeline advanced --provider ollama --store pgvector
```

O artefato (`output/advanced_*.json`) traz o trace completo: consultas por faceta,
recuperadores, contagens, filtro, reranker, backfill, cobertura, ranking final,
chamadas de ferramenta, decisão e telemetria.

## Critérios de aceite

- [x] Termos/códigos exatos recuperados pela busca lexical (BM25).
- [x] Vetorial e lexical contribuem com scores/ranks auditáveis (RRF).
- [x] Documentos fora de vigência não sustentam a decisão (filtro + motor).
- [x] Reranker recebe candidatos e produz ranking rastreável.
- [x] Cobertura verifica as facetas necessárias do caso.
- [x] Motor chamado por contrato (ferramenta), saída preservada.
- [x] Falta de evidência essencial → insuficiência, não alucinação.
- [x] Trace permite reconstruir por que cada chunk chegou ao contexto.
- [x] Ablações executáveis sem alterar código.
- [x] Nenhuma regra especial para escolher C (teste contrafactual MOTO → C reprovada).
- [x] Métricas separam consulta/retrieval/reranking/ferramentas/geração.
- [x] Saída final no mesmo contrato dos outros pipelines.

## Limitações (v1)

- O reranker local é lexical (para testes); um cross-encoder real entra pela mesma
  interface sem tocar no pipeline.
- Filtro de vigência por chunk depende de metadado que a ingestão v1 não popula
  (só versão de documento) — o motor é a garantia temporal final.
- Caso único (ORD-042); contrafactuais e multi-caso entram no harness (KAN-10).
```
