import React, { useState, useEffect } from 'react';
import { X, Shield, Cpu, Activity, Layout, Terminal } from 'lucide-react';

interface SettingsModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const SettingsModal: React.FC<SettingsModalProps> = ({ isOpen, onClose }) => {
  const [activeTab, setActiveTab] = useState('Agent');
  const [settings, setSettings] = useState<any>(null);
  const [servers, setServers] = useState<any[]>([]);

  useEffect(() => {
    if (isOpen) {
      fetchSettings();
      fetchServers();
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
          <div className="space-y-6">
            <div className="glass-card p-5 bg-white/[0.03]">
              <div className="flex items-center justify-between mb-4">
                <div>
                  <h4 className="text-sm font-bold text-white/90 tracking-tight">Strict Logic Validation</h4>
                  <p className="text-[11px] text-white/40 mt-1">Force agent to run full DRC before completion</p>
                </div>
                <button 
                  onClick={() => updateSetting('agent', 'strict_mode', !settings.agent.strict_mode)}
                  className={`w-11 h-6 rounded-full relative transition-all duration-300 ${settings.agent.strict_mode ? 'bg-indigo-600 shadow-[0_0_12px_theme("colors.indigo.600")]' : 'bg-white/10'}`}
                >
                  <div className={`w-4 h-4 bg-white rounded-full absolute top-1 transition-transform shadow-lg ${settings.agent.strict_mode ? 'translate-x-6' : 'translate-x-1'}`} />
                </button>
              </div>
            </div>

            <div className="glass-card p-5 bg-white/[0.03]">
              <h4 className="text-sm font-bold text-white/90 mb-3 tracking-tight">Step Review Policy</h4>
              <select 
                value={settings.agent.review_policy}
                onChange={(e) => updateSetting('agent', 'review_policy', e.target.value)}
                className="w-full bg-white/5 border border-white/10 rounded-xl p-3 text-xs text-white/80 outline-none focus:border-indigo-500/50 transition-all"
              >
                <option value="auto">Autonomous (No Intervention)</option>
                <option value="require_confirmation">Manual Approval Required</option>
                <option value="dry_run">Dry Run (No Hardware Sync)</option>
              </select>
            </div>

            <div className="glass-card p-5 bg-white/[0.03]">
              <h4 className="text-sm font-bold text-white/90 mb-3 tracking-tight">Maximum Iteration Depth</h4>
              <input 
                type="number" 
                value={settings.agent.max_iterations}
                onChange={(e) => updateSetting('agent', 'max_iterations', parseInt(e.target.value))}
                className="w-full bg-white/5 border border-white/10 rounded-xl p-3 text-xs text-white/80 outline-none focus:border-indigo-500/50"
              />
            </div>
          </div>
        );
      case 'Models':
        return (
          <div className="space-y-6">
            <div className="glass-card p-5 bg-white/[0.03]">
              <h4 className="text-sm font-bold text-white/90 mb-3 tracking-tight">Parsing Engine (Fast)</h4>
              <select 
                value={settings.models.fast_model}
                onChange={(e) => updateSetting('models', 'fast_model', e.target.value)}
                className="w-full bg-white/5 border border-white/10 rounded-xl p-3 text-xs text-white/80 outline-none focus:border-indigo-500/50"
              >
                <option>Gemini 1.5 Flash</option>
                <option>GPT-4o-mini</option>
              </select>
            </div>
            
            <div className="glass-card p-5 bg-white/[0.03]">
              <h4 className="text-sm font-bold text-white/90 mb-3 tracking-tight">Reasoning Engine (Deep)</h4>
              <select 
                value={settings.models.reasoning_model}
                onChange={(e) => updateSetting('models', 'reasoning_model', e.target.value)}
                className="w-full bg-white/5 border border-white/10 rounded-xl p-3 text-xs text-white/80 outline-none focus:border-indigo-500/50"
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
            <div className="flex gap-3">
              <button onClick={fetchServers} className="glass-button flex-1 text-xs py-3 border-white/10">Refresh Hub</button>
              <button className="glass-button flex-1 bg-indigo-600/20 text-indigo-400 border-indigo-500/30 text-xs py-3 hover:bg-indigo-600/30">System Config</button>
            </div>
            <div className="space-y-3">
              {servers.map(s => (
                <div key={s.name} className="glass-card p-4 flex items-center justify-between bg-white/[0.02]">
                  <div>
                    <h5 className="text-sm font-bold text-white/90 flex items-center gap-3">
                      <span className={`w-2 h-2 rounded-full ${s.status === 'running' ? 'bg-emerald-400 shadow-[0_0_10px_theme("colors.emerald.400")]' : 'bg-white/10'}`} />
                      {s.name}
                    </h5>
                    <p className="text-[10px] text-white/40 mt-1 uppercase font-bold tracking-widest">{s.tool_count} Active Tools</p>
                  </div>
                  <button 
                    onClick={() => toggleServer(s.name, s.status)}
                    className={`w-11 h-6 rounded-full relative transition-all duration-300 ${s.status === 'running' ? 'bg-indigo-600 shadow-[0_0_12px_theme("colors.indigo.600")]' : 'bg-white/10'}`}
                  >
                    <div className={`w-4 h-4 bg-white rounded-full absolute top-1 transition-transform ${s.status === 'running' ? 'translate-x-6' : 'translate-x-1'}`} />
                  </button>
                </div>
              ))}
            </div>
          </div>
        );
      case 'PCB':
        return (
          <div className="space-y-6">
            <div className="glass-card p-6 bg-white/[0.03] grid grid-cols-2 gap-6">
              <div>
                <h4 className="text-[10px] font-bold uppercase tracking-widest text-white/40 mb-2">Default Trace Width</h4>
                <input 
                  type="number" step="0.05"
                  value={settings.pcb.default_trace_width}
                  onChange={(e) => updateSetting('pcb', 'default_trace_width', parseFloat(e.target.value))}
                  className="w-full bg-white/5 border border-white/10 rounded-xl p-3 text-xs text-white/80 outline-none focus:border-indigo-500/50"
                />
              </div>
              <div>
                <h4 className="text-[10px] font-bold uppercase tracking-widest text-white/40 mb-2">Impedance Target</h4>
                <input 
                  type="text" 
                  value={settings.pcb.impedance_target}
                  onChange={(e) => updateSetting('pcb', 'impedance_target', e.target.value)}
                  className="w-full bg-white/5 border border-white/10 rounded-xl p-3 text-xs text-white/80 outline-none focus:border-indigo-500/50"
                />
              </div>
              <div>
                <h4 className="text-[10px] font-bold uppercase tracking-widest text-white/40 mb-2">Power Rails Min Width</h4>
                <input 
                  type="number" step="0.1"
                  value={settings.pcb.power_trace_min_width}
                  onChange={(e) => updateSetting('pcb', 'power_trace_min_width', parseFloat(e.target.value))}
                  className="w-full bg-white/5 border border-white/10 rounded-xl p-3 text-xs text-white/80 outline-none focus:border-indigo-500/50"
                />
              </div>
              <div>
                <h4 className="text-[10px] font-bold uppercase tracking-widest text-white/40 mb-2">Constraint Logic</h4>
                <select 
                  value={settings.pcb.constraint_mode}
                  onChange={(e) => updateSetting('pcb', 'constraint_mode', e.target.value)}
                  className="w-full bg-white/5 border border-white/10 rounded-xl p-3 text-xs text-white/80 outline-none focus:border-indigo-500/50"
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
          <div className="space-y-4">
            <button className="w-full glass-button bg-rose-500/10 text-rose-400 border-rose-500/20 py-4 hover:bg-rose-500/20 shadow-xl shadow-rose-500/5">
              Clear Volatile Memory
            </button>
            <button className="w-full glass-button bg-amber-500/10 text-amber-400 border-amber-500/20 py-4 hover:bg-amber-500/20 shadow-xl shadow-amber-500/5">
              Reset Semantic Layout Context
            </button>
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
    { name: 'System', icon: <Terminal size={16} /> },
  ];

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center p-12 bg-black/70 backdrop-blur-md animate-in fade-in duration-300">
      <div className="w-[1000px] h-[750px] flex glass-panel overflow-hidden border-white/20 shadow-[0_0_80px_rgba(0,0,0,0.6)]">
        
        {/* Sidebar */}
        <div className="w-[260px] bg-black/20 border-r border-white/10 p-8 flex flex-col">
          <div className="flex items-center gap-4 mb-12 px-2">
             <div className="w-10 h-10 rounded-2xl bg-indigo-600 flex items-center justify-center shadow-[0_0_20px_rgba(79,70,229,0.4)]">
                <Shield size={20} className="text-white" />
             </div>
             <h3 className="text-base font-black text-white tracking-widest uppercase">Settings</h3>
          </div>
          <div className="space-y-1 flex-1">
            {tabs.map(tab => (
              <button
                key={tab.name}
                onClick={() => setActiveTab(tab.name)}
                className={`w-full flex items-center gap-4 px-5 py-4 rounded-2xl text-sm transition-all duration-300 ${activeTab === tab.name ? 'bg-indigo-600/20 text-indigo-400 font-bold border border-indigo-500/20 shadow-xl shadow-indigo-500/5' : 'text-white/40 hover:bg-white/5 hover:text-white/70'}`}
              >
                {tab.icon}
                {tab.name}
              </button>
            ))}
          </div>
          <button onClick={onClose} className="glass-button text-xs py-4 border-white/10 text-white/40 hover:text-white mt-auto rounded-2xl">
             Close Interface
          </button>
        </div>

        {/* Content Area */}
        <div className="flex-1 flex flex-col bg-black/10">
          <div className="px-10 py-8 border-b border-white/10 flex justify-between items-center bg-white/[0.02]">
            <h2 className="text-2xl font-black text-white tracking-tight">{activeTab} <span className="text-white/20 font-light">Parameters</span></h2>
            <button onClick={onClose} className="p-3 rounded-2xl text-white/20 hover:bg-white/10 hover:text-white transition-all border border-transparent hover:border-white/10">
              <X size={24} />
            </button>
          </div>
          <div className="flex-1 overflow-y-auto p-10 scrollbar-none">
            {renderTabContent()}
          </div>
        </div>
      </div>
    </div>
  );
};
