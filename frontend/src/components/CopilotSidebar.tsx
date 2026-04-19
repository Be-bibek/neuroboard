import { useState, useRef, useEffect } from "react";
import {
  Bot, Send, CircuitBoard, CheckCircle2,
  AlertCircle, Loader2, X, PlusCircle, Layout,
} from "lucide-react";
import { useNeuroStore } from "../store/useNeuroStore";
import { getCompatibleModules, getModuleById } from "../templates/registry";
import { sendCommand } from "../network/syncEngine";
import type { PCBModule } from "../templates/registry";

// ── Types ──────────────────────────────────────────────────────────────────
type Stage = "idle" | "processing" | "done" | "error";

interface Message {
  role: "user" | "assistant";
  content: string;
  modules?: PCBModule[];   // suggested module list after a command
}

// ── Quick Suggestion Chip ──────────────────────────────────────────────────
function SuggestionChip({
  label,
  onClick,
}: {
  label: string;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className="text-xs bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700
                 rounded-full px-3 py-1 transition-colors"
    >
      {label}
    </button>
  );
}

// ── Module Result Card ─────────────────────────────────────────────────────
function ModuleCard({
  module,
  onAdd,
  alreadyAdded,
}: {
  module: PCBModule;
  onAdd: () => void;
  alreadyAdded: boolean;
}) {
  return (
    <div className="flex items-start gap-3 p-3 bg-slate-800/60 rounded-xl border border-slate-700 mt-2">
      <span className="text-2xl leading-none mt-0.5">{module.icon}</span>
      <div className="flex-1 min-w-0">
        <div className="text-sm font-semibold text-slate-200">{module.name}</div>
        <div className="text-xs text-slate-400 leading-relaxed mt-0.5">{module.description}</div>
        <div className="text-[10px] font-mono text-teal-400 mt-1">{module.footprint}</div>
      </div>
      <button
        onClick={onAdd}
        disabled={alreadyAdded}
        className={`flex-shrink-0 flex items-center gap-1 text-xs px-2.5 py-1.5 rounded-lg font-semibold transition-colors
          ${alreadyAdded
            ? "bg-emerald-900/50 text-emerald-400 border border-emerald-700/50 cursor-default"
            : "bg-teal-600 hover:bg-teal-500 text-white"
          }`}
      >
        {alreadyAdded ? <><CheckCircle2 size={11} /> Added</> : <><PlusCircle size={11} /> Add</>}
      </button>
    </div>
  );
}

// ── Parse user command and return relevant modules ─────────────────────────
function parseCommand(
  input: string,
  templateId: string | undefined
): { action: string; modules: PCBModule[] } | null {
  const lower = input.toLowerCase();
  const allCompatible = templateId ? getCompatibleModules(templateId) : [];

  // "add nvme / pcie / m.2"
  if (/nvme|pcie|m\.2|ssd/i.test(lower)) {
    const m = getModuleById("nvme-m2");
    return m ? { action: "ADD_MODULE", modules: [m] } : null;
  }
  // "add usb / usb-c"
  if (/usb/i.test(lower)) {
    const m = getModuleById("usb-c-port");
    return m ? { action: "ADD_MODULE", modules: [m] } : null;
  }
  // "add led / indicator"
  if (/led|light|indicator/i.test(lower)) {
    const m = getModuleById("led-indicator");
    return m ? { action: "ADD_MODULE", modules: [m] } : null;
  }
  // "add eeprom / hat eeprom"
  if (/eeprom/i.test(lower)) {
    const m = getModuleById("eeprom-hat");
    return m ? { action: "ADD_MODULE", modules: [m] } : null;
  }
  // "show modules / what can I add / list modules"
  if (/show|list|what|modules?/i.test(lower)) {
    return { action: "LIST_MODULES", modules: allCompatible.slice(0, 4) };
  }

  return null;
}

// ── Main Copilot Sidebar ───────────────────────────────────────────────────
export function CopilotSidebar() {
  const selectedTemplate = useNeuroStore((s) => s.selectedTemplate);
  const activeModules = useNeuroStore((s) => s.activeModules);
  const addModule = useNeuroStore((s) => s.addModule);
  const clearTemplate = useNeuroStore((s) => s.clearTemplate);
  const setView = useNeuroStore((s) => s.setView);
  const syncStatus = useNeuroStore((s) => s.syncStatus);
  const executionLogs = useNeuroStore((s) => s.executionLogs);
  const violations = useNeuroStore((s) => s.violations);

  const [messages, setMessages] = useState<Message[]>([
    {
      role: "assistant",
      content: selectedTemplate
        ? `✅ Template loaded: **${selectedTemplate.name}**\n\nTell me what to add. Try:\n• "Add NVMe slot"\n• "Add USB-C port"\n• "Show available modules"`
        : "Select a template first.",
    },
  ]);
  const [input, setInput] = useState("");
  const [stage, setStage] = useState<Stage>("idle");
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const addMsg = (m: Message) => setMessages((prev) => [...prev, m]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || stage === "processing") return;

    const userInput = input.trim();
    setInput("");
    addMsg({ role: "user", content: userInput });
    setStage("processing");

    const result = parseCommand(userInput, selectedTemplate?.id);
    await new Promise((r) => setTimeout(r, 600)); // simulate AI thinking

    if (!result) {
      addMsg({
        role: "assistant",
        content: `I'm not sure what you meant. Try:\n• "Add NVMe slot"\n• "Show available modules"`,
      });
    } else if (result.action === "LIST_MODULES") {
      addMsg({
        role: "assistant",
        content: `Here are modules compatible with **${selectedTemplate?.name}**:`,
        modules: result.modules,
      });
    } else if (result.action === "ADD_MODULE") {
      addMsg({
        role: "assistant",
        content: `Found ${result.modules.length} module(s). Click **Add** to place in KiCad via IPC:`,
        modules: result.modules,
      });
    }

    setStage("idle");
  };

  const handleAddModule = (module: PCBModule) => {
    addModule(module);
    // Fire the real IPC command to the backend
    sendCommand({
      type: "ADD_MODULE",
      payload: {
        module_id: module.id,
        footprint: module.footprint,
        template_id: selectedTemplate?.id,
        interface: module.interface,
      },
    });
    addMsg({
      role: "assistant",
      content: `${module.icon} **${module.name}** added to the board. KiCad IPC command sent.`,
    });
  };

  const syncDot =
    syncStatus === "CONNECTED"
      ? "bg-teal-400"
      : syncStatus === "SYNCING"
      ? "bg-amber-400 animate-pulse"
      : "bg-red-500";

  // Quick-suggestion chips based on template
  const quickSuggestions =
    selectedTemplate?.id === "rpi-hat"
      ? ["Add NVMe slot", "Add EEPROM", "Add LED indicator", "List modules"]
      : selectedTemplate?.id === "arduino-shield"
      ? ["Add LED indicator", "Add USB-C", "List modules"]
      : ["List modules"];

  return (
    <div className="flex flex-col w-full h-full bg-slate-900 text-slate-100">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-slate-800 bg-slate-950/80 flex-shrink-0">
        <div className="flex items-center gap-2">
          <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-teal-500 to-cyan-600 flex items-center justify-center">
            <CircuitBoard size={14} className="text-white" />
          </div>
          <div>
            <div className="text-xs font-bold text-slate-100">NeuroBoard Copilot</div>
            {selectedTemplate && (
              <div className="text-[10px] text-teal-400 font-mono">
                {selectedTemplate.icon} {selectedTemplate.name}
              </div>
            )}
          </div>
        </div>
        <div className="flex items-center gap-2">
          {/* KiCad sync status */}
          <span className="flex items-center gap-1.5 text-[10px] text-slate-400">
            <span className={`w-1.5 h-1.5 rounded-full ${syncDot}`} />
            {syncStatus}
          </span>
          {/* Planning board toggle */}
          <button
            onClick={() => setView("PLANNING_BOARD")}
            title="Open Planning Board"
            className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-400 hover:text-slate-200 transition-colors"
          >
            <Layout size={13} />
          </button>
          {/* Change template */}
          <button
            onClick={clearTemplate}
            title="Change Template"
            className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-400 hover:text-slate-200 transition-colors"
          >
            <X size={13} />
          </button>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-3 space-y-1 min-h-0">
        {messages.map((msg, i) => {
          const isUser = msg.role === "user";
          return (
            <div key={i} className={`flex ${isUser ? "justify-end" : "justify-start"} mb-3`}>
              {!isUser && (
                <div className="w-6 h-6 rounded-full bg-teal-700 flex items-center justify-center flex-shrink-0 mr-2 mt-0.5">
                  <Bot size={12} className="text-white" />
                </div>
              )}
              <div
                className={`max-w-[88%] rounded-2xl px-3 py-2 text-xs leading-relaxed ${
                  isUser
                    ? "bg-teal-700 text-white rounded-tr-sm"
                    : "bg-slate-800 text-slate-200 rounded-tl-sm"
                }`}
              >
                <p className="whitespace-pre-line">{msg.content}</p>
                {/* Module cards */}
                {msg.modules?.map((m) => (
                  <ModuleCard
                    key={m.id}
                    module={m}
                    onAdd={() => handleAddModule(m)}
                    alreadyAdded={!!activeModules.find((x) => x.id === m.id)}
                  />
                ))}
              </div>
            </div>
          );
        })}
        {stage === "processing" && (
          <div className="flex items-center gap-2 text-slate-400 text-xs pl-8">
            <Loader2 size={12} className="animate-spin" /> Thinking...
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Quick suggestion chips */}
      <div className="flex flex-wrap gap-1.5 px-3 pb-2 flex-shrink-0">
        {quickSuggestions.map((s) => (
          <SuggestionChip key={s} label={s} onClick={() => setInput(s)} />
        ))}
      </div>

      {/* Violations badge */}
      {violations.filter((v) => v.severity === "error").length > 0 && (
        <div className="mx-3 mb-2 flex items-center gap-2 text-xs py-1.5 px-2.5 bg-rose-900/40 border border-rose-700/40 rounded-lg text-rose-300">
          <AlertCircle size={12} />
          {violations.filter((v) => v.severity === "error").length} DRC error(s) from KiCad
        </div>
      )}

      {/* Input */}
      <form
        onSubmit={handleSubmit}
        className="flex gap-2 p-3 border-t border-slate-800 bg-slate-950/60 flex-shrink-0"
      >
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder='Try: "Add NVMe slot"'
          disabled={stage === "processing"}
          className="flex-1 bg-slate-800 border border-slate-700 rounded-xl px-3 py-2 text-xs
                     text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-1
                     focus:ring-teal-500 disabled:opacity-40 transition-all"
        />
        <button
          type="submit"
          disabled={stage === "processing" || !input.trim()}
          className="bg-teal-600 hover:bg-teal-500 disabled:opacity-40 text-white px-3 py-2 rounded-xl transition-colors flex-shrink-0"
        >
          <Send size={14} />
        </button>
      </form>

      {/* Execution Log Footer */}
      {executionLogs.length > 0 && (
        <div className="border-t border-slate-800 bg-slate-950/80 px-3 py-2 max-h-20 overflow-y-auto flex-shrink-0">
          {executionLogs.slice(-4).map((log, i) => (
            <div key={i} className="text-[10px] font-mono text-slate-500 leading-relaxed">
              {log}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
