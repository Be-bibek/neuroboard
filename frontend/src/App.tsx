
import {
  CircuitBoard
} from "lucide-react";
import { CopilotSidebar } from "./components/CopilotSidebar";
import { PlanningBoard } from "./components/PlanningBoard";
import { useUIStore } from "./store/useUIStore";

/* ── Top Header ─────────────────────────────────────────────────────────── */
function Header() {
  const { viewMode, toggleViewMode } = useUIStore();

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
          <span className="text-xs text-teal-400 ml-2 font-mono">v5.0 · Copilot</span>
        </div>
      </div>

      {/* Actions */}
      <div className="flex items-center gap-2">
        <button
          onClick={toggleViewMode}
          className="px-3 py-1.5 rounded-lg text-sm font-semibold bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 transition-colors"
        >
          {viewMode === 'SIDEBAR' ? 'Open Planning Board' : 'Back to Copilot Sidebar'}
        </button>
      </div>
    </header>
  );
}

/* ── Main App ───────────────────────────────────────────────────────────── */
export default function App() {
  const viewMode = useUIStore(state => state.viewMode);

  return (
    <div className="flex flex-col w-full h-screen bg-slate-950 text-slate-100 overflow-hidden font-sans antialiased">
      {/* Top bar */}
      <Header />

      {/* Main UI Area */}
      <div className="flex flex-1 min-h-0 overflow-hidden">
        {viewMode === 'SIDEBAR' ? (
          <div className="w-full flex justify-center">
            {/* The slim sidebar copilot view, matching the user's rectangular requirement */}
            <div className="w-full max-w-[450px] shadow-2xl shadow-black h-full">
              <CopilotSidebar />
            </div>
          </div>
        ) : (
          <div className="w-full h-full">
            <PlanningBoard />
          </div>
        )}
      </div>
    </div>
  );
}
