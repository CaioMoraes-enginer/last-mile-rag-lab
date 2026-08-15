"""Testes do harness de avaliacao (KAN-10).

Testam a RUBRICA com resultados sinteticos (para checar penalizacoes) e o runner
em modo fixture (deterministico, sem API).
"""
from domain.decision import Citation, DecisionResponse
from eval.cases import build_cases
from eval.report import aggregate
from eval.rubric import evaluate
from eval.runner import RunConfig, run_harness
from pipelines.base import ContextBundle, PipelineResult, Telemetry

CANONICO = build_cases()[0]   # gabarito = rota C


def _result(route="C", valid=True, citations=None, errors=None) -> PipelineResult:
    decision = DecisionResponse(
        order_id="ORD-042", decision_timestamp="2026-08-08T19:15:00-03:00",
        selected_route=route, valid=valid, citations=citations or [],
        status="SUCCESS" if route else "INSUFFICIENT_EVIDENCE",
    )
    return PipelineResult(
        pipeline_name="x", pipeline_version="1", decision=decision,
        telemetry=Telemetry(input_tokens=10, output_tokens=5, context_chars=100),
        context=ContextBundle(text="", chunk_ids=[], corpus_hash="h"),
        errors=errors or [],
    )


def _cit(doc, cid):
    return Citation(document_id=doc, chunk_id=cid)


# ---- rubrica ------------------------------------------------------------------

def test_gold_is_computed_not_hardcoded():
    casos = {c.case_id: c.gold.selected_route for c in build_cases()}
    assert casos["canonico"] == "C"
    assert casos["modal_moto"] == "B"       # contrafactual muda o gabarito
    assert casos["horario_apos_20h"] == "B"


def test_correct_route_without_evidence_is_not_full_marks():
    """Rota certa, mas SEM citacoes -> nao recebe 'motivos certos'."""
    score = evaluate(CANONICO, _result(route="C", citations=[]), "x")
    assert score.route_correct is True
    assert score.correct_for_right_reasons is False


def test_full_marks_when_grounded_and_covered():
    cits = [_cit("DOC-03", "DOC-03-P01-C01"), _cit("DOC-04", "DOC-04-P01-C01"),
            _cit("DOC-05", "DOC-05-P01-C01")]   # 3 facetas = 0.60
    score = evaluate(CANONICO, _result(route="C", citations=cits), "x")
    assert score.evidence_coverage >= 0.6
    assert score.correct_for_right_reasons is True


def test_dropped_citation_penalizes_precision():
    cits = [_cit("DOC-03", "DOC-03-P01-C01"), _cit("DOC-04", "DOC-04-P01-C01"),
            _cit("DOC-05", "DOC-05-P01-C01")]
    score = evaluate(CANONICO, _result(citations=cits, errors=["citacoes descartadas: ['Z']"]), "x")
    assert score.citation_precision == 0.5
    assert score.correct_for_right_reasons is False


def test_wrong_route_is_not_correct():
    score = evaluate(CANONICO, _result(route="A"), "x")
    assert score.route_correct is False
    assert score.correct_for_right_reasons is False


# ---- runner (fixture) ---------------------------------------------------------

def test_harness_runs_all_pipelines_over_all_cases():
    out = run_harness(RunConfig(provider="mock"))
    pipelines = {r.pipeline for r in out.records}
    assert pipelines == {"full_context", "vector", "advanced"}
    assert len(out.records) == 3 * len(build_cases())        # 3 pipelines x N casos


def test_fixture_run_is_deterministic():
    a = aggregate(run_harness(RunConfig(provider="mock")))
    b = aggregate(run_harness(RunConfig(provider="mock")))
    assert a == b


def test_failures_counted_in_denominator():
    """Fixture cita 1 chunk (cobertura baixa) -> conta como falha de 'motivos certos'."""
    agg = aggregate(run_harness(RunConfig(provider="mock")))
    assert agg["vector"]["route_accuracy"] == 1.0            # fixture acerta a rota
    assert agg["vector"]["failures"] >= 1                    # mas sem cobertura, nao e nota maxima
