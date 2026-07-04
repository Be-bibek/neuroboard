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

          <hr className="border-white/10" />

          {/* Section 4: System Architecture */}
          <section className="space-y-4">
            <div className="flex items-center gap-3 text-lg font-bold text-white">
              <Cpu className="text-white/70" />
              4. System Architecture
            </div>
            <div className="pl-9 space-y-3 text-sm text-white/60 leading-relaxed">
              <p>NeuroBoard acts as a <strong>Zero-Install Web Client with a Local Hardware Daemon</strong>. This creates a bidirectional, low-latency Digital Twin of your physical PCB.</p>
              <ul className="list-disc list-inside space-y-1 mt-2">
                <li><strong>Frontend:</strong> React, Tauri, and React Three Fiber (R3F) for a holographic 60fps telemetry dashboard.</li>
                <li><strong>Backend Engine:</strong> FastAPI + Python, utilizing an autonomous <em>2D Arithmetic Reflow Engine</em> for instant math-based trace detouring instead of relying on slow LLM pathfinding.</li>
                <li><strong>The Bridge:</strong> A native IPC socket (<code>api.sock</code>) via <code>kipy</code> hooks directly into KiCad 10's memory, allowing the AI to mutate the board in real-time.</li>
              </ul>

              {/* Architecture Diagram */}
              <div className="my-8 p-6 rounded-2xl bg-[#09090c] border border-white/10 relative overflow-hidden">
                <div className="absolute inset-0 bg-[linear-gradient(to_right,#4f4f4f15_1px,transparent_1px),linear-gradient(to_bottom,#4f4f4f15_1px,transparent_1px)] bg-[size:14px_24px]"></div>
                <div className="relative z-10 flex flex-col md:flex-row items-center justify-between gap-4">
                  
                  {/* Web UI */}
                  <div className="w-full md:w-1/3 p-4 rounded-xl bg-gradient-to-br from-indigo-500/10 to-purple-600/10 border border-indigo-500/30 text-center shadow-[0_0_20px_rgba(99,102,241,0.1)] backdrop-blur-xl">
                    <div className="mb-3 inline-flex p-2.5 rounded-xl bg-indigo-500/20"><Box size={24} className="text-indigo-400" /></div>
                    <h3 className="font-bold text-white mb-1">Web UI</h3>
                    <p className="text-[10px] text-white/50 uppercase tracking-widest font-bold">R3F • React • Tauri</p>
                  </div>
                  
                  {/* Arrow 1 */}
                  <div className="flex flex-col items-center shrink-0">
                    <div className="hidden md:flex w-12 h-px bg-gradient-to-r from-indigo-500/50 to-emerald-500/50 relative items-center justify-end">
                      <div className="w-2 h-2 border-r-2 border-t-2 border-emerald-500/50 rotate-45 mr-1"></div>
                    </div>
                    <div className="md:hidden h-8 w-px bg-gradient-to-b from-indigo-500/50 to-emerald-500/50 relative flex items-end justify-center">
                      <div className="w-2 h-2 border-r-2 border-b-2 border-emerald-500/50 rotate-45 mb-1"></div>
                    </div>
                    <span className="text-[10px] text-emerald-400 font-mono mt-1 bg-emerald-400/10 px-2 py-0.5 rounded">HTTP/WS</span>
                  </div>

                  {/* Backend */}
                  <div className="w-full md:w-1/3 p-4 rounded-xl bg-gradient-to-br from-emerald-500/10 to-teal-600/10 border border-emerald-500/30 text-center shadow-[0_0_20px_rgba(52,211,153,0.1)] backdrop-blur-xl">
                    <div className="mb-3 inline-flex p-2.5 rounded-xl bg-emerald-500/20"><Terminal size={24} className="text-emerald-400" /></div>
                    <h3 className="font-bold text-white mb-1">Backend Engine</h3>
                    <p className="text-[10px] text-white/50 uppercase tracking-widest font-bold">FastAPI • Python</p>
                  </div>

                  {/* Arrow 2 */}
                  <div className="flex flex-col items-center shrink-0">
                    <div className="hidden md:flex w-12 h-px bg-gradient-to-r from-emerald-500/50 to-rose-500/50 relative items-center justify-end">
                      <div className="w-2 h-2 border-r-2 border-t-2 border-rose-500/50 rotate-45 mr-1"></div>
                    </div>
                    <div className="md:hidden h-8 w-px bg-gradient-to-b from-emerald-500/50 to-rose-500/50 relative flex items-end justify-center">
                      <div className="w-2 h-2 border-r-2 border-b-2 border-rose-500/50 rotate-45 mb-1"></div>
                    </div>
                    <span className="text-[10px] text-rose-400 font-mono mt-1 bg-rose-400/10 px-2 py-0.5 rounded">api.sock</span>
                  </div>

                  {/* KiCad */}
                  <div className="w-full md:w-1/3 p-4 rounded-xl bg-gradient-to-br from-rose-500/10 to-red-600/10 border border-rose-500/30 text-center shadow-[0_0_20px_rgba(244,63,94,0.1)] backdrop-blur-xl">
                    <div className="mb-3 inline-flex p-2.5 rounded-xl bg-rose-500/20"><Cpu size={24} className="text-rose-400" /></div>
                    <h3 className="font-bold text-white mb-1">KiCad 10</h3>
                    <p className="text-[10px] text-white/50 uppercase tracking-widest font-bold">Live Digital Twin</p>
                  </div>

                </div>
              </div>
            </div>
          </section>

          {/* Section 5: Future Roadmap */}
          <section className="space-y-4">
            <div className="flex items-center gap-3 text-lg font-bold text-white">
              <Terminal className="text-white/70" />
              5. Future Roadmap
            </div>
            <div className="pl-9 space-y-3 text-sm text-white/60 leading-relaxed">
              <p>The journey doesn't stop here. Here is what we are building next:</p>
              <ul className="list-disc list-inside space-y-1 mt-2">
                <li><strong>Multi-Layer Auto-Routing:</strong> Expanding the arithmetic engine to seamlessly transition between 4-layer and 8-layer boards with intelligent via placements.</li>
                <li><strong>Semantic Schematic Understanding:</strong> Allowing the AI to read schematic nets and suggest bypass capacitor placements automatically.</li>
                <li><strong>Real-time DRC Validation:</strong> Instantly highlighting design rule violations on the holographic canvas before they are even committed to KiCad.</li>
              </ul>
            </div>
          </section>

          {/* Section 6: Get In Touch */}
          <section className="space-y-4">
            <div className="flex items-center gap-3 text-lg font-bold text-white">
              <BookOpen className="text-white/70" />
              6. Thanks & Get In Touch
            </div>
            <div className="pl-9 space-y-4">
              <p className="text-sm text-white/60">Thank you for exploring NeuroBoard! If you have questions, want to collaborate, or just want to say hi, feel free to reach out to me.</p>
              
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <a href="mailto:bibekdas1055@gmail.com" className="flex items-center gap-3 p-3 rounded-xl bg-white/5 border border-white/10 hover:bg-white/10 transition-colors group">
                  <div className="w-8 h-8 rounded-lg bg-indigo-500/20 text-indigo-400 flex items-center justify-center group-hover:scale-110 transition-transform">
                    ✉️
                  </div>
                  <div>
                    <p className="text-xs text-white/50 font-bold uppercase tracking-wider">Email</p>
                    <p className="text-sm text-white/90">bibekdas1055@gmail.com</p>
                  </div>
                </a>
                
                <a href="https://bibek-das.vercel.app/" target="_blank" rel="noreferrer" className="flex items-center gap-3 p-3 rounded-xl bg-white/5 border border-white/10 hover:bg-white/10 transition-colors group">
                  <div className="w-8 h-8 rounded-lg bg-indigo-500/20 text-indigo-400 flex items-center justify-center group-hover:scale-110 transition-transform">
                    🌐
                  </div>
                  <div>
                    <p className="text-xs text-white/50 font-bold uppercase tracking-wider">Portfolio</p>
                    <p className="text-sm text-white/90">bibek-das.vercel.app</p>
                  </div>
                </a>

                <a href="https://github.com/Be-bibek" target="_blank" rel="noreferrer" className="flex items-center gap-3 p-3 rounded-xl bg-white/5 border border-white/10 hover:bg-white/10 transition-colors group">
                  <div className="w-8 h-8 rounded-lg bg-indigo-500/20 text-indigo-400 flex items-center justify-center group-hover:scale-110 transition-transform">
                    <Box size={16} />
                  </div>
                  <div>
                    <p className="text-xs text-white/50 font-bold uppercase tracking-wider">GitHub</p>
                    <p className="text-sm text-white/90">Be-bibek</p>
                  </div>
                </a>

                <a href="https://linkedin.com/in/bibek-das" target="_blank" rel="noreferrer" className="flex items-center gap-3 p-3 rounded-xl bg-white/5 border border-white/10 hover:bg-white/10 transition-colors group">
                  <div className="w-8 h-8 rounded-lg bg-indigo-500/20 text-indigo-400 flex items-center justify-center group-hover:scale-110 transition-transform">
                    💼
                  </div>
                  <div>
                    <p className="text-xs text-white/50 font-bold uppercase tracking-wider">LinkedIn</p>
                    <p className="text-sm text-white/90">Bibek Das</p>
                  </div>
                </a>

                <a href="https://instagram.com/bibek-das" target="_blank" rel="noreferrer" className="flex items-center gap-3 p-3 rounded-xl bg-white/5 border border-white/10 hover:bg-white/10 transition-colors group">
                  <div className="w-8 h-8 rounded-lg bg-indigo-500/20 text-indigo-400 flex items-center justify-center group-hover:scale-110 transition-transform">
                    📸
                  </div>
                  <div>
                    <p className="text-xs text-white/50 font-bold uppercase tracking-wider">Instagram</p>
                    <p className="text-sm text-white/90">Bibek Das</p>
                  </div>
                </a>
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
