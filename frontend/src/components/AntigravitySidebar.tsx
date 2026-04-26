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
    <div className="flex flex-col h-full w-96 bg-gray-900/80 backdrop-blur-xl border-l border-white/10 text-gray-100 shadow-2xl font-sans">
      
      {/* Header & Status */}
      <div className="p-4 border-b border-white/10 flex flex-col gap-3 bg-gray-900/50">
        <div className="flex justify-between items-center">
          <h2 className="text-sm font-semibold tracking-wide text-gray-200">NeuroBoard AI</h2>
          <select 
            value={model} 
            onChange={(e) => setModel(e.target.value)}
            className="bg-gray-800 text-xs border border-gray-700 rounded-md px-2 py-1 outline-none focus:border-blue-500"
          >
            <option>Gemini 1.5 Flash</option>
            <option>Claude 3.5 Sonnet</option>
          </select>
        </div>
        
        {/* MCP Server List */}
        <div className="flex flex-col gap-1.5 mt-1 bg-gray-950/50 p-2 rounded-lg border border-gray-800">
          <div className="flex justify-between items-center mb-1">
            <span className="text-[10px] font-mono text-gray-400 uppercase tracking-widest">MCP Servers</span>
            <div className="flex items-center gap-1.5">
              <span className={`w-1.5 h-1.5 rounded-full ${kicadStatus === 'connected' ? 'bg-emerald-500' : 'bg-red-500'}`}></span>
              <span className="text-[9px] text-gray-500 uppercase tracking-wider">KiCad IPC</span>
            </div>
          </div>
          {servers.map(s => (
            <div key={s.name} className="flex items-center justify-between text-xs">
              <div className="flex items-center gap-2">
                 <span className={`w-1.5 h-1.5 rounded-full ${s.status === 'running' ? 'bg-emerald-500' : 'bg-red-500'}`}></span>
                 <span className="font-mono text-gray-300">{s.name}</span>
                 {s.status === 'running' && <span className="text-[9px] bg-blue-900/50 text-blue-300 px-1.5 rounded">tools: {s.tool_count}</span>}
              </div>
              <button 
                onClick={() => toggleServer(s.name, s.status)}
                className={`text-[9px] px-2 py-0.5 rounded border ${s.status === 'running' ? 'border-red-500/50 text-red-400 hover:bg-red-500/10' : 'border-emerald-500/50 text-emerald-400 hover:bg-emerald-500/10'}`}
              >
                {s.status === 'running' ? 'STOP' : 'START'}
              </button>
            </div>
          ))}
        </div>
      </div>

      {/* Chat Area */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4 scrollbar-thin scrollbar-thumb-gray-700">
        {messages.map(msg => (
          <div key={msg.id} className={`flex flex-col ${msg.role === 'user' ? 'items-end' : 'items-start'}`}>
            <div className={`
              max-w-[85%] rounded-2xl px-4 py-2.5 text-sm whitespace-pre-wrap
              ${msg.role === 'user' ? 'bg-blue-600/90 text-white rounded-br-none' : ''}
              ${msg.role === 'agent' ? 'bg-gray-800/90 border border-gray-700 text-gray-200 rounded-bl-none font-mono text-xs' : ''}
              ${msg.role === 'system' ? 'bg-indigo-900/40 border border-indigo-500/30 text-indigo-200 text-xs text-center self-center w-full' : ''}
            `}>
              {msg.content}
            </div>
          </div>
        ))}

        {/* Live Tool Execution Feed */}
        {toolsRunning.map(tool => (
          <div key={tool.id} className="bg-gray-800/60 border border-gray-700 rounded-lg p-3 text-xs w-[85%] self-start animate-fade-in">
            <div className="flex items-center gap-2 mb-1.5">
              {tool.status === 'running' && (
                <svg className="animate-spin h-3 w-3 text-blue-400" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path>
                </svg>
              )}
              {tool.status === 'success' && <span className="text-emerald-400">✓</span>}
              <span className="font-mono text-gray-300">Tool: {tool.tool}</span>
            </div>
            <div className="text-gray-500 font-mono text-[10px] bg-gray-900/50 p-1.5 rounded overflow-hidden text-ellipsis whitespace-nowrap">
              {JSON.stringify(tool.args)}
            </div>
          </div>
        ))}
        <div ref={messagesEndRef} />
      </div>

      {/* Input Area */}
      <div className="p-4 bg-gray-900/80 border-t border-white/10">
        <div className="relative">
          <textarea 
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                handleSend();
              }
            }}
            placeholder="Ask AI or type @board, @nets..."
            className="w-full bg-gray-800/80 border border-gray-700 focus:border-blue-500/50 focus:ring-1 focus:ring-blue-500/50 rounded-xl pl-4 pr-12 py-3 text-sm text-gray-200 placeholder-gray-500 resize-none outline-none transition-all"
            rows={2}
          />
          <button 
            onClick={handleSend}
            disabled={!input.trim()}
            className="absolute right-3 bottom-3 p-1.5 bg-blue-600 hover:bg-blue-500 disabled:bg-gray-700 disabled:text-gray-500 text-white rounded-lg transition-colors"
          >
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" className="w-4 h-4">
              <path d="M3.478 2.405a.75.75 0 00-.926.94l2.432 7.905H13.5a.75.75 0 010 1.5H4.984l-2.432 7.905a.75.75 0 00.926.94 60.519 60.519 0 0018.445-8.986.75.75 0 000-1.218A60.517 60.517 0 003.478 2.405z" />
            </svg>
          </button>
        </div>
        <div className="flex gap-2 mt-2">
          <button onClick={() => setInput(prev => prev + '@board ')} className="text-[10px] px-2 py-1 rounded border border-gray-700 text-gray-400 hover:bg-gray-800 transition-colors">@board</button>
          <button onClick={() => setInput(prev => prev + '@nets ')} className="text-[10px] px-2 py-1 rounded border border-gray-700 text-gray-400 hover:bg-gray-800 transition-colors">@nets</button>
        </div>
      </div>

    </div>
  );
};
