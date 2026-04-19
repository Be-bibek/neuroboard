import { CopilotPanel } from "./CopilotPanel";
import { ValidationPanel } from "./ValidationPanel";

export function CopilotSidebar() {
  return (
    <div className="flex flex-col w-full h-full bg-slate-950 text-slate-100 border-r border-slate-800">
      <div className="p-4 border-b border-slate-800 flex justify-between items-center bg-slate-900">
        <h2 className="font-bold tracking-tight">NeuroBoard AI</h2>
        <span className="text-xs bg-teal-900/50 text-teal-400 px-2 py-1 rounded border border-teal-800/50">
          Sync Active
        </span>
      </div>
      
      {/* Interactive AI Panel */}
      <div className="flex-1 min-h-0 overflow-hidden">
        <CopilotPanel />
      </div>

      {/* Validation & Electrical Status */}
      <div className="h-1/3 flex-shrink-0 border-t border-slate-800 bg-slate-900/50">
        <ValidationPanel />
      </div>
    </div>
  );
}
