import { useEffect, useRef, useState } from "react";
import { Activity } from "lucide-react";

export function PCBViewer2D() {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [status, setStatus] = useState("Disconnected");
  const [hasData, setHasData] = useState(false);
  const [presence, setPresence] = useState<{label: string, x: number, y: number} | null>(null);
  const [boardState, setBoardState] = useState<any>(null);
  const [lastModifiedId, setLastModifiedId] = useState<string | null>(null);

  useEffect(() => {
    const ws = new WebSocket("ws://127.0.0.1:8000/api/v1/live_stream");

    ws.onopen = () => setStatus("IPC ACTIVE");
    ws.onclose = () => setStatus("OFFLINE");
    
    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.type === "board_update" && data.state) {
        setHasData(true);
        setBoardState(data.state);
        if (data.modified_ref) setLastModifiedId(data.modified_ref);
      }
    };

    // Task 2: Listen for presence updates from the Sidebar/Orchestrator
    const handlePresence = (e: any) => {
      setPresence(e.detail);
      setTimeout(() => setPresence(null), 3000);
    };
    window.addEventListener('ai_presence_update', handlePresence);

    return () => {
      ws.close();
      window.removeEventListener('ai_presence_update', handlePresence);
    };
  }, []);

  // Task 3: Continuous render loop for animations/glows
  useEffect(() => {
    let frame: number;
    const render = () => {
      if (boardState) drawBoard(boardState);
      frame = requestAnimationFrame(render);
    };
    render();
    return () => cancelAnimationFrame(frame);
  }, [boardState, presence, lastModifiedId]);

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
        
        const isModified = lastModifiedId === fp.ref;
        
        // Task 3: Modified component glow
        if (isModified) {
          ctx.shadowBlur = 15;
          ctx.shadowColor = "rgba(167, 139, 250, 0.6)";
        }
        
        ctx.fillStyle = isModified ? "rgba(167, 139, 250, 0.2)" : "rgba(255, 255, 255, 0.1)";
        ctx.strokeStyle = isModified ? "rgba(167, 139, 250, 0.5)" : "rgba(255, 255, 255, 0.2)";
        ctx.lineWidth = 1;
        ctx.fillRect(x - 6, y - 6, 12, 12);
        ctx.strokeRect(x - 6, y - 6, 12, 12);
        
        ctx.shadowBlur = 0; // Reset
        
        ctx.fillStyle = isModified ? "#a78bfa" : "rgba(255, 255, 255, 0.9)";
        ctx.font = "bold 9px Inter, sans-serif";
        ctx.textAlign = "center";
        ctx.fillText(fp.ref, x, y - 10);
      });
    }

    // Task 2: AI Presence Overlay Rendering
    if (presence) {
      const px = presence.x * SCALE + OFFSET_X - 150;
      const py = presence.y * SCALE + OFFSET_Y - 100;

      // Glowing cursor
      ctx.beginPath();
      ctx.arc(px, py, 15 + Math.sin(Date.now() / 200) * 5, 0, Math.PI * 2);
      ctx.fillStyle = "rgba(167, 139, 250, 0.15)";
      ctx.fill();
      
      ctx.strokeStyle = "rgba(167, 139, 250, 0.4)";
      ctx.setLineDash([5, 5]);
      ctx.lineWidth = 1.5;
      ctx.stroke();
      ctx.setLineDash([]);

      // Floating Label
      ctx.fillStyle = "rgba(10, 10, 12, 0.85)";
      ctx.roundRect?.(px + 20, py - 12, ctx.measureText(presence.label).width + 24, 24, 8);
      ctx.fill();
      
      ctx.fillStyle = "#fff";
      ctx.font = "bold 10px Inter, sans-serif";
      ctx.textAlign = "left";
      ctx.fillText(presence.label, px + 32, py + 4);
      
      // Draw a line from cursor to label
      ctx.beginPath();
      ctx.moveTo(px + 10, py);
      ctx.lineTo(px + 20, py);
      ctx.strokeStyle = "rgba(167, 139, 250, 0.5)";
      ctx.stroke();
    }
  };

  return (
    <div className="flex flex-col h-full bg-transparent overflow-hidden relative group">
      {/* Overlay Status: Task 4 Enhancement */}
      <div className="absolute top-4 left-4 z-20 flex items-center gap-2 px-4 py-2 rounded-full bg-black/40 border border-white/10 backdrop-blur-2xl shadow-[0_0_20px_rgba(0,0,0,0.5)] group-hover:border-emerald-500/30 transition-all duration-500">
        <div className={`relative flex items-center justify-center w-2.5 h-2.5`}>
          <div className={`absolute inset-0 rounded-full ${status === "IPC ACTIVE" ? "bg-emerald-400" : "bg-rose-400"} ${status === "IPC ACTIVE" ? "animate-ping opacity-75" : ""}`} />
          <div className={`relative w-1.5 h-1.5 rounded-full ${status === "IPC ACTIVE" ? "bg-emerald-400 shadow-[0_0_8px_rgba(52,211,153,0.8)]" : "bg-rose-400"}`} />
        </div>
        <span className="text-[10px] font-bold text-white/80 uppercase tracking-widest">{status}</span>
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
