import { useEffect, useMemo, useState } from "react";
import ScenarioPanel, { type Scenario } from "./components/ScenarioPanel";
import PipelineColumn, { type ColState } from "./components/PipelineColumn";
import {
  DecideError,
  checkHealth,
  decide,
  getApiBase,
  setApiBase,
} from "./api";
import type { DecideRequest, PipelineName } from "./types";

const PIPELINES: PipelineName[] = ["full_context", "vector", "advanced"];

const emptyStates = (): Record<PipelineName, ColState> => ({
  full_context: { status: "idle" },
  vector: { status: "idle" },
  advanced: { status: "idle" },
});

export default function App() {
  const [scenario, setScenario] = useState<Scenario>({
    provider: "mock",
    modal: "BICICLETA",
    state: "DISPATCHED",
    decision_at: "",
    promised_at: "",
  });

  const [cols, setCols] = useState<Record<PipelineName, ColState>>(emptyStates);
  const [running, setRunning] = useState(false);
  const [apiUp, setApiUp] = useState<boolean | null>(null);
  const [apiBase, setBase] = useState(getApiBase());

  // Sonda o /health ao carregar e quando a base muda.
  useEffect(() => {
    let alive = true;
    setApiUp(null);
    checkHealth(apiBase).then((ok) => alive && setApiUp(ok));
    return () => {
      alive = false;
    };
  }, [apiBase]);

  const hasResults = PIPELINES.some((p) => cols[p].status !== "idle");

  // Veredito de convergencia: os pipelines concordam na rota?
  const verdict = useMemo(() => {
    const routes = PIPELINES.map((p) => cols[p].data?.decision.selected_route).filter(
      (r): r is string => r != null
    );
    if (routes.length < 2) return null;
    const unique = [...new Set(routes)];
    return { agree: unique.length === 1, routes: unique };
  }, [cols]);

  async function runAll() {
    setRunning(true);
    setCols(
      Object.fromEntries(
        PIPELINES.map((p) => [p, { status: "loading" }])
      ) as Record<PipelineName, ColState>
    );

    await Promise.all(
      PIPELINES.map(async (pipeline) => {
        const req: DecideRequest = {
          pipeline,
          provider: scenario.provider,
          modal: scenario.modal,
          state: scenario.state,
          decision_at: scenario.decision_at
            ? new Date(scenario.decision_at).toISOString()
            : null,
          promised_at: scenario.promised_at
            ? new Date(scenario.promised_at).toISOString()
            : null,
        };
        try {
          const data = await decide(req, apiBase);
          setCols((prev) => ({ ...prev, [pipeline]: { status: "done", data } }));
        } catch (e) {
          const error =
            e instanceof DecideError ? e : new DecideError(String(e));
          setCols((prev) => ({ ...prev, [pipeline]: { status: "error", error } }));
        }
      })
    );
    setRunning(false);
  }

  function commitBase(next: string) {
    const clean = next.trim().replace(/\/+$/, "");
    if (!clean) return;
    setApiBase(clean);
    setBase(clean);
  }

  return (
    <div className="app">
      <header className="topbar">
        <div className="brand">
          <div className="logo">🛵</div>
          <div>
            <h1>Last Mile RAG Lab</h1>
            <p className="sub">
              Comparador de decisao de rota · 3 pipelines, o mesmo contrato ·
              ORD-042
            </p>
          </div>
        </div>

        <div className="api-status">
          <span
            className={`dot ${apiUp === null ? "" : apiUp ? "on" : "off"}`}
          />
          {apiUp === null
            ? "checando API…"
            : apiUp
            ? "API online"
            : "API offline"}
          <input
            className="api-base-input"
            defaultValue={apiBase}
            spellCheck={false}
            title="Base da API"
            onBlur={(e) => commitBase(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") (e.target as HTMLInputElement).blur();
            }}
          />
        </div>
      </header>

      <ScenarioPanel
        value={scenario}
        onChange={setScenario}
        onRun={runAll}
        running={running}
      />

      {verdict && (
        <div className="summary">
          <span className={`verdict ${verdict.agree ? "agree" : "diverge"}`}>
            {verdict.agree ? (
              <>✓ Os pipelines convergiram na rota {verdict.routes[0]}</>
            ) : (
              <>⚠ Divergencia: rotas {verdict.routes.join(" · ")}</>
            )}
          </span>
        </div>
      )}

      <div className="columns" style={{ marginTop: verdict ? 0 : 20 }}>
        {!hasResults ? (
          <div className="placeholder">
            <div className="big">🧭</div>
            <h3>Monte um cenario e compare os pipelines</h3>
            <p>
              A mesma pergunta de rota passa pelos tres pipelines (P1 contexto
              completo, P2 vetorial, P3 avancado). Cada coluna mostra a decisao,
              a validacao pelo motor deterministico, as evidencias e a
              telemetria.
            </p>
          </div>
        ) : (
          PIPELINES.map((p) => (
            <PipelineColumn key={p} pipeline={p} state={cols[p]} />
          ))
        )}
      </div>

      <p className="footer-note">
        KAN-12 · consome <code>POST /v1/decide</code> da API (KAN-11). Fonte de
        verdade dos numeros: motor deterministico (KAN-4).
      </p>
    </div>
  );
}
