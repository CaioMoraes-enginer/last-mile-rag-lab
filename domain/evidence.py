"""Evidencias operacionais que o motor consome para decidir (KAN-4).

Sao os "fatos do mundo" extraidos dos documentos: o que bloqueia um segmento,
o que penaliza por chuva, o que autoriza um corredor controlado. Cada uma
carrega uma janela de vigencia, porque so vale se estiver ativa na hora da decisao.
"""
from datetime import datetime

from pydantic import BaseModel, Field

from domain.enums import Modal, OrderState, SegmentClass


class Segment(BaseModel):
    """Um trecho da malha, com sua classe (define a penalidade de chuva)."""
    segment_id: str
    segment_class: SegmentClass


class Incident(BaseModel):
    """Um bloqueio de segmento (interdicao). Invalida rotas que o usem."""
    incident_id: str
    segment_id: str
    version: str
    effective_from: datetime
    effective_to: datetime


class WeatherBulletin(BaseModel):
    """Boletim de chuva: adiciona minutos conforme a classe do segmento."""
    bulletin_id: str
    effective_from: datetime
    effective_to: datetime
    penalties_by_class: dict[SegmentClass, int] = Field(default_factory=dict)


class AccessNotice(BaseModel):
    """Aviso que autoriza um corredor controlado numa zona e janela."""
    notice_id: str
    segment_id: str
    zona: str
    version: str
    effective_from: datetime
    effective_to: datetime


class AccessPolicy(BaseModel):
    """Politica que rege o uso de corredores controlados (ex: POL-MODAL-CT-3.0).

    Define quais condicoes o pedido precisa cumprir para usar um corredor CT-BIKE.
    """
    policy_id: str
    version: str
    required_modal: Modal
    required_state: OrderState


if __name__ == "__main__":
    # Evidencias reais do cenario ORD-042 (extraidas dos DOC-02/03/04).
    incidente = Incident(
        incident_id="INC-Z03-042",
        segment_id="SG-BD",
        version="2.1",
        effective_from="2026-08-08T18:40:00-03:00",
        effective_to="2026-08-08T21:30:00-03:00",
    )
    chuva = WeatherBulletin(
        bulletin_id="WTH-Z03-018",
        effective_from="2026-08-08T18:55:00-03:00",
        effective_to="2026-08-08T20:10:00-03:00",
        penalties_by_class={"LOCAL": 1, "ARTERIAL": 6, "EXPRESS": 2, "CT-BIKE": 0},
    )
    aviso = AccessNotice(
        notice_id="ACCESS-Z03-017",
        segment_id="SG-CE",
        zona="ZONA-03",
        version="3.0",
        effective_from="2026-08-08T18:00:00-03:00",
        effective_to="2026-08-08T20:00:00-03:00",
    )
    print("INCIDENTE:", incidente.model_dump_json())
    print("CHUVA:", chuva.model_dump_json())
    print("AVISO:", aviso.model_dump_json())