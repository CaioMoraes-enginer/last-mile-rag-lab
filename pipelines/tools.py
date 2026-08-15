"""Ferramentas deterministicas (KAN-9).

O P3 nao pede ao LLM para calcular nada: ele DELEGA as regras duras ao motor
(KAN-4), chamado como ferramenta. Cada chamada tem schema tipado, validacao de
entrada e fica registrada (nome + args + resultado) para auditoria.

O motor e a fonte de verdade: o LLM sugere a rota; a ferramenta valida e calcula.
Se o LLM divergir do motor, a divergencia e registrada (nunca sobrescreve).
"""
from dataclasses import dataclass, field

from pydantic import BaseModel, ValidationError

from engine.decider import decide, evaluate_route
from domain.decision import DecisionResponse


class RouteValidationArgs(BaseModel):
    """Schema de entrada da ferramenta de validacao de rota."""
    route_id: str


@dataclass
class ToolCall:
    """Registro auditavel de uma chamada de ferramenta."""
    name: str
    args: dict
    result: dict
    ok: bool = True
    error: str | None = None


@dataclass
class ToolRunner:
    """Executa as ferramentas do motor sobre um cenario e registra as chamadas."""
    scenario: dict
    calls: list[ToolCall] = field(default_factory=list)

    def gold_decision(self) -> dict:
        """Ferramenta: decisao ouro do motor (rota valida mais rapida)."""
        gold: DecisionResponse = decide(**self.scenario)
        result = {
            "selected_route": gold.selected_route,
            "valid": gold.valid,
            "estimated_minutes": gold.estimated_minutes,
            "slack_minutes": gold.slack_minutes,
            "risk_class": str(gold.risk_class) if gold.risk_class else None,
            "status": str(gold.status),
        }
        self.calls.append(ToolCall(name="gold_decision", args={}, result=result))
        return result

    def validate_route(self, route_id) -> dict:
        """Ferramenta: valida UMA rota (validade + ETA/slack/risco), com validacao de entrada."""
        try:
            args = RouteValidationArgs(route_id=str(route_id))
        except ValidationError as exc:
            call = ToolCall(name="validate_route", args={"route_id": route_id},
                            result={}, ok=False, error=str(exc))
            self.calls.append(call)
            return {"ok": False, "error": "args invalidos"}

        route = next((r for r in self.scenario["routes"] if r.route_id == args.route_id), None)
        if route is None:
            result = {"ok": False, "error": f"rota {args.route_id} inexistente"}
            self.calls.append(ToolCall(name="validate_route", args=args.model_dump(),
                                       result=result, ok=False, error=result["error"]))
            return result

        segment_class = {s.segment_id: s.segment_class for s in self.scenario["segments"]}
        ev = evaluate_route(
            route, self.scenario["order"], segment_class,
            self.scenario["incidents"], self.scenario["bulletin"],
            self.scenario["notices"], self.scenario["policy"],
        )
        result = {
            "ok": True, "route_id": ev.route_id, "valid": ev.valid,
            "estimated_minutes": ev.estimated_minutes, "slack_minutes": ev.slack_minutes,
            "risk_class": str(ev.risk_class) if ev.risk_class else None,
            "reject_reason": ev.reject_reason,
        }
        self.calls.append(ToolCall(name="validate_route", args=args.model_dump(), result=result))
        return result

    def audit(self) -> list[dict]:
        """Trace das chamadas para o artefato."""
        return [
            {"name": c.name, "args": c.args, "result": c.result, "ok": c.ok, "error": c.error}
            for c in self.calls
        ]
