"""Relatorios do harness (KAN-10).

Gera um resumo legivel por maquina (dict/JSON) e um relatorio legivel por humanos
(Markdown): tabela lado a lado das dimensoes, matriz por caso e analise de falhas.
Toda medicao aqui e automatica (deterministica); nao ha julgamento por LLM.
"""
from statistics import mean

from eval.runner import HarnessOutput


def _rate(valores: list[bool]) -> float:
    return round(mean([1.0 if v else 0.0 for v in valores]), 4) if valores else 0.0


def aggregate(out: HarnessOutput) -> dict:
    """Metricas agregadas por pipeline (falhas incluidas no denominador)."""
    por_pipeline: dict[str, list] = {}
    for rec in out.records:
        por_pipeline.setdefault(rec.pipeline, []).append(rec.score)

    agregado = {}
    for pipeline, scores in por_pipeline.items():
        status_counts: dict[str, int] = {}
        for s in scores:
            status_counts[s.status] = status_counts.get(s.status, 0) + 1
        agregado[pipeline] = {
            "n": len(scores),
            "route_accuracy": _rate([s.route_correct for s in scores]),
            "correct_for_right_reasons": _rate([s.correct_for_right_reasons for s in scores]),
            "operational_validity": _rate([s.operationally_valid for s in scores]),
            "evidence_coverage": round(mean([s.evidence_coverage for s in scores]), 4),
            "citation_precision": round(mean([s.citation_precision for s in scores]), 4),
            "avg_latency_ms": round(mean([s.latency_ms for s in scores]), 2),
            "avg_output_tokens": round(mean([s.output_tokens for s in scores]), 1),
            "avg_context_chars": round(mean([s.context_chars for s in scores]), 1),
            "avg_cost_usd": round(mean([s.estimated_cost_usd for s in scores]), 6),
            "status_counts": status_counts,
            "failures": sum(1 for s in scores if not s.correct_for_right_reasons),
        }
    return agregado


def to_json(out: HarnessOutput) -> dict:
    return {
        "config": out.config,
        "aggregate": aggregate(out),
        "records": [
            {"case_id": r.case_id, "pipeline": r.pipeline, "repeat": r.repeat,
             "score": r.score.as_dict(), "engine_validation": r.engine_validation,
             "provenance": r.provenance}
            for r in out.records
        ],
    }


def _mark(ok: bool) -> str:
    return "OK" if ok else "--"


def to_markdown(out: HarnessOutput) -> str:
    agg = aggregate(out)
    linhas: list[str] = []
    linhas.append("# Benchmark comparativo dos pipelines (KAN-10)\n")
    cfg = out.config
    linhas.append(
        f"Provedor: **{cfg['provider']}** · modelo: `{cfg['model']}` · "
        f"embedding: `{cfg['embedding_model']}` · repeticoes: {cfg['n_repeats']} · seed: {cfg['seed']}\n"
    )
    linhas.append("> Medicao 100% automatica (deterministica). Falhas incluidas no denominador.\n")

    # tabela lado a lado
    linhas.append("## Resumo por pipeline\n")
    linhas.append("| Pipeline | Acerto rota | Motivos certos | Validade | Cobertura | Precisao cit. | Latencia (ms) | Tokens out | Contexto (chars) |")
    linhas.append("|---|--:|--:|--:|--:|--:|--:|--:|--:|")
    for p, a in agg.items():
        linhas.append(
            f"| {p} | {a['route_accuracy']:.0%} | **{a['correct_for_right_reasons']:.0%}** | "
            f"{a['operational_validity']:.0%} | {a['evidence_coverage']:.2f} | {a['citation_precision']:.2f} | "
            f"{a['avg_latency_ms']:.0f} | {a['avg_output_tokens']:.0f} | {a['avg_context_chars']:.0f} |"
        )

    # matriz por caso (motivos certos)
    linhas.append("\n## Matriz por caso (correto pelos motivos certos)\n")
    pipelines = list(agg.keys())
    linhas.append("| Caso | " + " | ".join(pipelines) + " |")
    linhas.append("|---" + "|---" * len(pipelines) + "|")
    casos = _cases_order(out)
    for caso in casos:
        celulas = []
        for p in pipelines:
            recs = [r for r in out.records if r.case_id == caso and r.pipeline == p]
            ok = bool(recs) and all(r.score.correct_for_right_reasons for r in recs)
            celulas.append(_mark(ok))
        linhas.append(f"| {caso} | " + " | ".join(celulas) + " |")

    # analise de falhas
    linhas.append("\n## Analise de falhas\n")
    falhas = [r for r in out.records if not r.score.correct_for_right_reasons]
    if not falhas:
        linhas.append("Nenhuma falha registrada.")
    for r in falhas:
        s = r.score
        motivo = []
        if not s.route_correct:
            motivo.append("rota incorreta")
        if not s.operationally_valid:
            motivo.append("rota invalida")
        if not s.has_citations:
            motivo.append("sem citacoes")
        elif s.evidence_coverage < 0.6:
            motivo.append(f"cobertura baixa ({s.evidence_coverage:.2f})")
        if s.citation_precision < 1.0 and s.has_citations:
            motivo.append("citacao descartada")
        linhas.append(f"- **{r.pipeline}** / `{r.case_id}` (status {s.status}): {', '.join(motivo) or 'ver score'}")

    return "\n".join(linhas) + "\n"


def _cases_order(out: HarnessOutput) -> list[str]:
    vistos: list[str] = []
    for r in out.records:
        if r.case_id not in vistos:
            vistos.append(r.case_id)
    return vistos
