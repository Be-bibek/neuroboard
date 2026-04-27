import React, { useState, useEffect } from 'react';
import { X, Shield, Cpu, Activity, Layout, Terminal, Zap } from 'lucide-react';

interface SettingsModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const SettingsModal: React.FC<SettingsModalProps> = ({ isOpen, onClose }) => {
  const [activeTab, setActiveTab] = useState('Agent');
  const [settings, setSettings] = useState<any>(null);
  const [servers, setServers] = useState<any[]>([]);
  const [llmStatus, setLlmStatus] = useState<any>(null);
  const [llmChecking, setLlmChecking] = useState(false);

  useEffect(() => {
    if (isOpen) {
      fetchSettings();
      fetchServers();
      fetchLlmStatus();
    }
  }, [isOpen]);

  const fetchSettings = async () => {
    try {
      const res = await fetch('http://localhost:8000/api/v1/settings');
      const data = await res.json();
      setSettings(data);
    } catch (e) {
      console.error("Failed to fetch settings:", e);
    }
  };

  const fetchServers = async () => {
    try {
      const res = await fetch('http://localhost:8000/api/v1/mcp/servers');
      const data = await res.json();
      setServers(data.servers);
    } catch (e) {
      console.error("Failed to fetch servers:", e);
    }
  };

  const fetchLlmStatus = async () => {
    setLlmChecking(true);
    try {
      const res = await fetch('http://localhost:8000/api/v1/llm/status');
      const data = await res.json();
      setLlmStatus(data);
    } catch (e) {
      setLlmStatus({ status: 'error', connected: false, provider: 'Google Gemini', message: 'Backend unreachable' });
    } finally {
      setLlmChecking(false);
    }
  };

  const updateSetting = async (section: string, key: string, value: any) => {
    const newSettings = {
      ...settings,
      [section]: {
        ...settings[section],
        [key]: value
      }
    };
    setSettings(newSettings);
    
    try {
      await fetch('http://localhost:8000/api/v1/settings', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(newSettings)
      });
    } catch (e) {
      console.error("Failed to update settings:", e);
    }
  };

  const toggleServer = async (server: string, currentStatus: string) => {
    const action = currentStatus === 'running' ? 'stop' : 'start';
    try {
      await fetch(`http://localhost:8000/api/v1/mcp/servers/${server}/${action}`, { method: 'POST' });
      fetchServers();
    } catch (e) {
      console.error(e);
    }
  };

  if (!isOpen || !settings) return null;

  const renderTabContent = () => {
    switch (activeTab) {
      case 'Agent':
        return (
          <div className="space-y-3">
            <div className="flex items-center justify-between p-3 border-b border-white/5 hover:bg-white/[0.02] transition-colors rounded-lg">
              <div>
                <h4 className="text-xs font-semibold text-white/90">Strict Logic Validation</h4>
                <p className="text-[10px] text-white/40 mt-0.5">Force agent to run full DRC before completion</p>
              </div>
              <button 
                onClick={() => updateSetting('agent', 'strict_mode', !settings.agent.strict_mode)}
                className={`w-8 h-4 rounded-full relative transition-all duration-300 ${settings.agent.strict_mode ? 'bg-indigo-600' : 'bg-white/10'}`}
              >
                <div className={`w-3 h-3 bg-white rounded-full absolute top-0.5 transition-transform ${settings.agent.strict_mode ? 'translate-x-4.5' : 'translate-x-0.5'}`} />
              </button>
            </div>

            <div className="flex items-center justify-between p-3 border-b border-white/5 hover:bg-white/[0.02] transition-colors rounded-lg">
              <div>
                <h4 className="text-xs font-semibold text-white/90">Step Review Policy</h4>
              </div>
              <select 
                value={settings.agent.review_policy}
                onChange={(e) => updateSetting('agent', 'review_policy', e.target.value)}
                className="bg-black/20 border border-white/10 rounded px-2 py-1 text-[11px] text-white/80 outline-none focus:border-indigo-500/50 w-48"
              >
                <option value="auto">Autonomous (No Intervention)</option>
                <option value="require_confirmation">Manual Approval Required</option>
                <option value="dry_run">Dry Run (No Hardware Sync)</option>
              </select>
            </div>

            <div className="flex items-center justify-between p-3 border-b border-white/5 hover:bg-white/[0.02] transition-colors rounded-lg">
              <div>
                <h4 className="text-xs font-semibold text-white/90">Maximum Iteration Depth</h4>
              </div>
              <input 
                type="number" 
                value={settings.agent.max_iterations}
                onChange={(e) => updateSetting('agent', 'max_iterations', parseInt(e.target.value))}
                className="bg-black/20 border border-white/10 rounded px-2 py-1 text-[11px] text-white/80 outline-none focus:border-indigo-500/50 w-20 text-right"
              />
            </div>
          </div>
        );
      case 'Models':
        return (
          <div className="space-y-3">
            <div className="flex items-center justify-between p-3 border-b border-white/5 hover:bg-white/[0.02] transition-colors rounded-lg">
              <h4 className="text-xs font-semibold text-white/90">Parsing Engine (Fast)</h4>
              <select 
                value={settings.models.fast_model}
                onChange={(e) => updateSetting('models', 'fast_model', e.target.value)}
                className="bg-black/20 border border-white/10 rounded px-2 py-1 text-[11px] text-white/80 outline-none focus:border-indigo-500/50 w-48"
              >
                <option>Gemini 1.5 Flash</option>
                <option>GPT-4o-mini</option>
              </select>
            </div>
            
            <div className="flex items-center justify-between p-3 border-b border-white/5 hover:bg-white/[0.02] transition-colors rounded-lg">
              <h4 className="text-xs font-semibold text-white/90">Reasoning Engine (Deep)</h4>
              <select 
                value={settings.models.reasoning_model}
                onChange={(e) => updateSetting('models', 'reasoning_model', e.target.value)}
                className="bg-black/20 border border-white/10 rounded px-2 py-1 text-[11px] text-white/80 outline-none focus:border-indigo-500/50 w-48"
              >
                <option>Claude 3.5 Sonnet</option>
                <option>GPT-4o</option>
                <option>Gemini 1.5 Pro</option>
              </select>
            </div>
          </div>
        );
      case 'MCP':
        return (
          <div className="space-y-4">
            <div className="flex gap-2 mb-4">
              <button onClick={fetchServers} className="bg-white/5 hover:bg-white/10 border border-white/10 rounded px-3 py-1 text-[10px] text-white/80 transition-colors">Refresh Hub</button>
              <button className="bg-indigo-600/20 hover:bg-indigo-600/30 text-indigo-400 border border-indigo-500/30 rounded px-3 py-1 text-[10px] transition-colors">System Config</button>
            </div>
            <div className="space-y-1">
              {servers.map(s => (
                <div key={s.name} className="flex items-center justify-between p-2 hover:bg-white/[0.02] border border-transparent hover:border-white/5 rounded-lg transition-colors">
                  <div className="flex items-center gap-2">
                    <span className={`w-1.5 h-1.5 rounded-full ${s.status === 'running' ? 'bg-emerald-400' : 'bg-white/20'}`} />
                    <h5 className="text-[11px] font-semibold text-white/90">{s.name}</h5>
                    <span className="text-[9px] text-white/40 ml-2 bg-black/20 px-1.5 rounded">{s.tool_count} tools</span>
                  </div>
                  <button 
                    onClick={() => toggleServer(s.name, s.status)}
                    className={`text-[9px] px-2 py-0.5 rounded border transition-colors ${s.status === 'running' ? 'bg-rose-500/10 text-rose-400 border-rose-500/20 hover:bg-rose-500/20' : 'bg-white/5 text-white/60 border-white/10 hover:text-white'}`}
                  >
                    {s.status === 'running' ? 'STOP' : 'START'}
                  </button>
                </div>
              ))}
            </div>
          </div>
        );
      case 'PCB':
        return (
          <div className="space-y-3">
            <div className="grid grid-cols-2 gap-3">
              <div className="bg-black/20 p-3 rounded-lg border border-white/5">
                <h4 className="text-[10px] font-bold uppercase tracking-widest text-white/40 mb-1.5">Default Trace Width</h4>
                <input 
                  type="number" step="0.05"
                  value={settings.pcb.default_trace_width}
                  onChange={(e) => updateSetting('pcb', 'default_trace_width', parseFloat(e.target.value))}
                  className="w-full bg-black/40 border border-white/10 rounded px-2 py-1.5 text-xs text-white/80 outline-none focus:border-indigo-500/50"
                />
              </div>
              <div className="bg-black/20 p-3 rounded-lg border border-white/5">
                <h4 className="text-[10px] font-bold uppercase tracking-widest text-white/40 mb-1.5">Impedance Target</h4>
                <input 
                  type="text" 
                  value={settings.pcb.impedance_target}
                  onChange={(e) => updateSetting('pcb', 'impedance_target', e.target.value)}
                  className="w-full bg-black/40 border border-white/10 rounded px-2 py-1.5 text-xs text-white/80 outline-none focus:border-indigo-500/50"
                />
              </div>
              <div className="bg-black/20 p-3 rounded-lg border border-white/5">
                <h4 className="text-[10px] font-bold uppercase tracking-widest text-white/40 mb-1.5">Power Rails Min Width</h4>
                <input 
                  type="number" step="0.1"
                  value={settings.pcb.power_trace_min_width}
                  onChange={(e) => updateSetting('pcb', 'power_trace_min_width', parseFloat(e.target.value))}
                  className="w-full bg-black/40 border border-white/10 rounded px-2 py-1.5 text-xs text-white/80 outline-none focus:border-indigo-500/50"
                />
              </div>
              <div className="bg-black/20 p-3 rounded-lg border border-white/5">
                <h4 className="text-[10px] font-bold uppercase tracking-widest text-white/40 mb-1.5">Constraint Logic</h4>
                <select 
                  value={settings.pcb.constraint_mode}
                  onChange={(e) => updateSetting('pcb', 'constraint_mode', e.target.value)}
                  className="w-full bg-black/40 border border-white/10 rounded px-2 py-1.5 text-xs text-white/80 outline-none focus:border-indigo-500/50"
                >
                  <option value="strict_physics">Deterministic Physics</option>
                  <option value="ai_assisted">LLM Optimized</option>
                </select>
              </div>
            </div>
          </div>
        );
      case 'System':
        return (
          <div className="space-y-3">
            <button className="w-full flex items-center justify-center gap-2 bg-rose-500/10 text-rose-400 border border-rose-500/20 rounded-lg py-2 text-xs hover:bg-rose-500/20 transition-colors">
              Clear Volatile Memory
            </button>
            <button className="w-full flex items-center justify-center gap-2 bg-amber-500/10 text-amber-400 border border-amber-500/20 rounded-lg py-2 text-xs hover:bg-amber-500/20 transition-colors">
              Reset Semantic Layout Context
            </button>
          </div>
        );
      case 'AI Engine':
        return (
          <div className="space-y-4">
            {/* Connection status card */}
            <div className="p-4 rounded-xl border border-white/10 bg-black/30 flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className={`relative flex h-3 w-3`}>
                  <span className={`animate-ping absolute inline-flex h-full w-full rounded-full opacity-75 ${
                    llmStatus?.connected ? 'bg-emerald-400' : 'bg-rose-400'
                  }`} />
                  <span className={`relative inline-flex rounded-full h-3 w-3 ${
                    llmStatus?.connected ? 'bg-emerald-500' : 'bg-rose-500'
                  }`} />
                </div>
                <div>
                  <p className="text-xs font-bold text-white/90">{llmStatus?.provider ?? 'Google Gemini'}</p>
                  <p className={`text-[10px] mt-0.5 ${
                    llmStatus?.connected ? 'text-emerald-400' : 'text-rose-400'
                  }`}>
                    {llmChecking ? 'Checking…' : (llmStatus?.connected ? '● Active — Connection Verified' : `✗ ${llmStatus?.message ?? 'Offline'}`)}
                  </p>
                </div>
              </div>
              <button
                onClick={fetchLlmStatus}
                disabled={llmChecking}
                className="text-[10px] px-3 py-1.5 rounded border border-white/10 bg-white/5 hover:bg-white/10 text-white/60 hover:text-white transition-colors disabled:opacity-40"
              >
                {llmChecking ? 'Testing…' : 'Re-check'}
              </button>
            </div>

            {/* Model info */}
            <div className="space-y-2">
              <div className="flex items-center justify-between p-3 rounded-lg border border-white/5 bg-black/20">
                <div>
                  <h4 className="text-xs font-semibold text-white/90">Planning Engine</h4>
                  <p className="text-[10px] text-white/40 mt-0.5">Gemini 1.5 Flash — 1M token context</p>
                </div>
                <span className="text-[9px] px-2 py-0.5 rounded-full bg-indigo-500/20 text-indigo-400 border border-indigo-500/30 font-semibold">PRIMARY</span>
              </div>
              <div className="flex items-center justify-between p-3 rounded-lg border border-white/5 bg-black/20">
                <div>
                  <h4 className="text-xs font-semibold text-white/90">Rate Limits (Free Tier)</h4>
                  <p className="text-[10px] text-white/40 mt-0.5">15 RPM · 1,500 RPD · 1M TPM</p>
                </div>
                <span className="text-[9px] px-2 py-0.5 rounded-full bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 font-semibold">UNLIMITED</span>
              </div>
              <div className="flex items-center justify-between p-3 rounded-lg border border-white/5 bg-black/20">
                <div>
                  <h4 className="text-xs font-semibold text-white/90">System Instruction</h4>
                  <p className="text-[10px] text-white/40 mt-0.5 leading-relaxed">Expert ECE Hardware Engineer → JSON plans for KiCad 10</p>
                </div>
                <span className="text-[9px] px-2 py-0.5 rounded-full bg-white/10 text-white/50 border border-white/10 font-semibold">LOCKED</span>
              </div>
            </div>
          </div>
        );
      default:
        return null;
    }
  };

  const tabs = [
    { name: 'Agent', icon: <Activity size={16} /> },
    { name: 'Models', icon: <Cpu size={16} /> },
    { name: 'MCP', icon: <Shield size={16} /> },
    { name: 'PCB', icon: <Layout size={16} /> },
    { name: 'AI Engine', icon: <Zap size={16} /> },
    { name: 'System', icon: <Terminal size={16} /> },
  ];

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/40 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="w-[700px] h-[450px] flex glass-panel overflow-hidden border-white/10 shadow-2xl rounded-xl">
        
        {/* Sidebar */}
        <div className="w-[160px] bg-black/40 border-r border-white/5 flex flex-col">
          <div className="flex items-center gap-2 p-4 border-b border-white/5">
             <div className="w-6 h-6 rounded flex items-center justify-center bg-indigo-500/20 text-indigo-400">
                <Shield size={14} />
             </div>
             <h3 className="text-xs font-bold text-white/80 tracking-wide uppercase">Settings</h3>
          </div>
          <div className="flex-1 p-2 space-y-0.5">
            {tabs.map(tab => (
              <button
                key={tab.name}
                onClick={() => setActiveTab(tab.name)}
                className={`w-full flex items-center gap-2 px-3 py-2 rounded text-[11px] transition-colors ${activeTab === tab.name ? 'bg-indigo-500/10 text-indigo-400 font-semibold' : 'text-white/50 hover:bg-white/5 hover:text-white/90'}`}
              >
                {tab.icon}
                {tab.name}
              </button>
            ))}
          </div>
          <div className="p-2 border-t border-white/5">
            <button onClick={onClose} className="w-full text-[10px] py-2 rounded hover:bg-white/5 text-white/40 hover:text-white transition-colors">
               Close
            </button>
          </div>
        </div>

        {/* Content Area */}
        <div className="flex-1 flex flex-col bg-black/20">
          <div className="px-6 py-3 border-b border-white/5 flex justify-between items-center bg-white/[0.01]">
            <h2 className="text-sm font-semibold text-white/90">{activeTab} Parameters</h2>
            <button onClick={onClose} className="p-1 rounded hover:bg-white/10 text-white/40 hover:text-white transition-colors">
              <X size={14} />
            </button>
          </div>
          <div className="flex-1 overflow-y-auto p-6 scrollbar-none">
            {renderTabContent()}
          </div>
        </div>
      </div>
    </div>
  );
};
