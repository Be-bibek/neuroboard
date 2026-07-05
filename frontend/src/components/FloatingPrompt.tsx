import { useState, useEffect } from "react";
import { Plus, ChevronDown, Activity, GitBranch, X, Undo2, ArrowUp } from "lucide-react";
import { useNeuroStore } from "../store/useNeuroStore";

export function FloatingPrompt() {
  const [input, setInput] = useState("");
  const { agentSelection, setAgentSelection, modelSelection, setModelSelection, autoDrc, setAutoDrc } = useNeuroStore();

  // Listen for escape to clear
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") setInput("");
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, []);

  const handleSubmit = () => {
    if (!input.trim()) return;
    
    // Dispatch an event that the main window will listen for
    // If running in a popup, window.opener refers to the main window
    const targetWindow = window.opener || window;
    
    targetWindow.dispatchEvent(
      new CustomEvent("central_prompt_submit", { detail: input })
    );
    
    setInput("");
  };

  return (
    <div className="w-full h-screen bg-[#fcfcfc] dark:bg-[#1a1a1a] flex items-center justify-center p-4">
      <div className="w-full max-w-3xl bg-[#fdfdfd] dark:bg-[#252525] rounded-[24px] shadow-[0_8px_30px_rgb(0,0,0,0.08)] dark:shadow-[0_8px_30px_rgb(0,0,0,0.4)] border border-gray-200 dark:border-white/10 flex flex-col overflow-hidden">
        
        {/* Text Area */}
        <textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              handleSubmit();
            }
          }}
          placeholder="Describe your PCB engineering goal..."
          className="w-full h-32 resize-none bg-transparent outline-none p-6 text-gray-800 dark:text-gray-100 text-lg placeholder-gray-400 dark:placeholder-gray-500 font-serif"
          autoFocus
        />

        {/* Divider */}
        <div className="h-px w-[calc(100%-48px)] mx-auto bg-gray-100 dark:bg-white/5" />

        {/* Bottom Toolbar */}
        <div className="flex items-center justify-between px-6 py-4">
          
          {/* Left Controls */}
          <div className="flex items-center gap-2">
            <button className="flex items-center justify-center w-10 h-10 rounded-full border border-gray-200 dark:border-white/10 text-gray-500 hover:bg-gray-50 dark:hover:bg-white/5 transition-colors">
              <Plus size={18} />
            </button>
            
            <button 
              className="flex items-center gap-2 px-4 h-10 rounded-full border border-gray-200 dark:border-white/10 text-gray-600 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-white/5 transition-colors font-medium text-sm"
              onClick={() => setAgentSelection(agentSelection === "Agent" ? "Planner" : "Agent")}
            >
              {agentSelection} <ChevronDown size={14} className="text-gray-400" />
            </button>

            <button 
              className="flex items-center gap-2 px-4 h-10 rounded-full border border-gray-200 dark:border-white/10 text-gray-600 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-white/5 transition-colors font-medium text-sm"
              onClick={() => setModelSelection(modelSelection === "GPT-4o mini" ? "Gemini 3.1 Pro" : "GPT-4o mini")}
            >
              {modelSelection} <ChevronDown size={14} className="text-gray-400" />
            </button>

            <button className="flex items-center justify-center w-10 h-10 rounded-xl border border-gray-200 dark:border-white/10 text-rose-400 hover:bg-gray-50 dark:hover:bg-white/5 transition-colors ml-1">
              <Activity size={18} />
            </button>

            <button className="flex items-center justify-center w-10 h-10 rounded-xl border border-gray-200 dark:border-white/10 text-gray-500 hover:bg-gray-50 dark:hover:bg-white/5 transition-colors">
              <GitBranch size={18} />
            </button>

            <label className="flex items-center gap-2 ml-2 cursor-pointer group">
              <div className="relative flex items-center justify-center w-5 h-5 rounded border border-gray-300 dark:border-gray-600 bg-white dark:bg-transparent group-hover:border-blue-500 transition-colors overflow-hidden">
                <input 
                  type="checkbox" 
                  checked={autoDrc}
                  onChange={(e) => setAutoDrc(e.target.checked)}
                  className="absolute inset-0 opacity-0 cursor-pointer z-10 w-full h-full" 
                />
                {autoDrc && <div className="absolute inset-0 bg-blue-500 flex items-center justify-center">
                   <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round"><polyline points="20 6 9 17 4 12"></polyline></svg>
                </div>}
              </div>
              <span className="text-sm font-medium text-gray-700 dark:text-gray-300">Auto ERC/DRC</span>
            </label>
          </div>

          {/* Right Controls */}
          <div className="flex items-center gap-2">
            <button 
              onClick={() => setInput("")}
              className="flex items-center justify-center w-10 h-10 rounded-full border border-gray-200 dark:border-white/10 text-gray-400 hover:text-gray-600 hover:bg-gray-50 dark:hover:bg-white/5 transition-colors"
            >
              <X size={18} />
            </button>
            <button 
              className="flex items-center justify-center w-10 h-10 rounded-full border border-gray-200 dark:border-white/10 text-gray-400 hover:text-gray-600 hover:bg-gray-50 dark:hover:bg-white/5 transition-colors"
            >
              <Undo2 size={18} />
            </button>
            <button 
              onClick={handleSubmit}
              disabled={!input.trim()}
              className="flex items-center justify-center w-10 h-10 rounded-full bg-[#d6876c] text-white hover:bg-[#c6765b] transition-colors disabled:opacity-50 disabled:cursor-not-allowed shadow-md"
            >
              <ArrowUp size={20} strokeWidth={2.5} />
            </button>
          </div>

        </div>
      </div>
    </div>
  );
}
