import { useEffect, useRef, useState } from "react";
import { Activity } from "lucide-react";

export function PCBViewer2D() {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [status, setStatus] = useState("Disconnected");
  const [hasData, setHasData] = useState(false);

  useEffect(() => {
    const ws = new WebSocket("ws://127.0.0.1:8000/api/v1/live_stream");

    ws.onopen = () => setStatus("IPC ACTIVE");
    ws.onclose = () => setStatus("OFFLINE");
    
    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.type === "board_update" && data.state) {
        setHasData(true);
        drawBoard(data.state);
      }
    };

    return () => ws.close();
  }, []);

  const drawBoard = (state: any) => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const SCALE = 5;
    const OFFSET_X = canvas.width / 2;
    const OFFSET_Y = canvas.height / 2;

    ctx.clearRect(0, 0, canvas.width, canvas.height);

    // Draw Tracks
    if (state.tracks) {
      ctx.strokeStyle = "rgba(99, 102, 241, 0.8)";
      ctx.lineWidth = 2;
      ctx.lineCap = "round";
      ctx.lineJoin = "round";
      state.tracks.forEach((track: any) => {
        ctx.beginPath();
        ctx.moveTo(track.start[0] * SCALE + OFFSET_X - 150, track.start[1] * SCALE + OFFSET_Y - 100);
        ctx.lineTo(track.end[0] * SCALE + OFFSET_X - 150, track.end[1] * SCALE + OFFSET_Y - 100);
        ctx.stroke();
      });
    }

    // Draw Footprints
    if (state.footprints) {
      state.footprints.forEach((fp: any) => {
        const x = fp.x * SCALE + OFFSET_X - 150;
        const y = fp.y * SCALE + OFFSET_Y - 100;
        
        ctx.fillStyle = "rgba(255, 255, 255, 0.1)";
        ctx.strokeStyle = "rgba(255, 255, 255, 0.2)";
        ctx.lineWidth = 1;
        ctx.fillRect(x - 6, y - 6, 12, 12);
        ctx.strokeRect(x - 6, y - 6, 12, 12);
        
        ctx.fillStyle = "rgba(255, 255, 255, 0.9)";
        ctx.font = "bold 9px Inter, sans-serif";
        ctx.textAlign = "center";
        ctx.fillText(fp.ref, x, y - 10);
      });
    }
  };

  return (
    <div className="flex flex-col h-full bg-transparent overflow-hidden relative group">
      {/* Overlay Status */}
      <div className="absolute top-4 left-4 z-20 flex items-center gap-2 px-4 py-1.5 rounded-full bg-white/5 border border-white/10 backdrop-blur-xl shadow-2xl transition-all duration-300 group-hover:bg-white/10">
        <Activity size={12} className={status === "IPC ACTIVE" ? "text-emerald-400 animate-pulse" : "text-rose-400"} />
        <span className="text-[10px] font-bold text-white/70 uppercase tracking-widest">{status}</span>
      </div>
      
      {/* Grid Pattern Overlay with animation */}
      <div className="absolute inset-0 pointer-events-none opacity-[0.03] animate-[pulse_4s_ease-in-out_infinite]" 
           style={{ backgroundImage: 'radial-gradient(circle, white 1px, transparent 1px)', backgroundSize: '24px 24px' }}></div>

      {/* Empty State / Hints */}
      {!hasData && (
        <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
          <div className="w-24 h-24 mb-6 rounded-full bg-indigo-500/5 flex items-center justify-center border border-indigo-500/10 shadow-[0_0_40px_rgba(99,102,241,0.1)]">
            <Activity size={32} className="text-indigo-400/50" />
          </div>
          <h2 className="text-xl font-bold text-white/50 tracking-tight mb-2">Awaiting AI Synthesis</h2>
          <p className="text-xs text-white/30 max-w-sm text-center leading-relaxed">
            Describe your hardware intent in the AI panel to begin autonomous routing and component placement.
          </p>
          <div className="mt-8 flex gap-4">
            <div className="px-4 py-2 rounded-lg bg-white/[0.02] border border-white/5 text-[10px] text-white/40 font-mono">
              try: "Route the ESP32 differential pairs"
            </div>
          </div>
        </div>
      )}

      <canvas
        ref={canvasRef}
        width={1000}
        height={800}
        className="w-full h-full cursor-crosshair relative z-10"
      />
    </div>
  );
}
