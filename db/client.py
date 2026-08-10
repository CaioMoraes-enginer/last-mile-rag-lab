"""Camada de acesso ao Postgres + pgvector do Last Mile RAG Lab (KAN-15).

Responsabilidade unica: abrir uma conexao ja configurada com o banco,
lendo as credenciais do .env. O resto do projeto importa connect() daqui,
em vez de espalhar usuario e senha pelo codigo.
"""
import os
from pathlib import Path

import psycopg
from dotenv import load_dotenv
from pgvector.psycopg import register_vector

# Resolve o .env pela raiz do repositorio, independentemente do diretorio atual.
ENV_FILE = Path(__file__).resolve().parents[1] / ".env"
load_dotenv(ENV_FILE)


def get_dsn() -> str:
    """Monta a string de conexao a partir das variaveis de ambiente."""
    url = os.getenv("DATABASE_URL")
    if url:
        return url
    # Plano B: montar a partir das variaveis separadas (mesmos defaults do compose).
    user = os.getenv("POSTGRES_USER", "lastmile")
    password = os.getenv("POSTGRES_PASSWORD", "lastmile")
    db = os.getenv("POSTGRES_DB", "lastmile_rag")
    host = os.getenv("DB_HOST", "localhost")
    port = os.getenv("DB_HOST_PORT", "5433")
    return f"postgresql://{user}:{password}@{host}:{port}/{db}"


def connect() -> psycopg.Connection:
    """Abre a conexao e registra o tipo vector (pgvector) nela.

    O register_vector registra os adaptadores do pgvector. A camada de
    repository converte listas de numeros em objetos Vector antes das queries.
    """
    conn = psycopg.connect(get_dsn())
    register_vector(conn)
    return conn


if __name__ == "__main__":
    # Rodar `python db/client.py` faz um teste minimo: so conectar e perguntar "1".
    with connect() as conn:
        resposta = conn.execute("SELECT 1").fetchone()[0]
        print("Conexao OK, o banco respondeu:", resposta)
