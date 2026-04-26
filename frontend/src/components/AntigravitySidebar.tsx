import React, { useState, useEffect, useRef } from 'react';

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

// --- Antigravity Style Sidebar ---
export const AntigravitySidebar: React.FC = () => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [model, setModel] = useState('Gemini 1.5 Flash');
  const [toolsRunning, setToolsRunning] = useState<ToolExecution[]>([]);
  const [servers, setServers] = useState<MCPServer[]>([]);
  const [kicadStatus, setKicadStatus] = useState<'connected' | 'disconnected'>('disconnected');
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll
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
      content: 'Welcome to NeuroBoard AI. MCP Runtime initialized. Type @board for context or @nets to query connections.',
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
    const newMsg: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: intent,
      timestamp: new Date()
    };
    
    setMessages(prev => [...prev, newMsg]);
    setInput('');
    
    const agentMsgId = (Date.now() + 1).toString();
    setMessages(prev => [...prev, {
      id: agentMsgId,
      role: 'agent',
      content: 'Initializing LangGraph Agent Workflow...',
      timestamp: new Date()
    }]);

    const eventSource = new EventSource(`http://localhost:8000/api/v1/agent/run?intent=${encodeURIComponent(intent)}`);
    
    eventSource.onmessage = (event) => {
      const data = JSON.parse(event.data);
      const nodeName = data.node;
      
      if (nodeName === 'END') {
        setMessages(prev => prev.map(m => 
          m.id === agentMsgId 
            ? { ...m, content: m.content + '\n\n✅ Workflow Completed.' }
            : m
        ));
        eventSource.close();
        return;
      }
      
      if (nodeName === 'ERROR') {
         setMessages(prev => prev.map(m => 
          m.id === agentMsgId 
            ? { ...m, content: m.content + `\n\n❌ Error: ${data.error}` }
            : m
        ));
        eventSource.close();
        return;
      }

      setMessages(prev => prev.map(m => 
        m.id === agentMsgId 
          ? { ...m, content: m.content + `\n\n[Agent Node] Executed: **${nodeName}**` }
          : m
      ));

      if (nodeName === 'execution' && data.state.execution_results) {
        data.state.execution_results.forEach((res: any, idx: number) => {
           const tid = `tool_${Date.now()}_${idx}`;
           setToolsRunning(prev => [...prev, {
             id: tid,
             tool: res.action === 'executed' ? 'mcp.apply_routing_strategy' : 'mcp.simulate',
             status: res.action === 'error' ? 'error' : 'success',
             args: res.plan_item,
             result: res.result
           }]);
        });
      }
      
      if (nodeName === 'verification' && data.state.drc_errors?.length > 0) {
        setMessages(prev => prev.map(m => 
          m.id === agentMsgId 
            ? { ...m, content: m.content + `\n\n⚠️ DRC Errors found: ${data.state.drc_errors.join(', ')}` }
            : m
        ));
      }
    };
    
    eventSource.onerror = (err) => {
      console.error("SSE Error:", err);
      eventSource.close();
    };
  };

  return (
    <div className="flex flex-col h-full w-full bg-zinc-900/40 backdrop-blur-xl border-l border-white/10 text-gray-100 shadow-2xl font-sans rounded-l-2xl overflow-hidden transition-all duration-200 shadow-inner shadow-white/5">
      
      {/* Header & Status (Continue.dev + LibreChat hybrid) */}
      <div className="p-5 border-b border-white/10 flex flex-col gap-4 bg-zinc-950/30">
        <div className="flex justify-between items-center">
          <h2 className="text-sm font-semibold tracking-wide text-zinc-100 flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-teal-500 shadow-[0_0_8px_rgba(20,184,166,0.8)] animate-pulse"></span>
            NeuroBoard Agent
          </h2>
          
          {/* LibreChat Style Model Select */}
          <div className="relative group">
            <select 
              value={model} 
              onChange={(e) => setModel(e.target.value)}
              className="appearance-none bg-zinc-800/50 hover:bg-zinc-700/60 text-xs font-medium border border-white/10 rounded-xl pl-3 pr-8 py-1.5 outline-none focus:border-teal-500/50 focus:ring-1 focus:ring-teal-500/50 transition-all duration-200 cursor-pointer shadow-inner shadow-white/5"
            >
              <option value="Gemini 1.5 Flash">Gemini 1.5 Flash (Fast)</option>
              <option value="Claude 3.5 Sonnet">Claude 3.5 Sonnet (Reasoning)</option>
            </select>
            <div className="absolute right-2 top-1/2 -translate-y-1/2 pointer-events-none text-zinc-400 group-hover:text-zinc-300">
              <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="w-4 h-4">
                <path fillRule="evenodd" d="M5.22 8.22a.75.75 0 0 1 1.06 0L10 11.94l3.72-3.72a.75.75 0 1 1 1.06 1.06l-4.25 4.25a.75.75 0 0 1-1.06 0L5.22 9.28a.75.75 0 0 1 0-1.06Z" clipRule="evenodd" />
              </svg>
            </div>
          </div>
        </div>
        
        {/* MCP Server List (Roo Code Style Hub) */}
        <div className="flex flex-col gap-2 mt-1 bg-zinc-900/60 p-3 rounded-2xl border border-white/5 shadow-inner shadow-black/20">
          <div className="flex justify-between items-center mb-1">
            <span className="text-[10px] font-mono text-zinc-400 uppercase tracking-widest font-semibold">MCP Hub</span>
            <div className="flex items-center gap-1.5 bg-zinc-800/50 px-2 py-0.5 rounded-full border border-white/5">
              <span className={`w-1.5 h-1.5 rounded-full ${kicadStatus === 'connected' ? 'bg-emerald-400 shadow-[0_0_5px_rgba(52,211,153,0.8)]' : 'bg-red-500'}`}></span>
              <span className="text-[9px] text-zinc-300 uppercase tracking-wider font-semibold">KiCad IPC</span>
            </div>
          </div>
          {servers.map(s => (
            <div key={s.name} className="flex items-center justify-between text-xs py-1">
              <div className="flex items-center gap-2">
                 <span className={`w-1.5 h-1.5 rounded-full ${s.status === 'running' ? 'bg-teal-400 shadow-[0_0_5px_rgba(45,212,191,0.8)]' : 'bg-rose-500'}`}></span>
                 <span className="font-mono text-zinc-200">{s.name}</span>
                 {s.status === 'running' && <span className="text-[9px] bg-indigo-500/20 text-indigo-300 border border-indigo-500/30 px-1.5 py-0.5 rounded-md font-mono">{s.tool_count} tools</span>}
              </div>
              <button 
                onClick={() => toggleServer(s.name, s.status)}
                className={`text-[9px] px-2.5 py-1 rounded-lg border font-semibold transition-all duration-200 ${s.status === 'running' ? 'border-rose-500/30 text-rose-400 hover:bg-rose-500/15' : 'border-teal-500/30 text-teal-400 hover:bg-teal-500/15'}`}
              >
                {s.status === 'running' ? 'STOP' : 'START'}
              </button>
            </div>
          ))}
        </div>
      </div>

      {/* Chat Area (Continue.dev Style Streaming) */}
      <div className="flex-1 overflow-y-auto p-5 space-y-5 scrollbar-thin scrollbar-thumb-zinc-700/50 scrollbar-track-transparent">
        {messages.map(msg => (
          <div key={msg.id} className={`flex flex-col ${msg.role === 'user' ? 'items-end' : 'items-start'}`}>
            <div className={`
              max-w-[85%] px-4 py-3 text-sm whitespace-pre-wrap transition-all duration-200
              ${msg.role === 'user' ? 'bg-indigo-600/90 text-white rounded-2xl rounded-br-sm shadow-md' : ''}
              ${msg.role === 'agent' ? 'bg-zinc-800/80 border border-white/10 text-zinc-200 rounded-2xl rounded-bl-sm font-mono text-xs shadow-md shadow-black/20' : ''}
              ${msg.role === 'system' ? 'bg-teal-900/20 border border-teal-500/20 text-teal-200 text-xs text-center self-center w-full rounded-xl shadow-inner shadow-teal-500/10' : ''}
            `}>
              {msg.content}
            </div>
          </div>
        ))}

        {/* Live Tool Execution Feed */}
        {toolsRunning.map(tool => (
          <div key={tool.id} className="bg-zinc-800/60 border border-white/5 rounded-2xl p-3 text-xs w-[90%] self-start animate-fade-in shadow-lg shadow-black/20">
            <div className="flex items-center gap-2 mb-2">
              {tool.status === 'running' && (
                <svg className="animate-spin h-3.5 w-3.5 text-teal-400" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path>
                </svg>
              )}
              {tool.status === 'success' && <span className="text-emerald-400 text-sm font-bold">✓</span>}
              <span className="font-mono text-zinc-300 text-[11px] bg-zinc-900/80 px-2 py-0.5 rounded-md border border-white/5">
                {tool.tool}
              </span>
            </div>
            <div className="text-zinc-400 font-mono text-[10px] bg-black/40 p-2 rounded-xl overflow-hidden text-ellipsis whitespace-nowrap border border-black/50 shadow-inner">
              {JSON.stringify(tool.args)}
            </div>
          </div>
        ))}
        <div ref={messagesEndRef} />
      </div>

      {/* Input Area */}
      <div className="p-5 bg-zinc-900/60 border-t border-white/10 shadow-[0_-10px_30px_rgba(0,0,0,0.2)]">
        <div className="relative group">
          <textarea 
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                handleSend();
              }
            }}
            placeholder="Type @board to read layout, @nets to analyze..."
            className="w-full bg-zinc-950/50 border border-white/10 hover:border-white/20 focus:border-teal-500/50 focus:ring-1 focus:ring-teal-500/50 rounded-2xl pl-4 pr-12 py-3.5 text-sm text-zinc-200 placeholder-zinc-500 resize-none outline-none transition-all duration-200 shadow-inner shadow-black/50"
            rows={2}
          />
          <button 
            onClick={handleSend}
            disabled={!input.trim()}
            className="absolute right-2 bottom-2 p-2 bg-indigo-600 hover:bg-indigo-500 disabled:bg-zinc-800 disabled:text-zinc-600 text-white rounded-xl transition-all duration-200 shadow-md disabled:shadow-none"
          >
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" className="w-4 h-4">
              <path d="M3.478 2.405a.75.75 0 00-.926.94l2.432 7.905H13.5a.75.75 0 010 1.5H4.984l-2.432 7.905a.75.75 0 00.926.94 60.519 60.519 0 0018.445-8.986.75.75 0 000-1.218A60.517 60.517 0 003.478 2.405z" />
            </svg>
          </button>
        </div>
        <div className="flex gap-2 mt-3">
          <button onClick={() => setInput(prev => prev + '@board ')} className="text-[10px] px-2.5 py-1 rounded-lg border border-white/10 text-zinc-400 hover:bg-zinc-800 hover:text-zinc-300 hover:border-white/20 transition-all duration-200 shadow-sm">@board</button>
          <button onClick={() => setInput(prev => prev + '@nets ')} className="text-[10px] px-2.5 py-1 rounded-lg border border-white/10 text-zinc-400 hover:bg-zinc-800 hover:text-zinc-300 hover:border-white/20 transition-all duration-200 shadow-sm">@nets</button>
        </div>
      </div>

    </div>
  );
};
