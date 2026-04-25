/**
 * api/pcbClient.ts — Phase 8.3
 * HTTP API client for the NeuroBoard FastAPI backend.
 */

const API_BASE = "http://localhost:8000";

// ── Types ──────────────────────────────────────────────────────────────────

export interface NetResult {
  net: string;
  status: "created" | "warn";
}

export interface PinConnection {
  pad: string;
  net: string;
  status: "ok" | "warn";
}

export interface PlacementResult {
  module: string;
  status: "success" | "warn" | "failed";
  placed_at?: [number, number];
  reason?: string;
  net_connections: PinConnection[];
}

export interface AddModuleResponse {
  status: string;
  intent: string;
  resolved_sequence: string[];
  nets_created: NetResult[];
  execution_results: PlacementResult[];
}

// ── API Client ─────────────────────────────────────────────────────────────

/**
 * POST /api/v1/pcb/add_module
 * Resolves module dependencies, creates nets, places footprints, and connects pins.
 */
export async function addModule(moduleName: string): Promise<AddModuleResponse> {
  const resp = await fetch(`${API_BASE}/api/v1/pcb/add_module`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ module: moduleName }),
  });

  if (!resp.ok) {
    const errText = await resp.text();
    throw new Error(`Backend error ${resp.status}: ${errText}`);
  }

  return resp.json() as Promise<AddModuleResponse>;
}

/**
 * POST /api/v1/pcb/inject_decoupling
 */
export async function injectDecoupling(targetRef: string = "J3"): Promise<any> {
  const resp = await fetch(`${API_BASE}/api/v1/pcb/inject_decoupling`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ target_ref: targetRef }),
  });

  if (!resp.ok) {
    const errText = await resp.text();
    throw new Error(`Backend error ${resp.status}: ${errText}`);
  }
  return resp.json();
}

/**
 * POST /api/v1/pcb/save
 */
export async function saveBoard(): Promise<any> {
  const resp = await fetch(`${API_BASE}/api/v1/pcb/save`, {
    method: "POST",
  });

  if (!resp.ok) {
    const errText = await resp.text();
    throw new Error(`Backend error ${resp.status}: ${errText}`);
  }
  return resp.json();
}
