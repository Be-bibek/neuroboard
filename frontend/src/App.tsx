import { CircuitBoard } from "lucide-react";
import { useNeuroStore } from "./store/useNeuroStore";
import { TemplateSelector } from "./components/TemplateSelector";
import { CopilotSidebar } from "./components/CopilotSidebar";
import { PlanningBoard } from "./components/PlanningBoard";

// ── App Shell ──────────────────────────────────────────────────────────────
export default function App() {
  const view = useNeuroStore((s) => s.view);
  const selectedTemplate = useNeuroStore((s) => s.selectedTemplate);

  return (
    <div className="flex flex-col w-full h-screen bg-slate-950 text-slate-100 overflow-hidden font-sans antialiased">

      {/* ── Top Bar (only in SIDEBAR/PLANNING_BOARD views) ── */}
      {view !== "TEMPLATE_SELECT" && (
        <header className="flex items-center justify-between px-5 py-2.5 bg-slate-950 border-b border-slate-800 flex-shrink-0">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-teal-500 to-cyan-600 flex items-center justify-center shadow shadow-teal-900/40">
              <CircuitBoard size={16} className="text-white" />
            </div>
            <div>
              <span className="text-sm font-bold text-slate-100">NeuroBoard</span>
              {selectedTemplate && (
                <span className="text-xs text-slate-500 ml-2 font-mono">
                  {selectedTemplate.icon} {selectedTemplate.name}
                </span>
              )}
            </div>
          </div>
          <span className="text-[10px] text-teal-400 font-mono border border-teal-800/50 bg-teal-900/20 px-2 py-0.5 rounded">
            v5.0 · Copilot
          </span>
        </header>
      )}

      {/* ── Main View Router ── */}
      <div className="flex flex-1 min-h-0 overflow-hidden">
        {view === "TEMPLATE_SELECT" && <TemplateSelector />}
        {view === "SIDEBAR" && <CopilotSidebar />}
        {view === "PLANNING_BOARD" && <PlanningBoard />}
      </div>

    </div>
  );
}
