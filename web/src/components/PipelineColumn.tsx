import type { DecideResponse, PipelineName, RetrievalItem } from "../types";
import { DecideError } from "../api";
import { Bar, Chip, RiskChip, Section } from "./bits";

export interface ColState {
  status: "idle" | "loading" | "done" | "error";
  data?: DecideResponse;
  error?: DecideError;
}

const META: Record<
  PipelineName,
  { label: string; tag: string; color: string }
> = {
  full_context: {
    label: "Contexto completo",
    tag: "P1 · sem recuperacao",
    color: "var(--p-full)",
  },
  vector: {
    label: "RAG vetorial",
    tag: "P2 · busca densa",
    color: "var(--p-vector)",
  },
  advanced: {
    label: "RAG avancado",
    tag: "P3 · hibrido + rerank + tools",
    color: "var(--p-advanced)",
  },
};

function scoreOf(it: RetrievalItem): number | undefined {
  return it.rrf_score ?? it.score;
}

function RetrievalTable({ items }: { items: RetrievalItem[] }) {
  if (!items.length)
    return (
      <p className="empty-note">
        Sem ranking — este pipeline entrega o corpus inteiro ao modelo (sem
        etapa de recuperacao).
      </p>
    );

  const scores = items.map((i) => scoreOf(i) ?? 0);
  const max = Math.max(...scores, 0.000001);
  const hybrid = items.some((i) => i.contributions);

  return (
    <table className="retr-table">
      <thead>
        <tr>
          <th>#</th>
          <th>chunk</th>
          <th>pg</th>
          <th>{hybrid ? "rrf" : "score"}</th>
          <th className="scorebar-cell"></th>
        </tr>
      </thead>
      <tbody>
        {items.slice(0, 8).map((it) => {
          const s = scoreOf(it) ?? 0;
          return (
            <tr key={it.chunk_id}>
              <td>{it.rank}</td>
              <td>
                <div className="chunk">{it.chunk_id}</div>
                {it.contributions && (
                  <div className="contrib">
                    {Object.entries(it.contributions)
                      .slice(0, 6)
                      .map(([k, v]) => (
                        <span className="src" key={k}>
                          {k}:{v}
                        </span>
                      ))}
                  </div>
                )}
              </td>
              <td>{it.page ?? "—"}</td>
              <td className="score">{s.toFixed(3)}</td>
              <td className="scorebar-cell">
                <div className="scorebar">
                  <span style={{ width: `${(s / max) * 100}%` }} />
                </div>
              </td>
            </tr>
          );
        })}
      </tbody>
    </table>
  );
}

export default function PipelineColumn({
  pipeline,
  state,
}: {
  pipeline: PipelineName;
  state: ColState;
}) {
  const meta = META[pipeline];
  const styleVar = { ["--col" as string]: meta.color } as React.CSSProperties;

  return (
    <div className="card pcol" style={styleVar}>
      <div className="head">
        <div>
          <div className="name">{meta.label}</div>
          <div className="tag">{meta.tag}</div>
        </div>
        {state.status === "done" && state.data && (
          <Chip className={state.data.source === "live" ? "badge-ok" : ""}>
            {state.data.source}
          </Chip>
        )}
      </div>

      {state.status === "idle" && (
        <div className="col-state skeleton-hint">Aguardando execucao…</div>
      )}

      {state.status === "loading" && (
        <div className="col-state">
          <div className="spinner" />
          Consultando o pipeline…
        </div>
      )}

      {state.status === "error" && state.error && (
        <div className="body">
          <div className="col-error">
            <strong>Falhou:</strong> {state.error.message}
            {(state.error.code || state.error.runId) && (
              <div className="code">
                {state.error.code && <>code={state.error.code} </>}
                {state.error.runId && <>run_id={state.error.runId}</>}
              </div>
            )}
          </div>
        </div>
      )}

      {state.status === "done" && state.data && (
        <Body data={state.data} color={meta.color} />
      )}
    </div>
  );
}

function Body({ data, color }: { data: DecideResponse; color: string }) {
  const d = data.decision;
  const ev = data.engine_validation;
  const t = data.telemetry;

  return (
    <div className="body">
      {/* Decisao principal */}
      <div className="decision-hero">
        <div className={`route-badge ${d.selected_route ? "" : "none"}`}>
          {d.selected_route ?? "—"}
        </div>
        <div className="decision-meta">
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
            <RiskChip risk={d.risk_class} />
            <Chip className={d.valid ? "badge-ok" : "badge-no"}>
              {d.valid ? "valida" : "invalida"}
            </Chip>
            <Chip className={`status-${d.status}`}>{d.status}</Chip>
          </div>
          <div className="decision-action">{d.recommended_action || "—"}</div>
        </div>
      </div>

      <div className="metric-row">
        <div className="metric">
          <div className="k">tempo est.</div>
          <div className="v">
            {d.estimated_minutes ?? "—"}
            <span style={{ fontSize: 11, color: "var(--text-faint)" }}> min</span>
          </div>
        </div>
        <div className="metric">
          <div className="k">folga (slack)</div>
          <div className="v">
            {d.slack_minutes ?? "—"}
            <span style={{ fontSize: 11, color: "var(--text-faint)" }}> min</span>
          </div>
        </div>
        <div className="metric" style={{ flex: 1 }}>
          <div className="k">confianca · {(d.confidence * 100).toFixed(0)}%</div>
          <div style={{ marginTop: 8 }}>
            <Bar value={d.confidence} />
          </div>
        </div>
      </div>

      {/* Validacao pelo motor deterministico (fonte de verdade) */}
      {ev && (
        <div
          className="section open"
          style={{ borderTopColor: "var(--border)" }}
        >
          <div className="section-title" style={{ marginBottom: 10 }}>
            Motor deterministico
            <Chip className={ev.route_agreement ? "badge-ok" : "badge-no"}>
              {ev.route_agreement ? "LLM = motor" : "LLM ≠ motor"}
            </Chip>
          </div>
          <div className="metric-row">
            <div className="metric">
              <div className="k">rota ouro</div>
              <div className="v" style={{ color }}>
                {ev.gold_route ?? "—"}
              </div>
            </div>
            <div className="metric">
              <div className="k">rota do LLM</div>
              <div className="v">{ev.llm_route ?? "—"}</div>
            </div>
            <div className="metric">
              <div className="k">motor: status</div>
              <div className="v" style={{ fontSize: 13 }}>
                {ev.gold_status}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Evidencias */}
      <Section
        title="Restricoes checadas"
        count={d.constraints_checked.length}
        defaultOpen={d.constraints_checked.length > 0}
      >
        <div className="constraints">
          {d.constraints_checked.length ? (
            d.constraints_checked.map((c) => <Chip key={c}>{c}</Chip>)
          ) : (
            <span className="empty-note">nenhuma</span>
          )}
        </div>
      </Section>

      <Section title="Citacoes" count={d.citations.length}>
        {d.citations.length ? (
          d.citations.map((c, i) => (
            <div className="cite" key={i}>
              <div className="ids">
                {c.document_id} · {c.chunk_id}
                {c.page != null ? ` · p.${c.page}` : ""}
                {c.version ? ` · v${c.version}` : ""}
              </div>
              {c.snippet && <div className="snippet">“{c.snippet}”</div>}
            </div>
          ))
        ) : (
          <span className="empty-note">
            Nenhuma citacao retornada nesta execucao.
          </span>
        )}
      </Section>

      <Section title="Rotas descartadas" count={d.rejected_routes.length}>
        {d.rejected_routes.length ? (
          d.rejected_routes.map((r, i) => (
            <div className="rejected" key={i}>
              <span className="rid">{r.route_id}</span>
              <span className="reason">{r.reason}</span>
            </div>
          ))
        ) : (
          <span className="empty-note">nenhuma</span>
        )}
      </Section>

      <Section
        title="Recuperacao (retrieval)"
        count={data.retrieval.length}
        defaultOpen={data.retrieval.length > 0}
      >
        <RetrievalTable items={data.retrieval} />
      </Section>

      {data.errors.length > 0 && (
        <div className="col-error">
          {data.errors.map((e, i) => (
            <div key={i}>{e}</div>
          ))}
        </div>
      )}

      {/* Telemetria */}
      <div className="telemetry">
        <div className="tele">
          <span className="k">latencia</span>
          <span className="v">{t.latency_ms.toFixed(0)} ms</span>
        </div>
        <div className="tele">
          <span className="k">contexto</span>
          <span className="v">{t.context_chars.toLocaleString()} ch</span>
        </div>
        <div className="tele">
          <span className="k">tokens in</span>
          <span className="v">{t.input_tokens.toLocaleString()}</span>
        </div>
        <div className="tele">
          <span className="k">tokens out</span>
          <span className="v">{t.output_tokens.toLocaleString()}</span>
        </div>
      </div>

      <div className="runid">run_id: {data.run_id}</div>
    </div>
  );
}
