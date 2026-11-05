# KAN-12 — Interface para comparar decisões e evidências dos pipelines

## Objetivo

Fechar o loop de demonstração da v1: uma interface que roda o **mesmo cenário**
pelos três pipelines (KAN-7/8/9) através da API (KAN-11) e expõe, lado a lado, a
decisão, as evidências que a sustentam e a telemetria — deixando visível *por que*
cada pipeline chegou (ou não) à mesma rota.

## Decisões de projeto

- **Stack: React + Vite + TypeScript**, sem UI kit. O `types.ts` espelha os
  contratos de `api/models.py` e `domain/decision.py`, então divergência de
  schema aparece como erro de tipo no build, não em runtime.
- **Comparação paralela**: o clique dispara três `POST /v1/decide` (um por
  pipeline) em paralelo (`Promise.all`); cada coluna resolve o seu estado de
  forma independente (loading/erro/resultado), sem travar as demais.
- **Motor como fonte de verdade em evidência**: cada coluna destaca o
  `engine_validation` (rota ouro × rota do LLM, selo `LLM = motor`), reforçando a
  separação da v1 — o LLM sugere, o motor determinístico valida.
- **Retrieval honesto por pipeline**: P1 mostra "sem recuperação"; P2 mostra o
  `score` denso; P3 mostra `rrf_score` + as `contributions` por fonte (vetorial /
  lexical por faceta), tornando auditável a fusão híbrida.
- **Veredito de convergência**: um resumo no topo indica se os três pipelines
  concordaram na rota selecionada — o sinal mais rápido de leitura do case.

## Integração

- Base da API configurável na UI (default `http://localhost:8000`), persistida em
  `localStorage`; indicador online/offline sondando `/health`.
- CORS: `http://localhost:5173` (Vite) já estava liberado em `api/settings.py`
  desde o KAN-11.

## Como demonstrar

1. `uvicorn api.main:app --port 8000` na raiz.
2. `npm install && npm run dev` em `web/`.
3. Abrir `http://localhost:5173`, ajustar o cenário e clicar em
   **Comparar os 3 pipelines**.

Detalhes de execução e estrutura de pastas: [`web/README.md`](../web/README.md).
