import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { getCurrentWindow } from '@tauri-apps/api/window';
import { Sparkles, Terminal, Activity, X } from 'lucide-react';

interface FloatingCopilotProps {
  onToggleMode: () => void;
}

export function FloatingCopilot({ onToggleMode }: FloatingCopilotProps) {
  const [prompt, setPrompt] = useState("");
  const [loading, setLoading] = useState(false);
  const [step, setStep] = useState<string | null>(null);

  // Global escape key listener
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        getCurrentWindow().hide();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!prompt.trim() || loading) return;

    setLoading(true);
    try {
      setStep("Parsing Intent...");
      const resPrompt = await axios.post("http://localhost:8000/api/v1/copilot/prompt", { intent: prompt });
      
      setStep("AABB Physics Placement...");
      await axios.post("http://localhost:8000/api/v1/copilot/confirm", {
        spec: resPrompt.data.spec,
        manifest: resPrompt.data.manifest
      });
      
      setStep("Injecting KiCad IPC...");
      await axios.post("http://localhost:8000/api/v1/pipeline/run", { force_sim: false });
      
      setStep("Success!");
      setPrompt("");
      setTimeout(() => setStep(null), 2000);
    } catch (err) {
      console.error(err);
      setStep("Error: Failed to process");
      setTimeout(() => setStep(null), 3000);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="w-screen h-screen flex items-center justify-center pointer-events-none p-4">
      {/* Floating Card */}
      <div className="pointer-events-auto w-full max-w-xl bg-slate-950/85 backdrop-blur-2xl border border-white/15 rounded-3xl p-5 shadow-[0_0_50px_rgba(0,0,0,0.8)] text-white flex flex-col gap-4 transition-all duration-300">
        
        {/* Header - Drag Region */}
        <div 
          className="flex items-center justify-between cursor-move select-none -mt-1 -mx-1 p-1 rounded-t-xl"
          data-tauri-drag-region
        >
          <div className="flex items-center gap-3 pointer-events-none" data-tauri-drag-region>
            <div className="relative flex items-center justify-center w-3 h-3">
              <div className="absolute inset-0 bg-emerald-400 rounded-full animate-ping opacity-75" />
              <div className="relative w-2 h-2 bg-emerald-400 rounded-full shadow-[0_0_8px_rgba(52,211,153,0.8)]" />
            </div>
            <span className="font-semibold text-sm tracking-wide text-white/90">⚡ NeuroBoard Copilot</span>
          </div>
          
          <div className="flex items-center gap-2">
            <button 
              onClick={onToggleMode}
              className="px-3 py-1 rounded-full bg-white/5 hover:bg-white/10 text-xs font-medium text-indigo-300 transition-colors border border-white/10"
              title="Switch to Full Studio Mode"
            >
              Studio Mode
            </button>
            <button 
              onClick={() => getCurrentWindow().hide()}
              className="p-1.5 rounded-full hover:bg-white/10 text-white/50 hover:text-white transition-colors"
            >
              <X size={16} />
            </button>
          </div>
        </div>

        {/* Input Area */}
        <form onSubmit={handleSubmit} className="relative">
          <div className="absolute left-4 top-1/2 -translate-y-1/2 text-white/40">
            <Sparkles size={20} />
          </div>
          <input
            type="text"
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            disabled={loading}
            placeholder="E.g., Place a 12-LED Neopixel ring with an ESP32..."
            className="w-full bg-white/5 border border-white/10 rounded-2xl py-4 pl-12 pr-4 text-white placeholder-white/30 focus:outline-none focus:ring-2 focus:ring-indigo-500/50 transition-all text-sm"
          />
        </form>

        {/* Progress Chips */}
        <div className="flex items-center gap-2 h-6 px-1">
          {step && (
            <div className="flex items-center gap-2 px-3 py-1 rounded-full bg-indigo-500/20 border border-indigo-500/30 text-indigo-300 text-xs font-medium animate-in fade-in zoom-in duration-300">
              <Activity size={12} className={loading ? "animate-spin" : ""} />
              {step}
            </div>
          )}
          {!step && (
            <div className="flex items-center gap-2 px-3 py-1 text-white/30 text-xs">
              <Terminal size={12} />
              Ready (Press Esc to dismiss)
            </div>
          )}
        </div>

      </div>
    </div>
  );
}
