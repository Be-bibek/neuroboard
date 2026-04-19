import { TEMPLATES } from "../templates/registry";
import { useNeuroStore } from "../store/useNeuroStore";
import type { PCBTemplate } from "../templates/registry";

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

// ── Template Selector Screen ───────────────────────────────────────────────
export function TemplateSelector() {
  const selectTemplate = useNeuroStore((s) => s.selectTemplate);

  // Group templates by category
  const rpi = TEMPLATES.filter((t) => t.category === "RPI");
  const arduino = TEMPLATES.filter((t) => t.category === "ARDUINO");
  const custom = TEMPLATES.filter((t) => t.category === "CUSTOM");

  const Section = ({
    label,
    items,
  }: {
    label: string;
    items: PCBTemplate[];
  }) => (
    <div className="mb-8">
      <h2 className="text-xs font-semibold text-slate-500 uppercase tracking-widest mb-3">
        {label}
      </h2>
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {items.map((t) => (
          <TemplateCard key={t.id} template={t} onSelect={() => selectTemplate(t)} />
        ))}
      </div>
    </div>
  );

  return (
    <div className="flex flex-col w-full h-full bg-slate-950 text-slate-100 overflow-y-auto">
      {/* Header */}
      <div className="flex items-center gap-4 px-8 pt-8 pb-6 border-b border-slate-800">
        <div className="w-12 h-12 rounded-2xl bg-gradient-to-br from-teal-500 to-cyan-600 flex items-center justify-center shadow-lg shadow-teal-900/50">
          <span className="text-2xl">🧠</span>
        </div>
        <div>
          <h1 className="text-2xl font-bold text-slate-100 tracking-tight">
            NeuroBoard
          </h1>
          <p className="text-sm text-slate-400">
            Select a PCB template to begin AI-powered design
          </p>
        </div>
      </div>

      {/* Template list */}
      <div className="flex-1 px-8 pt-6 pb-10">
        <Section label="Raspberry Pi" items={rpi} />
        <Section label="Arduino" items={arduino} />
        <Section label="Custom" items={custom} />
      </div>
    </div>
  );
}
