"""Aplicacao FastAPI (KAN-11).

Monta as rotas, o CORS para a interface local (KAN-12), e o handler que converte
ApiError em resposta estavel (com o run_id da requisicao, sem stack trace). O
OpenAPI (/docs, /openapi.json) e gerado automaticamente a partir dos modelos.
"""
import logging
import uuid

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from api.errors import ApiError, error_body
from api.routes import decide, health
from api.settings import ALLOWED_ORIGINS

logging.basicConfig(level=logging.INFO)


def create_app() -> FastAPI:
    app = FastAPI(
        title="Last Mile RAG Lab API",
        version="1.0.0",
        description="Decisao de rota do ORD-042 pelos tres pipelines (KAN-7/8/9).",
    )
    app.add_middleware(
        CORSMiddleware, allow_origins=ALLOWED_ORIGINS,
        allow_methods=["GET", "POST"], allow_headers=["*"],
    )

    @app.exception_handler(ApiError)
    async def _handle_api_error(request: Request, err: ApiError):
        run_id = getattr(request.state, "run_id", None) or str(uuid.uuid4())
        logging.getLogger("api").warning("api error run_id=%s code=%s", run_id, err.code)
        return JSONResponse(status_code=err.http, content=error_body(err, run_id))

    app.include_router(health.router)        # /health (sem versao)
    app.include_router(decide.router)        # /v1/...
    return app


app = create_app()
