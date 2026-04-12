import { useState } from "react";
import axios from "axios";
import {
  CircuitBoard, Zap, Play,
} from "lucide-react";
import { CopilotPanel }       from "./components/CopilotPanel";
import { PCBViewer2D }        from "./components/PCBViewer2D";
import { WorkflowGraph }      from "./components/WorkflowGraph";
import { ValidationPanel }    from "./components/ValidationPanel";
import { ComponentLibrary }   from "./components/ComponentLibrary";

const API = "http://127.0.0.1:8000";

/* ── Top Header ─────────────────────────────────────────────────────────── */
function Header({ onRunPipeline, running }: { onRunPipeline: () => void; running: boolean }) {
  return (
    <header className="flex items-center justify-between px-5 py-3
                       bg-slate-950 border-b border-slate-800 flex-shrink-0">
      {/* Brand */}
      <div className="flex items-center gap-3">
        <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-teal-500 to-cyan-600
                         flex items-center justify-center shadow-lg shadow-teal-900/40">
          <CircuitBoard size={20} className="text-white" />
        </div>
        <div>
          <span className="text-lg font-bold text-slate-100 tracking-tight">NeuroBoard</span>
          <span className="text-xs text-teal-400 ml-2 font-mono">v5.0 · Copilot Edition</span>
        </div>
      </div>

      {/* Status pills */}
      <div className="flex items-center gap-2 text-xs font-mono">
        <span className="flex items-center gap-1.5 px-3 py-1 rounded-full
                         bg-slate-800 border border-slate-700 text-slate-300">
          <span className="w-1.5 h-1.5 rounded-full bg-teal-400" />
          KiCad IPC
        </span>
        <span className="flex items-center gap-1.5 px-3 py-1 rounded-full
                         bg-slate-800 border border-slate-700 text-slate-300">
          <Zap size={10} className="text-amber-400" />
          Hailo-8 · 26 TOPS
        </span>
      </div>

      {/* Actions */}
      <div className="flex items-center gap-2">
        <button
          onClick={onRunPipeline}
          disabled={running}
          className="flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-semibold
                     bg-teal-600 hover:bg-teal-500 disabled:opacity-50 text-white transition-colors"
        >
          {running
            ? <span className="animate-pulse">Running…</span>
            : <><Play size={14} /> Run Full Pipeline</>}
        </button>
      </div>
    </header>
  );
}

/* ── Main App ───────────────────────────────────────────────────────────── */
export default function App() {
  const [pipelineRunning, setPipelineRunning] = useState(false);

  const handleRunPipeline = async () => {
    setPipelineRunning(true);
    try {
      await axios.post(`${API}/api/v1/pipeline/run`, { force_sim: false });
    } catch (e) {
      console.error("Pipeline error:", e);
    } finally {
      setPipelineRunning(false);
    }
  };

  return (
    <div className="flex flex-col w-full h-screen bg-slate-950 text-slate-100
                    overflow-hidden font-sans antialiased">
      {/* Top bar */}
      <Header onRunPipeline={handleRunPipeline} running={pipelineRunning} />

      {/* Main body: three column layout */}
      <div className="flex flex-1 min-h-0 overflow-hidden">

        {/* ── Left: Copilot Chat + Component Library ──────────────── */}
        <aside className="w-[360px] flex-shrink-0 flex flex-col border-r border-slate-800">
          {/* Copilot chat takes most of this column */}
          <div className="flex-1 min-h-0">
            <CopilotPanel />
          </div>
          {/* Component library below it */}
          <div className="h-52 flex-shrink-0 border-t border-slate-800">
            <ComponentLibrary />
          </div>
        </aside>

        {/* ── Center: PCB Canvas + Workflow Graph ─────────────────── */}
        <main className="flex flex-col flex-1 min-w-0 p-3 gap-3">
          {/* 2D Live PCB digital twin — gets most of the space */}
          <div className="flex-1 min-h-0">
            <PCBViewer2D />
          </div>
          {/* LangGraph execution flow below */}
          <div className="h-52 flex-shrink-0">
            <WorkflowGraph />
          </div>
        </main>

        {/* ── Right: Validation + Inspect ─────────────────────────── */}
        <aside className="w-72 flex-shrink-0 flex flex-col border-l border-slate-800 p-3 gap-3">
          <div className="flex-1 min-h-0">
            <ValidationPanel />
          </div>
        </aside>

      </div>
    </div>
  );
}
