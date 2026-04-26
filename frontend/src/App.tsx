import { useState } from "react";
import axios from "axios";
import { CircuitBoard, Zap, Play } from "lucide-react";
import { useNeuroStore } from "./store/useNeuroStore";
// ── Core Views ─────────────────────────────────────────────────────────────
import { TemplateSelector } from "./components/TemplateSelector";
import { AntigravitySidebar } from "./components/AntigravitySidebar";
import { PlanningBoard } from "./components/PlanningBoard";
// ── Legacy Layout Components ───────────────────────────────────────────────
import { ComponentLibrary } from "./components/ComponentLibrary";
import { PCBViewer2D } from "./components/PCBViewer2D";
import { WorkflowGraph } from "./components/WorkflowGraph";
import { ValidationPanel } from "./components/ValidationPanel";

const API = "http://localhost:8000";

/* ── Top Header ─────────────────────────────────────────────────────────── */
function Header({ onRunPipeline, running, syncStatus }: { onRunPipeline: () => void; running: boolean; syncStatus: string }) {
  const selectedTemplate = useNeuroStore((s) => s.selectedTemplate);
  
  return (
    <header className="flex items-center justify-between px-6 py-4
                       backdrop-blur-xl bg-zinc-900/30 border-b border-white/10 flex-shrink-0 z-50">
      {/* Brand */}
      <div className="flex items-center gap-4">
        <div className="w-10 h-10 rounded-2xl bg-gradient-to-br from-indigo-500 to-purple-600
                         flex items-center justify-center shadow-2xl shadow-indigo-500/20 active:scale-95 transition-transform">
          <CircuitBoard size={22} className="text-white" />
        </div>
        <div>
          <h1 className="text-xl font-bold text-white tracking-tight">NeuroBoard</h1>
          {selectedTemplate ? (
            <span className="text-xs text-indigo-400 font-medium">
              {selectedTemplate.icon} {selectedTemplate.name}
            </span>
          ) : (
            <span className="text-xs text-indigo-400 font-medium">v5.0 · Autonomous Agent</span>
          )}
        </div>
      </div>

      {/* Status pills */}
      <div className="flex items-center gap-3">
        <div className="flex items-center gap-2 px-4 py-1.5 rounded-2xl
                          bg-white/5 border border-white/10 text-white/80 text-xs font-semibold backdrop-blur-md">
          <span className={`w-2 h-2 rounded-full ${syncStatus === "CONNECTED" ? "bg-emerald-400 shadow-[0_0_8px_theme('colors.emerald.400')]" : "bg-red-500 animate-pulse"}`} />
          {syncStatus === "CONNECTED" ? "KiCad IPC" : "IPC Disconnected"}
        </div>
        <div className="flex items-center gap-2 px-4 py-1.5 rounded-2xl
                          bg-white/5 border border-white/10 text-white/80 text-xs font-semibold backdrop-blur-md">
          <Zap size={12} className="text-amber-400" />
          Hailo-8 · 26 TOPS
        </div>
      </div>

      {/* Actions */}
      <div className="flex items-center gap-4">
        <button
          onClick={onRunPipeline}
          disabled={running}
          className="glass-button bg-indigo-600/80 hover:bg-indigo-500 text-white shadow-xl shadow-indigo-500/20"
        >
          {running
            ? <span className="animate-pulse flex items-center gap-2"><Zap size={16} /> Thinking…</span>
            : <><Play size={16} fill="currentColor" /> Execute Goal</>}
        </button>
      </div>
    </header>
  );
}

/* ── Main App ───────────────────────────────────────────────────────────── */
export default function App() {
  const [pipelineRunning, setPipelineRunning] = useState(false);
  const view = useNeuroStore((s) => s.view);
  const syncStatus = useNeuroStore((s) => s.syncStatus);

  const handleRunPipeline = async () => {
    setPipelineRunning(true);
    try {
      await axios.post(`${API}/api/v1/agent/execute`, {
        goal: "Analyze board and optimize routing strategy"
      });
    } catch (e) {
      console.error("Agent execute error:", e);
    } finally {
      setPipelineRunning(false);
    }
  };

  if (view === "TEMPLATE_SELECT") {
    return <TemplateSelector />;
  }

  return (
    <div className="flex flex-col w-full h-screen bg-[#0b0f1a] text-white/90 overflow-hidden font-sans antialiased">
      {/* Top bar */}
      <Header onRunPipeline={handleRunPipeline} running={pipelineRunning} syncStatus={syncStatus} />

      {/* Main Layout */}
      <div className="flex flex-1 min-h-0 overflow-hidden p-4 gap-4">

        {/* ── Center: Main Canvas Area ─────────────────────────── */}
        <main className="flex flex-col flex-1 min-w-0 gap-4">
          <div className="flex-1 min-h-0 glass-panel overflow-hidden relative">
            {view === "PLANNING_BOARD" ? <PlanningBoard /> : <PCBViewer2D />}
          </div>
          
          <div className="h-64 flex-shrink-0 flex gap-4">
             <div className="flex-1 min-w-0 glass-panel p-4 overflow-hidden">
                <WorkflowGraph />
             </div>
             <div className="w-80 flex-shrink-0 glass-panel p-4 overflow-hidden">
                <ComponentLibrary />
             </div>
          </div>
        </main>

        {/* ── Right Sidebar: AI Panel + Validation ──────────────── */}
        <aside className="w-[420px] flex-shrink-0 flex flex-col gap-4">
          <div className="flex-[3] min-h-0 glass-panel overflow-hidden">
            <AntigravitySidebar />
          </div>
          <div className="flex-[1] min-h-0 glass-panel p-4 overflow-hidden">
            <ValidationPanel />
          </div>
        </aside>

      </div>
    </div>
  );
}
