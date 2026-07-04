import { useState } from "react";
import axios from "axios";
import { CircuitBoard, Zap, Play } from "lucide-react";
import { useNeuroStore } from "./store/useNeuroStore";
// ── Core Views ─────────────────────────────────────────────────────────────
import { TemplateSelector } from "./components/TemplateSelector";
import { AntigravitySidebar } from "./components/AntigravitySidebar";
import { PlanningBoard } from "./components/PlanningBoard";
import { ProjectSelector } from "./components/ProjectSelector";
// ── Legacy Layout Components ───────────────────────────────────────────────
import { ComponentLibrary } from "./components/ComponentLibrary";
import { PCBViewer2D } from "./components/PCBViewer2D";
import { WorkflowGraph } from "./components/WorkflowGraph";
import { ValidationPanel } from "./components/ValidationPanel";
import { ResizablePanel } from "./components/ResizablePanel";
import { ListTree, Box, Activity as ActivityIcon, ChevronDown } from "lucide-react";

const API = "http://localhost:8000";

/* ── Top Header ─────────────────────────────────────────────────────────── */
import { UserManualModal } from "./components/UserManualModal";
import { Info } from "lucide-react";

function Header({ onRunPipeline, running, syncStatus }: { onRunPipeline: () => void; running: boolean; syncStatus: string }) {
  const selectedTemplate = useNeuroStore((s) => s.selectedTemplate);
  const [showManual, setShowManual] = useState(false);
  
  return (
    <>
    <header className="flex items-center justify-between px-6 py-4
                       backdrop-blur-xl bg-zinc-900/30 border-b border-white/10 flex-shrink-0 z-50">
      {/* Brand & Project Selector */}
      <div className="flex items-center gap-6">
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
        
        <div className="h-6 w-px bg-white/10 mx-2"></div>
        
        <ProjectSelector />
      </div>

      {/* Status pills & Manual */}
      <div className="flex items-center gap-3">
        {/* User Manual Button */}
        <button
          onClick={() => setShowManual(true)}
          className={`flex items-center gap-2 px-3 py-1.5 rounded-2xl border text-xs font-semibold backdrop-blur-md transition-all
            ${syncStatus !== "CONNECTED" 
              ? "bg-rose-500/20 border-rose-500/50 text-rose-300 animate-[pulse_1.5s_ease-in-out_infinite] hover:bg-rose-500/30 shadow-[0_0_20px_rgba(244,63,94,0.5)]" 
              : "bg-white/5 border-white/10 text-white/60 hover:bg-white/10 hover:text-white/80"}`}
        >
          <Info size={syncStatus !== "CONNECTED" ? 18 : 14} className={syncStatus !== "CONNECTED" ? "text-rose-400 drop-shadow-[0_0_8px_rgba(244,63,94,0.8)]" : ""} />
          How to Setup
        </button>

        <div className="flex items-center gap-2 px-4 py-1.5 rounded-2xl
                          bg-white/5 border border-white/10 text-white/80 text-xs font-semibold backdrop-blur-md">
          <span className={`w-2 h-2 rounded-full ${syncStatus === "CONNECTED" ? "bg-emerald-400 shadow-[0_0_8px_theme('colors.emerald.400')]" : "bg-red-500"}`} />
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
    <UserManualModal isOpen={showManual} onClose={() => setShowManual(false)} />
    </>
  );
}

/* ── Main App ───────────────────────────────────────────────────────────── */
import { PCBViewer3D } from "./components/PCBViewer3D";

export default function App() {
  const [pipelineRunning, setPipelineRunning] = useState(false);
  const [show3D, setShow3D] = useState(false);
  const view = useNeuroStore((s) => s.view);
  const syncStatus = useNeuroStore((s) => s.syncStatus);
  
  // IDE Panel State
  const [bottomTab, setBottomTab] = useState<'workflow' | 'library' | 'validation' | null>(null);
  const isRightPanelOpen = true;

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
      <Header onRunPipeline={handleRunPipeline} running={pipelineRunning} syncStatus={syncStatus} />

      {/* Main IDE Workspace */}
      <div className="flex flex-row flex-1 min-h-0 min-w-0 overflow-hidden relative">
        
        {/* Center: Main Canvas Area & Bottom Dock */}
        <main className="flex flex-col flex-1 min-w-0 overflow-hidden relative bg-[#0b0f1a] z-0">
          <div className="flex-1 min-h-0 min-w-0 relative group">
            
            {/* 3D/2D Toggle Button */}
            {view !== "PLANNING_BOARD" && (
              <div className="absolute top-4 right-4 z-20 opacity-0 group-hover:opacity-100 transition-opacity">
                <button 
                  onClick={() => setShow3D(!show3D)}
                  className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-black/50 border border-white/10 text-white/70 hover:text-white hover:bg-black/80 backdrop-blur-md text-xs font-semibold shadow-xl transition-all"
                >
                  <Box size={14} className={show3D ? "text-amber-400" : "text-white/50"} />
                  {show3D ? "3D Hologram Active" : "Enable 3D Hologram"}
                </button>
              </div>
            )}

            {view === "PLANNING_BOARD" ? (
              <PlanningBoard />
            ) : show3D ? (
              <PCBViewer3D />
            ) : (
              <PCBViewer2D />
            )}
          </div>
          
          {/* Bottom Dock */}
          {bottomTab && (
            <ResizablePanel side="bottom" initialWidth={0} initialHeight={300} minHeight={150} maxHeight={600} className="border-t border-white/10 bg-zinc-900/40 backdrop-blur-3xl shadow-[0_-20px_40px_rgba(0,0,0,0.5)] z-20 shrink-0">
              <div className="flex items-center justify-between px-4 py-2 border-b border-white/5 bg-black/20 shrink-0">
                 <div className="flex items-center gap-4">
                    <button onClick={() => setBottomTab('workflow')} className={`text-[11px] font-bold uppercase tracking-widest px-2 py-1 rounded transition-colors ${bottomTab === 'workflow' ? 'text-indigo-400 bg-white/5' : 'text-white/40 hover:text-white'}`}>
                      Workflow
                    </button>
                    <button onClick={() => setBottomTab('library')} className={`text-[11px] font-bold uppercase tracking-widest px-2 py-1 rounded transition-colors ${bottomTab === 'library' ? 'text-indigo-400 bg-white/5' : 'text-white/40 hover:text-white'}`}>
                      Library
                    </button>
                    <button onClick={() => setBottomTab('validation')} className={`text-[11px] font-bold uppercase tracking-widest px-2 py-1 rounded transition-colors ${bottomTab === 'validation' ? 'text-indigo-400 bg-white/5' : 'text-white/40 hover:text-white'}`}>
                      Validation
                    </button>
                 </div>
                 <button onClick={() => setBottomTab(null)} className="p-1 text-white/40 hover:text-white rounded hover:bg-white/10">
                    <ChevronDown size={14} />
                 </button>
              </div>
              <div className="flex-1 min-h-0 min-w-0 overflow-hidden relative">
                {bottomTab === 'workflow' && <WorkflowGraph />}
                {bottomTab === 'library' && <div className="p-4 h-full overflow-y-auto"><ComponentLibrary /></div>}
                {bottomTab === 'validation' && <div className="p-4 h-full overflow-y-auto"><ValidationPanel /></div>}
              </div>
            </ResizablePanel>
          )}

          {/* Bottom Dock Bar (when collapsed) */}
          {!bottomTab && (
            <div className="h-8 shrink-0 border-t border-white/10 bg-zinc-900/60 backdrop-blur-xl flex items-center px-4 gap-4 z-20">
              <button onClick={() => setBottomTab('workflow')} className="flex items-center gap-2 text-[10px] font-bold uppercase tracking-widest text-white/50 hover:text-white transition-colors">
                <ListTree size={12} /> Workflow
              </button>
              <button onClick={() => setBottomTab('library')} className="flex items-center gap-2 text-[10px] font-bold uppercase tracking-widest text-white/50 hover:text-white transition-colors">
                <Box size={12} /> Object Library
              </button>
              <button onClick={() => setBottomTab('validation')} className="flex items-center gap-2 text-[10px] font-bold uppercase tracking-widest text-white/50 hover:text-white transition-colors">
                <ActivityIcon size={12} /> Telemetry
              </button>
            </div>
          )}
        </main>

        {/* Right Sidebar: AI Panel */}
        {isRightPanelOpen && (
          <AntigravitySidebar />
        )}

      </div>
    </div>
  );
}
