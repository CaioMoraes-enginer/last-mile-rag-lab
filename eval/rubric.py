"""Rubrica deterministica de avaliacao (KAN-10).

Avalia uma execucao (PipelineResult) contra o gabarito do caso, por dimensoes
objetivas. A dimensao central e `correct_for_right_reasons`: a rota certa SEM
validade operacional, cobertura de evidencias ou citacoes NAO recebe nota maxima
(escopo secao 9). Toda medicao aqui e automatica (sem LLM-as-judge).
"""
from dataclasses import asdict, dataclass

from eval.cases import EvalCase
from pipelines.base import PipelineResult
from pipelines.facets import REQUIRED_FACETS, facet_of

COVERAGE_MIN = 0.6   # fração mínima de facetas citadas para "motivos certos"


@dataclass
class CaseScore:
    case_id: str
    pipeline: str
    status: str
    # decisao
    route_correct: bool
    operationally_valid: bool
    abstention_correct: bool
    # evidencias
    evidence_coverage: float      # facetas citadas / 5
    citation_precision: float     # citacoes validas / emitidas (proxy)
    has_citations: bool
    # composto (o que mais importa)
    correct_for_right_reasons: bool
    # eficiencia
    latency_ms: float
    input_tokens: int
    output_tokens: int
    context_chars: int
    estimated_cost_usd: float
    errors_count: int

    def as_dict(self) -> dict:
        return asdict(self)


def _evidence_coverage(result: PipelineResult) -> float:
    facetas = {facet_of(c.document_id) for c in result.decision.citations}
    facetas.discard(None)
    return round(len(facetas) / len(REQUIRED_FACETS), 4)


def _citation_precision(result: PipelineResult) -> float:
    citadas = len(result.decision.citations)
    descartou = any("descart" in e for e in result.errors)
    if citadas == 0:
        return 0.0
    return 0.5 if descartou else 1.0


def evaluate(case: EvalCase, result: PipelineResult, pipeline_name: str) -> CaseScore:
    d = result.decision
    gold = case.gold

    route_correct = d.selected_route == gold.selected_route
    valid = bool(d.valid)
    coverage = _evidence_coverage(result)
    precision = _citation_precision(result)
    has_cit = len(d.citations) > 0
    abstention_correct = (str(d.status) == "INSUFFICIENT_EVIDENCE") == (str(gold.status) == "INSUFFICIENT_EVIDENCE")

    correct_for_right_reasons = (
        route_correct and valid and has_cit
        and coverage >= COVERAGE_MIN and precision >= 1.0
    )

    return CaseScore(
        case_id=case.case_id, pipeline=pipeline_name, status=str(d.status),
        route_correct=route_correct, operationally_valid=valid,
        abstention_correct=abstention_correct,
        evidence_coverage=coverage, citation_precision=precision, has_citations=has_cit,
        correct_for_right_reasons=correct_for_right_reasons,
        latency_ms=round(result.telemetry.latency_ms, 2),
        input_tokens=result.telemetry.input_tokens,
        output_tokens=result.telemetry.output_tokens,
        context_chars=result.telemetry.context_chars,
        estimated_cost_usd=result.telemetry.estimated_cost_usd,
        errors_count=len(result.errors),
    )
