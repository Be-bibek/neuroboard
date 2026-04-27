import React, { useState } from 'react';
import {
  Brain, ChevronDown, ChevronRight, Terminal,
  ShieldCheck, Info, RefreshCw, Cpu, BookOpen, Zap,
} from 'lucide-react';

// ─── Types ────────────────────────────────────────────────────────────────────

export type MessageRole = 'user' | 'agent' | 'system';

export interface Message {
  id: string; role: MessageRole; content: string;
  timestamp: Date; model?: string;
}
export interface ThoughtEvent {
  id: string; type: 'thought'; content: string;
  model?: string; isStreaming?: boolean;
}
export interface ScriptEvent {
  id: string; type: 'script';
  script_code: string; stdout: string; stderr: string;
  status: 'success' | 'failed'; message: string; model?: string;
  raw_args?: Record<string, any>;
}
export interface ReflectEvent {
  id: string; type: 'reflect';
  attempt: number; corrected_script: string;
  message: string; model?: string;
}
export interface ToolExecution {
  id: string; tool: string;
  status: 'running' | 'success' | 'error';
  args: Record<string, any>; result?: any;
}
export interface MCPServer { name: string; status: string; tool_count: number; }

export type ChatItem =
  | { kind: 'message'; data: Message }
  | { kind: 'thought'; data: ThoughtEvent }
  | { kind: 'script'; data: ScriptEvent }
  | { kind: 'reflect'; data: ReflectEvent }
  | { kind: 'tool'; data: ToolExecution };

// ─── ModelBadge ───────────────────────────────────────────────────────────────

export const ModelBadge: React.FC<{ model?: string; active?: boolean }> = ({ model, active }) => {
  if (!model) return null;
  const isLite = model.toLowerCase().includes('lite');
  return (
    <span className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded-md text-[9px] font-bold uppercase tracking-wider border ${
      isLite
        ? 'bg-amber-500/15 text-amber-400 border-amber-500/20'
        : 'bg-indigo-500/15 text-indigo-400 border-indigo-500/20'
    }`}>
      {active && <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />}
      {isLite ? '⚡ Flash-Lite' : '🧠 Gemini 3 Flash'}
    </span>
  );
};

// ─── ContextChip ──────────────────────────────────────────────────────────────

export const ContextChip: React.FC<{ name: string; onRemove: () => void }> = ({ name, onRemove }) => {
  let bgClass = 'bg-violet-600/20 border-violet-500/30 text-violet-300';
  let Icon = Cpu;
  if (name === 'mem') {
    bgClass = 'bg-teal-600/20 border-teal-500/30 text-teal-300';
    Icon = BookOpen;
  } else if (name === 'nets') {
    bgClass = 'bg-amber-600/20 border-amber-500/30 text-amber-300';
    Icon = Activity;
  }

  return (
    <div className={`flex items-center gap-1.5 px-2 py-1 rounded-lg border animate-in fade-in duration-200 ${bgClass}`}>
      <Icon size={9} />
      <span className="text-[10px] font-bold font-mono">@{name}</span>
      <button onClick={onRemove} className="opacity-50 hover:opacity-100 transition-opacity ml-0.5 text-[8px]">✕</button>
    </div>
  );
};

// ─── ThoughtBubble (Glassmorphism Reasoning Block) ────────────────────────────

export const ThoughtBubble: React.FC<{ event: ThoughtEvent }> = ({ event }) => {
  const [expanded, setExpanded] = useState(true);
  const preview = event.content.slice(0, 100) + (event.content.length > 100 ? '…' : '');

  return (
    <div className="flex items-start gap-2 animate-in slide-in-from-top-2 duration-300">
      <div className={`mt-1 flex-shrink-0 w-6 h-6 rounded-full flex items-center justify-center border ${
        event.isStreaming
          ? 'bg-violet-500/30 border-violet-400/50 shadow-[0_0_12px_rgba(167,139,250,0.4)]'
          : 'bg-violet-500/15 border-violet-500/25'
      }`}>
        <Brain size={11} className={`text-violet-400 ${event.isStreaming ? 'animate-pulse' : ''}`} />
      </div>

      <div className="flex-1 backdrop-blur-md bg-white/[0.04] border border-white/10 rounded-2xl rounded-tl-none overflow-hidden shadow-xl">
        {/* Header */}
        <button
          onClick={() => setExpanded(e => !e)}
          className="w-full flex items-center justify-between px-4 py-2.5 hover:bg-white/5 transition-colors"
        >
          <div className="flex items-center gap-2">
            <span className="text-[9px] font-bold text-violet-400/80 uppercase tracking-widest">
              {event.isStreaming ? '● Thinking...' : 'Engineering Thought'}
            </span>
            {event.isStreaming && (
              <span className="flex gap-0.5">
                {[0, 1, 2].map(i => (
                  <span key={i} className="w-1 h-1 rounded-full bg-violet-400/60 animate-bounce"
                    style={{ animationDelay: `${i * 0.15}s` }} />
                ))}
              </span>
            )}
          </div>
          <div className="flex items-center gap-2">
            <ModelBadge model={event.model} active={event.isStreaming} />
            {expanded ? <ChevronDown size={12} className="text-white/30" /> : <ChevronRight size={12} className="text-white/30" />}
          </div>
        </button>

        {/* Body */}
        {expanded && (
          <div className="px-4 pb-3 border-t border-white/5">
            <p className="text-[11px] leading-relaxed text-white/60 font-mono pt-2.5 whitespace-pre-wrap">
              {event.content || preview}
            </p>
          </div>
        )}
        {!expanded && (
          <p className="px-4 pb-2.5 text-[10px] text-white/35 font-mono truncate">{preview}</p>
        )}
      </div>
    </div>
  );
};

// ─── ScriptCard (Expandable Tool Execution — shows raw JSON) ─────────────────

export const ScriptCard: React.FC<{ event: ScriptEvent }> = ({ event }) => {
  const [expanded, setExpanded] = useState(false);
  const [showRaw, setShowRaw] = useState(false);
  const ok = event.status === 'success';

  return (
    <div className="flex items-start gap-2 animate-in slide-in-from-left-2 duration-300">
      <div className={`mt-1 flex-shrink-0 w-6 h-6 rounded-full flex items-center justify-center border ${
        ok ? 'bg-emerald-500/20 border-emerald-500/30' : 'bg-rose-500/20 border-rose-500/30'
      }`}>
        <Terminal size={10} className={ok ? 'text-emerald-400' : 'text-rose-400'} />
      </div>

      <div className="flex-1 backdrop-blur-md bg-white/[0.04] border border-white/10 rounded-2xl rounded-tl-none overflow-hidden shadow-xl">
        {/* Header */}
        <button
          onClick={() => setExpanded(e => !e)}
          className="w-full flex items-center justify-between px-4 py-2.5 hover:bg-white/5 transition-colors"
        >
          <div className="flex items-center gap-2">
            <span className={`w-1.5 h-1.5 rounded-full ${ok ? 'bg-emerald-400' : 'bg-rose-400'}`} />
            <span className="text-[9px] font-bold uppercase tracking-widest text-white/60">
              {ok ? 'Script Executed' : 'Script Failed'}
            </span>
          </div>
          <div className="flex items-center gap-2">
            <ModelBadge model={event.model} />
            {expanded ? <ChevronDown size={12} className="text-white/30" /> : <ChevronRight size={12} className="text-white/30" />}
          </div>
        </button>

        {expanded && (
          <div className="border-t border-white/5 px-4 pb-3 space-y-2.5 pt-2.5">
            {/* Script code */}
            <div>
              <p className="text-[9px] text-white/30 uppercase tracking-widest mb-1.5">Python Script</p>
              <pre className="text-[10px] font-mono text-white/70 bg-black/30 rounded-xl p-3 overflow-x-auto leading-relaxed border border-white/5 max-h-36 overflow-y-auto">
                {event.script_code}
              </pre>
            </div>

            {/* stdout */}
            {event.stdout && (
              <div>
                <p className="text-[9px] text-emerald-400/60 uppercase tracking-widest mb-1.5">stdout</p>
                <pre className="text-[10px] font-mono text-emerald-300/80 bg-emerald-950/20 rounded-xl p-2.5 border border-emerald-500/10 max-h-24 overflow-y-auto">
                  {event.stdout}
                </pre>
              </div>
            )}

            {/* stderr */}
            {event.stderr && (
              <div>
                <p className="text-[9px] text-rose-400/60 uppercase tracking-widest mb-1.5">stderr</p>
                <pre className="text-[10px] font-mono text-rose-300/80 bg-rose-950/20 rounded-xl p-2.5 border border-rose-500/10 max-h-24 overflow-y-auto">
                  {event.stderr}
                </pre>
              </div>
            )}

            {/* Raw JSON sent to IPC — click to reveal */}
            {event.raw_args && (
              <div>
                <button
                  onClick={() => setShowRaw(r => !r)}
                  className="text-[9px] text-indigo-400/60 hover:text-indigo-400 uppercase tracking-widest flex items-center gap-1 transition-colors"
                >
                  <Zap size={9} /> {showRaw ? 'Hide' : 'Show'} Raw KiCad IPC JSON
                </button>
                {showRaw && (
                  <pre className="mt-1.5 text-[10px] font-mono text-white/50 bg-black/30 rounded-xl p-2.5 border border-white/5 overflow-x-auto max-h-32 overflow-y-auto">
                    {JSON.stringify(event.raw_args, null, 2)}
                  </pre>
                )}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

// ─── ReflectCard ─────────────────────────────────────────────────────────────

export const ReflectCard: React.FC<{ event: ReflectEvent }> = ({ event }) => {
  const [expanded, setExpanded] = useState(false);
  return (
    <div className="flex items-start gap-2 animate-in slide-in-from-right-2 duration-300">
      <div className="mt-1 flex-shrink-0 w-6 h-6 rounded-full bg-amber-500/20 border border-amber-500/30 flex items-center justify-center">
        <RefreshCw size={10} className="text-amber-400" />
      </div>
      <div className="flex-1 backdrop-blur-md bg-amber-950/20 border border-amber-500/20 rounded-2xl rounded-tl-none overflow-hidden shadow-xl">
        <button
          onClick={() => setExpanded(e => !e)}
          className="w-full flex items-center justify-between px-4 py-2.5 hover:bg-amber-500/5 transition-colors"
        >
          <div className="flex items-center gap-2">
            <span className="w-1.5 h-1.5 rounded-full bg-amber-400 animate-pulse" />
            <span className="text-[9px] font-bold text-amber-400/80 uppercase tracking-widest">
              Self-Correcting · Attempt {event.attempt}/2
            </span>
          </div>
          {expanded ? <ChevronDown size={12} className="text-white/30" /> : <ChevronRight size={12} className="text-white/30" />}
        </button>
        {expanded && (
          <div className="border-t border-amber-500/10 px-4 pb-3 pt-2.5">
            <p className="text-[10px] text-amber-200/60 mb-2">{event.message}</p>
            <pre className="text-[10px] font-mono text-white/60 bg-black/30 rounded-xl p-2.5 border border-white/5 overflow-x-auto max-h-28 overflow-y-auto">
              {event.corrected_script}
            </pre>
          </div>
        )}
      </div>
    </div>
  );
};

// ─── ActionLogItem (OpenHands-style live step) ────────────────────────────────

export const ActionLogItem: React.FC<{ tool: ToolExecution }> = ({ tool }) => {
  const [showJson, setShowJson] = useState(false);
  return (
    <div className="flex items-start gap-2 animate-in slide-in-from-right-2 duration-200">
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

      <div className="flex-1 backdrop-blur-md bg-white/[0.03] border border-white/8 rounded-2xl rounded-tl-none overflow-hidden">
        <button
          onClick={() => setShowJson(j => !j)}
          className="w-full flex items-center justify-between px-4 py-2.5 hover:bg-white/5 transition-colors text-left"
        >
          <span className="text-[11px] font-bold text-white/80 font-mono">{tool.tool}</span>
          <span className={`text-[9px] font-bold px-2 py-0.5 rounded-md uppercase tracking-wider ${
            tool.status === 'running' ? 'bg-indigo-500/20 text-indigo-400'
            : tool.status === 'success' ? 'bg-emerald-500/20 text-emerald-400'
            : 'bg-rose-500/20 text-rose-400'
          }`}>{tool.status}</span>
        </button>
        {tool.args.action && (
          <p className="px-4 pb-1.5 text-[10px] text-white/35 italic">{tool.args.action}</p>
        )}
        {/* Raw JSON on click */}
        {showJson && (
          <div className="px-4 pb-3 border-t border-white/5 pt-2">
            <p className="text-[9px] text-indigo-400/60 uppercase tracking-widest mb-1.5">Raw KiCad IPC JSON</p>
            <pre className="text-[10px] font-mono text-white/50 bg-black/30 rounded-xl p-2.5 border border-white/5 overflow-x-auto max-h-32 overflow-y-auto">
              {JSON.stringify({ tool: tool.tool, args: tool.args, result: tool.result }, null, 2)}
            </pre>
          </div>
        )}
      </div>
    </div>
  );
};
