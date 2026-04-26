import { useCallback, useEffect, useRef } from "react";
import ReactFlow, {
  Controls,
  Background,
  useNodesState,
  useEdgesState,
  addEdge,
  Connection,
  Edge,
  Node,
  ReactFlowProvider,
} from "reactflow";
import "reactflow/dist/style.css";
import { useNeuroStore } from "../store/useNeuroStore";
import { getCompatibleModules } from "../templates/registry";
import { sendCommand } from "../network/syncEngine";
import type { PCBModule } from "../templates/registry";

// ── Node Style helpers ─────────────────────────────────────────────────────
const NODE_BASE: React.CSSProperties = {
  background: "rgba(255, 255, 255, 0.05)",
  color: "#f8fafc",
  border: "1px solid rgba(255, 255, 255, 0.1)",
  borderRadius: "16px",
  padding: "12px 16px",
  minWidth: 160,
  fontSize: 13,
  backdropFilter: "blur(12px)",
  boxShadow: "0 10px 30px -10px rgba(0,0,0,0.5)",
  fontWeight: "600",
};

const REQUIRED_NODE: React.CSSProperties = {
  ...NODE_BASE,
  borderColor: "rgba(99, 102, 241, 0.5)",
  background: "rgba(99, 102, 241, 0.1)",
};

// ── Convert active modules to React Flow nodes ─────────────────────────────
function buildNodes(
  modules: PCBModule[],
  requiredIds: string[]
): Node[] {
  return modules.map((m, i) => ({
    id: m.id,
    type: "default",
    data: { label: `${m.icon} ${m.name}` },
    position: { x: 250 + (i % 3) * 220, y: 150 + Math.floor(i / 3) * 120 },
    style: requiredIds.includes(m.id) ? REQUIRED_NODE : NODE_BASE,
  }));
}

// ── DnD Sidebar (Objects Library) ──────────────────────────────────────────
function ObjectsLibrary() {
  const selectedTemplate = useNeuroStore((s) => s.selectedTemplate);
  const activeModules = useNeuroStore((s) => s.activeModules);
  
  const compatibleModules = selectedTemplate 
    ? getCompatibleModules(selectedTemplate.id) 
    : [];

  const onDragStart = (event: React.DragEvent, module: PCBModule) => {
    event.dataTransfer.setData("application/reactflow", JSON.stringify(module));
    event.dataTransfer.effectAllowed = "move";
  };

  return (
    <aside className="w-72 flex-shrink-0 flex flex-col h-full overflow-hidden border-r border-white/5">
      <div className="p-6 border-b border-white/5 flex-shrink-0">
        <h3 className="text-sm font-bold text-white/90 uppercase tracking-[0.2em]">
          Object Catalog
        </h3>
        <p className="text-[10px] text-white/30 mt-1.5 font-medium">Drag to instantiate on board</p>
      </div>
      
      <div className="flex-1 overflow-y-auto p-4 space-y-3 scrollbar-none">
        {compatibleModules.map((comp) => {
          const isAdded = !!activeModules.find(m => m.id === comp.id);
          return (
            <div
              key={comp.id}
              draggable={!isAdded}
              onDragStart={(e) => onDragStart(e, comp)}
              className={`flex items-start gap-4 p-4 rounded-2xl border transition-all duration-300
                ${isAdded 
                  ? "bg-white/[0.02] border-white/5 opacity-40 grayscale cursor-not-allowed" 
                  : "glass-card bg-white/[0.03] border-white/10 hover:bg-white/[0.08] hover:scale-[1.02] cursor-grab active:cursor-grabbing"
                }`}
            >
              <div className="mt-0.5 text-2xl leading-none drop-shadow-lg">{comp.icon}</div>
              <div className="flex flex-col min-w-0">
                <span className="text-xs text-white/90 font-bold truncate leading-tight tracking-tight">{comp.name}</span>
                <span className="text-[10px] text-indigo-400 font-bold truncate mt-1 uppercase tracking-wider" title={comp.footprint}>
                  {comp.footprint.split(':')[1] || comp.footprint}
                </span>
                {isAdded && (
                  <div className="flex items-center gap-1.5 mt-2">
                    <div className="w-1.5 h-1.5 rounded-full bg-emerald-500 shadow-[0_0_8px_theme('colors.emerald.500')]"></div>
                    <span className="text-[9px] text-emerald-500/80 font-bold uppercase tracking-widest">Active</span>
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </aside>
  );
}

// ── The Canvas ─────────────────────────────────────────────────────────────
function BoardCanvas() {
  const reactFlowWrapper = useRef<HTMLDivElement>(null);
  
  const selectedTemplate = useNeuroStore((s) => s.selectedTemplate);
  const activeModules = useNeuroStore((s) => s.activeModules);
  const addModule = useNeuroStore((s) => s.addModule);

  const requiredIds = selectedTemplate?.requiredModules ?? [];
  const initialNodes = buildNodes(activeModules, requiredIds);

  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);

  useEffect(() => {
    const newNodes = activeModules.filter(m => !nodes.find(n => n.id === m.id));
    if (newNodes.length > 0) {
       const mapped = buildNodes(newNodes, requiredIds);
       setNodes(nds => [...nds, ...mapped]);
    }
  }, [activeModules, nodes, requiredIds, setNodes]);

  const onConnect = useCallback(
    (params: Edge | Connection) => setEdges((eds) => addEdge(params, eds)),
    [setEdges]
  );

  const onDragOver = useCallback((event: React.DragEvent) => {
    event.preventDefault();
    event.dataTransfer.dropEffect = "move";
  }, []);

  const onDrop = useCallback(
    (event: React.DragEvent) => {
      event.preventDefault();

      const reactFlowBounds = reactFlowWrapper.current?.getBoundingClientRect();
      const rawData = event.dataTransfer.getData("application/reactflow");

      if (!rawData || !reactFlowBounds) return;

      const module = JSON.parse(rawData) as PCBModule;

      const position = {
         x: event.clientX - reactFlowBounds.left - 80,
         y: event.clientY - reactFlowBounds.top - 20,
      };

      const newNode: Node = {
        id: module.id,
        type: "default",
        position,
        data: { label: `${module.icon} ${module.name}` },
        style: requiredIds.includes(module.id) ? REQUIRED_NODE : NODE_BASE,
      };

      setNodes((nds) => [...nds, newNode]);
      addModule(module);
      
      sendCommand({
        type: "ADD_MODULE",
        payload: {
          module_id: module.id,
          footprint: module.footprint,
          template_id: selectedTemplate?.id,
          interface: module.interface,
        },
      });
      useNeuroStore.getState().appendLog(`[DnD] Added ${module.name} to layout.`);
    },
    [setNodes, addModule, selectedTemplate, requiredIds]
  );

  return (
    <div className="flex-1 h-full bg-transparent relative" ref={reactFlowWrapper}>
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onConnect={onConnect}
        onInit={(instance) => instance.fitView()}
        onDragOver={onDragOver}
        onDrop={onDrop}
        minZoom={0.2}
      >
        <Background variant={'dots' as any} gap={20} size={1} style={{ opacity: 0.05 }} />
        <Controls className="!bg-white/5 !border-white/10 !fill-white/40 !shadow-none rounded-xl overflow-hidden" />
      </ReactFlow>
    </div>
  );
}

// ── Planning Board Main ────────────────────────────────────────────────────
export function PlanningBoard() {
  const selectedTemplate = useNeuroStore((s) => s.selectedTemplate);
  const setView = useNeuroStore((s) => s.setView);

  return (
    <div className="w-full h-full flex flex-col bg-transparent">
      {/* Toolbar */}
      <div className="flex items-center justify-between px-6 py-4 border-b border-white/5 bg-white/[0.02] flex-shrink-0 z-10 backdrop-blur-md">
        <div>
          <h2 className="text-base font-bold text-white/90 tracking-tight">
            {selectedTemplate ? `${selectedTemplate.icon} ${selectedTemplate.name}` : "Planning Board"}
          </h2>
          <p className="text-[10px] text-white/40 font-medium uppercase tracking-wider mt-0.5">
            Architectural System Design & Module Mapping
          </p>
        </div>
        <div className="flex gap-3">
          <button
            onClick={() => setView("SIDEBAR")}
            className="glass-button text-[11px] px-4 py-2 border-white/10 text-white/60 hover:text-white"
          >
            ← Back
          </button>
          <button className="glass-button text-[11px] px-5 py-2 bg-indigo-600/80 hover:bg-indigo-500 text-white border-none shadow-xl shadow-indigo-500/20">
            Synthesize Board →
          </button>
        </div>
      </div>

      {/* Main Area: Library + Canvas */}
      <div className="flex flex-1 min-h-0">
        <ReactFlowProvider>
          <ObjectsLibrary />
          <BoardCanvas />
        </ReactFlowProvider>
      </div>
    </div>
  );
}
