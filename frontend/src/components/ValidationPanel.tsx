import { useEffect, useState } from "react";
import axios from "axios";
import { ShieldCheck } from "lucide-react";

export function ValidationPanel() {
  const [report, setReport] = useState<any>(null);

  useEffect(() => {
    // Poll for the latest report
    const interval = setInterval(async () => {
      try {
        const res = await axios.get("http://127.0.0.1:8000/api/v1/validation/report");
        setReport(res.data);
      } catch (err) {
        // Silently fail if report not available yet
      }
    }, 5000);
    return () => clearInterval(interval);
  }, []);

  if (!report) {
    return (
      <div className="flex flex-col h-full bg-slate-900 border border-slate-700 rounded-lg p-4 text-slate-400 items-center justify-center">
        Waiting for validation data...
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full bg-slate-900 border border-slate-700 rounded-lg p-4 overflow-y-auto">
      <h3 className="text-sm font-semibold text-slate-200 mb-3 flex items-center gap-2">
        <ShieldCheck size={16} className="text-emerald-400" />
        Physics & Validation Report
      </h3>
      
      <div className="space-y-3">
        <div className="p-3 bg-slate-800 rounded border border-slate-700">
          <div className="text-xs text-slate-400 uppercase tracking-widest mb-1">Signal Integrity</div>
          <div className="flex justify-between text-sm">
            <span>S11 Return Loss:</span>
            <span className={report.signal_integrity?.pass_s11 ? "text-emerald-400" : "text-rose-400"}>
              {report.signal_integrity?.s11_db?.toFixed(1) || "N/A"} dB
            </span>
          </div>
          <div className="flex justify-between text-sm">
            <span>Diff Impedance:</span>
            <span className={report.signal_integrity?.pass_impedance ? "text-emerald-400" : "text-rose-400"}>
              {report.signal_integrity?.impedance?.toFixed(1) || "N/A"} Ω
            </span>
          </div>
        </div>

        <div className="p-3 bg-slate-800 rounded border border-slate-700">
          <div className="text-xs text-slate-400 uppercase tracking-widest mb-1">Power Integrity</div>
          <div className="flex justify-between text-sm">
            <span>IR Drop ({report.power_integrity?.rail || "NET"}):</span>
            <span className={report.power_integrity?.pass ? "text-emerald-400" : "text-rose-400"}>
              {report.power_integrity?.ir_drop_v ? (report.power_integrity?.ir_drop_v * 1000).toFixed(1) : "N/A"} mV
            </span>
          </div>
        </div>

        <div className="p-3 bg-slate-800 rounded border border-slate-700">
          <div className="text-xs text-slate-400 uppercase tracking-widest mb-1">KiCad Compliances</div>
           <div className="flex justify-between text-sm">
            <span>DRC Violations:</span>
            <span className={report.drc_status === "PASS" ? "text-emerald-400" : "text-rose-400"}>
              {report.drc_status || "PENDING"}
            </span>
          </div>
          <div className="flex justify-between text-sm">
            <span>Target Routing:</span>
            <span className={report.routing_metrics?.failures === 0 ? "text-emerald-400" : "text-rose-400"}>
              {report.routing_metrics?.failures === 0 ? "PASS" : `${report.routing_metrics?.failures} Fails`}
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}
