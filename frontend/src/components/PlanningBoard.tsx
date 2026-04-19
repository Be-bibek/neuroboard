import { useCallback } from "react";
import ReactFlow, {
  Controls,
  Background,
  useNodesState,
  useEdgesState,
  addEdge,
  Connection,
  Edge,
  Node,
} from "reactflow";
import "reactflow/dist/style.css";
import { useNeuroStore } from "../store/useNeuroStore";

// ── Node Style helpers ─────────────────────────────────────────────────────
const NODE_BASE: React.CSSProperties = {
  background: "#1e293b",
  color: "#f8fafc",
  border: "1px solid #334155",
  borderRadius: "10px",
  padding: "12px 16px",
  minWidth: 160,
  fontSize: 13,
};

const REQUIRED_NODE: React.CSSProperties = {
  ...NODE_BASE,
  borderColor: "#0ea5e9",
  background: "#0c1a2e",
};

// ── Convert active modules to React Flow nodes ─────────────────────────────
function buildNodes(
  modules: { id: string; name: string; icon: string }[],
  requiredIds: string[]
): Node[] {
  return modules.map((m, i) => ({
    id: m.id,
    data: { label: `${m.icon} ${m.name}` },
    position: { x: 60 + (i % 3) * 220, y: 80 + Math.floor(i / 3) * 120 },
    style: requiredIds.includes(m.id) ? REQUIRED_NODE : NODE_BASE,
  }));
}

// ── Planning Board ─────────────────────────────────────────────────────────
export function PlanningBoard() {
  const { selectedTemplate, activeModules, setView } = useNeuroStore((s) => ({
    selectedTemplate: s.selectedTemplate,
    activeModules: s.activeModules,
    setView: s.setView,
  }));

  const requiredIds = selectedTemplate?.requiredModules ?? [];
  const initialNodes = buildNodes(activeModules, requiredIds);

  const [nodes, , onNodesChange] = useNodesState(initialNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);

  const onConnect = useCallback(
    (params: Edge | Connection) => setEdges((eds) => addEdge(params, eds)),
    [setEdges]
  );

  const isEmpty = activeModules.length === 0;

  return (
    <div className="w-full h-full flex flex-col bg-slate-950">
      {/* Toolbar */}
      <div className="flex items-center justify-between px-5 py-3 border-b border-slate-800 bg-slate-900 flex-shrink-0">
        <div>
          <h2 className="text-sm font-bold text-slate-100">
            {selectedTemplate ? `${selectedTemplate.icon} ${selectedTemplate.name}` : "Planning Board"}
          </h2>
          <p className="text-xs text-slate-500">
            Drag and connect hardware modules before synthesis.
          </p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => setView("SIDEBAR")}
            className="text-xs px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 transition-colors"
          >
            ← Back to Copilot
          </button>
          <button className="text-xs px-3 py-1.5 rounded-lg bg-teal-600 hover:bg-teal-500 text-white font-semibold transition-colors">
            Synthesize to KiCad →
          </button>
        </div>
      </div>

      {/* Canvas */}
      <div className="flex-1">
        {isEmpty ? (
          <div className="flex flex-col items-center justify-center h-full text-center">
            <span className="text-5xl mb-4">🔲</span>
            <p className="text-slate-400 font-semibold">No modules added yet</p>
            <p className="text-slate-600 text-sm mt-1">
              Use the Copilot Sidebar to add modules like "Add NVMe slot"
            </p>
          </div>
        ) : (
          <ReactFlow
            nodes={nodes}
            edges={edges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onConnect={onConnect}
            fitView
            minZoom={0.2}
          >
            <Background color="#334155" gap={16} size={1} />
            <Controls />
          </ReactFlow>
        )}
      </div>
    </div>
  );
}
