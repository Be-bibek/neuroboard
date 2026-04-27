import React, { useState, useEffect, useRef } from 'react';
import { SettingsModal } from './SettingsModal';
import { Send, Zap, Cpu, Activity, ShieldCheck, Info, ChevronDown, ChevronRight, Brain, RefreshCw, Terminal, BookOpen } from 'lucide-react';

// ── Types ──────────────────────────────────────────────────────────────────────

type MessageRole = 'user' | 'agent' | 'system';

interface Message {
  id: string;
  role: MessageRole;
  content: string;
  timestamp: Date;
  model?: string;
}

interface ThoughtEvent {
  id: string;
  type: 'thought';
  content: string;
  model?: string;
}

interface ScriptEvent {
  id: string;
  type: 'script';
  script_code: string;
  stdout: string;
  stderr: string;
  status: 'success' | 'failed';
  message: string;
  model?: string;
}

interface ReflectEvent {
  id: string;
  type: 'reflect';
  attempt: number;
  corrected_script: string;
  message: string;
  model?: string;
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

type ChatItem =
  | { kind: 'message'; data: Message }
  | { kind: 'thought'; data: ThoughtEvent }
  | { kind: 'script'; data: ScriptEvent }
  | { kind: 'reflect'; data: ReflectEvent }
  | { kind: 'tool'; data: ToolExecution };

// ── Sub-components ─────────────────────────────────────────────────────────────

const ModelBadge: React.FC<{ model?: string }> = ({ model }) => {
  if (!model) return null;
  const isLite = model.toLowerCase().includes('lite');
  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[9px] font-bold uppercase tracking-wider border ${
      isLite
        ? 'bg-amber-500/15 text-amber-400 border-amber-500/20'
        : 'bg-indigo-500/15 text-indigo-400 border-indigo-500/20'
    }`}>
      {isLite ? '⚡ Flash-Lite' : '🧠 Flash'}
    </span>
  );
};

const ContextChip: React.FC<{ name: string; onRemove: () => void }> = ({ name, onRemove }) => (
  <div className="flex items-center gap-1.5 px-2 py-1 bg-violet-600/20 border border-violet-500/30 rounded-lg animate-in fade-in scale-in-95 duration-200">
    <div className="w-2 h-2 rounded-full bg-violet-400 shadow-[0_0_8px_rgba(167,139,250,0.6)]" />
    <span className="text-[10px] font-bold text-violet-300 font-mono">@{name}</span>
    <button onClick={onRemove} className="text-violet-400/60 hover:text-white transition-colors">
      <Send size={8} className="rotate-45" />
    </button>
  </div>
);

const ThoughtBubble: React.FC<{ event: ThoughtEvent }> = ({ event }) => {
  const [expanded, setExpanded] = useState(false);
  const preview = event.content.slice(0, 120) + (event.content.length > 120 ? '...' : '');

  return (
    <div className="flex items-start gap-2 animate-in slide-in-from-top-2 duration-300">
      <div className="mt-1 flex-shrink-0 w-6 h-6 rounded-full bg-violet-500/20 flex items-center justify-center border border-violet-500/30">
        <Brain size={11} className="text-violet-400" />
      </div>
      <div className="flex-1 bg-violet-950/40 border border-violet-500/20 rounded-2xl rounded-tl-none px-4 py-3">
        <button
          onClick={() => setExpanded(e => !e)}
          className="w-full flex items-center justify-between gap-2 text-left"
        >
          <span className="text-[10px] font-bold text-violet-400/80 uppercase tracking-widest">
            Engineering Thought
          </span>
          <div className="flex items-center gap-2">
            <ModelBadge model={event.model} />
            {expanded
              ? <ChevronDown size={12} className="text-violet-400/60" />
              : <ChevronRight size={12} className="text-violet-400/60" />
            }
          </div>
        </button>
        <p className="mt-2 text-[11px] text-violet-200/70 leading-relaxed font-mono italic">
          {expanded ? event.content : preview}
        </p>
      </div>
    </div>
  );
};

const ScriptCard: React.FC<{ event: ScriptEvent }> = ({ event }) => {
  const [expanded, setExpanded] = useState(true);
  const success = event.status === 'success';

  return (
    <div className="flex items-start gap-2 animate-in slide-in-from-bottom-2 duration-300">
      <div className={`mt-1 flex-shrink-0 w-6 h-6 rounded-full flex items-center justify-center border ${
        success
          ? 'bg-emerald-500/20 border-emerald-500/30'
          : 'bg-rose-500/20 border-rose-500/30'
      }`}>
        <Terminal size={11} className={success ? 'text-emerald-400' : 'text-rose-400'} />
      </div>
      <div className={`flex-1 border rounded-2xl rounded-tl-none overflow-hidden ${
        success
          ? 'bg-emerald-950/30 border-emerald-500/20'
          : 'bg-rose-950/30 border-rose-500/20'
      }`}>
        <button
          onClick={() => setExpanded(e => !e)}
          className="w-full flex items-center justify-between gap-2 px-4 py-3 text-left"
        >
          <span className={`text-[10px] font-bold uppercase tracking-widest ${success ? 'text-emerald-400/80' : 'text-rose-400/80'}`}>
            {success ? '✓ Script Executed' : '✗ Script Failed'}
          </span>
          <div className="flex items-center gap-2">
            <ModelBadge model={event.model} />
            {expanded
              ? <ChevronDown size={12} className="text-white/30" />
              : <ChevronRight size={12} className="text-white/30" />
            }
          </div>
        </button>

        {expanded && (
          <>
            <div className="px-4 pb-2">
              <div className="text-[9px] text-white/30 uppercase tracking-widest mb-1">Python Script</div>
              <pre className="bg-black/40 rounded-xl p-3 text-[10px] text-green-300/80 font-mono overflow-x-auto max-h-48 border border-white/5 leading-relaxed">
                {event.script_code}
              </pre>
            </div>

            {event.stdout && (
              <div className="px-4 pb-2">
                <div className="text-[9px] text-emerald-400/50 uppercase tracking-widest mb-1">stdout</div>
                <pre className="bg-black/30 rounded-xl p-2 text-[10px] text-emerald-300/70 font-mono overflow-x-auto border border-emerald-500/10">
                  {event.stdout}
                </pre>
              </div>
            )}

            {event.stderr && (
              <div className="px-4 pb-3">
                <div className="text-[9px] text-rose-400/50 uppercase tracking-widest mb-1">stderr</div>
                <pre className="bg-black/30 rounded-xl p-2 text-[10px] text-rose-300/70 font-mono overflow-x-auto border border-rose-500/10">
                  {event.stderr}
                </pre>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
};

const ReflectCard: React.FC<{ event: ReflectEvent }> = ({ event }) => {
  const [expanded, setExpanded] = useState(true);

  return (
    <div className="flex items-start gap-2 animate-in slide-in-from-bottom-2 duration-300">
      <div className="mt-1 flex-shrink-0 w-6 h-6 rounded-full bg-amber-500/20 flex items-center justify-center border border-amber-500/30">
        <RefreshCw size={11} className="text-amber-400 animate-spin [animation-duration:2s]" />
      </div>
      <div className="flex-1 bg-amber-950/30 border border-amber-500/20 rounded-2xl rounded-tl-none overflow-hidden">
        <button
          onClick={() => setExpanded(e => !e)}
          className="w-full flex items-center justify-between gap-2 px-4 py-3 text-left"
        >
          <span className="text-[10px] font-bold text-amber-400/80 uppercase tracking-widest">
            🔄 Self-Correcting — Attempt {event.attempt}/3
          </span>
          <div className="flex items-center gap-2">
            <ModelBadge model={event.model} />
            {expanded
              ? <ChevronDown size={12} className="text-white/30" />
              : <ChevronRight size={12} className="text-white/30" />
            }
          </div>
        </button>

        {expanded && event.corrected_script && (
          <div className="px-4 pb-3">
            <div className="text-[9px] text-amber-400/50 uppercase tracking-widest mb-1">Corrected Script</div>
            <pre className="bg-black/40 rounded-xl p-3 text-[10px] text-amber-200/70 font-mono overflow-x-auto max-h-40 border border-amber-500/10 leading-relaxed">
              {event.corrected_script}
            </pre>
          </div>
        )}
      </div>
    </div>
  );
};

const MemoryBadge: React.FC = () => (
  <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-teal-500/10 border border-teal-500/20 text-[9px] font-bold text-teal-400 uppercase tracking-widest animate-in fade-in duration-500">
    <BookOpen size={9} />
    Pattern saved to memory
  </div>
);

// ── Main Sidebar ───────────────────────────────────────────────────────────────

export const AntigravitySidebar: React.FC = () => {
  const [items, setItems] = useState<ChatItem[]>([]);
  const [input, setInput] = useState('');
  const [selectedContexts, setSelectedContexts] = useState<string[]>([]);
  const [showContextSelector, setShowContextSelector] = useState(false);
  const [servers, setServers] = useState<MCPServer[]>([]);
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);
  const [isStreaming, setIsStreaming] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);
  const esRef = useRef<EventSource | null>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [items]);

  const fetchServers = async () => {
    try {
      const res = await fetch('http://localhost:8000/api/v1/mcp/servers');
      const data = await res.json();
      if (data.status === 'success') setServers(data.servers);
    } catch {}
  };

  useEffect(() => {
    fetchServers();
    setItems([{
      kind: 'message',
      data: { id: 'welcome', role: 'system', content: 'NeuroBoard AI v6.0 · Hardware Coder active.', timestamp: new Date() }
    }]);

    const handleProjectChange = () => {
      setItems([{
        kind: 'message',
        data: { id: 'switch', role: 'system', content: 'Project switched · Memory context refreshed.', timestamp: new Date() }
      }]);
    };

    window.addEventListener('projectChanged', handleProjectChange);
    return () => window.removeEventListener('projectChanged', handleProjectChange);
  }, []);

  const toggleServer = async (server: string, status: string) => {
    const action = status === 'running' ? 'stop' : 'start';
    await fetch(`http://localhost:8000/api/v1/mcp/servers/${server}/${action}`, { method: 'POST' });
    fetchServers();
  };

  const addItem = (item: ChatItem) => setItems(prev => [...prev, item]);

  const handleSend = async () => {
    if (!input.trim() || isStreaming) return;

    const intent = input.trim();
    setInput('');
    setIsStreaming(true);

    // Add user message
    const userId = `u_${Date.now()}`;
    addItem({ kind: 'message', data: { id: userId, role: 'user', content: intent, timestamp: new Date() } });

    // Add agent loading message
    const agentId = `a_${Date.now()}`;
    addItem({ kind: 'message', data: { id: agentId, role: 'agent', content: 'Booting Hardware Coder...', timestamp: new Date(), model: undefined } });

    const updateAgentMsg = (patch: Partial<Message>) => {
      setItems(prev => prev.map(it =>
        it.kind === 'message' && it.data.id === agentId
          ? { kind: 'message', data: { ...it.data, ...patch } }
          : it
      ));
    };

    if (esRef.current) esRef.current.close();
    const contextQuery = selectedContexts.length > 0 ? `&contexts=${encodeURIComponent(selectedContexts.join(','))}` : '';
    const es = new EventSource(`http://localhost:8000/api/v1/agent/run?intent=${encodeURIComponent(intent)}${contextQuery}`);
    esRef.current = es;

    setSelectedContexts([]);

    es.onmessage = (event) => {
      const data = JSON.parse(event.data);
      const node = data.node;

      if (node === 'thought') {
        addItem({
          kind: 'thought',
          data: { id: `t_${Date.now()}`, type: 'thought', content: data.content, model: data.model }
        });
        return;
      }

      if (node === 'script') {
        addItem({
          kind: 'script',
          data: {
            id: `s_${Date.now()}`, type: 'script',
            script_code: data.script_code, stdout: data.stdout,
            stderr: data.stderr, status: data.status,
            message: data.message, model: data.model
          }
        });
        // If success, show memory badge
        if (data.status === 'success') {
          setTimeout(() => {
            addItem({ kind: 'message', data: { id: `mem_${Date.now()}`, role: 'system', content: '📖 Pattern saved to memory', timestamp: new Date() } });
          }, 400);
        }
        return;
      }

      if (node === 'reflect') {
        addItem({
          kind: 'reflect',
          data: {
            id: `r_${Date.now()}`, type: 'reflect',
            attempt: data.attempt, corrected_script: data.corrected_script,
            message: data.message, model: data.model
          }
        });
        return;
      }

      if (node === 'status') {
        updateAgentMsg({ content: (prev => {
          const current = prev || '';
          return current === 'Booting Hardware Coder...'
            ? data.message
            : current + '\n' + data.message;
        })(undefined), model: data.model });
        return;
      }

      if (node === 'planning' && data.plan) {
        const planText = data.plan.map((s: any, i: number) =>
          `  ${i + 1}. ${s.action || s.tool}`
        ).join('\n');
        updateAgentMsg({
          content: `📋 Plan: ${data.plan.length} steps\n${planText}`,
          model: data.model
        });
        return;
      }

      if (node === 'tool_selection') {
        addItem({
          kind: 'tool',
          data: { id: `tl_${Date.now()}`, tool: data.tool, status: 'running', args: { action: data.action } }
        });
        return;
      }

      if (node === 'execution') {
        setItems(prev => {
          const idx = [...prev].reverse().findIndex(it => it.kind === 'tool' && it.data.status === 'running');
          if (idx === -1) return prev;
          const realIdx = prev.length - 1 - idx;
          const updated = [...prev];
          const tool = updated[realIdx].data as ToolExecution;
          updated[realIdx] = {
            kind: 'tool',
            data: { ...tool, tool: data.tool, status: data.status === 'success' ? 'success' : 'error', result: data.result }
          };
          return updated;
        });
        return;
      }

      if (node === 'END') {
        updateAgentMsg({ content: `✅ ${data.message}` });
        setIsStreaming(false);
        es.close();
        return;
      }

      if (node === 'ERROR') {
        updateAgentMsg({ content: `❌ ${data.error}` });
        setIsStreaming(false);
        es.close();
      }
    };

    es.onerror = () => {
      setIsStreaming(false);
      es.close();
    };
  };

  return (
    <div className="flex flex-col h-full w-full bg-transparent text-white overflow-hidden font-sans">

      {/* Header */}
      <div className="px-6 py-5 border-b border-white/5 bg-white/5 backdrop-blur-md">
        <div className="flex justify-between items-center mb-4">
          <div className="flex items-center gap-2">
            <div className="relative">
              <Activity size={16} className="text-indigo-400" />
              <span className="absolute -top-1 -right-1 w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
            </div>
            <h2 className="text-sm font-bold tracking-tight text-white/90 uppercase">Hardware Coder</h2>
            {isStreaming && (
              <span className="px-2 py-0.5 rounded-full bg-violet-500/20 border border-violet-500/30 text-[9px] font-bold text-violet-400 uppercase tracking-widest animate-pulse">
                Thinking
              </span>
            )}
          </div>
          <button onClick={() => setIsSettingsOpen(true)} className="p-2 hover:bg-white/10 rounded-xl transition-colors">
            <Cpu size={16} className="text-white/60" />
          </button>
        </div>

        {/* MCP Hub */}
        <div className="bg-black/20 border border-white/5 rounded-2xl p-3 shadow-inner shadow-black/40">
          <div className="flex items-center gap-2 mb-3 px-1">
            <ShieldCheck size={12} className="text-indigo-400" />
            <span className="text-[10px] font-bold text-white/40 uppercase tracking-[0.2em]">Runtime Hub</span>
          </div>
          <div className="space-y-2">
            {servers.map(s => (
              <div key={s.name} className="flex items-center justify-between text-[11px] group">
                <div className="flex items-center gap-2">
                  <div className={`w-1.5 h-1.5 rounded-full transition-all ${
                    s.status === 'running'
                      ? 'bg-indigo-400 shadow-[0_0_8px_theme("colors.indigo.400")]'
                      : 'bg-white/20'
                  }`} />
                  <span className="font-medium text-white/70 group-hover:text-white transition-colors">{s.name}</span>
                </div>
                <button
                  onClick={() => toggleServer(s.name, s.status)}
                  className={`px-3 py-1 rounded-lg border text-[10px] font-bold transition-all ${
                    s.status === 'running'
                      ? 'border-rose-500/20 text-rose-400 hover:bg-rose-500/10'
                      : 'border-white/10 text-white/40 hover:bg-white/5 hover:text-white/80'
                  }`}
                >
                  {s.status === 'running' ? 'OFF' : 'ON'}
                </button>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Feed */}
      <div className="flex-1 overflow-y-auto px-4 py-4 space-y-4 scrollbar-none">
        {items.map((item, i) => {
          if (item.kind === 'message') {
            const msg = item.data;
            return (
              <div key={msg.id} className={`flex flex-col ${msg.role === 'user' ? 'items-end' : 'items-start'}`}>
                <div className={`
                  max-w-[92%] px-4 py-3 text-sm leading-relaxed shadow-xl
                  ${msg.role === 'user' ? 'bg-indigo-600/80 text-white rounded-[20px] rounded-tr-none border border-white/10' : ''}
                  ${msg.role === 'agent' ? 'bg-white/5 backdrop-blur-xl border border-white/10 text-white/85 rounded-[20px] rounded-tl-none font-medium' : ''}
                  ${msg.role === 'system' ? 'text-[10px] text-indigo-400/70 font-bold tracking-widest uppercase self-center bg-transparent border-none shadow-none px-0' : ''}
                `}>
                  <div className="whitespace-pre-wrap">{msg.content}</div>
                  {msg.role === 'agent' && msg.model && (
                    <div className="mt-3">
                      <ModelBadge model={msg.model} />
                    </div>
                  )}
                  {msg.role === 'agent' && msg.content.includes('Booting') && isStreaming && (
                    <div className="flex gap-1 mt-3 opacity-50">
                      <div className="w-1.5 h-1.5 bg-white rounded-full animate-bounce [animation-delay:-0.3s]" />
                      <div className="w-1.5 h-1.5 bg-white rounded-full animate-bounce [animation-delay:-0.15s]" />
                      <div className="w-1.5 h-1.5 bg-white rounded-full animate-bounce" />
                    </div>
                  )}
                </div>
              </div>
            );
          }

          if (item.kind === 'thought') {
            return <ThoughtBubble key={item.data.id} event={item.data} />;
          }

          if (item.kind === 'script') {
            return <ScriptCard key={item.data.id} event={item.data} />;
          }

          if (item.kind === 'reflect') {
            return <ReflectCard key={item.data.id} event={item.data} />;
          }

          if (item.kind === 'tool') {
            const tool = item.data;
            return (
              <div key={tool.id} className="flex items-start gap-2 animate-in slide-in-from-right-2 duration-200">
                <div className={`mt-1 flex-shrink-0 w-6 h-6 rounded-full flex items-center justify-center border ${
                  tool.status === 'running'
                    ? 'bg-indigo-500/20 border-indigo-500/30'
                    : tool.status === 'success'
                      ? 'bg-emerald-500/20 border-emerald-500/30'
                      : 'bg-rose-500/20 border-rose-500/30'
                }`}>
                  {tool.status === 'running'
                    ? <div className="w-3 h-3 rounded-full border-2 border-indigo-400/40 border-t-indigo-400 animate-spin" />
                    : tool.status === 'success'
                      ? <ShieldCheck size={10} className="text-emerald-400" />
                      : <Info size={10} className="text-rose-400" />
                  }
                </div>
                <div className="flex-1 bg-white/3 border border-white/8 rounded-2xl rounded-tl-none px-4 py-3">
                  <div className="flex items-center justify-between">
                    <span className="text-[11px] font-bold text-white/80 font-mono">{tool.tool}</span>
                    <span className={`text-[9px] font-bold px-2 py-0.5 rounded-md uppercase tracking-wider ${
                      tool.status === 'running' ? 'bg-indigo-500/20 text-indigo-400'
                      : tool.status === 'success' ? 'bg-emerald-500/20 text-emerald-400'
                      : 'bg-rose-500/20 text-rose-400'
                    }`}>{tool.status}</span>
                  </div>
                  {tool.args.action && (
                    <p className="mt-1 text-[10px] text-white/40 italic">{tool.args.action}</p>
                  )}
                </div>
              </div>
            );
          }

          return null;
        })}
        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <div className="p-5 bg-white/5 backdrop-blur-2xl border-t border-white/5 shadow-[0_-10px_40px_rgba(0,0,0,0.4)]">
        
        {/* Context Chips */}
        {selectedContexts.length > 0 && (
          <div className="flex flex-wrap gap-2 mb-3">
            {selectedContexts.map(ctx => (
              <ContextChip 
                key={ctx} 
                name={ctx} 
                onRemove={() => setSelectedContexts(prev => prev.filter(c => c !== ctx))} 
              />
            ))}
          </div>
        )}

        <div className="relative flex items-end gap-3">
          <div className="flex-1 relative">
            <textarea
              value={input}
              onChange={e => {
                const val = e.target.value;
                setInput(val);
                if (val.endsWith('@')) {
                  setShowContextSelector(true);
                } else if (showContextSelector && !val.includes('@')) {
                  setShowContextSelector(false);
                }
              }}
              onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSend(); } }}
              placeholder="Describe your PCB engineering goal..."
              className="w-full bg-white/5 border border-white/10 focus:border-violet-500/50 focus:ring-1 focus:ring-violet-500/20 rounded-2xl pl-4 pr-12 py-4 text-sm text-white placeholder-white/20 resize-none outline-none transition-all duration-200 min-h-[56px] max-h-[160px]"
              rows={1}
            />

            {/* Context Selector Menu (Continue-style) */}
            {showContextSelector && (
              <div className="absolute left-0 bottom-full mb-2 w-48 bg-[#0a0a0c] border border-white/10 rounded-xl shadow-2xl overflow-hidden animate-in slide-in-from-bottom-2 duration-200 z-50">
                <div className="px-3 py-2 text-[9px] font-bold text-white/30 uppercase tracking-widest border-b border-white/5">Context Providers</div>
                <button 
                  onClick={() => { setSelectedContexts(p => Array.from(new Set([...p, 'board']))); setShowContextSelector(false); setInput(i => i.replace(/@$/, '')); }}
                  className="w-full flex items-center gap-3 px-3 py-2.5 hover:bg-violet-600/20 text-white/70 hover:text-white transition-all text-left"
                >
                  <Cpu size={14} className="text-violet-400" />
                  <div className="flex flex-col">
                    <span className="text-xs font-bold">@board</span>
                    <span className="text-[9px] opacity-40">Live KiCad State</span>
                  </div>
                </button>
                <button 
                  onClick={() => { setSelectedContexts(p => Array.from(new Set([...p, 'mem']))); setShowContextSelector(false); setInput(i => i.replace(/@$/, '')); }}
                  className="w-full flex items-center gap-3 px-3 py-2.5 hover:bg-violet-600/20 text-white/70 hover:text-white transition-all text-left"
                >
                  <BookOpen size={14} className="text-teal-400" />
                  <div className="flex flex-col">
                    <span className="text-xs font-bold">@mem</span>
                    <span className="text-[9px] opacity-40">Project Memory</span>
                  </div>
                </button>
              </div>
            )}

            <button
              onClick={handleSend}
              disabled={!input.trim() || isStreaming}
              className="absolute right-3 bottom-3 p-2 bg-violet-600 hover:bg-violet-500 disabled:opacity-30 text-white rounded-xl transition-all shadow-xl shadow-violet-600/20 hover:scale-110 active:scale-95"
            >
              <Send size={16} fill="currentColor" />
            </button>
          </div>
        </div>
        <div className="mt-2 flex items-center justify-between px-1">
          <div className="flex items-center gap-2">
            <div className="w-1.5 h-1.5 rounded-full bg-teal-400 animate-pulse" />
            <span className="text-[9px] text-white/30 font-medium">Context active · {selectedContexts.length > 0 ? selectedContexts.join(', ') : 'None'}</span>
          </div>
          <button 
            onClick={() => setShowContextSelector(!showContextSelector)}
            className="text-[9px] font-bold text-violet-400/60 hover:text-violet-400 uppercase tracking-widest flex items-center gap-1"
          >
            <Zap size={10} />
            Add Context
          </button>
        </div>
      </div>

      <SettingsModal isOpen={isSettingsOpen} onClose={() => setIsSettingsOpen(false)} />
    </div>
  );
};
