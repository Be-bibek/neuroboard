import { Cpu, Cable } from "lucide-react";

const mockComponents = [
  { id: "U1", name: "Hailo-8 M.2 CPU", type: "IC", status: "AI Selected" },
  { id: "J1", name: "40-Pin RPi Header", type: "Connector", status: "Required Constraints" },
  { id: "J3", name: "PCIe FPC X4", type: "Connector", status: "AI Routed" },
  { id: "U2", name: "AT24C32 EEPROM", type: "IC", status: "Schematic Matched" },
];

export function ComponentLibrary() {
  return (
    <div className="flex flex-col h-full bg-slate-900 border-r border-slate-700 w-64 p-4 overflow-y-auto">
      <h3 className="text-sm font-semibold text-slate-200 mb-4 uppercase tracking-wider">
        Objects Library
      </h3>
      
      <div className="space-y-2">
        {mockComponents.map(comp => (
          <div key={comp.id} className="flex items-center gap-3 p-2 bg-slate-800 rounded border border-slate-700 hover:bg-slate-750 cursor-pointer transition-colors">
            {comp.type === "IC" ? <Cpu size={16} className="text-teal-400" /> : <Cable size={16} className="text-blue-400" />}
            <div className="flex flex-col">
              <span className="text-sm text-slate-200 font-medium">{comp.name}</span>
              <span className="text-xs text-slate-500">{comp.id} - {comp.status}</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
