import React, { useState, useEffect, useRef } from 'react';
import { SettingsModal } from './SettingsModal';
import { Send, Zap, Cpu, Activity, ShieldCheck, Info } from 'lucide-react';

// --- Types ---
interface Message {
  id: string;
  role: 'user' | 'agent' | 'system';
  content: string;
  timestamp: Date;
}

interface ToolExecution {
  id: string;
  tool: string;
  status: 'running' | 'success' | 'error';
  args: Record<string, any>;
  result?: any;
}

interface MCPServer {
  name: string;
  status: string;
  tool_count: number;
}

export const AntigravitySidebar: React.FC = () => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [model, setModel] = useState('Gemini 1.5 Flash');
  const [toolsRunning, setToolsRunning] = useState<ToolExecution[]>([]);
  const [servers, setServers] = useState<MCPServer[]>([]);
  const [kicadStatus, setKicadStatus] = useState<'connected' | 'disconnected'>('disconnected');
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, toolsRunning]);

  const fetchServers = async () => {
    try {
      const res = await fetch('http://localhost:8000/api/v1/mcp/servers');
      const data = await res.json();
      if (data.status === 'success') {
        setServers(data.servers);
      }
    } catch (e) {
      console.error("Failed to fetch MCP servers");
    }
  };

  useEffect(() => {
    setKicadStatus('connected');
    fetchServers();
    
    setMessages([{
      id: 'welcome',
      role: 'system',
      content: 'NeuroBoard AI v5.0 · MCP Runtime initialized.',
      timestamp: new Date()
    }]);
  }, []);

  const toggleServer = async (server: string, currentStatus: string) => {
    const action = currentStatus === 'running' ? 'stop' : 'start';
    try {
      await fetch(`http://localhost:8000/api/v1/mcp/servers/${server}/${action}`, { method: 'POST' });
      fetchServers();
    } catch (e) {
      console.error(e);
    }
  };

  const handleSend = async () => {
    if (!input.trim()) return;
    
    const intent = input;
    setMessages(prev => [...prev, {
      id: Date.now().toString(),
      role: 'user',
      content: intent,
      timestamp: new Date()
    }]);
    setInput('');
    
    const agentMsgId = (Date.now() + 1).toString();
    setMessages(prev => [...prev, {
      id: agentMsgId,
      role: 'agent',
      content: 'Initializing reasoning engine...',
      timestamp: new Date()
    }]);

    const eventSource = new EventSource(`http://localhost:8000/api/v1/agent/run?intent=${encodeURIComponent(intent)}`);
    
    eventSource.onmessage = (event) => {
      const data = JSON.parse(event.data);
      const node = data.type;

      if (node === 'completed') {
        setMessages(prev => prev.map(m =>
          m.id === agentMsgId ? { ...m, content: m.content + `\n\n✅ ${data.message}` } : m
        ));
        setToolsRunning(prev => prev.map(t => t.status === 'running' ? { ...t, status: 'success' } : t));
        eventSource.close();
        return;
      }

      if (node === 'error') {
        setMessages(prev => prev.map(m =>
          m.id === agentMsgId ? { ...m, content: m.content + `\n\n❌ ${data.message}` } : m
        ));
        eventSource.close();
        return;
      }

      if (node === 'status') {
        setMessages(prev => prev.map(m =>
          m.id === agentMsgId ? { ...m, content: m.content + `\n${data.message}` } : m
        ));
        return;
      }

      if (node === 'plan' && data.plan) {
        const planText = data.plan.map((s: any, i: number) =>
          `  ${i + 1}. ${s.action || s.tool}`
        ).join('\n');
        setMessages(prev => prev.map(m =>
          m.id === agentMsgId
            ? { ...m, content: m.content + `\n\n📋 **Plan:**\n${planText}` }
            : m
        ));
        return;
      }

      if (node === 'tool_selected') {
        const tid = `tool_${Date.now()}`;
        setToolsRunning(prev => [...prev, {
          id: tid,
          tool: data.tool,
          status: 'running',
          args: { action: data.action },
        }]);
        return;
      }

      if (node === 'action') {
        setToolsRunning(prev => {
          const last = [...prev].reverse().find(t => t.status === 'running');
          if (!last) return [...prev, {
            id: `tool_${Date.now()}`,
            tool: data.tool,
            status: data.status === 'success' ? 'success' : 'error',
            args: {},
            result: data.result,
          }];
          return prev.map(t => t.id === last.id
            ? { ...t, tool: data.tool, status: data.status === 'success' ? 'success' : 'error', result: data.result }
            : t
          );
        });
        if (data.message) {
          setMessages(prev => prev.map(m =>
            m.id === agentMsgId ? { ...m, content: m.content + `\n${data.message}` } : m
          ));
        }
      }
    };

    eventSource.onerror = () => eventSource.close();
  };

  return (
    <div className="flex flex-col h-full w-full bg-transparent text-white overflow-hidden font-sans">
      
      {/* Header */}
      <div className="px-6 py-5 border-b border-white/5 bg-white/5 backdrop-blur-md">
        <div className="flex justify-between items-center mb-4">
          <div className="flex items-center gap-2">
            <div className="relative">
               <Activity size={16} className="text-indigo-400" />
               <span className="absolute -top-1 -right-1 w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
            </div>
            <h2 className="text-sm font-bold tracking-tight text-white/90 uppercase">AI Reasoning</h2>
          </div>
          <button onClick={() => setIsSettingsOpen(true)} className="p-2 hover:bg-white/10 rounded-xl transition-colors">
             <Cpu size={16} className="text-white/60" />
          </button>
        </div>
        
        {/* MCP Hub Glass Panel */}
        <div className="bg-black/20 border border-white/5 rounded-2xl p-3 shadow-inner shadow-black/40">
          <div className="flex items-center gap-2 mb-3 px-1">
             <ShieldCheck size={12} className="text-indigo-400" />
             <span className="text-[10px] font-bold text-white/40 uppercase tracking-[0.2em]">Runtime Hub</span>
          </div>
          <div className="space-y-2">
            {servers.map(s => (
              <div key={s.name} className="flex items-center justify-between text-[11px] group">
                <div className="flex items-center gap-2">
                   <div className={`w-1.5 h-1.5 rounded-full ${s.status === 'running' ? 'bg-indigo-400 shadow-[0_0_8px_theme("colors.indigo.400")]' : 'bg-white/20'}`}></div>
                   <span className="font-medium text-white/70 group-hover:text-white transition-colors">{s.name}</span>
                </div>
                <button 
                  onClick={() => toggleServer(s.name, s.status)}
                  className={`px-3 py-1 rounded-lg border text-[10px] font-bold transition-all ${s.status === 'running' ? 'border-rose-500/20 text-rose-400 hover:bg-rose-500/10' : 'border-white/10 text-white/40 hover:bg-white/5 hover:text-white/80'}`}
                >
                  {s.status === 'running' ? 'OFF' : 'ON'}
                </button>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Chat History */}
      <div className="flex-1 overflow-y-auto px-6 py-6 space-y-6 scrollbar-none">
        {messages.map(msg => (
          <div key={msg.id} className={`flex flex-col ${msg.role === 'user' ? 'items-end' : 'items-start'}`}>
            <div className={`
              max-w-[90%] px-4 py-3 text-sm leading-relaxed shadow-2xl transition-all
              ${msg.role === 'user' ? 'bg-indigo-600/80 text-white rounded-[20px] rounded-tr-none border border-white/10' : ''}
              ${msg.role === 'agent' ? 'bg-white/5 backdrop-blur-xl border border-white/10 text-white/80 rounded-[20px] rounded-tl-none font-medium' : ''}
              ${msg.role === 'system' ? 'text-[11px] text-indigo-400/80 font-bold tracking-widest uppercase self-center' : ''}
            `}>
              <div className="whitespace-pre-wrap">{msg.content}</div>
            </div>
          </div>
        ))}

        {/* Tool Cards */}
        <div className="space-y-3">
          {toolsRunning.map(tool => (
            <div key={tool.id} className="glass-card p-4 animate-in slide-in-from-right-4 duration-300">
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-3">
                  {tool.status === 'running' ? (
                    <div className="relative flex items-center justify-center">
                       <div className="absolute w-4 h-4 rounded-full border-2 border-indigo-500/30 border-t-indigo-500 animate-spin"></div>
                       <Zap size={10} className="text-indigo-400 animate-pulse" />
                    </div>
                  ) : tool.status === 'success' ? (
                    <div className="bg-emerald-500/20 p-1 rounded-lg">
                       <ShieldCheck size={12} className="text-emerald-400" />
                    </div>
                  ) : (
                    <div className="bg-rose-500/20 p-1 rounded-lg">
                       <Info size={12} className="text-rose-400" />
                    </div>
                  )}
                  <span className="text-[11px] font-bold text-white/90 tracking-tight">{tool.tool}</span>
                </div>
                <span className={`text-[9px] font-bold px-2 py-0.5 rounded-md uppercase tracking-wider ${tool.status === 'running' ? 'bg-indigo-500/20 text-indigo-400' : tool.status === 'success' ? 'bg-emerald-500/20 text-emerald-400' : 'bg-rose-500/20 text-rose-400'}`}>
                   {tool.status}
                </span>
              </div>
              <div className="bg-black/30 rounded-xl p-3 font-mono text-[10px] text-white/40 border border-white/5 overflow-x-auto">
                {JSON.stringify(tool.args, null, 2)}
              </div>
            </div>
          ))}
        </div>
        <div ref={messagesEndRef} />
      </div>

      {/* Input Area */}
      <div className="p-6 bg-white/5 backdrop-blur-2xl border-t border-white/5 shadow-[0_-10px_40px_rgba(0,0,0,0.4)]">
        <div className="relative flex items-end gap-3">
          <div className="flex-1 relative">
            <textarea 
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault();
                  handleSend();
                }
              }}
              placeholder="How can I optimize your PCB today?"
              className="w-full bg-white/5 border border-white/10 focus:border-indigo-500/50 focus:ring-1 focus:ring-indigo-500/50 rounded-2xl pl-4 pr-10 py-4 text-sm text-white placeholder-white/20 resize-none outline-none transition-all duration-300 min-h-[56px] max-h-[160px]"
              rows={1}
            />
            <div className="absolute right-3 bottom-3 flex gap-2">
                <button 
                  onClick={handleSend}
                  disabled={!input.trim()}
                  className="p-2 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-30 text-white rounded-xl transition-all shadow-xl shadow-indigo-600/20 hover:scale-110 active:scale-95"
                >
                  <Send size={16} fill="currentColor" />
                </button>
            </div>
          </div>
        </div>
      </div>
      
      <SettingsModal isOpen={isSettingsOpen} onClose={() => setIsSettingsOpen(false)} />
    </div>
  );
};
