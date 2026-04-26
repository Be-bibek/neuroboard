import { Cpu, Cable, Layers } from "lucide-react";

const mockComponents = [
  { id: "U1", name: "Hailo-8 M.2 CPU", type: "IC", status: "AI Selected" },
  { id: "J1", name: "40-Pin RPi Header", type: "Connector", status: "Required Constraints" },
  { id: "J3", name: "PCIe FPC X4", type: "Connector", status: "AI Routed" },
  { id: "U2", name: "AT24C32 EEPROM", type: "IC", status: "Schematic Matched" },
];

export function ComponentLibrary() {
  return (
    <div className="flex flex-col h-full overflow-hidden">
      <h3 className="text-sm font-bold text-white/90 mb-4 flex items-center gap-2 px-1 tracking-tight uppercase">
        <Layers size={16} className="text-indigo-400" />
        Object Library
      </h3>
      
      <div className="space-y-2 overflow-y-auto pr-1 scrollbar-none">
        {mockComponents.map(comp => (
          <div key={comp.id} className="glass-card p-3 flex items-center gap-4 bg-white/[0.03] group">
            <div className="bg-white/5 p-2 rounded-xl group-hover:bg-indigo-500/20 transition-colors">
               {comp.type === "IC" ? <Cpu size={18} className="text-indigo-400" /> : <Cable size={18} className="text-blue-400" />}
            </div>
            <div className="flex flex-col">
              <span className="text-sm text-white/90 font-bold tracking-tight">{comp.name}</span>
              <span className="text-[10px] text-white/40 font-medium uppercase tracking-wider">{comp.id} · {comp.status}</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
