"""Smoke test do banco (KAN-15).

Prova, de ponta a ponta e sem tocar nos dados reais do corpus, que:
  1. o Python conecta no Postgres do Docker;
  2. da pra gravar um chunk com embedding (vetor de 768) e metadados;
  3. a busca por SIMILARIDADE (vetorial, operador <=>) acha o vizinho certo;
  4. a busca LEXICAL (tsvector) acha um ID exato tipo 'SG-BD'.
  5. os filtros por zona, versao e vigencia temporal funcionam.

Cria linhas de teste com prefixo 'SMOKE-' e apaga tudo no fim, entao pode
rodar quantas vezes quiser sem sujar o banco.

Rode da raiz do projeto (com o .venv ativo):
    python -m db.smoke_test
"""
from datetime import datetime

from pgvector import Vector

from db.client import connect

DECISION_AT = datetime.fromisoformat("2026-08-08T19:15:00-03:00")
SMOKE_LIKE = "SMOKE-%"
DIM = 768


def one_hot(pos: int, dim: int = DIM) -> Vector:
    v = [0.0] * dim
    v[pos] = 1.0
    return Vector(v)


def main() -> int:
    linhas = [
        (
            "SMOKE-1",
            "Bloqueio total no trecho SG-BD",
            one_hot(0),
            "2.1",
            datetime.fromisoformat("2026-08-08T18:40:00-03:00"),
            datetime.fromisoformat("2026-08-08T21:30:00-03:00"),
        ),
        (
            "SMOKE-2",
            "Desvio pelo corredor arterial SG-CF",
            one_hot(1),
            "1.0",
            datetime.fromisoformat("2026-08-08T18:00:00-03:00"),
            datetime.fromisoformat("2026-08-08T19:00:00-03:00"),
        ),
        (
            "SMOKE-3",
            "Corredor controlado SG-CE liberado",
            one_hot(2),
            "3.0",
            datetime.fromisoformat("2026-08-08T18:00:00-03:00"),
            datetime.fromisoformat("2026-08-08T20:00:00-03:00"),
        ),
    ]

    conn = connect()
    try:
        with conn.cursor() as cur:
            # 0) comeca do zero (apaga sobras de execucoes anteriores)
            cur.execute("DELETE FROM chunks WHERE chunk_id LIKE %s", (SMOKE_LIKE,))

            # 1) grava os 3 chunks de teste
            for chunk_id, content, emb, version, effective_from, effective_to in linhas:
                cur.execute(
                    """
                    INSERT INTO chunks (
                        chunk_id,
                        document_id,
                        content,
                        embedding,
                        zona,
                        version,
                        effective_from,
                        effective_to
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        chunk_id,
                        "SMOKE-DOC",
                        content,
                        emb,
                        "ZONA-03",
                        version,
                        effective_from,
                        effective_to,
                    ),
                )
            print(f"[1] inseridos {len(linhas)} chunks de teste")

            # 2) busca VETORIAL: quem esta mais perto do vetor one_hot(2)?
            #    Esperado: SMOKE-3, que tem o mesmo 1.0 na posicao 2 (distancia ~0).
            alvo = one_hot(2)
            cur.execute(
                """
                SELECT chunk_id, content, embedding <=> %s AS distancia
                FROM chunks
                WHERE chunk_id LIKE %s
                ORDER BY embedding <=> %s
                LIMIT 1
                """,
                (alvo, SMOKE_LIKE, alvo),
            )
            vid, vcontent, vdist = cur.fetchone()
            print(f"[2] vizinho mais proximo: {vid} (distancia={vdist:.4f}) -> {vcontent}")
            assert vid == "SMOKE-3", f"esperava SMOKE-3, mas veio {vid}"

            # 3) busca LEXICAL por ID exato 'SG-BD' (usando o indice tsvector)
            cur.execute(
                """
                SELECT chunk_id
                FROM chunks
                WHERE chunk_id LIKE %s
                  AND content_tsv @@ plainto_tsquery('portuguese', %s)
                """,
                (SMOKE_LIKE, "SG-BD"),
            )
            achados = [row[0] for row in cur.fetchall()]
            print(f"[3] busca lexical por 'SG-BD' achou: {achados}")
            assert "SMOKE-1" in achados, "a busca lexical nao achou o SMOKE-1"

            # 4) filtros de metadados: zona, versao e vigencia em DECISION_AT
            cur.execute(
                """
                SELECT chunk_id
                FROM chunks
                WHERE chunk_id LIKE %s
                  AND zona = %s
                ORDER BY chunk_id
                """,
                (SMOKE_LIKE, "ZONA-03"),
            )
            por_zona = [row[0] for row in cur.fetchall()]
            print(f"[4a] filtro por zona achou: {por_zona}")
            assert por_zona == ["SMOKE-1", "SMOKE-2", "SMOKE-3"]

            cur.execute(
                """
                SELECT chunk_id
                FROM chunks
                WHERE chunk_id LIKE %s
                  AND version = %s
                ORDER BY chunk_id
                """,
                (SMOKE_LIKE, "3.0"),
            )
            por_versao = [row[0] for row in cur.fetchall()]
            print(f"[4b] filtro por versao achou: {por_versao}")
            assert por_versao == ["SMOKE-3"]

            cur.execute(
                """
                SELECT chunk_id
                FROM chunks
                WHERE chunk_id LIKE %s
                  AND effective_from <= %s
                  AND (effective_to IS NULL OR effective_to >= %s)
                ORDER BY chunk_id
                """,
                (SMOKE_LIKE, DECISION_AT, DECISION_AT),
            )
            vigentes = [row[0] for row in cur.fetchall()]
            print(f"[4c] vigentes em {DECISION_AT.isoformat()}: {vigentes}")
            assert vigentes == ["SMOKE-1", "SMOKE-3"]

            # 5) limpa tudo pra nao deixar lixo no banco
            cur.execute("DELETE FROM chunks WHERE chunk_id LIKE %s", (SMOKE_LIKE,))

        conn.commit()  # torna as mudancas permanentes (aqui, o banco volta limpo)
        print(
            "\nOK! Banco + pgvector + buscas vetorial/lexical + "
            "filtros de metadados: tudo funcionando."
        )
        return 0
    finally:
        conn.close()  # fecha a conexao aconteca o que acontecer


if __name__ == "__main__":
    raise SystemExit(main())
