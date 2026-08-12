"""Regras de SLA: calculo de folga (slack) e classe de risco (KAN-4).

Funcoes puras (sem banco, sem LLM): entram numeros/datas, sai um resultado
deterministico. Sao a base do motor de decisao.
"""
from datetime import datetime

from domain.enums import RiskClass


def compute_slack_minutes(
    decision_at: datetime,
    promised_at: datetime,
    estimated_route_minutes: int,
) -> int:
    """Folga em minutos: quanto tempo sobra depois de rodar a rota.

    slack = (promised_at - decision_at) - estimated_route_minutes

    Positivo = sobra tempo; zero ou negativo = estoura o prazo.
    """
    minutos_ate_o_prazo = (promised_at - decision_at).total_seconds() / 60
    return round(minutos_ate_o_prazo - estimated_route_minutes)


def classify_risk(slack_minutes: int) -> RiskClass:
    """Traduz a folga em classe de risco (regra do manual de SLA, DOC-05).

      slack > 15  -> STANDARD
      slack 8..15 -> ATTENTION
      slack 1..7  -> AT_RISK
      slack <= 0  -> BREACH
    """
    if slack_minutes > 15:
        return RiskClass.STANDARD
    if slack_minutes >= 8:
        return RiskClass.ATTENTION
    if slack_minutes >= 1:
        return RiskClass.AT_RISK
    return RiskClass.BREACH


if __name__ == "__main__":
    # ORD-042: decisao 19:15, prometido 19:32 -> 17 minutos ate o prazo.
    decisao = datetime.fromisoformat("2026-08-08T19:15:00-03:00")
    prometido = datetime.fromisoformat("2026-08-08T19:32:00-03:00")

    print("ETA -> slack -> risco (prazo de 17 min):")
    for eta in (0, 2, 10, 16, 17, 25):
        slack = compute_slack_minutes(decisao, prometido, eta)
        print(f"  ETA={eta:>2}min -> slack={slack:>3}min -> {classify_risk(slack)}")
