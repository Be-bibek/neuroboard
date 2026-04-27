import React, { useState, useEffect, useRef, useCallback } from 'react';
import { SettingsModal } from './SettingsModal';
import {
  Send, Settings, Activity, Cpu, BookOpen,
  Zap, ChevronDown, ChevronRight, GripVertical,
} from 'lucide-react';
import {
  ChatItem, MCPServer, Message, ThoughtEvent, ScriptEvent, ReflectEvent, ToolExecution,
  ModelBadge, ContextChip, ThoughtBubble, ScriptCard, ReflectCard, ActionLogItem,
} from './sidebar/SidebarComponents';

const API = 'http://localhost:8000';

// ── Resizable hook ────────────────────────────────────────────────────────────

function useResizable(initial: number, min = 280, max = 680) {
  const [width, setWidth] = useState(initial);
  const dragging = useRef(false);

  const onMouseDown = useCallback(() => { dragging.current = true; }, []);

  useEffect(() => {
    const onMove = (e: MouseEvent) => {
      if (!dragging.current) return;
      const next = window.innerWidth - e.clientX;
      setWidth(Math.max(min, Math.min(max, next)));
    };
    const onUp = () => { dragging.current = false; };
    window.addEventListener('mousemove', onMove);
    window.addEventListener('mouseup', onUp);
    return () => { window.removeEventListener('mousemove', onMove); window.removeEventListener('mouseup', onUp); };
  }, [min, max]);

  return { width: dragging.current ? width : (initial === 0 ? 0 : width), onMouseDown, setWidth };
}

// ── MCP Server Status Row ─────────────────────────────────────────────────────

const McpRow: React.FC<{ server: MCPServer; onToggle: () => void }> = ({ server, onToggle }) => {
  const live = server.status === 'running';
  return (
    <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg hover:bg-white/5 transition-all group">
      {/* Green Dot */}
      <div className={`w-2 h-2 rounded-full flex-shrink-0 transition-all ${
        live
          ? 'bg-emerald-400 shadow-[0_0_8px_rgba(52,211,153,0.7)]'
          : 'bg-white/15'
      }`} />
      <span className="text-[10px] font-mono text-white/60 flex-1 truncate">{server.name}</span>
      {live && (
        <span className="text-[9px] text-emerald-400/60 font-bold">{server.tool_count} tools</span>
      )}
      <button
        onClick={onToggle}
        className={`opacity-0 group-hover:opacity-100 text-[9px] font-bold px-2 py-0.5 rounded-md border transition-all ${
          live
            ? 'border-rose-500/20 text-rose-400 hover:bg-rose-500/10'
            : 'border-white/10 text-white/40 hover:bg-white/5'
        }`}
      >
        {live ? 'OFF' : 'ON'}
      </button>
    </div>
  );
};

// ── Main Sidebar ──────────────────────────────────────────────────────────────

export const AntigravitySidebar: React.FC = () => {
  const [items, setItems] = useState<ChatItem[]>([]);
  const [input, setInput] = useState('');
  const [selectedContexts, setSelectedContexts] = useState<string[]>([]);
  const [showContextMenu, setShowContextMenu] = useState(false);
  const [servers, setServers] = useState<MCPServer[]>([]);
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);
  const [isStreaming, setIsStreaming] = useState(false);
  const [showServers, setShowServers] = useState(false);
  const [isCollapsed, setIsCollapsed] = useState(false);
  const esRef = useRef<EventSource | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);
  const { width, onMouseDown } = useResizable(360);

  // Scroll to bottom on new items
  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: 'smooth' }); }, [items]);

  // Fetch MCP servers
  useEffect(() => {
    fetch(`${API}/api/v1/mcp/servers`)
      .then(r => r.json())
      .then(d => setServers(d.servers || []))
      .catch(() => {});
  }, []);

  const addItem = useCallback((item: ChatItem) => {
    setItems(prev => [...prev, item]);
  }, []);

  const uid = () => `${Date.now()}_${Math.random().toString(36).slice(2, 6)}`;

  const toggleServer = async (name: string, status: string) => {
    const endpoint = status === 'running' ? 'stop' : 'start';
    await fetch(`${API}/api/v1/mcp/${endpoint}/${name}`, { method: 'POST' }).catch(() => {});
    setServers(prev => prev.map(s => s.name === name
      ? { ...s, status: status === 'running' ? 'stopped' : 'running' }
      : s));
  };

  const handleSend = () => {
    const intent = input.trim();
    if (!intent || isStreaming) return;

    // Add user message with @context chips rendered inline
    const contextLabel = selectedContexts.length
      ? ` [${selectedContexts.map(c => `@${c}`).join(' ')}]`
      : '';
    addItem({ kind: 'message', data: { id: uid(), role: 'user', content: intent + contextLabel, timestamp: new Date() } });
    setInput('');
    setIsStreaming(true);

    const agentId = uid();
    addItem({ kind: 'message', data: { id: agentId, role: 'agent', content: '⚡ Booting Hardware Coder…', timestamp: new Date() } });

    const updateAgent = (patch: Partial<Message>) => {
      setItems(prev => prev.map(it =>
        it.kind === 'message' && it.data.id === agentId
          ? { kind: 'message', data: { ...it.data, ...patch } }
          : it
      ));
    };

    if (esRef.current) esRef.current.close();

    const ctxQuery = selectedContexts.length
      ? `&contexts=${encodeURIComponent(selectedContexts.join(','))}`
      : '';
    const es = new EventSource(`${API}/api/v1/agent/run?intent=${encodeURIComponent(intent)}${ctxQuery}`);
    esRef.current = es;
    setSelectedContexts([]);

    es.onmessage = (e) => {
      const data = JSON.parse(e.data);
      const node = data.node;

      // Task 2: Broadcast AI Presence to the PCB Canvas
      if (data.presence) {
        window.dispatchEvent(new CustomEvent('ai_presence_update', { detail: data.presence }));
      }

      // ── OpenHands-style Action Log ────────────────────────────────────────
      if (node === 'status') {
        updateAgent({ content: data.message, model: data.model });
        return;
      }

      // ── PILLAR 2: Live Reasoning Stream ───────────────────────────────────
      if (node === 'thought') {
        addItem({
          kind: 'thought',
          data: { id: uid(), type: 'thought', content: data.content, model: data.model, isStreaming: false },
        });
        return;
      }

      if (node === 'planning') {
        const planText = (data.plan || []).map((s: any, i: number) =>
          `  ${i + 1}. ${s.action || s.tool}`
        ).join('\n');
        updateAgent({ content: `📋 Plan ready — ${(data.plan || []).length} steps\n${planText}`, model: data.model });
        return;
      }

      // ── Tool execution (Roo-Code style green dots) ─────────────────────
      if (node === 'tool_selection') {
        addItem({ kind: 'tool', data: { id: uid(), tool: data.tool, status: 'running', args: { action: data.action } } });
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
            data: { ...tool, tool: data.tool, status: data.status === 'success' ? 'success' : 'error', result: data.result },
          };
          return updated;
        });
        return;
      }

      // ── Script card (Step 2 — ScriptCard with raw IPC JSON) ──────────────
      if (node === 'script') {
        addItem({
          kind: 'script',
          data: {
            id: uid(), type: 'script',
            script_code: data.script_code || '', stdout: data.stdout || '',
            stderr: data.stderr || '', status: data.status, message: data.message || '',
            model: data.model,
            raw_args: { script_code: data.script_code, description: data.message },
          },
        });
        if (data.status === 'success') {
          setTimeout(() => addItem({
            kind: 'message',
            data: { id: uid(), role: 'system', content: '📖 Pattern saved to project memory', timestamp: new Date() },
          }), 400);
        }
        return;
      }

      // ── Reflect card ─────────────────────────────────────────────────────
      if (node === 'reflect') {
        addItem({
          kind: 'reflect',
          data: { id: uid(), type: 'reflect', attempt: data.attempt, corrected_script: data.corrected_script, message: data.message, model: data.model },
        });
        return;
      }

      // ── Completion ────────────────────────────────────────────────────────
      if (node === 'END') {
        updateAgent({ content: `✅ ${data.message || 'Mission complete.'}`, model: undefined });
        setIsStreaming(false);
        es.close();
        return;
      }

      if (node === 'ERROR') {
        updateAgent({ content: `❌ ${data.error}` });
        setIsStreaming(false);
        es.close();
      }
    };

    es.onerror = () => {
      updateAgent({ content: '❌ Connection lost. Check backend.' });
      setIsStreaming(false);
      es.close();
    };
  };

  // Close context menu on outside click
  useEffect(() => {
    const handler = () => setShowContextMenu(false);
    if (showContextMenu) document.addEventListener('click', handler);
    return () => document.removeEventListener('click', handler);
  }, [showContextMenu]);

  return (
    <div
      className={`relative flex h-full transition-all duration-500 ease-in-out ${isCollapsed ? 'w-[64px]!' : ''}`}
      style={{ width: isCollapsed ? 64 : width }}
    >
      {/* Resize grip */}
      {!isCollapsed && (
        <div
          onMouseDown={onMouseDown}
          className="absolute left-0 top-0 h-full w-1.5 cursor-col-resize flex items-center justify-center group z-50"
        >
          <GripVertical size={12} className="text-white/10 group-hover:text-white/40 transition-colors" />
        </div>
      )}

      {/* Focus Mode / Collapsed Sidebar */}
      {isCollapsed && (
        <div className="flex-1 flex flex-col items-center py-6 bg-[#09090c]/95 backdrop-blur-2xl border-l border-white/5 gap-6 shadow-2xl">
          <button 
            onClick={() => setIsCollapsed(false)}
            className="w-10 h-10 rounded-xl bg-violet-600/20 border border-violet-500/30 flex items-center justify-center text-violet-400 hover:bg-violet-600/40 transition-all"
          >
            <ChevronLeft size={20} className="rotate-180" />
          </button>
          
          <div className="flex flex-col gap-4 items-center">
             <div className={`w-3 h-3 rounded-full border-2 ${isStreaming ? 'border-violet-500 animate-spin border-t-transparent' : 'border-white/10'}`} />
             <Activity size={18} className={isStreaming ? "text-violet-400 animate-pulse" : "text-white/20"} />
          </div>
          
          <div className="mt-auto pb-4">
            <button onClick={() => setIsSettingsOpen(true)} className="p-2 text-white/20 hover:text-white/60">
              <Settings size={18} />
            </button>
          </div>
        </div>
      )}

      {/* Main panel */}
      {!isCollapsed && (
        <div className="flex-1 flex flex-col bg-[#09090c]/95 backdrop-blur-2xl border-l border-white/5 overflow-hidden ml-1.5 shadow-2xl">

          {/* Header */}
          <div className="flex items-center justify-between px-5 py-4 border-b border-white/5 bg-white/[0.02]">
            <div className="flex items-center gap-2.5">
              <div className="w-7 h-7 rounded-xl bg-gradient-to-br from-violet-600/80 to-indigo-700/80 flex items-center justify-center shadow-lg shadow-violet-600/20">
                <Zap size={13} className="text-white" fill="currentColor" />
              </div>
              <div>
                <h2 className="text-[13px] font-bold text-white/90 leading-tight">Hardware Coder</h2>
                <p className="text-[9px] text-white/30 font-medium tracking-wider">Gemini 3 Flash · IPC Live</p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <button 
                onClick={() => setIsCollapsed(true)}
                className="p-1.5 rounded-lg hover:bg-white/8 transition-colors text-white/30 hover:text-white/70"
                title="Focus Mode"
              >
                <ChevronRight size={14} />
              </button>
              <button onClick={() => setIsSettingsOpen(true)} className="p-1.5 rounded-lg hover:bg-white/8 transition-colors text-white/30 hover:text-white/70">
                <Settings size={14} />
              </button>
            </div>
          </div>

        {/* MCP Servers (Roo-Code Green Dots) */}
        <div className="border-b border-white/5">
          <button
            onClick={() => setShowServers(s => !s)}
            className="w-full flex items-center justify-between px-5 py-2.5 hover:bg-white/3 transition-colors"
          >
            <div className="flex items-center gap-2">
              <Activity size={10} className="text-white/30" />
              <span className="text-[9px] font-bold text-white/30 uppercase tracking-widest">PCB Servers</span>
              <div className="flex gap-1">
                {servers.filter(s => s.status === 'running').map(s => (
                  <span key={s.name} className="w-1.5 h-1.5 rounded-full bg-emerald-400 shadow-[0_0_6px_rgba(52,211,153,0.6)]" />
                ))}
              </div>
            </div>
            {showServers
              ? <ChevronDown size={11} className="text-white/25" />
              : <ChevronRight size={11} className="text-white/25" />
            }
          </button>
          {showServers && (
            <div className="px-3 pb-2 space-y-0.5 animate-in slide-in-from-top-1 duration-150">
              {servers.length === 0 && (
                <p className="text-[10px] text-white/20 px-3 py-2">No servers detected</p>
              )}
              {servers.map(s => (
                <McpRow key={s.name} server={s} onToggle={() => toggleServer(s.name, s.status)} />
              ))}
            </div>
          )}
        </div>

        {/* Chat Feed */}
        <div className="flex-1 overflow-y-auto px-4 py-4 space-y-4 scrollbar-none">
          {items.length === 0 && (
            <div className="flex flex-col items-center justify-center h-full gap-3 opacity-40">
              <Zap size={24} className="text-violet-400" />
              <p className="text-[11px] text-white/40 text-center leading-relaxed">
                Type a PCB engineering goal.<br/>
                Use <span className="font-mono text-violet-400">@</span> to inject board context.
              </p>
            </div>
          )}

          {items.map((item) => {
            if (item.kind === 'message') {
              const msg = item.data;
              return (
                <div key={msg.id} className={`flex flex-col ${msg.role === 'user' ? 'items-end' : 'items-start'}`}>
                  <div className={`
                    max-w-[92%] px-4 py-3 text-sm leading-relaxed shadow-xl
                    ${msg.role === 'user' ? 'bg-indigo-600/80 text-white rounded-[20px] rounded-tr-none border border-white/10' : ''}
                    ${msg.role === 'agent' ? 'backdrop-blur-md bg-white/[0.04] border border-white/10 text-white/80 rounded-[20px] rounded-tl-none font-medium' : ''}
                    ${msg.role === 'system' ? 'text-[10px] text-indigo-400/60 font-bold tracking-widest uppercase self-center bg-transparent border-none shadow-none px-0 py-1' : ''}
                  `}>
                    <div className="whitespace-pre-wrap text-sm">{msg.content}</div>
                    {msg.role === 'agent' && msg.model && (
                      <div className="mt-2.5">
                        <ModelBadge model={msg.model} active={isStreaming && msg.content.includes('Booting')} />
                      </div>
                    )}
                    {msg.role === 'agent' && isStreaming && msg.content.includes('Booting') && (
                      <div className="flex gap-1 mt-3 opacity-50">
                        {[0, 1, 2].map(i => (
                          <div key={i} className="w-1.5 h-1.5 bg-white rounded-full animate-bounce"
                            style={{ animationDelay: `${i * 0.15}s` }} />
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              );
            }

            if (item.kind === 'thought') return <ThoughtBubble key={item.data.id} event={item.data} />;
            if (item.kind === 'script') return <ScriptCard key={item.data.id} event={item.data} />;
            if (item.kind === 'reflect') return <ReflectCard key={item.data.id} event={item.data} />;
            if (item.kind === 'tool') return <ActionLogItem key={item.data.id} tool={item.data} />;
            return null;
          })}

          <div ref={bottomRef} />
        </div>

        {/* Input */}
        <div className="p-4 bg-white/[0.02] backdrop-blur-2xl border-t border-white/5 shadow-[0_-8px_32px_rgba(0,0,0,0.4)]">

          {/* Context Chips */}
          {selectedContexts.length > 0 && (
            <div className="flex flex-wrap gap-1.5 mb-2.5">
              {selectedContexts.map(ctx => (
                <ContextChip key={ctx} name={ctx} onRemove={() => setSelectedContexts(p => p.filter(c => c !== ctx))} />
              ))}
            </div>
          )}

          <div className="relative flex items-end gap-2">
            <div className="flex-1 relative">
              <textarea
                value={input}
                onChange={e => {
                  const v = e.target.value;
                  setInput(v);
                  if (v.endsWith('@')) setShowContextMenu(true);
                  else if (!v.includes('@')) setShowContextMenu(false);
                }}
                onKeyDown={e => {
                  if (e.key === 'Escape') setShowContextMenu(false);
                  if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSend(); }
                }}
                placeholder="Describe your PCB engineering goal…"
                className="w-full bg-white/5 border border-white/10 focus:border-violet-500/50 focus:ring-1 focus:ring-violet-500/20 rounded-2xl pl-4 pr-11 py-3.5 text-sm text-white placeholder-white/20 resize-none outline-none transition-all duration-200 min-h-[52px] max-h-[140px] font-sans"
                rows={1}
              />

              {/* @context popover (Continue-style) */}
              {showContextMenu && (
                <div
                  onClick={e => e.stopPropagation()}
                  className="absolute left-0 bottom-full mb-2 w-52 bg-[#0b0b0f] border border-white/10 rounded-2xl shadow-2xl overflow-hidden animate-in slide-in-from-bottom-2 duration-150 z-50"
                >
                  <div className="px-3 py-2 text-[8px] font-bold text-white/25 uppercase tracking-widest border-b border-white/5">
                    Context Providers
                  </div>
                  {[
                    { id: 'board', icon: <Cpu size={13} className="text-violet-400" />, label: '@board', sub: 'Live KiCad Board State' },
                    { id: 'mem', icon: <BookOpen size={13} className="text-teal-400" />, label: '@mem', sub: 'Project Memory & Patterns' },
                    { id: 'nets', icon: <Activity size={13} className="text-amber-400" />, label: '@nets', sub: 'Routing Topology' },
                  ].map(ctx => (
                    <button
                      key={ctx.id}
                      onClick={() => {
                        setSelectedContexts(p => Array.from(new Set([...p, ctx.id])));
                        setShowContextMenu(false);
                        setInput(i => i.replace(/@$/, ''));
                      }}
                      className="w-full flex items-center gap-3 px-3 py-3 hover:bg-violet-600/15 transition-all text-left"
                    >
                      {ctx.icon}
                      <div>
                        <p className="text-xs font-bold text-white/80">{ctx.label}</p>
                        <p className="text-[9px] text-white/30">{ctx.sub}</p>
                      </div>
                    </button>
                  ))}
                </div>
              )}

              <button
                onClick={handleSend}
                disabled={!input.trim() || isStreaming}
                className="absolute right-2.5 bottom-2.5 p-2 bg-violet-600 hover:bg-violet-500 disabled:opacity-25 text-white rounded-xl transition-all shadow-lg shadow-violet-600/25 hover:scale-110 active:scale-95"
              >
                <Send size={15} fill="currentColor" />
              </button>
            </div>
          </div>

          {/* Footer status bar */}
          <div className="mt-2 flex items-center justify-between px-1">
            <div className="flex items-center gap-1.5">
              <span className={`w-1.5 h-1.5 rounded-full ${isStreaming ? 'bg-violet-400 animate-pulse' : 'bg-teal-400'}`} />
              <span className="text-[9px] text-white/25 font-medium">
                {isStreaming ? 'Hardware Coder active' : `Context: ${selectedContexts.length ? selectedContexts.join(' + ') : 'none'}`}
              </span>
            </div>
            <button
              onClick={e => { e.stopPropagation(); setShowContextMenu(m => !m); }}
              className="text-[9px] font-bold text-violet-400/50 hover:text-violet-400 flex items-center gap-1 transition-colors"
            >
              <Zap size={9} />@context
            </button>
          </div>
        </div>
      </div>

      <SettingsModal isOpen={isSettingsOpen} onClose={() => setIsSettingsOpen(false)} />
    </div>
  );
};
