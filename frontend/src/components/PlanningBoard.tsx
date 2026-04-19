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
    <aside className="w-64 flex-shrink-0 bg-slate-900 border-r border-slate-800 flex flex-col h-full overflow-hidden">
      <div className="p-4 border-b border-slate-800 flex-shrink-0 bg-slate-950/50">
        <h3 className="text-sm font-semibold text-slate-200 uppercase tracking-widest">
          Objects Library
        </h3>
        <p className="text-[10px] text-slate-500 mt-1">Drag and drop to add</p>
      </div>
      
      <div className="flex-1 overflow-y-auto p-3 space-y-2">
        {compatibleModules.map((comp) => {
          const isAdded = !!activeModules.find(m => m.id === comp.id);
          return (
            <div
              key={comp.id}
              draggable={!isAdded}
              onDragStart={(e) => onDragStart(e, comp)}
              className={`flex items-start gap-3 p-2.5 rounded border transition-colors 
                ${isAdded 
                  ? "bg-slate-800/40 border-slate-700/50 opacity-50 cursor-not-allowed" 
                  : "bg-slate-800 border-slate-700 hover:bg-slate-700 hover:border-slate-600 cursor-grab active:cursor-grabbing"
                }`}
            >
              <div className="mt-0.5 text-lg leading-none">{comp.icon}</div>
              <div className="flex flex-col min-w-0">
                <span className="text-xs text-slate-200 font-semibold truncate leading-tight">{comp.name}</span>
                <span className="text-[10px] text-teal-400 font-mono truncate mt-0.5" title={comp.footprint}>
                  {comp.footprint.split(':')[1] || comp.footprint}
                </span>
                {isAdded && <span className="text-[9px] text-emerald-500 font-bold mt-1 uppercase tracking-wider">On Board</span>}
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
  
  const { selectedTemplate, activeModules, addModule } = useNeuroStore((s) => ({
    selectedTemplate: s.selectedTemplate,
    activeModules: s.activeModules,
    addModule: s.addModule,
  }));

  const requiredIds = selectedTemplate?.requiredModules ?? [];
  const initialNodes = buildNodes(activeModules, requiredIds);

  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);

  // Sync state if activeModules changes from generic store
  useEffect(() => {
    // Only add nodes that aren't already mapped
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

      // Calculate drop position manually due to ReactFlowProvider context needs
      // Note: Full mapping requires useReactFlow, this is a simplified drop mapping
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
      
      // Update global store
      addModule(module);
      
      // Sync to KiCad
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
    <div className="flex-1 h-full bg-slate-950 relative" ref={reactFlowWrapper}>
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
        <Background color="#334155" gap={16} size={1} />
        <Controls className="bg-slate-800 text-white border-slate-700 fill-white" />
      </ReactFlow>
    </div>
  );
}

// ── Planning Board Main ────────────────────────────────────────────────────
export function PlanningBoard() {
  const { selectedTemplate, setView } = useNeuroStore((s) => ({
    selectedTemplate: s.selectedTemplate,
    setView: s.setView,
  }));

  return (
    <div className="w-full h-full flex flex-col bg-slate-950">
      {/* Toolbar */}
      <div className="flex items-center justify-between px-5 py-3 border-b border-slate-800 bg-slate-900 flex-shrink-0 shadow-md z-10">
        <div>
          <h2 className="text-sm font-bold text-slate-100">
            {selectedTemplate ? `${selectedTemplate.icon} ${selectedTemplate.name}` : "Planning Board"}
          </h2>
          <p className="text-xs text-slate-500">
            Drag items from the Objects Library to the board.
          </p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => setView("SIDEBAR")}
            className="text-xs px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 transition-colors"
          >
            ← Back to Copilot
          </button>
          <button className="text-xs px-3 py-1.5 rounded-lg bg-teal-600 hover:bg-teal-500 text-white font-semibold shadow-lg shadow-teal-900/30 transition-colors">
            Synthesize to KiCad →
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
