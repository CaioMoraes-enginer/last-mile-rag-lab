"""Healthcheck (KAN-11): barato e separado — nao chama LLM nem constroi indice."""
from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict:
    return {"status": "ok", "pipelines": ["full_context", "vector", "advanced"]}
