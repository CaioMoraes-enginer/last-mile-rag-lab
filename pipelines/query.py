"""Construcao da consulta de recuperacao (KAN-8).

Deriva uma consulta ESTAVEL do pedido para a busca vetorial. A consulta descreve
o que precisamos saber (bloqueios, acesso, clima, SLA) sem conter a rota ouro nem
texto copiado do gabarito (criterio de aceite). Versionada para reprodutibilidade.
"""
from domain.models import Order

QUERY_VERSION = "vector_query_v1"


def build_retrieval_query(order: Order) -> str:
    """Consulta derivada do pedido, sem gabarito."""
    return (
        f"Pedido {order.order_id} na zona {order.zona}, modal {order.modal}, "
        f"estado {order.state}, decisao as {order.decision_at.isoformat()}. "
        "Quais segmentos estao bloqueados por incidentes ativos, quais corredores "
        "controlados exigem aviso de acesso e politica de modal, quais penalidades "
        "de clima se aplicam por classe de via e quais regras de SLA e prazo valem "
        "para escolher a rota operacionalmente valida mais rapida."
    )
