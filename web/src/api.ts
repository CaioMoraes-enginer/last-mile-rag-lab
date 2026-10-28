import type { ApiErrorBody, DecideRequest, DecideResponse } from "./types";

// Base da API configuravel: default 8000 (uvicorn), sobrescrevivel na UI e
// persistido em localStorage para nao reconfigurar a cada reload.
const STORAGE_KEY = "lmrl.apiBase";
const DEFAULT_BASE = "http://localhost:8000";

export function getApiBase(): string {
  return localStorage.getItem(STORAGE_KEY) || DEFAULT_BASE;
}

export function setApiBase(base: string): void {
  localStorage.setItem(STORAGE_KEY, base.replace(/\/+$/, ""));
}

/** Erro de aplicacao com o run_id da API, para exibir de forma estavel. */
export class DecideError extends Error {
  code?: string;
  runId?: string;
  constructor(message: string, code?: string, runId?: string) {
    super(message);
    this.name = "DecideError";
    this.code = code;
    this.runId = runId;
  }
}

async function parseError(res: Response): Promise<DecideError> {
  try {
    const body = (await res.json()) as ApiErrorBody;
    const msg = body?.error?.message || `HTTP ${res.status}`;
    return new DecideError(msg, body?.error?.code, body?.run_id);
  } catch {
    return new DecideError(`HTTP ${res.status} ${res.statusText}`);
  }
}

export async function checkHealth(base = getApiBase()): Promise<boolean> {
  try {
    const res = await fetch(`${base}/health`);
    return res.ok;
  } catch {
    return false;
  }
}

export async function decide(
  req: DecideRequest,
  base = getApiBase()
): Promise<DecideResponse> {
  let res: Response;
  try {
    res = await fetch(`${base}/v1/decide`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(req),
    });
  } catch (e) {
    throw new DecideError(
      `Sem conexao com a API em ${base}. A API esta no ar?`
    );
  }
  if (!res.ok) throw await parseError(res);
  return (await res.json()) as DecideResponse;
}
