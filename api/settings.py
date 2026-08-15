"""Configuracao da API (KAN-11): limites e origens, via ambiente."""
import os

# timeout por requisicao de decisao (chamadas de LLM sao lentas)
TIMEOUT_SECONDS = float(os.getenv("API_TIMEOUT_S", "180"))

# CORS: apenas as interfaces locais aprovadas (KAN-12)
ALLOWED_ORIGINS = os.getenv(
    "API_CORS_ORIGINS", "http://localhost:5173,http://localhost:3000"
).split(",")
