"""Enums do dominio: conjuntos fechados de valores validos (KAN-3).

Um Enum e uma lista fixa de opcoes com nome. Usar Enum no lugar de strings
soltas evita erro de digitacao e deixa num lugar so TODOS os valores possiveis.

Herdamos de StrEnum (Python 3.11+): os membros SAO strings de verdade, entao
viram o texto certo no JSON e podem ser comparados direto com uma string.
"""
from enum import StrEnum


class RiskClass(StrEnum):
    """Classe de risco do pedido, definida pela folga de tempo (slack).

    Regra do manual de SLA (DOC-05):
      - STANDARD:  slack maior que 15 min
      - ATTENTION: slack de 8 a 15 min
      - AT_RISK:   slack de 1 a 7 min
      - BREACH:    slack menor ou igual a 0 (estourou o prazo)
    """
    STANDARD = "STANDARD"
    ATTENTION = "ATTENTION"
    AT_RISK = "AT_RISK"
    BREACH = "BREACH"


class DecisionStatus(StrEnum):
    """Como a decisao terminou."""
    SUCCESS = "SUCCESS"                                # achou uma rota valida
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"    # faltou evidencia pra decidir
    ERROR = "ERROR"                                    # falha de execucao (ex: JSON invalido do LLM)

class Modal(StrEnum):
    """Meio de transporte do entregador."""
    BICICLETA = "BICICLETA"
    MOTO = "MOTO"
    CARRO = "CARRO"
    A_PE = "A_PE"


class OrderState(StrEnum):
    """Estado do pedido na linha do tempo operacional (ver DOC-01)."""
    CREATED = "CREATED"
    ASSIGNED = "ASSIGNED"
    DISPATCHED = "DISPATCHED"
    PICKED_UP = "PICKED_UP"
    DELIVERED = "DELIVERED"
    CANCELLED = "CANCELLED"

class SegmentClass(StrEnum):
    """Classe da via de um segmento (define a penalidade de chuva, DOC-03)."""
    LOCAL = "LOCAL"
    ARTERIAL = "ARTERIAL"
    EXPRESS = "EXPRESS"
    CT_BIKE = "CT-BIKE"