import { useState, useEffect, useRef } from "react";
import { Plus, ChevronDown, GitBranch, X, Undo2, ArrowUp, Zap, Check, Cpu, Network, FileCode2 } from "lucide-react";
import { useNeuroStore } from "../../store/useNeuroStore";

interface PromptBoxProps {
  onSubmitStart?: (prompt: string) => void;
  className?: string;
  autoFocus?: boolean;
}

export function PromptBox({ onSubmitStart, className = "", autoFocus = true }: PromptBoxProps) {
  const [input, setInput] = useState("");
  const { modelSelection, setModelSelection, autoDrc, setAutoDrc } = useNeuroStore();
  
  // Dropdown states
  const [openDropdown, setOpenDropdown] = useState<"context" | "model" | "github" | null>(null);

  // Close dropdowns on outside click
  const boxRef = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const handleClick = (e: MouseEvent) => {
      if (boxRef.current && !boxRef.current.contains(e.target as Node)) {
        setOpenDropdown(null);
      }
    };
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, []);

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
    
    if (onSubmitStart) {
      onSubmitStart(input);
    } else {
      const targetWindow = window.opener || window;
      targetWindow.dispatchEvent(
        new CustomEvent("central_prompt_submit", { detail: input })
      );
    }
    
    setInput("");
  };

  const MODELS = ["Gemini 1.5 Pro", "Gemini 1.5 Flash", "Claude 3.5 Sonnet", "GPT-4o"];

  return (
    <div 
      ref={boxRef}
      className={`w-full max-w-3xl bg-zinc-900/60 backdrop-blur-3xl rounded-[24px] shadow-[0_20px_60px_rgba(0,0,0,0.5)] border border-white/10 flex flex-col overflow-visible relative ${className}`}
    >
      
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
        className="w-full h-32 resize-none bg-transparent outline-none p-6 text-slate-200 text-lg placeholder-slate-500 font-serif"
        autoFocus={autoFocus}
      />

      {/* Divider */}
      <div className="h-px w-[calc(100%-48px)] mx-auto bg-white/5" />

      {/* Bottom Toolbar */}
      <div className="flex items-center justify-between px-6 py-4">
        
        {/* Left Controls */}
        <div className="flex items-center gap-2">
          {/* Add PDF/Stubs */}
          <button 
            title="Add PDF or Stubs"
            className="flex items-center justify-center w-10 h-10 rounded-full border border-white/10 text-slate-400 hover:text-white hover:bg-white/10 transition-colors"
          >
            <Plus size={18} />
          </button>
          
          {/* Context Dropdown */}
          <div className="relative">
            <button 
              className={`flex items-center gap-2 px-4 h-10 rounded-full border ${openDropdown === 'context' ? 'bg-white/10 border-white/20' : 'border-white/10'} text-slate-300 hover:bg-white/10 transition-colors font-medium text-sm`}
              onClick={() => setOpenDropdown(openDropdown === "context" ? null : "context")}
            >
              <Zap size={14} className="text-amber-400" /> Context <ChevronDown size={14} className="text-slate-500" />
            </button>
            {openDropdown === "context" && (
              <div className="absolute top-full left-0 mt-2 w-48 bg-zinc-900 border border-white/10 rounded-xl shadow-2xl py-2 z-50 overflow-hidden backdrop-blur-xl">
                <div className="px-3 py-1.5 text-[10px] font-bold text-slate-500 uppercase tracking-wider">Context Providers</div>
                <button className="w-full text-left px-4 py-2 hover:bg-white/5 text-sm text-slate-300 flex items-center gap-2"><Cpu size={14} className="text-purple-400"/> @board</button>
                <button className="w-full text-left px-4 py-2 hover:bg-white/5 text-sm text-slate-300 flex items-center gap-2"><FileCode2 size={14} className="text-emerald-400"/> @mem</button>
                <button className="w-full text-left px-4 py-2 hover:bg-white/5 text-sm text-slate-300 flex items-center gap-2"><Network size={14} className="text-amber-400"/> @nets</button>
              </div>
            )}
          </div>

          {/* Model Dropdown */}
          <div className="relative">
            <button 
              className={`flex items-center gap-2 px-4 h-10 rounded-full border ${openDropdown === 'model' ? 'bg-white/10 border-white/20' : 'border-white/10'} text-slate-300 hover:bg-white/10 transition-colors font-medium text-sm`}
              onClick={() => setOpenDropdown(openDropdown === "model" ? null : "model")}
            >
              {modelSelection} <ChevronDown size={14} className="text-slate-500" />
            </button>
            {openDropdown === "model" && (
              <div className="absolute top-full left-0 mt-2 w-56 bg-zinc-900 border border-white/10 rounded-xl shadow-2xl py-2 z-50 overflow-hidden backdrop-blur-xl">
                <div className="px-3 py-1.5 text-[10px] font-bold text-slate-500 uppercase tracking-wider">Select Model</div>
                {MODELS.map(m => (
                  <button 
                    key={m}
                    className="w-full text-left px-4 py-2 hover:bg-white/5 text-sm text-slate-300 flex items-center justify-between"
                    onClick={() => { setModelSelection(m); setOpenDropdown(null); }}
                  >
                    {m}
                    {modelSelection === m && <Check size={14} className="text-emerald-500" />}
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* GitHub Menu */}
          <div className="relative ml-1">
            <button 
              className={`flex items-center justify-center w-10 h-10 rounded-xl border ${openDropdown === 'github' ? 'bg-white/10 border-white/20 text-white' : 'border-white/10 text-slate-400'} hover:bg-white/10 hover:text-white transition-colors`}
              onClick={() => setOpenDropdown(openDropdown === "github" ? null : "github")}
            >
              <GitBranch size={18} />
            </button>
            {openDropdown === "github" && (
              <div className="absolute top-full left-0 mt-2 w-64 bg-[#fbfbfb] dark:bg-zinc-900 border border-gray-200 dark:border-white/10 rounded-xl shadow-2xl py-2 z-50 overflow-hidden">
                <div className="px-4 py-2 text-xs text-gray-500 dark:text-slate-400 border-b border-gray-100 dark:border-white/5 mb-1">
                  Connected: <span className="font-medium text-gray-800 dark:text-slate-200">@bibek</span>
                </div>
                
                <button className="w-full text-left px-4 py-1.5 hover:bg-gray-100 dark:hover:bg-white/5 text-sm text-gray-700 dark:text-slate-300">Status</button>
                <button className="w-full text-left px-4 py-1.5 hover:bg-gray-100 dark:hover:bg-white/5 text-sm text-gray-700 dark:text-slate-300">Push (commit + push)</button>
                <button className="w-full text-left px-4 py-1.5 hover:bg-gray-100 dark:hover:bg-white/5 text-sm text-gray-700 dark:text-slate-300 border-b border-gray-100 dark:border-white/5 pb-2 mb-1">Pull latest</button>
                
                <button className="w-full text-left px-4 py-1.5 hover:bg-gray-100 dark:hover:bg-white/5 text-sm text-gray-700 dark:text-slate-300">New branch...</button>
                <button className="w-full text-left px-4 py-1.5 hover:bg-gray-100 dark:hover:bg-white/5 text-sm text-gray-700 dark:text-slate-300">List branches</button>
                <button className="w-full text-left px-4 py-1.5 hover:bg-gray-100 dark:hover:bg-white/5 text-sm text-gray-700 dark:text-slate-300">List pull requests</button>
                <button className="w-full text-left px-4 py-1.5 hover:bg-gray-100 dark:hover:bg-white/5 text-sm text-gray-700 dark:text-slate-300">List repositories</button>
                <button className="w-full text-left px-4 py-1.5 hover:bg-gray-100 dark:hover:bg-white/5 text-sm text-gray-700 dark:text-slate-300 border-b border-gray-100 dark:border-white/5 pb-2 mb-1">List issues</button>
                
                <button className="w-full text-left px-4 py-1.5 hover:bg-gray-100 dark:hover:bg-white/5 text-sm text-gray-700 dark:text-slate-300">How to get a GitHub token...</button>
                <button className="w-full text-left px-4 py-1.5 hover:bg-red-50 dark:hover:bg-rose-500/10 text-sm text-red-600 dark:text-rose-400">Disconnect</button>
              </div>
            )}
          </div>

          <label className="flex items-center gap-2 ml-2 cursor-pointer group">
            <div className="relative flex items-center justify-center w-5 h-5 rounded border border-white/20 bg-black/20 group-hover:border-indigo-500 transition-colors overflow-hidden">
              <input 
                type="checkbox" 
                checked={autoDrc}
                onChange={(e) => setAutoDrc(e.target.checked)}
                className="absolute inset-0 opacity-0 cursor-pointer z-10 w-full h-full" 
              />
              {autoDrc && <div className="absolute inset-0 bg-indigo-500 flex items-center justify-center">
                 <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round"><polyline points="20 6 9 17 4 12"></polyline></svg>
              </div>}
            </div>
            <span className="text-sm font-medium text-slate-400 group-hover:text-slate-200 transition-colors">Auto ERC/DRC</span>
          </label>
        </div>

        {/* Right Controls */}
        <div className="flex items-center gap-2">
          <button 
            onClick={() => setInput("")}
            className="flex items-center justify-center w-10 h-10 rounded-full border border-white/10 text-slate-500 hover:text-slate-300 hover:bg-white/10 transition-colors"
          >
            <X size={18} />
          </button>
          <button 
            className="flex items-center justify-center w-10 h-10 rounded-full border border-white/10 text-slate-500 hover:text-slate-300 hover:bg-white/10 transition-colors"
          >
            <Undo2 size={18} />
          </button>
          <button 
            onClick={handleSubmit}
            disabled={!input.trim()}
            className="flex items-center justify-center w-10 h-10 rounded-full bg-indigo-600 text-white hover:bg-indigo-500 transition-colors disabled:opacity-50 disabled:cursor-not-allowed shadow-[0_0_15px_rgba(79,70,229,0.4)]"
          >
            <ArrowUp size={20} strokeWidth={2.5} />
          </button>
        </div>

      </div>
    </div>
  );
}
