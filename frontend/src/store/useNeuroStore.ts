import { create } from "zustand";
import type { PCBTemplate, PCBModule } from "../templates/registry";

// ── Types ──────────────────────────────────────────────────────────────────

export type UIView = "TEMPLATE_SELECT" | "SIDEBAR" | "PLANNING_BOARD";
export type ExecutionStatus = "IDLE" | "COMPILING" | "ROUTING" | "VALIDATING" | "DONE" | "ERROR";
export type SyncStatus = "DISCONNECTED" | "CONNECTED" | "SYNCING";

export interface DeltaEvent {
  type: "COMPONENT_ADD" | "COMPONENT_MOVE" | "NET_UPDATE" | "COMPONENT_DELETE";
  ref: string;
  payload: Record<string, any>;
  timestamp: number;
}

export interface ValidationViolation {
  severity: "error" | "warning";
  message: string;
  ref?: string;
}

// ── Global Zustand Store ───────────────────────────────────────────────────

interface NeuroStore {
  // ── Phase 1: UI View ──
  view: UIView;
  setView: (v: UIView) => void;

  // ── Phase 1: Template ──
  selectedTemplate: PCBTemplate | null;
  selectTemplate: (t: PCBTemplate) => void;
  clearTemplate: () => void;

  // ── Phase 2: Active Modules on the board ──
  activeModules: PCBModule[];
  addModule: (m: PCBModule) => void;
  removeModule: (id: string) => void;

  // ── Phase 4: Sync Engine State ──
  syncStatus: SyncStatus;
  setSyncStatus: (s: SyncStatus) => void;
  deltaQueue: DeltaEvent[];
  pushDelta: (d: DeltaEvent) => void;

  // ── Execution Status ──
  executionStatus: ExecutionStatus;
  setExecutionStatus: (s: ExecutionStatus) => void;
  executionLogs: string[];
  appendLog: (msg: string) => void;
  clearLogs: () => void;

  // ── Validation ──
  violations: ValidationViolation[];
  setViolations: (v: ValidationViolation[]) => void;
}

export const useNeuroStore = create<NeuroStore>((set) => ({
  // ── View ──
  view: "TEMPLATE_SELECT",
  setView: (v) => set({ view: v }),

  // ── Template ──
  selectedTemplate: null,
  selectTemplate: (t) =>
    set({ selectedTemplate: t, activeModules: [], view: "SIDEBAR" }),
  clearTemplate: () =>
    set({ selectedTemplate: null, activeModules: [], view: "TEMPLATE_SELECT" }),

  // ── Modules ──
  activeModules: [],
  addModule: (m) =>
    set((s) => {
      if (s.activeModules.find((x) => x.id === m.id)) return s; // no duplicates
      return { activeModules: [...s.activeModules, m] };
    }),
  removeModule: (id) =>
    set((s) => ({ activeModules: s.activeModules.filter((m) => m.id !== id) })),

  // ── Sync Engine ──
  syncStatus: "DISCONNECTED",
  setSyncStatus: (s) => set({ syncStatus: s }),
  deltaQueue: [],
  pushDelta: (d) =>
    set((s) => ({ deltaQueue: [...s.deltaQueue.slice(-49), d] })), // keep last 50

  // ── Execution ──
  executionStatus: "IDLE",
  setExecutionStatus: (s) => set({ executionStatus: s }),
  executionLogs: [],
  appendLog: (msg) =>
    set((s) => ({ executionLogs: [...s.executionLogs.slice(-99), msg] })),
  clearLogs: () => set({ executionLogs: [] }),

  // ── Validation ──
  violations: [],
  setViolations: (v) => set({ violations: v }),
}));
