"""Prompts versionados dos pipelines (KAN-7).

Versionar o prompt e requisito de reprodutibilidade (RNF-01): o texto exato entra
na proveniencia de cada resultado. A versao atual e `full_context_v1`.

Principios embutidos (escopo secoes 6 e 11):
  - instrucoes, pedido e documentos ficam separados por delimitadores claros;
  - o LLM SUGERE a rota e cita evidencias; NAO calcula ETA/slack (isso e do motor);
  - toda alegacao relevante precisa de citacao (chunk_id + pagina);
  - se faltar evidencia, o LLM se abstem (INSUFFICIENT_EVIDENCE);
  - o prompt nao revela nem assume qual rota e a correta.
"""
from domain.models import Order, RouteCandidate

FULL_CONTEXT_VERSION = "full_context_v1"

_INSTRUCTIONS = """\
Voce e um analista de operacoes de last-mile. Sua tarefa e escolher a MELHOR rota
VALIDA (a que minimiza o tempo de entrega) para o pedido, usando SOMENTE as
evidencias dos documentos fornecidos.

Regras:
- Analise CADA rota candidata (A, B, C) individualmente: diga se e valida e por que.
- Baseie-se apenas nos documentos abaixo. Nao invente fatos.
- NAO calcule minutos de ETA, slack ou risco: um motor deterministico faz isso.
  Seu papel e escolher a rota e sustentar com evidencias.
- Toda alegacao relevante (bloqueio, chuva, politica, aviso, SLA) precisa de uma
  citacao apontando chunk_id + pagina do documento que a sustenta.
- Se as evidencias forem insuficientes para decidir, use status
  "INSUFFICIENT_EVIDENCE" e selected_route = null.
- Responda SOMENTE com um objeto JSON valido, sem texto antes ou depois.

Formato EXATO do JSON de saida:
{
  "selected_route": "A" | "B" | "C" | null,
  "status": "SUCCESS" | "INSUFFICIENT_EVIDENCE",
  "confidence": <numero entre 0 e 1>,
  "recommended_action": "<acao recomendada em uma frase>",
  "rejected_routes": [
    {"route_id": "A", "reason": "<motivo com evidencia>"}
  ],
  "citations": [
    {"document_id": "DOC-03", "chunk_id": "DOC-03-P02-C01", "page": 2, "snippet": "<trecho curto>"}
  ]
}"""


def render_decision_prompt(order: Order, routes: list[RouteCandidate], context_text: str) -> str:
    """Monta o prompt de decisao (compartilhado por P1/P2).

    As instrucoes e o formato de saida sao os mesmos; a diferenca entre os
    pipelines esta apenas no `context_text` (corpus integral vs. chunks top-k).
    """
    pedido = (
        f"order_id: {order.order_id}\n"
        f"zona: {order.zona}\n"
        f"modal: {order.modal}\n"
        f"estado: {order.state}\n"
        f"decision_at: {order.decision_at.isoformat()}\n"
        f"promised_at: {order.promised_at.isoformat()}"
    )
    rotas = "\n".join(
        f"- Rota {r.route_id}: segmentos {r.segments} (custo nominal {r.nominal_cost_minutes} min)"
        for r in routes
    )
    return (
        f"{_INSTRUCTIONS}\n\n"
        f"===== PEDIDO =====\n{pedido}\n\n"
        f"===== ROTAS CANDIDATAS =====\n{rotas}\n\n"
        f"===== DOCUMENTOS (CORPUS) =====\n{context_text}\n\n"
        f"===== FIM DOS DOCUMENTOS =====\n"
        f"Responda agora SOMENTE com o JSON."
    )


# Compatibilidade: nome historico usado pelo pipeline P1.
render_full_context = render_decision_prompt
