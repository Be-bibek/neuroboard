import React from 'react';
import { BookOpen, X, Box, Terminal, Cpu } from 'lucide-react';

interface UserManualModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const UserManualModal: React.FC<UserManualModalProps> = ({ isOpen, onClose }) => {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center p-4">
      {/* Backdrop */}
      <div 
        className="absolute inset-0 bg-black/60 backdrop-blur-md"
        onClick={onClose}
      />
      
      {/* Modal Container */}
      <div className="relative w-full max-w-4xl max-h-[90vh] overflow-hidden rounded-2xl border border-white/10 bg-zinc-900/80 backdrop-blur-2xl shadow-2xl flex flex-col">
        
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-white/10 bg-white/5">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-indigo-500/20 text-indigo-400">
              <BookOpen size={24} />
            </div>
            <div>
              <h2 className="text-xl font-bold text-white tracking-tight">NeuroBoard Quick Start Guide</h2>
              <p className="text-sm text-white/50">Local Architecture & API Setup</p>
            </div>
          </div>
          <button 
            onClick={onClose}
            className="p-2 rounded-lg hover:bg-white/10 text-white/50 hover:text-white transition-colors"
          >
            <X size={20} />
          </button>
        </div>

        {/* Scrollable Content */}
        <div className="flex-1 overflow-y-auto p-6 md:p-8 space-y-8 custom-scrollbar">
          
          <div className="bg-indigo-500/10 border border-indigo-500/20 rounded-xl p-5 text-indigo-200 text-sm leading-relaxed">
            <strong>Welcome to NeuroBoard!</strong> This website is a cloud-hosted "Local-First" dashboard. It acts as a UI command center, but it <strong>requires a local Python backend and KiCad 10</strong> running on your machine to actually manipulate hardware files. Follow these steps to connect your local machine.
          </div>

          {/* Section 1: Clone & Setup */}
          <section className="space-y-4">
            <div className="flex items-center gap-3 text-lg font-bold text-white">
              <Box className="text-white/70" />
              1. Download & Install Locally
            </div>
            <div className="pl-9 space-y-3">
              <p className="text-sm text-white/60">Clone the repository and install the Python backend dependencies to act as the bridge between this website and KiCad.</p>
              <div className="bg-black/50 border border-white/5 rounded-lg p-4 font-mono text-xs text-emerald-400">
                git clone https://github.com/Be-bibek/neuroboard.git<br/>
                cd neuroboard<br/>
                pip install -r requirements.txt
              </div>
            </div>
          </section>

          {/* Section 2: API Keys */}
          <section className="space-y-4">
            <div className="flex items-center gap-3 text-lg font-bold text-white">
              <Terminal className="text-white/70" />
              2. Configure Your AI API Keys
            </div>
            <div className="pl-9 space-y-3">
              <p className="text-sm text-white/60">The autonomous agent requires a Google Gemini 3.1 or Anthropic API key to process natural language.</p>
              <ol className="list-decimal list-inside text-sm text-white/60 space-y-2">
                <li>Create a <code className="bg-white/10 px-1.5 py-0.5 rounded text-white">.env</code> file in the root of the repository.</li>
                <li>Add your keys inside the file:</li>
              </ol>
              <div className="bg-black/50 border border-white/5 rounded-lg p-4 font-mono text-xs text-emerald-400">
                GEMINI_API_KEY="your-gemini-key-here"<br/>
                ANTHROPIC_API_KEY="your-anthropic-key-here"
              </div>
            </div>
          </section>

          {/* Section 3: Connect KiCad */}
          <section className="space-y-4">
            <div className="flex items-center gap-3 text-lg font-bold text-white">
              <Cpu className="text-white/70" />
              3. Launch the Backend & Connect KiCad
            </div>
            <div className="pl-9 space-y-3">
              <p className="text-sm text-white/60">Start the Python bridge server, then open your KiCad project. The backend will automatically bind to KiCad's live memory via <code>api.sock</code>.</p>
              
              <div className="space-y-2">
                <p className="text-xs font-bold text-white/80 uppercase tracking-widest">Step A: Start the Python Server</p>
                <div className="bg-black/50 border border-white/5 rounded-lg p-4 font-mono text-xs text-emerald-400">
                  python ai_core/api/server.py
                </div>
              </div>

              <div className="space-y-2 mt-4">
                <p className="text-xs font-bold text-white/80 uppercase tracking-widest">Step B: Open KiCad 10</p>
                <p className="text-sm text-white/60">Open KiCad 10 on your computer and open any PCB layout (e.g., an LED Ring or Pi HAT project).</p>
              </div>

              <div className="space-y-2 mt-4">
                <p className="text-xs font-bold text-white/80 uppercase tracking-widest">Step C: Select Project in Dashboard</p>
                <p className="text-sm text-white/60">Finally, click the <strong>"Select Project"</strong> folder icon at the top of this web page and select your KiCad project. The "IPC Disconnected" status will change to "KiCad IPC" and your components will instantly appear on the holographic canvas!</p>
              </div>
            </div>
          </section>

        </div>
        
        {/* Footer */}
        <div className="p-4 border-t border-white/10 bg-white/5 flex justify-end">
          <button 
            onClick={onClose}
            className="px-6 py-2 rounded-xl bg-indigo-500 hover:bg-indigo-400 text-white font-semibold transition-colors"
          >
            Got it, let's go!
          </button>
        </div>
      </div>
    </div>
  );
};
