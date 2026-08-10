# Banco local — PostgreSQL + pgvector

Esta pasta contém a infraestrutura de armazenamento do **KAN-15**. O banco guarda os chunks preparados pela ingestão e oferece upsert, busca vetorial, busca lexical e filtros estruturados.

## Componentes

- `init/01_schema.sql`: extensão pgvector, tabela e índices.
- `client.py`: conexão configurada pelo `.env`.
- `repository.py`: upsert e consultas reutilizáveis.
- `loader.py`: carga idempotente de arquivos JSONL.
- `fixtures/chunks.sample.jsonl`: contrato mínimo representativo da futura saída da KAN-6.
- `*_smoke_test.py`: verificações executáveis do armazenamento.
- `../docs/kan-15-database-guide.html`: explicação visual da arquitetura.

## Configuração

Copie `.env.example` para `.env` e ajuste apenas valores locais. O `.env` é ignorado pelo Git.

```powershell
Copy-Item .env.example .env
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Subir e verificar

```powershell
docker compose up -d
docker compose ps
python -m db.smoke_test
python -m db.repository_smoke_test
python -m db.query_smoke_test
python -m db.loader_smoke_test
```

Todos os smoke tests usam prefixos/documentos reservados e removem os registros de teste ao final.

## Carregar um JSONL

```powershell
python -m db.loader db/fixtures/chunks.sample.jsonl
```

Cada linha deve ser um objeto JSON. Campos mínimos:

```json
{
  "chunk_id": "DOC-03-P02-C01",
  "document_id": "DOC-03",
  "content": "Texto normalizado do chunk."
}
```

Campos opcionais reconhecidos: `document_title`, `document_type`, `page`, `section`, `version`, `effective_from`, `effective_to`, `zona`, `entity_ids`, `embedding` e `source_hash`.

O embedding é opcional porque o artefato intermediário da KAN-6 deve ser independente de provedor. Quando presente na v1, precisa ter 768 dimensões para corresponder ao schema atual.

O loader usa `chunk_id` como chave de idempotência: reexecutar o mesmo arquivo atualiza os registros existentes e não cria duplicações.

## Beekeeper Studio

Use:

```text
Type: PostgreSQL
Host: localhost
Port: 5433
Database: lastmile_rag
User/password: valores de POSTGRES_USER e POSTGRES_PASSWORD no .env
SSL: desligado
```

## Consultas rápidas

```sql
SELECT extversion FROM pg_extension WHERE extname = 'vector';
SELECT COUNT(*) FROM public.chunks;
SELECT * FROM public.chunks ORDER BY ingested_at DESC LIMIT 20;
```

## Persistência e reset

Parar sem apagar os dados:

```powershell
docker compose down
```

O comando abaixo remove também o volume e todos os dados locais. Use somente quando o reset completo for intencional:

```powershell
docker compose down -v
```

Depois do reset, `docker compose up -d` recria extensão, tabela e índices por meio do script de inicialização.
