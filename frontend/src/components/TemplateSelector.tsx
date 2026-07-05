import { TEMPLATES } from "../templates/registry";
import { useNeuroStore } from "../store/useNeuroStore";
import type { PCBTemplate } from "../templates/registry";
import { PromptBox } from "./shared/PromptBox";

// ── Category label map ─────────────────────────────────────────────────────
const CATEGORY_LABEL: Record<string, string> = {
  RPI: "Raspberry Pi",
  ARDUINO: "Arduino",
  CUSTOM: "Custom",
};

const CATEGORY_COLOR: Record<string, string> = {
  RPI: "from-rose-500/20 to-rose-700/10 border-rose-600/40 hover:border-rose-400",
  ARDUINO: "from-blue-500/20 to-blue-700/10 border-blue-600/40 hover:border-blue-400",
  CUSTOM: "from-slate-500/20 to-slate-700/10 border-slate-600/40 hover:border-slate-400",
};

const CATEGORY_BADGE: Record<string, string> = {
  RPI: "bg-rose-900/60 text-rose-300 border-rose-600/30",
  ARDUINO: "bg-blue-900/60 text-blue-300 border-blue-600/30",
  CUSTOM: "bg-slate-800 text-slate-300 border-slate-600/30",
};

// ── Template Card ──────────────────────────────────────────────────────────
function TemplateCard({
  template,
  onSelect,
}: {
  template: PCBTemplate;
  onSelect: () => void;
}) {
  const colors = CATEGORY_COLOR[template.category];
  const badge = CATEGORY_BADGE[template.category];

  return (
    <button
      onClick={onSelect}
      className={`
        group w-full text-left rounded-2xl border bg-gradient-to-br p-5
        transition-all duration-200 cursor-pointer
        ${colors}
        hover:scale-[1.02] hover:shadow-xl hover:shadow-black/40
      `}
    >
      {/* Icon + Category */}
      <div className="flex items-start justify-between mb-3">
        <span className="text-4xl leading-none">{template.icon}</span>
        <span
          className={`text-xs font-semibold font-mono px-2 py-0.5 rounded border ${badge}`}
        >
          {CATEGORY_LABEL[template.category]}
        </span>
      </div>

      {/* Name + Description */}
      <h3 className="text-base font-bold text-slate-100 mb-1 group-hover:text-white transition-colors">
        {template.name}
      </h3>
      <p className="text-xs text-slate-400 leading-relaxed mb-3">
        {template.description}
      </p>

      {/* Interface tags */}
      {template.interfaces.length > 0 && (
        <div className="flex flex-wrap gap-1">
          {template.interfaces.map((iface) => (
            <span
              key={iface}
              className="text-[10px] font-mono bg-slate-800/80 text-slate-400 px-1.5 py-0.5 rounded"
            >
              {iface}
            </span>
          ))}
        </div>
      )}
    </button>
  );
}

export function TemplateSelector() {
  const selectTemplate = useNeuroStore((s) => s.selectTemplate);
  const setInitialPrompt = useNeuroStore((s) => s.setInitialPrompt);

  // Group templates by category
  const rpi = TEMPLATES.filter((t) => t.category === "RPI");
  const arduino = TEMPLATES.filter((t) => t.category === "ARDUINO");
  const custom = TEMPLATES.filter((t) => t.category === "CUSTOM");

  const handlePromptSubmit = (prompt: string) => {
    setInitialPrompt(prompt);
    // Auto-select Custom to boot the IDE workspace
    const customTemplate = custom[0] || TEMPLATES[0];
    selectTemplate(customTemplate);
  };

  const Section = ({
    label,
    items,
  }: {
    label: string;
    items: PCBTemplate[];
  }) => (
    <div className="mb-8 flex-1">
      <h2 className="text-xs font-semibold text-slate-500 uppercase tracking-widest mb-3">
        {label}
      </h2>
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-1 gap-4">
        {items.map((t) => (
          <TemplateCard key={t.id} template={t} onSelect={() => selectTemplate(t)} />
        ))}
      </div>
    </div>
  );

  return (
    <div className="flex flex-col w-full h-full bg-slate-900 text-slate-100 overflow-y-auto items-center pt-12 sm:pt-20">
      {/* Hero Section */}
      <div className="w-full max-w-4xl flex flex-col items-center text-center mb-12 px-4 sm:px-6">
        <h1 className="text-4xl sm:text-6xl font-bold text-transparent bg-clip-text bg-gradient-to-r from-indigo-400 to-cyan-400 tracking-tight mb-4 font-serif">
          Prompt-to-Hardware
        </h1>
        <p className="text-base sm:text-xl text-slate-400 mb-8 max-w-2xl font-light">
          The World's First Mobile AI Compiler for Native KiCad Designs.
        </p>
        
        <div className="w-full max-w-3xl flex flex-col items-center">
          <PromptBox onSubmitStart={handlePromptSubmit} className="shadow-[0_0_40px_rgba(79,70,229,0.15)] w-full" />
          
          <div className="mt-6 flex flex-wrap items-center justify-center gap-2 text-xs text-slate-500">
            <span className="font-semibold text-slate-400 mr-2">Try:</span>
            <button onClick={() => handlePromptSubmit("Design schematics for an audio amplifier")} className="px-3 py-1.5 rounded-full bg-white/5 border border-white/10 hover:bg-white/10 transition-colors">Design schematics</button>
            <button onClick={() => handlePromptSubmit("Review my PCB-generated BOM")} className="px-3 py-1.5 rounded-full bg-white/5 border border-white/10 hover:bg-white/10 transition-colors">Review PCB BOM</button>
            <button onClick={() => handlePromptSubmit("Design a Raspberry Pi HAT")} className="px-3 py-1.5 rounded-full bg-white/5 border border-white/10 hover:bg-white/10 transition-colors">Raspberry Pi</button>
            <button onClick={() => handlePromptSubmit("Design an Arduino Uno shield")} className="px-3 py-1.5 rounded-full bg-white/5 border border-white/10 hover:bg-white/10 transition-colors">Arduino Uno</button>
          </div>
        </div>
      </div>

      {/* Quick Start Options */}
      <div className="w-full max-w-6xl px-4 sm:px-8 pb-10 flex-1">
        <div className="flex items-center gap-4 mb-8">
          <div className="h-px bg-white/5 flex-1"></div>
          <h2 className="text-xs sm:text-sm font-semibold text-slate-600 uppercase tracking-widest">Or choose a quick start template</h2>
          <div className="h-px bg-white/5 flex-1"></div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          <Section label="Raspberry Pi" items={rpi} />
          <Section label="Arduino" items={arduino} />
          <Section label="Custom" items={custom} />
        </div>
      </div>

      {/* Footer */}
      <div className="w-full border-t border-white/5 bg-black/20 py-6 mt-auto">
        <div className="max-w-6xl mx-auto px-6 flex flex-col sm:flex-row items-center justify-between gap-6 text-xs text-slate-500">
          <div className="flex items-center gap-2">
            <span className="text-xl">🧠</span>
            <span className="font-semibold text-slate-400">NeuroBoard AI</span>
          </div>

          <div className="flex items-center gap-4">
            <span className="font-semibold text-slate-400 mr-2">Connect with me:</span>
            <a href="https://bibek-das.vercel.app/" target="_blank" rel="noopener noreferrer" className="opacity-70 hover:opacity-100 transition-opacity">
              <img src="https://github.com/Be-bibek/Be-bibek/blob/main/portfolio.svg?raw=true" alt="Portfolio" width="32" className="rounded" />
            </a>
            <a href="mailto:bibekdas1055@gmail.com" className="opacity-70 hover:opacity-100 transition-opacity">
              <img src="https://skillicons.dev/icons?i=gmail" alt="Gmail" width="32" />
            </a>
            <a href="https://www.linkedin.com/in/bibek-das-364367323/" target="_blank" rel="noopener noreferrer" className="opacity-70 hover:opacity-100 transition-opacity">
              <img src="https://skillicons.dev/icons?i=linkedin" alt="LinkedIn" width="32" />
            </a>
            <a href="https://www.instagram.com/bibek_ai_deas/" target="_blank" rel="noopener noreferrer" className="opacity-70 hover:opacity-100 transition-opacity">
              <img src="https://skillicons.dev/icons?i=instagram" alt="Instagram" width="32" />
            </a>
            <a href="https://youtube.com/@be-bibek" target="_blank" rel="noopener noreferrer" className="opacity-70 hover:opacity-100 transition-opacity">
              <img src="https://github.com/Be-bibek/Be-bibek/blob/main/youtube.svg?raw=true" alt="YouTube" width="32" />
            </a>
          </div>

          <div>
            Developed by <a href="https://bibek-das.vercel.app/" target="_blank" rel="noreferrer" className="text-indigo-400 hover:text-indigo-300 font-medium transition-colors">Bibek Das</a>
          </div>
        </div>
      </div>
    </div>
  );
}
