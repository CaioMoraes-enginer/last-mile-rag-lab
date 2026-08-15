"""Parsing e validacao da resposta do LLM (KAN-7).

Transforma o texto cru do modelo no proposta estruturada e resolve as citacoes
contra o corpus real. Trata falhas (JSON invalido/ausente) SEM mascara-las: quem
chama recebe o erro e decide o status.

Estrategia de reparo unica e mensuravel (escopo, instrucao 7): se o texto nao for
JSON puro, tenta extrair o primeiro objeto {...} balanceado. Se isso for usado,
sinaliza `repair_applied=True`. Nenhuma outra "correcao magica" e aplicada.
"""
import json

from domain.decision import Citation, RejectedRoute


class ParseError(ValueError):
    """A resposta do LLM nao pode ser interpretada como o JSON esperado."""


def _extract_json_object(text: str) -> tuple[str, bool]:
    """Devolve (json_str, repair_applied).

    Primeiro tenta o texto inteiro. Se falhar, recorta o primeiro objeto {...}
    balanceado (reparo unico). Levanta ParseError se nao houver objeto plausivel.
    """
    stripped = text.strip()
    # remove cercas de codigo ```json ... ``` se existirem
    if stripped.startswith("```"):
        stripped = stripped.strip("`")
        if stripped.lstrip().lower().startswith("json"):
            stripped = stripped.lstrip()[4:]
        stripped = stripped.strip()

    try:
        json.loads(stripped)
        return stripped, False
    except json.JSONDecodeError:
        pass

    # reparo: recorta o primeiro objeto {...} balanceado
    inicio = stripped.find("{")
    if inicio == -1:
        raise ParseError("nenhum objeto JSON encontrado na resposta do LLM")
    profundidade = 0
    for pos in range(inicio, len(stripped)):
        char = stripped[pos]
        if char == "{":
            profundidade += 1
        elif char == "}":
            profundidade -= 1
            if profundidade == 0:
                candidato = stripped[inicio : pos + 1]
                try:
                    json.loads(candidato)
                    return candidato, True
                except json.JSONDecodeError as exc:
                    raise ParseError(f"objeto JSON invalido: {exc}") from exc
    raise ParseError("objeto JSON nao fechado na resposta do LLM")


def parse_proposal(text: str) -> tuple[dict, bool]:
    """Interpreta a resposta do LLM. Retorna (proposta, repair_applied)."""
    json_str, repaired = _extract_json_object(text)
    proposal = json.loads(json_str)
    if not isinstance(proposal, dict):
        raise ParseError("a resposta do LLM nao e um objeto JSON")
    return proposal, repaired


def resolve_citations(
    raw_citations: list, chunk_index: dict[str, dict],
) -> tuple[list[Citation], list[str]]:
    """Mantem so citacoes que apontam para um chunk REAL do corpus.

    Retorna (citacoes_validas, ids_descartados). Quando o chunk existe, completa
    document_id/page/snippet a partir da fonte (fonte de verdade e o corpus).
    """
    validas: list[Citation] = []
    descartadas: list[str] = []
    for item in raw_citations or []:
        if not isinstance(item, dict):
            continue
        chunk_id = item.get("chunk_id")
        fonte = chunk_index.get(chunk_id)
        if fonte is None:
            descartadas.append(str(chunk_id))
            continue
        snippet = item.get("snippet") or fonte["content"][:160]
        validas.append(Citation(
            document_id=fonte["document_id"],
            chunk_id=chunk_id,
            page=fonte.get("page"),
            version=fonte.get("version"),
            snippet=snippet,
        ))
    return validas, descartadas


def parse_rejected_routes(raw: list) -> list[RejectedRoute]:
    """Normaliza as rotas descartadas declaradas pelo LLM (para auditoria)."""
    rejeitadas: list[RejectedRoute] = []
    for item in raw or []:
        if isinstance(item, dict) and item.get("route_id"):
            rejeitadas.append(RejectedRoute(
                route_id=str(item["route_id"]),
                reason=str(item.get("reason", "")),
            ))
    return rejeitadas
