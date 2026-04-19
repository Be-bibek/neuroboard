/**
 * WebSocket Event Ingestion Layer
 * Connects to the NeuroBoard FastAPI backend and normalizes events
 * into Zustand store updates. Runs once at app startup.
 *
 * Event types from backend:
 *   DELTA_UPDATE       → KiCad component moved/added/deleted
 *   VALIDATION_UPDATE  → New DRC / ERC violations reported
 *   EXECUTION_STATUS   → Pipeline stage changed
 *   PCB_STATE_UPDATE   → Full board state snapshot
 */

import { useNeuroStore } from "../store/useNeuroStore";
import type { DeltaEvent, ValidationViolation } from "../store/useNeuroStore";

const WS_URL = "ws://127.0.0.1:8000/ws/sync";

let socket: WebSocket | null = null;
let reconnectTimer: ReturnType<typeof setTimeout> | null = null;

function handleMessage(raw: string) {
  let event: { type: string; payload: any };
  try {
    event = JSON.parse(raw);
  } catch {
    console.warn("[NeuroSync] Invalid JSON:", raw);
    return;
  }

  const store = useNeuroStore.getState();

  switch (event.type) {
    case "DELTA_UPDATE": {
      const delta: DeltaEvent = {
        type: event.payload.delta_type,
        ref: event.payload.ref,
        payload: event.payload,
        timestamp: Date.now(),
      };
      store.pushDelta(delta);
      store.appendLog(
        `[KiCad] ${delta.type}: ${delta.ref}`
      );
      break;
    }

    case "VALIDATION_UPDATE": {
      const violations: ValidationViolation[] = (
        event.payload.violations || []
      ).map((v: any) => ({
        severity: v.severity,
        message: v.message,
        ref: v.ref,
      }));
      store.setViolations(violations);
      if (violations.length > 0) {
        store.appendLog(
          `[DRC] ${violations.filter((v) => v.severity === "error").length} errors, ` +
          `${violations.filter((v) => v.severity === "warning").length} warnings`
        );
      }
      break;
    }

    case "EXECUTION_STATUS": {
      store.setExecutionStatus(event.payload.status);
      if (event.payload.message) {
        store.appendLog(`[Pipeline] ${event.payload.message}`);
      }
      break;
    }

    case "PCB_STATE_UPDATE": {
      // Full board snapshot — log it but don't try to render it in React
      store.appendLog(
        `[Sync] Board snapshot: ${event.payload.component_count} components, ` +
        `${event.payload.net_count} nets`
      );
      break;
    }

    default:
      console.log("[NeuroSync] Unknown event:", event.type);
  }
}

function connect() {
  if (socket && socket.readyState === WebSocket.OPEN) return;

  const store = useNeuroStore.getState();
  store.setSyncStatus("DISCONNECTED");
  store.appendLog("[Sync] Connecting to backend...");

  socket = new WebSocket(WS_URL);

  socket.onopen = () => {
    store.setSyncStatus("CONNECTED");
    store.appendLog("[Sync] Connected to NeuroBoard backend ✓");
    if (reconnectTimer) clearTimeout(reconnectTimer);
  };

  socket.onmessage = (e) => handleMessage(e.data);

  socket.onerror = () => {
    store.appendLog("[Sync] WebSocket error — running in offline mode");
  };

  socket.onclose = () => {
    store.setSyncStatus("DISCONNECTED");
    store.appendLog("[Sync] Connection closed. Reconnecting in 5s...");
    reconnectTimer = setTimeout(connect, 5000);
  };
}

/**
 * Call once in main.tsx to boot the sync engine.
 * The engine handles reconnection automatically.
 */
export function initSyncEngine() {
  connect();
}

/** Send a command to the backend (e.g., ADD_MODULE) */
export function sendCommand(command: { type: string; payload: any }) {
  if (!socket || socket.readyState !== WebSocket.OPEN) {
    useNeuroStore
      .getState()
      .appendLog("[Sync] Command dropped — not connected");
    return;
  }
  socket.send(JSON.stringify(command));
}
