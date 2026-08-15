"""Erros tipados da API (KAN-11).

Cada situacao prevista tem um codigo estavel e um status HTTP. O corpo de erro
NUNCA carrega stack trace, prompt secreto ou credencial — so `code` + `message`.
O traceback vai para o log (com o run_id), nunca para a resposta.
"""


class ApiError(Exception):
    """Erro previsto, com codigo estavel e status HTTP."""

    def __init__(self, code: str, http: int, message: str):
        self.code, self.http, self.message = code, http, message
        super().__init__(message)


def invalid_input(msg: str) -> ApiError:
    return ApiError("invalid_input", 422, msg)


def pipeline_not_found(name: str) -> ApiError:
    return ApiError("pipeline_not_found", 404, f"pipeline '{name}' nao existe")


def corpus_unavailable(msg: str) -> ApiError:
    return ApiError("corpus_unavailable", 503, msg)


def evidence_conflict(msg: str) -> ApiError:
    return ApiError("evidence_conflict", 409, msg)


def provider_unavailable(msg: str) -> ApiError:
    return ApiError("provider_unavailable", 504, msg)


def model_output_invalid(msg: str) -> ApiError:
    return ApiError("model_output_invalid", 502, msg)


def error_body(err: ApiError, run_id: str) -> dict:
    """Corpo de erro estavel (sem detalhes internos)."""
    return {"error": {"code": err.code, "message": err.message}, "run_id": run_id}
