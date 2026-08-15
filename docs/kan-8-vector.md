# Pipeline P2 — RAG vetorial simples (KAN-8)

> Entregável da tarefa **[KAN-8 / EP01-T07]**. Segundo dos três pipelines: um RAG
> básico e reconhecível — consulta → embeddings → similaridade → top-k → geração.

## Papel no experimento

O P2 é o **baseline de recuperação**: introduz a etapa que o P1 não tem (seleção
de contexto por similaridade), mas sem os refinamentos do P3 (híbrido, filtros,
reranking). Comparar P1 × P2 × P3 no harness (KAN-10) mostra o ganho de *recuperar*
e depois o ganho de *recuperar bem*.

## Arquitetura

Reutiliza a interface e o parser do KAN-7 — **só o `retrieve()` muda**:

```
pedido ORD-042
      │
      ▼
build_retrieval_query()      consulta estável derivada do pedido (sem gabarito)
      │
      ▼
EmbeddingProvider.embed()    vetor da consulta (Ollama nomic-embed-text, 768d)
      │
      ▼
VectorStore.search(top_k)    similaridade pura → chunks com rank + score
      │
      ▼
contexto = SÓ os chunks recuperados
      │
      ▼
[compartilhado com P1] prompt → LLM → parse → validação pelo motor
```

### Componentes

| Módulo | Papel |
|---|---|
| `pipelines/query.py` | consulta estável derivada do pedido (versionada, sem rota ouro) |
| `pipelines/embeddings.py` | `OllamaEmbeddingProvider` (real) + `HashingEmbeddingProvider` (determinístico, testes) |
| `pipelines/vectorstore.py` | `PgVectorStore` (reusa `vector_search` do KAN-15) + `InMemoryVectorStore` (testes) |
| `pipelines/vector.py` | `VectorPipeline` — só a estratégia de recuperação |
| `pipelines/decision.py` | montagem/validação da decisão **compartilhada** com o P1 |

### Política de recuperação (explícita)

- **Só similaridade vetorial** (cosseno). Sem BM25, filtro temporal/versão, fusão
  ou reranking — isso é o P3 (KAN-9).
- **top-k** configurável (`--top-k`, default 8), registrado na proveniência.
- **Empate:** desempate estável por `chunk_id`.
- **Dedup:** por `chunk_id`, mantendo o melhor score.
- **Limite de contexto:** apenas os top-k chunks entram no prompt.
- **Rank e score** preservados no artefato para auditoria.
- **O gerador só vê os chunks recuperados:** citações fora do conjunto são
  descartadas (e registradas).

## Como rodar

### Offline (embeddings determinísticos + índice em memória + LLM mock)

```bash
python -m pipelines.cli --pipeline vector --provider mock --top-k 4
```

### Real com índice em memória (Ollama)

```bash
ollama serve
ollama pull nomic-embed-text
ollama pull llama3.1
python -m pipelines.cli --pipeline vector --provider ollama --top-k 8
```

### Real com pgvector (Postgres do KAN-15)

```bash
docker compose up -d                      # sobe o Postgres + pgvector (porta 5433)
python -m pipelines.build_index           # embeda os chunks e carrega no banco
python -m pipelines.cli --pipeline vector --provider ollama --store pgvector
```

Cada execução grava um artefato em `output/vector_<timestamp>.json` com config,
proveniência, **ranking recuperado**, decisão, telemetria e validação do motor.

## Métricas separadas

A telemetria distingue as fases (escopo §8): `context_chars` mede o volume
recuperado; o ranking (`retrieval`) expõe `rank`/`score` por chunk. Latência de
embedding, retrieval e geração são medidas separadamente quando o backend real é
usado (o mock zera a latência).

## Limitações (v1)

- **Qualidade depende do embedding:** um modelo fraco pode não recuperar a
  evidência necessária — e isso **aparece no artefato** (citações descartadas,
  cobertura baixa). Medir isso é o objetivo do baseline.
- **Sem filtros:** o P2 pode recuperar versões revogadas ou fora de vigência; a
  correção temporal é responsabilidade do P3.
- **Caso único (ORD-042):** contrafactuais e multi-caso entram no harness (KAN-10).
- O `HashingEmbeddingProvider` é lexical (para testes), não semântico; o caminho
  real usa `nomic-embed-text`.
```
