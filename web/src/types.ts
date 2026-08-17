// Espelho TypeScript dos contratos da API (KAN-11).
// Fonte de verdade: api/models.py (DecideResponse) + domain/decision.py (KAN-3).

export type PipelineName = "full_context" | "vector" | "advanced";
export type ProviderName = "mock" | "ollama";

export type Modal = "BICICLETA" | "MOTO" | "CARRO" | "A_PE";
export type OrderState =
  | "CREATED"
  | "ASSIGNED"
  | "DISPATCHED"
  | "PICKED_UP"
  | "DELIVERED"
  | "CANCELLED";

export type RiskClass = "STANDARD" | "ATTENTION" | "AT_RISK" | "BREACH";
export type DecisionStatus = "SUCCESS" | "INSUFFICIENT_EVIDENCE" | "ERROR";

export interface Citation {
  document_id: string;
  chunk_id: string;
  page?: number | null;
  version?: string | null;
  snippet?: string | null;
}

export interface RejectedRoute {
  route_id: string;
  reason: string;
}

export interface Decision {
  order_id: string;
  decision_timestamp: string;
  selected_route: string | null;
  valid: boolean;
  estimated_minutes: number | null;
  slack_minutes: number | null;
  risk_class: RiskClass | null;
  recommended_action: string;
  constraints_checked: string[];
  rejected_routes: RejectedRoute[];
  citations: Citation[];
  confidence: number;
  status: DecisionStatus;
}

// Item de recuperacao. `score` vem do P2 (vetorial); `rrf_score` + `contributions`
// vem do P3 (fusao hibrida). O baseline P1 devolve a lista vazia.
export interface RetrievalItem {
  rank: number;
  chunk_id: string;
  document_id: string;
  page?: number | null;
  score?: number;
  rrf_score?: number;
  contributions?: Record<string, number>;
}

export interface Telemetry {
  input_tokens: number;
  output_tokens: number;
  latency_ms: number;
  context_chars: number;
  estimated_cost_usd: number;
}

export interface EngineValidation {
  gold_route: string | null;
  gold_valid: boolean;
  gold_estimated_minutes: number | null;
  gold_slack_minutes: number | null;
  gold_risk_class: RiskClass | null;
  gold_status: DecisionStatus;
  llm_route: string | null;
  llm_route_valid: boolean;
  route_agreement: boolean;
}

export interface DecideRequest {
  pipeline: PipelineName;
  provider: ProviderName;
  modal: Modal;
  state: OrderState;
  decision_at?: string | null;
  promised_at?: string | null;
}

export interface DecideResponse {
  run_id: string;
  pipeline: string;
  source: "fixture" | "live";
  decision: Decision;
  retrieval: RetrievalItem[];
  telemetry: Telemetry;
  engine_validation?: EngineValidation | null;
  errors: string[];
}

// Formato estavel de erro da API (api/errors.py).
export interface ApiErrorBody {
  error: { code?: string; message?: string; [k: string]: unknown };
  run_id: string;
}
