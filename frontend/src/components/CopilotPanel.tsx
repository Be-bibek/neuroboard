import { useState, useRef, useEffect } from "react";
import axios from "axios";
import {
  Bot, Send, CircuitBoard,CheckCircle2,
  AlertCircle, Loader2, X,
} from "lucide-react";

const API = "http://127.0.0.1:8000";

/* ─────────────────────────────────────────────────────────────────────── */
/*  Types                                                                   */
/* ─────────────────────────────────────────────────────────────────────── */

type Stage = "idle" | "suggesting" | "confirming" | "generating" | "done" | "error";

interface BomEntry {
  component: string;
  quantity: number;
  footprint: string;
  value: string;
}

interface SuggestionData {
  spec: {
    form_factor: string;
    board_size: string;
    accelerator: string | null;
    interfaces: string[];
    features: string[];
  };
  bom_preview: BomEntry[];
  component_count: number;
  warnings: string[];
  _internal_spec: object;
  _internal_manifest: object;
}

interface GenerationResult {
  stage: string;
  status: string;
  steps: Record<string, any>;
  netlist_path?: string;
  ready_for_placement?: boolean;
}

interface Message {
  role: "user" | "assistant" | "system";
  content: string;
  suggestion?: SuggestionData;
  generation?: GenerationResult;
}

/* ─────────────────────────────────────────────────────────────────────── */
/*  Sub-components                                                          */
/* ─────────────────────────────────────────────────────────────────────── */

function SpecBadge({ label }: { label: string }) {
  return (
    <span className="inline-block bg-teal-900/60 border border-teal-600/40 text-teal-300
                     text-xs font-mono rounded px-2 py-0.5 mr-1 mb-1">
      {label}
    </span>
  );
}

function BomTable({ entries }: { entries: BomEntry[] }) {
  return (
    <div className="overflow-x-auto mt-3">
      <table className="w-full text-xs border-collapse">
        <thead>
          <tr className="text-slate-400 border-b border-slate-700">
            <th className="text-left py-1 pr-3">Component</th>
            <th className="text-left py-1 pr-3">Qty</th>
            <th className="text-left py-1 pr-3">Value</th>
            <th className="text-left py-1">Footprint</th>
          </tr>
        </thead>
        <tbody>
          {entries.map((e, i) => (
            <tr key={i} className="border-b border-slate-800 hover:bg-slate-800/50 transition-colors">
              <td className="py-1.5 pr-3 text-slate-200 font-medium">{e.component}</td>
              <td className="py-1.5 pr-3 text-cyan-400 font-mono">{e.quantity}</td>
              <td className="py-1.5 pr-3 text-amber-300 font-mono">{e.value || "—"}</td>
              <td className="py-1.5 text-slate-400 font-mono truncate max-w-[180px]" title={e.footprint}>
                {e.footprint}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function SuggestionCard({
  data,
  onConfirm,
  onReject,
  disabled,
}: {
  data: SuggestionData;
  onConfirm: () => void;
  onReject: () => void;
  disabled: boolean;
}) {
  return (
    <div className="mt-3 bg-slate-800/80 border border-slate-600 rounded-lg p-4">
      {/* Spec summary */}
      <div className="mb-3">
        <div className="text-xs text-slate-400 uppercase tracking-widest mb-1.5">Design Spec</div>
        <SpecBadge label={`Form: ${data.spec.form_factor}`} />
        <SpecBadge label={`Size: ${data.spec.board_size}`} />
        {data.spec.accelerator && <SpecBadge label={`AI: ${data.spec.accelerator}`} />}
        {data.spec.interfaces.map(i => <SpecBadge key={i} label={i} />)}
        {data.spec.features.map(f => <SpecBadge key={f} label={f} />)}
      </div>

      {/* BOM */}
      <div className="text-xs text-slate-400 uppercase tracking-widest mb-1">
        Bill of Materials ({data.component_count} components)
      </div>
      <BomTable entries={data.bom_preview} />

      {/* Warnings */}
      {data.warnings.length > 0 && (
        <div className="mt-3 p-2 bg-amber-900/30 border border-amber-600/40 rounded text-xs text-amber-300">
          {data.warnings.map((w, i) => <div key={i}>⚠ {w}</div>)}
        </div>
      )}

      {/* Actions */}
      <div className="flex gap-3 mt-4">
        <button
          onClick={onConfirm}
          disabled={disabled}
          className="flex-1 flex items-center justify-center gap-2 py-2 px-4
                     bg-teal-600 hover:bg-teal-500 disabled:opacity-50
                     text-white text-sm font-semibold rounded-lg transition-colors"
        >
          <CheckCircle2 size={16} />
          Confirm & Generate Schematic
        </button>
        <button
          onClick={onReject}
          disabled={disabled}
          className="py-2 px-3 bg-slate-700 hover:bg-slate-600
                     disabled:opacity-50 text-slate-300 text-sm rounded-lg transition-colors"
        >
          <X size={16} />
        </button>
      </div>
    </div>
  );
}

function GenerationCard({ data }: { data: GenerationResult }) {
  const steps = data.steps || {};
  const isOk = data.status === "ok";

  return (
    <div className={`mt-3 border rounded-lg p-4 ${isOk
      ? "bg-emerald-900/20 border-emerald-600/40"
      : "bg-rose-900/20 border-rose-600/40"}`}
    >
      <div className="flex items-center gap-2 mb-3 font-semibold text-sm">
        {isOk
          ? <CheckCircle2 size={16} className="text-emerald-400" />
          : <AlertCircle size={16} className="text-rose-400" />}
        <span className={isOk ? "text-emerald-300" : "text-rose-300"}>
          {isOk ? "Schematic Generated Successfully" : "Generation Failed"}
        </span>
      </div>

      {/* Step statuses */}
      <div className="space-y-1.5">
        {Object.entries(steps).map(([step, info]: [string, any]) => (
          <div key={step} className="flex items-center gap-2 text-xs">
            {info.status === "ok"
              ? <CheckCircle2 size={12} className="text-emerald-400 flex-shrink-0" />
              : <AlertCircle size={12} className="text-amber-400 flex-shrink-0" />}
            <span className="text-slate-300 capitalize">{step.replace(/_/g, " ")}:</span>
            <span className="text-slate-400 font-mono">
              {info.status === "ok"
                ? info.net_count
                  ? `${info.net_count} nets, ${(info.diff_pairs || []).length} diff pairs`
                  : info.fetched !== undefined
                    ? `${info.fetched} fetched, ${info.cached} cached`
                    : info.component_count
                      ? `${info.component_count} parts`
                      : "✓"
                : info.error || "warning"}
            </span>
          </div>
        ))}
      </div>

      {data.netlist_path && (
        <div className="mt-3 p-2 bg-slate-800/60 rounded text-xs font-mono text-teal-400">
          📄 Netlist: {data.netlist_path}
        </div>
      )}

      {data.ready_for_placement && (
        <div className="mt-3 text-xs text-emerald-400 font-semibold">
          ✅ Ready for Stage 6: Semantic Placement + Routing
        </div>
      )}
    </div>
  );
}

function ChatMessage({ msg, onConfirm, onReject, isLast, generating }: {
  msg: Message;
  onConfirm: () => void;
  onReject: () => void;
  isLast: boolean;
  generating: boolean;
}) {
  const isUser = msg.role === "user";
  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"} mb-4`}>
      {!isUser && (
        <div className="w-7 h-7 rounded-full bg-teal-700 flex items-center justify-center
                        flex-shrink-0 mr-2 mt-0.5">
          <Bot size={14} className="text-white" />
        </div>
      )}
      <div className={`max-w-[85%] rounded-2xl px-4 py-2.5 text-sm leading-relaxed ${
        isUser
          ? "bg-teal-700 text-white rounded-tr-sm"
          : "bg-slate-800 text-slate-200 rounded-tl-sm"
      }`}>
        <p className="whitespace-pre-line">{msg.content}</p>
        {msg.suggestion && isLast && !generating && (
          <SuggestionCard
            data={msg.suggestion}
            onConfirm={onConfirm}
            onReject={onReject}
            disabled={generating}
          />
        )}
        {msg.generation && <GenerationCard data={msg.generation} />}
      </div>
    </div>
  );
}

/* ─────────────────────────────────────────────────────────────────────── */
/*  Main Copilot Component                                                  */
/* ─────────────────────────────────────────────────────────────────────── */

export function CopilotPanel() {
  const [messages, setMessages] = useState<Message[]>([
    {
      role: "assistant",
      content:
        "👋 Hi! I'm the NeuroBoard Copilot.\n\n" +
        "Describe the PCB you want to build and I'll suggest all the components, " +
        "generate the schematic, and kick off the full design pipeline.\n\n" +
        "Try: \"Create a Raspberry Pi HAT with Hailo-8 and dual SD card slots\"",
    },
  ]);
  const [input, setInput] = useState("");
  const [stage, setStage] = useState<Stage>("idle");
  const [pendingSuggestion, setPendingSuggestion] = useState<SuggestionData | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const addMessage = (msg: Message) => setMessages(prev => [...prev, msg]);

  /** Stage 1+2: Send prompt, get component suggestions */
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || stage !== "idle") return;

    const userMsg = input.trim();
    setInput("");
    addMessage({ role: "user", content: userMsg });
    setStage("suggesting");

    try {
      const res = await axios.post(`${API}/api/v1/copilot/prompt`, { intent: userMsg });
      const data: SuggestionData = res.data;

      if (!data._internal_spec) {
        throw new Error("Backend returned an unexpected response.");
      }

      setPendingSuggestion(data);

      const summary =
        `I've analyzed your request. Here's what I suggest building:\n\n` +
        `📐 Form Factor: ${data.spec.form_factor}\n` +
        `📏 Board Size: ${data.spec.board_size}\n` +
        (data.spec.accelerator ? `🧠 AI Accelerator: ${data.spec.accelerator}\n` : "") +
        `🔌 Interfaces: ${data.spec.interfaces.join(", ") || "GPIO"}\n` +
        `📦 Total Components: ${data.component_count}\n\n` +
        `Review the Bill of Materials below and confirm to generate the schematic.`;

      addMessage({ role: "assistant", content: summary, suggestion: data });
      setStage("confirming");
    } catch (err: any) {
      addMessage({
        role: "assistant",
        content: `❌ Failed to parse intent: ${err.message || "Backend unreachable"}. Make sure the backend is running.`,
      });
      setStage("idle");
    }
  };


  /** Stage 3+4+5: Confirm BOM → generate schematic */
  const handleConfirm = async () => {
    if (!pendingSuggestion) return;
    setStage("generating");
    addMessage({ role: "assistant", content: "⚙️ Confirmed! Fetching libraries and generating schematic..." });

    try {
      const res = await axios.post(`${API}/api/v1/copilot/confirm`, {
        spec: pendingSuggestion._internal_spec,
        manifest: pendingSuggestion._internal_manifest,
      });
      const data: GenerationResult = res.data;
      setPendingSuggestion(null);

      if (data.status === "ok") {
        addMessage({
          role: "assistant",
          content:
            `✅ Schematic and netlist generated successfully!\n\n` +
            `The design is now ready for semantic placement and routing.\n` +
            `Click "Run Full Pipeline" in the Actions panel to continue.`,
          generation: data,
        });
      } else {
        addMessage({
          role: "assistant",
          content: `⚠️ Generation completed with issues. Check the details below.`,
          generation: data,
        });
      }
      setStage("done");
    } catch (err: any) {
      addMessage({
        role: "assistant",
        content: `❌ Schematic generation failed: ${err.message}`,
      });
      setStage("idle");
    }
  };

  const handleReject = () => {
    setPendingSuggestion(null);
    addMessage({
      role: "assistant",
      content: "No problem! Tell me what to change and I'll suggest a new component list.",
    });
    setStage("idle");
  };

  const handleNewDesign = () => {
    setMessages([{
      role: "assistant",
      content: "Ready for a new design! Describe the PCB you want to build.",
    }]);
    setPendingSuggestion(null);
    setStage("idle");
  };

  const isLoading = stage === "suggesting" || stage === "generating";

  return (
    <div className="flex flex-col h-full bg-slate-900 border-r border-slate-700">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3
                      border-b border-slate-700 bg-slate-950/60 flex-shrink-0">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-lg bg-teal-700 flex items-center justify-center">
            <CircuitBoard size={16} className="text-white" />
          </div>
          <div>
            <div className="text-sm font-semibold text-slate-100">NeuroBoard Copilot</div>
            <div className="text-xs text-slate-500">AI PCB Design Assistant</div>
          </div>
        </div>
        {stage === "done" && (
          <button
            onClick={handleNewDesign}
            className="text-xs text-teal-400 hover:text-teal-300 transition-colors"
          >
            New Design
          </button>
        )}
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-1 min-h-0">
        {messages.map((msg, i) => (
          <ChatMessage
            key={i}
            msg={msg}
            onConfirm={handleConfirm}
            onReject={handleReject}
            isLast={i === messages.length - 1}
            generating={isLoading}
          />
        ))}
        {isLoading && (
          <div className="flex items-center gap-2 text-slate-400 text-sm pl-9">
            <Loader2 size={14} className="animate-spin" />
            {stage === "suggesting" ? "Analyzing intent..." : "Generating schematic..."}
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input Bar */}
      <form
        onSubmit={handleSubmit}
        className="flex gap-2 p-3 border-t border-slate-700 bg-slate-950/60 flex-shrink-0"
      >
        <input
          type="text"
          value={input}
          onChange={e => setInput(e.target.value)}
          placeholder={
            stage === "confirming"
              ? "Confirm above ↑ or type to modify..."
              : stage === "done"
                ? "Describe another design..."
                : "Describe your PCB design..."
          }
          disabled={isLoading || stage === "confirming"}
          className="flex-1 bg-slate-800 border border-slate-600 rounded-xl px-4 py-2.5 text-sm
                     text-slate-100 placeholder-slate-500
                     focus:outline-none focus:ring-2 focus:ring-teal-500
                     disabled:opacity-40 transition-all"
        />
        <button
          type="submit"
          disabled={isLoading || !input.trim() || stage === "confirming"}
          className="bg-teal-600 hover:bg-teal-500 disabled:opacity-40
                     text-white px-4 py-2.5 rounded-xl transition-colors flex-shrink-0"
        >
          <Send size={16} />
        </button>
      </form>
    </div>
  );
}
