"""Rotas de decisao versionadas (KAN-11): /v1/decide e /v1/pipelines.

O `decide` roda o pipeline (sincrono, lento) num executor com timeout, para nao
bloquear o loop e poder cancelar chamadas longas. O run_id nasce aqui e vai para
o `request.state`, de modo que ate o corpo de erro carregue o mesmo id.
"""
import asyncio
import uuid

from fastapi import APIRouter, Request

from api.errors import provider_unavailable
from api.models import DecideRequest, DecideResponse, ErrorResponse
from api.service import run_decision
from api.settings import TIMEOUT_SECONDS

router = APIRouter(prefix="/v1", tags=["decide"])

_ERRORS = {
    404: {"model": ErrorResponse}, 409: {"model": ErrorResponse},
    502: {"model": ErrorResponse}, 503: {"model": ErrorResponse},
    504: {"model": ErrorResponse},
}


@router.get("/pipelines")
def list_pipelines() -> dict:
    return {"pipelines": ["full_context", "vector", "advanced"]}


@router.post("/decide", response_model=DecideResponse, responses=_ERRORS)
async def decide(req: DecideRequest, request: Request):
    run_id = str(uuid.uuid4())
    request.state.run_id = run_id            # correlaciona resposta, logs e erro
    loop = asyncio.get_running_loop()
    try:
        return await asyncio.wait_for(
            loop.run_in_executor(None, run_decision, req, run_id),
            timeout=TIMEOUT_SECONDS,
        )
    except asyncio.TimeoutError:
        raise provider_unavailable(f"timeout apos {TIMEOUT_SECONDS:.0f}s")
