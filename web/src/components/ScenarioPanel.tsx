import type { Modal, OrderState, ProviderName } from "../types";

export interface Scenario {
  provider: ProviderName;
  modal: Modal;
  state: OrderState;
  decision_at: string;
  promised_at: string;
}

const MODALS: Modal[] = ["BICICLETA", "MOTO", "CARRO", "A_PE"];
const STATES: OrderState[] = [
  "CREATED",
  "ASSIGNED",
  "DISPATCHED",
  "PICKED_UP",
  "DELIVERED",
  "CANCELLED",
];

export default function ScenarioPanel({
  value,
  onChange,
  onRun,
  running,
}: {
  value: Scenario;
  onChange: (s: Scenario) => void;
  onRun: () => void;
  running: boolean;
}) {
  const set = <K extends keyof Scenario>(k: K, v: Scenario[K]) =>
    onChange({ ...value, [k]: v });

  return (
    <div className="card panel">
      <div className="scenario">
        <div className="field">
          <label>Provedor</label>
          <select
            value={value.provider}
            onChange={(e) => set("provider", e.target.value as ProviderName)}
          >
            <option value="mock">mock (fixture)</option>
            <option value="ollama">ollama (live)</option>
          </select>
        </div>

        <div className="field">
          <label>Modal</label>
          <select
            value={value.modal}
            onChange={(e) => set("modal", e.target.value as Modal)}
          >
            {MODALS.map((m) => (
              <option key={m} value={m}>
                {m}
              </option>
            ))}
          </select>
        </div>

        <div className="field">
          <label>Estado do pedido</label>
          <select
            value={value.state}
            onChange={(e) => set("state", e.target.value as OrderState)}
          >
            {STATES.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
        </div>

        <div className="field">
          <label>Decisao em (opcional)</label>
          <input
            type="datetime-local"
            value={value.decision_at}
            onChange={(e) => set("decision_at", e.target.value)}
          />
        </div>

        <div className="field">
          <label>Prometido para (opcional)</label>
          <input
            type="datetime-local"
            value={value.promised_at}
            onChange={(e) => set("promised_at", e.target.value)}
          />
        </div>

        <div className="field actions">
          <button className="btn" onClick={onRun} disabled={running}>
            {running ? "Comparando…" : "Comparar os 3 pipelines"}
          </button>
        </div>
      </div>
    </div>
  );
}
