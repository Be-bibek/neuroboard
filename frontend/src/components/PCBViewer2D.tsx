import { useEffect, useRef, useState } from "react";

export function PCBViewer2D() {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [status, setStatus] = useState("Disconnected");

  useEffect(() => {
    const ws = new WebSocket("ws://127.0.0.1:8000/api/v1/live_stream");

    ws.onopen = () => setStatus("Connected (Live IPC Stream)");
    ws.onclose = () => setStatus("Disconnected");
    
    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.type === "board_update" && data.state) {
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

    // Very basic coordinate scaling for generic bounding boxes
    const SCALE = 5;
    const OFFSET_X = canvas.width / 2;
    const OFFSET_Y = canvas.height / 2;

    ctx.clearRect(0, 0, canvas.width, canvas.height);

    // Draw Tracks
    if (state.tracks) {
      ctx.strokeStyle = "#10b981"; // Emerald
      ctx.lineWidth = 1.5;
      state.tracks.forEach((track: any) => {
        ctx.beginPath();
        // Assume KiCad coordinates might be centered differently, adding offset manually
        ctx.moveTo(track.start[0] * SCALE + OFFSET_X - 150, track.start[1] * SCALE + OFFSET_Y - 100);
        ctx.lineTo(track.end[0] * SCALE + OFFSET_X - 150, track.end[1] * SCALE + OFFSET_Y - 100);
        ctx.stroke();
      });
    }

    // Draw Footprints (Mock bounding rects)
    if (state.footprints) {
      ctx.fillStyle = "rgba(59, 130, 246, 0.4)"; // Transparent Blue
      ctx.strokeStyle = "#3b82f6";
      ctx.lineWidth = 1;
      
      state.footprints.forEach((fp: any) => {
        const x = fp.x * SCALE + OFFSET_X - 150;
        const y = fp.y * SCALE + OFFSET_Y - 100;
        ctx.fillRect(x - 5, y - 5, 10, 10);
        ctx.strokeRect(x - 5, y - 5, 10, 10);
        
        ctx.fillStyle = "#e2e8f0";
        ctx.font = "10px monospace";
        ctx.fillText(fp.ref, x - 10, y - 10);
        ctx.fillStyle = "rgba(59, 130, 246, 0.4)";
      });
    }
  };

  return (
    <div className="flex flex-col h-full bg-slate-950 rounded-lg border border-slate-700 overflow-hidden relative">
      <div className="absolute top-2 left-2 px-3 py-1 bg-slate-800 rounded shadow-md text-xs font-mono text-slate-300">
        STATUS: <span className={status.includes("Connected") ? "text-emerald-400" : "text-rose-400"}>{status}</span>
      </div>
      <canvas
        ref={canvasRef}
        width={800}
        height={600}
        className="w-full h-full"
      />
    </div>
  );
}
