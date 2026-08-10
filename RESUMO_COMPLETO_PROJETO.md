# Resumo completo — Last Mile RAG Lab

## 1. Resumo executivo

O **Last Mile RAG Lab** é um projeto público de portfólio que combina **GenAI, RAG, logística de última milha, avaliação de sistemas de IA e integração com hardware embarcado**.

A proposta não é simplesmente construir um chatbot que lê PDFs. O projeto pretende demonstrar, de forma reproduzível, se diferentes arquiteturas de RAG conseguem tomar uma **decisão operacional correta, temporalmente válida e sustentada por evidências fragmentadas**.

O repositório oficial é:

- Local: `C:\Users\caiol\OneDrive\Desktop\Projetos_Oficiais\last-mile-rag-lab`
- GitHub: <https://github.com/CaioMoraes-enginer/last-mile-rag-lab>
- Conta autorizada para commits e pushes: `CaioMoraes-enginer`

As contas `loomisdataanalysis` e `lomiens` não devem ser utilizadas sem autorização explícita.

O corpus e o cenário são sintéticos, determinísticos e independentes. O projeto não possui associação oficial com iFood, Bosch, WeHandle ou qualquer plataforma de entrega.

## 1.1. Status atual (registro de progresso)

> Seção viva — atualizada a cada avanço. Última atualização: 09/08/2026.

**Etapa atual:** `KAN-15` — PostgreSQL + pgvector e camada de armazenamento. **Implementação e validação concluídas localmente; pronta para commit, push e PR após revisão do proprietário.**

### Contexto de fluxo (permanece)

- `docs/escopo-v1.md` — escopo executável da v1 congelado (entregável da **KAN-2**) e integrado à `main` pelo **PR #1**.
- **KAN-15** criado no Jira — card dedicado de infraestrutura do banco (posição lógica entre KAN-6 e KAN-8).
- Decisão de arquitetura: **banco = PostgreSQL + pgvector**, rodando local via **Docker** na porta `5433`.
- Decisões de fluxo: **um PR por card** (branch → commit com a chave → push → PR); **`main` protegida** por ruleset (sem commit/force-push direto); commits/PRs **100% de autoria do Caio** (sem atribuição de IA).
- Branch de trabalho atual: `feat/KAN-15-postgres-pgvector`.

### KAN-15 — o que foi feito e verificado

Ambiente da máquina (Windows 11): Docker Desktop + Docker Compose v5, Python 3.13, virtualenv em `.venv/`.

1. **`docker-compose.yml`** (raiz) — serviço `db` com a imagem `pgvector/pgvector:pg16`; porta do host **5433** → 5432 do container; volume nomeado `pgdata`; `healthcheck` via `pg_isready`; monta `./db/init` como scripts de inicialização (`/docker-entrypoint-initdb.d`).
2. **`db/init/01_schema.sql`** — roda na **primeira** subida do banco (volume vazio): `CREATE EXTENSION vector`; tabela `chunks` (metadados + `content` + `content_tsv` gerado + `embedding vector(768)`); índice **GIN** no tsvector (busca lexical); índices B-tree (`document_id`, `zona`, `version`); índice **HNSW** cosseno no `embedding` (busca vetorial).
3. **Banco no ar e verificado** — container `lastmile-rag-db` `healthy`. Confirmado por `\dx` (extensão **vector 0.8.6**), `\dt` (tabela `chunks`), `\d chunks` (colunas + 6 índices). Postgres **16.14**.
4. **`.env` e `.env.example`** (raiz) — configuração. `.env` é **ignorado pelo git**; `.env.example` é o molde versionado. Variáveis: `POSTGRES_USER/PASSWORD/DB`, `DB_HOST_PORT=5433`, `DB_HOST=localhost`, `DATABASE_URL=postgresql://lastmile:lastmile@localhost:5433/lastmile_rag`. Credenciais locais/sintéticas: `lastmile / lastmile / lastmile_rag`.
5. **`requirements.txt`** — adicionadas as dependências do banco: `psycopg[binary]>=3.2,<4`, `pgvector>=0.3,<1`, `python-dotenv>=1,<2` (instaladas no `.venv`).
6. **`db/client.py`** — conexão centralizada por variáveis de ambiente, resolução determinística do `.env` pela raiz do repositório e registro dos adaptadores pgvector.
7. **`db/repository.py`** — `upsert_many()` idempotente, busca vetorial top-k, busca lexical e filtros por documento, zona, versão, vigência e entidade.
8. **`db/loader.py`** — CLI de carga JSONL em lotes, com erros por linha, transação controlada pelo chamador e idempotência por `chunk_id`.
9. **Testes executáveis** — infraestrutura, upsert, queries e loader cobertos por `db/smoke_test.py`, `db/repository_smoke_test.py`, `db/query_smoke_test.py` e `db/loader_smoke_test.py`. Todos passam e removem os dados temporários ao final.
10. **Documentação** — `db/README.md` registra configuração, contrato JSONL, comandos, Beekeeper e reset; `docs/kan-15-database-guide.html` explica visualmente o fluxo.

### Validação final local da KAN-15

- container `lastmile-rag-db`: saudável;
- busca vetorial: `SMOKE-3` com distância `0.0000`;
- busca lexical: `SG-BD` recupera o chunk esperado;
- filtros: zona, versão, vigência e entidade validados;
- upsert: duas execuções mantêm uma única linha atualizada;
- loader: duas cargas do mesmo JSONL mantêm somente dois IDs únicos;
- quantidade final na tabela após os testes: `0`.

### Próximos passos para publicar a KAN-15

1. Revisar o diff e confirmar ausência de segredos.
2. Criar commit com a chave `KAN-15`.
3. Fazer push da branch `feat/KAN-15-postgres-pgvector`.
4. Abrir o PR com a chave `KAN-15` no título.

### Comandos úteis de retomada

- Subir banco: `docker compose up -d` · Status: `docker compose ps` · Derrubar e **zerar dados**: `docker compose down -v`
- Ativar venv (PowerShell): `.\.venv\Scripts\Activate.ps1`
- Testar conexão: `python -m db.client` · Testes: `python -m db.smoke_test`, `python -m db.repository_smoke_test`, `python -m db.query_smoke_test` e `python -m db.loader_smoke_test`
- Abrir o psql no container: `docker compose exec db psql -U lastmile -d lastmile_rag`

**Próxima etapa depois da KAN-15:** `KAN-3` — formalizar o modelo de domínio e o contrato estruturado de decisão. Aqui se escolhe o **provedor de embeddings** — atenção: o schema fixou `embedding vector(768)`, então o modelo precisa gerar **768 dimensões** (senão, ajustar o schema e recriar o banco com `docker compose down -v && docker compose up -d`). Depois, a cadeia até a ingestão (KAN-6), quando o banco recebe os dados reais dos 5 PDFs.

## 2. O problema do projeto

O sistema precisa escolher uma rota válida para entregar um pedido de última milha.

Embora isso pareça inicialmente um problema de menor caminho, a rota mais curta no mapa pode:

- estar bloqueada por um incidente;
- sofrer penalidade por chuva;
- exigir uma política especial de acesso;
- ser permitida somente para determinados modais;
- ser válida apenas em uma janela de horário;
- depender do estado atual do pedido;
- violar o SLA mesmo sendo tecnicamente transitável.

O caso principal acompanha o pedido sintético **ORD-042**.

A resposta correta não aparece diretamente em nenhum documento. O sistema precisa recuperar e conectar informações provenientes de cinco fontes diferentes:

```mermaid
flowchart LR
    Q["Pedido ORD-042 às 19:15"] --> O["Pedido, modal e estado"]
    Q --> M["Malha e rotas"]
    Q --> I["Bloqueios e clima"]
    Q --> P["Políticas de acesso"]
    Q --> S["SLA e regras de decisão"]

    O --> D["Motor de decisão"]
    M --> D
    I --> D
    P --> D
    S --> D

    D --> R["Rota válida + ETA + risco + evidências"]
```

O projeto deve provar que um sistema RAG precisa fazer mais do que encontrar trechos semanticamente parecidos. Ele deve:

1. recuperar todas as evidências necessárias;
2. distinguir versões atuais de versões antigas;
3. respeitar períodos de validade;
4. resolver conflitos e eventos temporais;
5. aplicar regras determinísticas;
6. apresentar citações verificáveis;
7. abster-se quando as evidências forem insuficientes.

## 3. Funcionamento do caso ORD-042

No momento principal da decisão:

- Pedido: **ORD-042**
- Zona: **ZONA-03**
- Modal: **BICICLETA**
- Estado: **DISPATCHED**
- Horário de decisão: **19:15**
- Horário prometido: **19:32**

O sistema precisa avaliar três rotas candidatas.

### 3.1. Rota A

A rota A possui o menor custo nominal e, olhando apenas para o mapa, parece ser a melhor escolha.

O problema é que ela utiliza o segmento `SG-BD`, correspondente ao trecho B–D.

Existe um incidente ativo:

- ID: `INC-Z03-042`
- versão vigente: `2.1`
- bloqueio total nos dois sentidos;
- válido entre 18:40 e 21:30;
- aplicável a todos os modais.

Como a decisão acontece às 19:15, o bloqueio está ativo.

**Conclusão:** a rota A é curta, mas operacionalmente inválida.

Um sistema que escolher A provavelmente encontrou o mapa, mas não recuperou ou não aplicou corretamente o boletim operacional.

### 3.2. Rota B

A rota B utiliza o desvio convencional, passando pelo caminho B–C–F–D.

Ela não utiliza o trecho bloqueado e, portanto, continua operacionalmente válida.

Entretanto, existe um boletim de chuva forte ativo entre 18:55 e 20:10. A política climática aplica penalidades diferentes conforme a classe do segmento:

- LOCAL: +1 minuto;
- ARTERIAL: +6 minutos;
- EXPRESS: +2 minutos;
- CT-BIKE: sem acréscimo no corredor coberto.

A rota B passa pelo segmento arterial `SG-CF`, recebendo uma penalidade de **+6 minutos**, além de já ser um desvio mais longo.

**Conclusão:** a rota B é válida, mas fica mais lenta por causa do desvio e da chuva.

Ela funciona como alternativa segura, mas não é a melhor rota válida no cenário canônico.

### 3.3. Rota C

A rota C utiliza o segmento controlado:

- segmento: `SG-CE`;
- classe: `CT-BIKE`.

Ela não pode ser considerada válida somente olhando o mapa. Seu uso depende de uma composição de evidências.

A política vigente `POL-MODAL-CT-3.0` estabelece que o corredor pode ser utilizado quando:

- o modal é BICICLETA;
- o pedido está no estado DISPATCHED;
- trata-se de uma operação de entrega;
- existe um aviso de acesso ativo;
- o horário está dentro da janela autorizada.

O aviso `ACCESS-Z03-017`, versão vigente `3.0`, autoriza o segmento `SG-CE` na ZONA-03 entre 18:00 e 20:00.

No caso ORD-042:

- modal = BICICLETA;
- estado = DISPATCHED;
- horário = 19:15;
- corredor = SG-CE;
- aviso = ativo;
- janela = válida;
- classe CT-BIKE = sem penalidade adicional da chuva.

**Conclusão:** a rota C é operacionalmente válida e emerge como a melhor rota válida no cenário canônico.

Essa conclusão não deve ser programada como resposta fixa. Ela precisa surgir da aplicação das regras sobre os documentos. Se o modal, o horário, o estado do pedido, a política ou o aviso forem alterados, o resultado pode mudar.

## 4. Corpus documental

O corpus é sintético, determinístico, em português e possui:

- 5 PDFs;
- 42 páginas;
- versão `0.1.0`;
- geração registrada em 8 de agosto de 2026;
- hashes SHA-256;
- IDs, versões, datas e períodos de vigência;
- informações distratoras;
- eventos atrasados e fora de ordem;
- documentos históricos e substituídos.

O manifesto está em `data/corpus/manifest.json`.

### 4.1. DOC-01 — Dossiê operacional de pedidos

Arquivo: `data/corpus/documents/01-dossie-operacional-de-pedidos.pdf`

Contém:

- dados do ORD-042;
- modal BICICLETA;
- zona operacional;
- estado DISPATCHED;
- horário prometido;
- linha do tempo do pedido;
- eventos de despacho;
- registros duplicados;
- eventos fora de ordem;
- IDs semelhantes usados como distração;
- regras de qualidade de dados.

Esse documento informa o que está sendo entregue e em qual estado, mas não contém a malha, os bloqueios, as políticas completas nem a rota final.

### 4.2. DOC-02 — Catálogo da malha logística

Arquivo: `data/corpus/documents/02-catalogo-da-malha-logistica.pdf`

Contém:

- nós e segmentos da malha;
- classes de vias;
- custos nominais;
- versões da rede;
- rotas candidatas A, B e C;
- segmento convencional B–D;
- desvio B–C–F–D;
- segmento controlado SG-CE;
- outras regiões e versões usadas como distração.

Esse documento permite montar as rotas, mas não informa sozinho se os segmentos estão disponíveis no horário da decisão.

### 4.3. DOC-03 — Boletins operacionais

Arquivo: `data/corpus/documents/03-boletins-operacionais.pdf`

Contém:

- incidente `INC-Z03-042`;
- bloqueio ativo de `SG-BD`;
- versões antigas e substituídas do incidente;
- boletim de chuva `WTH-Z03-018`;
- penalidades por classe de segmento;
- desvio convencional;
- períodos de vigência;
- eventos de outras regiões;
- diferenças entre horário do evento e horário de ingestão.

Esse documento elimina a rota A e penaliza a rota B.

### 4.4. DOC-04 — Políticas de acesso e modais

Arquivo: `data/corpus/documents/04-politicas-de-acesso-e-modais.pdf`

Contém:

- política vigente `POL-MODAL-CT-3.0`;
- critérios para utilização de corredores CT-BIKE;
- aviso `ACCESS-Z03-017`;
- autorização de `SG-CE`;
- janela 18:00–20:00;
- condições de modal e estado do pedido;
- políticas históricas revogadas;
- avisos semelhantes de outras zonas.

Esse é o documento que permite provar que a rota C está autorizada para o ORD-042 naquele momento.

### 4.5. DOC-05 — Manual de SLA e decisões

Arquivo: `data/corpus/documents/05-manual-de-sla-e-decisoes.pdf`

Contém a metodologia genérica de decisão:

1. descartar rotas inválidas;
2. ordenar as válidas pelo ETA ajustado;
3. calcular o slack;
4. classificar o risco;
5. recomendar uma ação;
6. citar todas as evidências utilizadas.

A fórmula central é:

```text
slack_minutes = promised_at - decision_at - estimated_route_minutes
```

Classes de risco:

- `STANDARD`: mais de 15 minutos;
- `ATTENTION`: de 8 a 15;
- `AT_RISK`: de 1 a 7;
- `BREACH`: zero ou negativo.

O manual também define:

- desempate por maior slack;
- depois, menor quantidade de segmentos controlados;
- estado `INSUFFICIENT_EVIDENCE`;
- cobertura mínima de evidências;
- estrutura esperada da resposta.

O DOC-05 não contém `ORD-042`, justamente para não entregar a solução do benchmark.

## 5. Os três caminhos experimentais

O projeto compara três arquiteturas executando a mesma tarefa e utilizando o mesmo contrato de saída.

### 5.1. Estratégia 1 — Contexto completo sem recuperação

Os cinco documentos são enviados ao modelo, ou o máximo possível deles.

Essa estratégia serve como baseline de força bruta.

Vantagens:

- implementação simples;
- menor risco inicial de a busca omitir um documento;
- boa referência para comparar os demais pipelines.

Limitações:

- contexto grande;
- maior uso de tokens;
- maior custo;
- maior latência;
- distração por versões antigas e IDs parecidos;
- dificuldade de crescer para um corpus maior;
- possibilidade de o modelo ignorar evidências mesmo tendo recebido tudo.

### 5.2. Estratégia 2 — RAG vetorial simples

Os PDFs são divididos em chunks, indexados por embeddings e consultados por similaridade semântica.

Vantagens:

- contexto menor;
- custo potencialmente menor;
- arquitetura próxima de muitos sistemas RAG reais;
- recuperação mais seletiva.

Limitações:

- uma única pergunta pode não recuperar as cinco categorias de evidência;
- IDs como `SG-BD`, `ORD-042` e `ACCESS-Z03-017` podem exigir busca lexical;
- embeddings não resolvem vigência temporal;
- chunks semanticamente próximos podem representar versões revogadas;
- pode selecionar a rota esperada sem conseguir prová-la corretamente.

### 5.3. Estratégia 3 — RAG avançado

Combina:

- busca vetorial;
- busca lexical/BM25;
- expansão ou decomposição da consulta;
- filtros por zona, versão e período de validade;
- fusão de rankings;
- reranking;
- ferramentas determinísticas;
- validação de cobertura de evidências;
- resposta estruturada;
- rastreamento das fontes utilizadas.

Essa estratégia deve recuperar separadamente:

- contexto do pedido;
- malha;
- bloqueios e clima;
- autorização modal;
- regras de SLA.

O LLM interpreta a pergunta e organiza a explicação. O motor determinístico verifica:

- versão vigente;
- validade temporal;
- disponibilidade dos segmentos;
- permissões;
- penalidades;
- ETA;
- slack;
- classe de risco.

O objetivo não é demonstrar que o RAG avançado sempre ganha, mas medir em quais condições ele oferece melhor equilíbrio entre qualidade, evidência, custo e latência.

## 6. O que já está implementado

Atualmente, o projeto possui uma fundação documental sólida.

Já existem:

- README estruturado;
- corpus sintético completo;
- cinco PDFs;
- manifesto do corpus;
- hashes dos documentos;
- scripts reproduzíveis de geração;
- validador automático;
- imagens explicativas;
- licença;
- dependências Python;
- histórico Git;
- repositório público;
- backlog detalhado no Jira;
- integração GitHub–Jira.

O `README.md` descreve o problema, o experimento, as estratégias e os comandos de reprodução.

Os geradores estão em:

- `tools/generate_document_01.py`
- `tools/generate_documents_02_05.py`

O validador está em:

- `tools/validate_corpus.py`

Ele verifica:

- quantidade de documentos;
- número total de páginas;
- hashes SHA-256;
- extração mínima de texto;
- presença de termos esperados;
- ausência de e-mails;
- marcação do corpus como sintético;
- ausência proposital de `ORD-042` no manual de SLA.

As dependências atuais estão em `requirements.txt`:

- ReportLab;
- pdfplumber;
- pypdf.

## 7. Histórico Git

O histórico possui cinco commits principais:

1. `83bc223` — criação do corpus inicial.
2. `adc16af` — documentação visual da progressão das estratégias de RAG.
3. `abca76a` — adoção da charge em pixel art 32-bit.
4. `b3a403a` — reorganização da explicação do problema e do experimento.
5. `5c040c2` — confirmação da autoria do repositório.

Todos foram registrados com a identidade:

```text
Caio Moraes
270493421+CaioMoraes-enginer@users.noreply.github.com
```

Estado verificado:

- branch atual: `main`;
- upstream: `origin/main`;
- remote: `CaioMoraes-enginer/last-mile-rag-lab`;
- arquivos rastreados: limpos;
- repositório GitHub: público;
- não há mudanças rastreadas pendentes antes da criação deste relatório.

Existem artefatos ignorados em diretórios como `tmp`, `output` e `__pycache__`, mas eles não fazem parte do estado versionado.

## 8. Imagens e diagramas

Os arquivos visuais estão no diretório `assets`.

### 8.1. `01-problema-last-mile-rag.png`

Apresenta visualmente:

- as três rotas;
- o bloqueio;
- a fragmentação das evidências;
- a necessidade de combinar documentos.

Seu papel é explicar rapidamente o problema logístico.

### 8.2. `02-comparacao-rag-3x3.png`

Mostra a progressão entre:

- contexto completo;
- RAG vetorial simples;
- RAG avançado.

Funciona como representação visual da hipótese experimental.

### 8.3. `charge-rag-rotas.png`

É uma versão conceitual anterior da ilustração do problema.

### 8.4. `charge-rag-rotas-32bit.png`

É a versão em pixel art adotada para dar personalidade visual ao projeto e ajudar na apresentação como case de portfólio.

Essas imagens são explicativas e não devem ser indexadas como evidência do benchmark.

## 9. Arquitetura técnica recomendada

A arquitetura deve separar claramente IA generativa de regras operacionais.

```mermaid
flowchart TD
    PDF["PDFs do corpus"] --> ING["Ingestão e normalização"]
    ING --> IDX["Índice vetorial + lexical"]
    IDX --> P1["Pipeline 1: contexto completo"]
    IDX --> P2["Pipeline 2: RAG vetorial"]
    IDX --> P3["Pipeline 3: RAG avançado"]

    P1 --> ENG["Motor determinístico"]
    P2 --> ENG
    P3 --> ENG

    ENG --> OUT["Contrato estruturado"]
    OUT --> EVAL["Avaliação"]
    OUT --> API["API"]
    API --> UI["Interface"]
    API --> SER["Adaptador serial"]
    SER --> ARD["Arduino + LEDs"]
```

### 9.1. Ingestão

A ingestão deverá:

- extrair texto por página;
- preservar tabelas quando possível;
- normalizar caracteres;
- identificar cabeçalhos e seções;
- gerar chunks semanticamente coerentes;
- registrar metadados rastreáveis.

Cada chunk deve carregar pelo menos:

```text
document_id
document_title
page_number
section
chunk_id
document_version
effective_from
effective_to
region
entity_ids
source_hash
```

A citação não pode ser apenas “segundo o documento”. Ela precisa permitir chegar ao documento, página e trecho utilizado.

### 9.2. Recuperação

Deve existir uma interface comum para todos os recuperadores.

O RAG avançado pode utilizar:

- embeddings;
- BM25;
- Reciprocal Rank Fusion;
- filtros por metadados;
- reranker;
- recuperação orientada por categoria de evidência.

A consulta deve ser decomposta em perguntas menores, como:

- qual é o estado e modal do pedido?
- quais são as rotas possíveis?
- quais segmentos estão bloqueados?
- quais penalidades climáticas estão vigentes?
- a política permite SG-CE?
- como o SLA deve ser calculado?

### 9.3. Motor determinístico

Esse é o núcleo de confiabilidade.

Ele deverá:

- reduzir eventos fora de ordem;
- selecionar a versão vigente;
- verificar intervalos de validade;
- validar segmentos;
- aplicar bloqueios;
- aplicar penalidades;
- calcular ETA;
- calcular slack;
- classificar risco;
- selecionar a melhor rota válida.

Ele não deve depender do SDK de nenhum LLM. O modelo não será autorizado a inventar os cálculos ou decidir sozinho se um evento está ativo.

### 9.4. Contrato estruturado

Uma resposta poderá seguir uma estrutura semelhante a:

```json
{
  "order_id": "ORD-042",
  "decision_timestamp": "2026-08-08T19:15:00-03:00",
  "selected_route": "C",
  "valid": true,
  "estimated_minutes": 0,
  "slack_minutes": 0,
  "risk_class": "AT_RISK",
  "recommended_action": "",
  "constraints_checked": [],
  "rejected_routes": [],
  "citations": [],
  "confidence": 0.0,
  "status": "SUCCESS"
}
```

Os valores numéricos devem ser calculados pelo motor a partir dos dados da malha. Não devem ser preenchidos como constantes para produzir a rota C.

### 9.5. API

Uma API em FastAPI é uma escolha adequada.

Endpoints possíveis:

```text
GET  /health
POST /api/v1/decisions
POST /api/v1/retrieval/debug
POST /api/v1/evaluations/run
GET  /api/v1/evaluations/{run_id}
POST /api/v1/hardware/signal
```

A API deve expor:

- decisão;
- evidências;
- rotas descartadas;
- rastreamento da recuperação;
- latência;
- tokens;
- custo estimado;
- versão do corpus;
- versão do pipeline.

### 9.6. Interface

A interface deve permitir comparar os três pipelines lado a lado.

Ela deve mostrar:

- rota selecionada;
- validade;
- ETA;
- slack;
- risco;
- evidências recuperadas;
- documentos ausentes;
- citações;
- latência;
- tokens;
- custo;
- erros e abstenções.

Streamlit permitiria avançar rapidamente. React ofereceria uma apresentação mais refinada para portfólio. Essa escolha ainda pode ser tomada mais adiante.

### 9.7. Arduino

O Arduino Uno terá três LEDs azuis:

- LED A;
- LED B;
- LED C.

O computador executa todo o raciocínio e envia por serial algo como:

```text
ROUTE:A
ROUTE:B
ROUTE:C
ROUTE:OFF
```

O Arduino:

- interpreta a mensagem;
- apaga os demais LEDs;
- acende somente o LED selecionado;
- devolve um `ACK`;
- mantém estado seguro para comandos inválidos.

O hardware é uma visualização física do resultado, e não parte do raciocínio.

## 10. Avaliação do benchmark

Cada pipeline deve rodar sobre o mesmo conjunto de casos e produzir o mesmo contrato.

As métricas principais serão:

- acurácia da rota escolhida;
- validade operacional;
- cobertura das evidências obrigatórias;
- correção das citações;
- grounding;
- validade temporal;
- exatidão dos cálculos;
- taxa de abstenção correta;
- latência;
- tokens de entrada e saída;
- tamanho do contexto;
- custo estimado;
- estabilidade entre execuções.

É importante separar:

```text
Escolheu a rota esperada?
             ↓
A rota era realmente válida?
             ↓
As evidências recuperadas eram suficientes?
             ↓
As citações sustentam a conclusão?
             ↓
Os cálculos estão corretos?
```

Um modelo que escolhe C por coincidência, mas cita uma política revogada, deve falhar no benchmark.

Também serão necessários cenários contrafactuais, por exemplo:

- horário depois das 20:00;
- pedido ainda não despachado;
- modal diferente de bicicleta;
- aviso de corredor expirado;
- chuva encerrada;
- bloqueio removido;
- documentos obrigatórios ausentes;
- versões conflitantes;
- eventos recebidos fora de ordem.

Esses casos impedem que a implementação simplesmente force a resposta C.

## 11. Jira e rastreabilidade

Foi criado o épico:

- `KAN-1` — `[EP01] Last Mile RAG Lab v1 — Benchmark de decisão de rotas com RAG`

As tarefas vinculadas são:

- `KAN-2` — congelar o escopo executável;
- `KAN-3` — formalizar domínio e contrato de decisão;
- `KAN-4` — motor determinístico;
- `KAN-5` — testes ouro e contrafactuais;
- `KAN-6` — ingestão dos PDFs;
- `KAN-7` — baseline de contexto completo;
- `KAN-8` — RAG vetorial simples;
- `KAN-9` — RAG avançado;
- `KAN-10` — harness de avaliação;
- `KAN-11` — API;
- `KAN-12` — interface;
- `KAN-13` — Arduino;
- `KAN-14` — testes, documentação e hardening.

Todos estão atualmente em **A fazer**.

A integração oficial GitHub for Atlassian está instalada:

- conta conectada: `CaioMoraes-enginer`;
- repositório selecionado com acesso completo: `last-mile-rag-lab`;
- sincronização histórica concluída.

Para ligar desenvolvimento e Jira:

```text
Branch: feat/KAN-2-escopo-v1
Commit: docs(KAN-2): definir escopo executável da v1
PR: [EP01-T01][KAN-2] Definir escopo executável da v1
```

Quando a chave aparece na branch, commit ou PR, o Jira passa a mostrar essas informações no painel de desenvolvimento do card.

Criar um card Jira não cria automaticamente uma issue no GitHub, e abrir um PR sem a chave `KAN-*` não cria o vínculo.

## 12. O que ainda precisa ser construído

Ainda não existem:

- pacote principal da aplicação;
- modelo formal de domínio;
- schema definitivo de resposta;
- ingestão executável;
- chunks reais do corpus produzidos e persistidos pela KAN-6;
- índices vetorial e lexical populados com o corpus real;
- baseline de contexto completo;
- baseline vetorial;
- RAG avançado;
- motor determinístico;
- dataset ouro;
- cenários contrafactuais;
- harness de avaliação;
- rastreamento de tokens e custos;
- API;
- interface;
- código Arduino;
- protocolo serial;
- CI;
- suíte automatizada completa do produto;
- relatório final do benchmark.

Ou seja: a narrativa, o corpus e a infraestrutura local de armazenamento já existem; domínio, ingestão real, pipelines e produto ainda serão implementados.

## 13. Riscos e pontos em aberto

Os principais riscos são:

- **Vazamento de resposta:** README, imagens e resultados de avaliação nunca devem entrar no índice do corpus.
- **Overfitting ao ORD-042:** o código não pode conter regras específicas para retornar C.
- **Versões revogadas:** busca sem filtro temporal pode recuperar políticas antigas.
- **IDs exatos:** busca exclusivamente vetorial pode falhar com códigos como `SG-BD`.
- **Chunking de tabelas:** uma divisão ruim pode separar condição, período e consequência.
- **Citação incompleta:** escolher a rota certa sem provar pedido, rede, incidente, acesso e SLA.
- **Não determinismo:** temperatura, modelo e prompts precisam ser versionados.
- **Portabilidade:** os geradores atualmente possuem dependências de fontes Arial em caminhos do Windows.
- **Regeneração do corpus:** mudanças nos PDFs exigem atualização intencional dos hashes.
- **Custo:** ainda é necessário escolher modelo generativo, embeddings e estratégia de contabilização.
- **Infraestrutura:** vector store e reranker ainda não foram definidos.
- **Automação Jira:** o vínculo existe, mas transições automáticas de status ainda não foram configuradas.
- **Proteção da main:** o fluxo ideal é uma tarefa por branch e pull request, mesmo trabalhando sozinho.

## 14. Backlog priorizado

### Fase 1 — Fundação executável

1. `KAN-2`: congelar o escopo da v1.
2. `KAN-3`: formalizar o domínio e o contrato estruturado.
3. `KAN-4`: implementar o motor determinístico.
4. `KAN-5`: criar testes ouro e cenários contrafactuais.

### Fase 2 — Dados e recuperação

5. `KAN-6`: implementar ingestão, chunking e citações.
6. `KAN-7`: implementar o baseline de contexto completo.
7. `KAN-8`: implementar o RAG vetorial simples.
8. `KAN-9`: implementar o RAG avançado.

### Fase 3 — Avaliação e produto

9. `KAN-10`: construir o harness comparativo.
10. `KAN-11`: expor os pipelines pela API.
11. `KAN-12`: construir a interface comparativa.

### Fase 4 — Hardware e entrega

12. `KAN-13`: integrar o Arduino Uno.
13. `KAN-14`: consolidar testes, documentação, CI, reprodutibilidade e hardening.

## 15. Próximo passo recomendado

O próximo passo correto é executar o `KAN-2`: **congelar o escopo executável da v1**.

Antes de começar o RAG, deve ser produzida uma especificação curta e versionada contendo:

- objetivo da v1;
- pergunta operacional oficial;
- timestamp canônico;
- documentos permitidos;
- resposta estruturada esperada;
- critérios de sucesso;
- métricas;
- política de citação;
- comportamento para evidência insuficiente;
- itens fora de escopo;
- definição de pronto.

Depois disso, a sequência recomendada é:

```text
KAN-2 Escopo
   ↓
KAN-3 Domínio e contrato
   ↓
KAN-4 Motor determinístico
   ↓
KAN-5 Testes ouro
   ↓
KAN-6 Ingestão
   ↓
KAN-7 / KAN-8 / KAN-9 Pipelines
   ↓
KAN-10 Benchmark
   ↓
KAN-11 / KAN-12 API e interface
   ↓
KAN-13 Arduino
   ↓
KAN-14 Hardening e documentação
```

## 16. Conclusão

O projeto já possui uma base narrativa e documental consistente. Seu diferencial será transformar essa fundação em um benchmark tecnicamente sério, no qual recuperação, validade temporal, regras determinísticas, citações e avaliação sejam componentes separados e auditáveis.

A implementação não deve provar artificialmente que a rota C é correta. Ela deve construir um sistema capaz de concluir que C é a melhor rota no cenário canônico e de produzir respostas diferentes quando as evidências ou condições forem alteradas.
