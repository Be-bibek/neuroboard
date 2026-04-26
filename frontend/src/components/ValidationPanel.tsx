import { useEffect, useState } from "react";
import axios from "axios";
import { ShieldCheck, Activity, Zap, Ruler } from "lucide-react";

export function ValidationPanel() {
  const [report, setReport] = useState<any>(null);

  useEffect(() => {
    const interval = setInterval(async () => {
      try {
        const res = await axios.get("http://127.0.0.1:8000/api/v1/validation/report");
        setReport(res.data);
      } catch (err) {
        // Silently fail
      }
    }, 5000);
    return () => clearInterval(interval);
  }, []);

  if (!report) {
    return (
      <div className="flex flex-col h-full bg-white/5 backdrop-blur-xl border border-white/5 rounded-3xl p-4 text-white/40 items-center justify-center font-medium">
        <Activity size={24} className="mb-2 animate-pulse text-indigo-400/40" />
        Waiting for validation telemetry...
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full overflow-hidden">
      <h3 className="text-sm font-bold text-white/90 mb-4 flex items-center gap-2 px-1 tracking-tight">
        <ShieldCheck size={18} className="text-indigo-400" />
        Physics Engine Validation
      </h3>
      
      <div className="space-y-4 overflow-y-auto pr-2 scrollbar-none">
        <div className="glass-card p-4 bg-white/[0.03]">
          <div className="flex items-center gap-2 mb-3">
             <Activity size={12} className="text-indigo-400" />
             <div className="text-[10px] text-white/40 uppercase tracking-[0.15em] font-bold">Signal Integrity</div>
          </div>
          <div className="space-y-2">
            <div className="flex justify-between text-xs">
              <span className="text-white/60">S11 Return Loss:</span>
              <span className={`font-mono font-bold ${report.signal_integrity?.pass_s11 ? "text-emerald-400" : "text-rose-400"}`}>
                {report.signal_integrity?.s11_db?.toFixed(1) || "N/A"} dB
              </span>
            </div>
            <div className="flex justify-between text-xs">
              <span className="text-white/60">Diff Impedance:</span>
              <span className={`font-mono font-bold ${report.signal_integrity?.pass_impedance ? "text-emerald-400" : "text-rose-400"}`}>
                {report.signal_integrity?.impedance?.toFixed(1) || "N/A"} Ω
              </span>
            </div>
          </div>
        </div>

        <div className="glass-card p-4 bg-white/[0.03]">
          <div className="flex items-center gap-2 mb-3">
             <Zap size={12} className="text-amber-400" />
             <div className="text-[10px] text-white/40 uppercase tracking-[0.15em] font-bold">Power Integrity</div>
          </div>
          <div className="flex justify-between text-xs">
            <span className="text-white/60">IR Drop ({report.power_integrity?.rail || "NET"}):</span>
            <span className={`font-mono font-bold ${report.power_integrity?.pass ? "text-emerald-400" : "text-rose-400"}`}>
              {report.power_integrity?.ir_drop_v ? (report.power_integrity?.ir_drop_v * 1000).toFixed(1) : "N/A"} mV
            </span>
          </div>
        </div>

        <div className="glass-card p-4 bg-white/[0.03]">
          <div className="flex items-center gap-2 mb-3">
             <Ruler size={12} className="text-indigo-400" />
             <div className="text-[10px] text-white/40 uppercase tracking-[0.15em] font-bold">KiCad Compliances</div>
          </div>
          <div className="space-y-2">
            <div className="flex justify-between text-xs">
              <span className="text-white/60">DRC Violations:</span>
              <span className={`font-bold ${report.drc_status === "PASS" ? "text-emerald-400" : "text-rose-400"}`}>
                {report.drc_status || "PENDING"}
              </span>
            </div>
            <div className="flex justify-between text-xs">
              <span className="text-white/60">Target Routing:</span>
              <span className={`font-bold ${report.routing_metrics?.failures === 0 ? "text-emerald-400" : "text-rose-400"}`}>
                {report.routing_metrics?.failures === 0 ? "PASS" : `${report.routing_metrics?.failures} FAILS`}
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
