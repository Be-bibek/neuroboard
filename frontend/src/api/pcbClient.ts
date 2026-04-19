/**
 * api/pcbClient.ts
 * HTTP API client for the NeuroBoard FastAPI backend.
 * Phase 8.2 — Direct POST calls for PCB module placement.
 */

const API_BASE = "http://127.0.0.1:8000";

// ── Types ──────────────────────────────────────────────────────────────────

export interface AddModuleResponse {
  status: string;
  intent: string;
  resolved_sequence: string[];
  execution_results: Array<{
    module: string;
    status: "success" | "failed";
    placed_at?: [number, number];
    reason?: string;
  }>;
}

// ── API Client ─────────────────────────────────────────────────────────────

/**
 * POST /api/v1/pcb/add_module
 * Sends a module intent to the backend.
 * The backend resolves dependencies and places all required components in KiCad.
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
