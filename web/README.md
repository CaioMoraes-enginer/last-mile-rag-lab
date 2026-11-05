# Interface de comparação dos pipelines (KAN-12)

SPA em **React + Vite + TypeScript** que consome a API versionada (KAN-11) e
compara, lado a lado, a decisão de rota produzida pelos três pipelines da v1:

| Coluna | Pipeline | Estratégia de recuperação |
|--------|----------|---------------------------|
| P1 | `full_context` | contexto completo, sem recuperação |
| P2 | `vector` | RAG vetorial (busca densa) |
| P3 | `advanced` | híbrido + filtros + reranking + ferramentas |

Cada coluna mostra a **decisão** (rota, validade, classe de risco, folga,
confiança), a **validação pelo motor determinístico** (rota ouro × rota do LLM,
com o selo `LLM = motor`), as **evidências** (restrições checadas, citações,
rotas descartadas), o **ranking de recuperação** (score no P2; RRF +
contribuições por fonte no P3) e a **telemetria** (latência, tokens, contexto).
No topo, um veredito indica se os pipelines **convergiram na mesma rota**.

## Rodando

Pré-requisito: a API (KAN-11) no ar. Na raiz do repositório:

```bash
uvicorn api.main:app --reload --port 8000
```

Depois, nesta pasta:

```bash
npm install
npm run dev
```

Abra <http://localhost:5173>. A porta 5173 já está na allowlist de CORS da API
(`api/settings.py`).

### Base da API

O default é `http://localhost:8000`. Para apontar para outra porta/host, edite o
campo no canto superior direito (persistido em `localStorage`). O indicador
`API online/offline` sonda o `/health`.

## Build

```bash
npm run build    # tsc -b && vite build  → dist/
npm run preview  # serve o build de produção
```

## Estrutura

```
src/
  types.ts                  espelho dos contratos da API (KAN-11 + KAN-3)
  api.ts                    cliente fetch (base configurável, erro com run_id)
  App.tsx                   orquestra a comparação paralela dos 3 pipelines
  components/
    ScenarioPanel.tsx       controles do cenário (provedor, modal, estado, datas)
    PipelineColumn.tsx      coluna de resultado (decisão + evidências + retrieval)
    bits.tsx                UI compartilhada (chips, barras, seções colapsáveis)
  styles.css                design system (tema dark, tokens em :root)
```
