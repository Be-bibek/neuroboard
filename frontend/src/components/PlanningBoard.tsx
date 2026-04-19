import { useCallback } from 'react';
import ReactFlow, {
  Controls,
  Background,
  useNodesState,
  useEdgesState,
  addEdge,
  Connection,
  Edge,
  Node
} from 'reactflow';
import 'reactflow/dist/style.css';

// Mock initial nodes for the Hardware Planning Board
const initialNodes: Node[] = [
  {
    id: 'rpi-gpio',
    type: 'default',
    data: { label: 'Raspberry Pi GPIO Header' },
    position: { x: 250, y: 100 },
    style: {
      background: '#1e293b',
      color: '#f8fafc',
      border: '1px solid #334155',
      borderRadius: '8px',
      padding: '12px',
      width: 200,
    }
  },
  {
    id: 'nvme-m2',
    type: 'default',
    data: { label: 'M.2 NVMe Socket (PCIe)' },
    position: { x: 250, y: 300 },
    style: {
      background: '#1e293b',
      color: '#f8fafc',
      border: '1px solid #334155',
      borderRadius: '8px',
      padding: '12px',
      width: 200,
    }
  },
  {
    id: 'pi-hat-power',
    type: 'default',
    data: { label: '5V to 3.3V Buck Converter' },
    position: { x: 50, y: 200 },
    style: {
      background: '#1e293b',
      color: '#f8fafc',
      border: '1px solid #334155',
      borderRadius: '8px',
      padding: '12px',
      width: 180,
    }
  }
];

const initialEdges: Edge[] = [
  { id: 'e-power-nvme', source: 'pi-hat-power', target: 'nvme-m2', animated: true, style: { stroke: '#0ea5e9' } },
  { id: 'e-rpi-nvme', source: 'rpi-gpio', target: 'nvme-m2', label: 'PCIe x1' }
];

export function PlanningBoard() {
  const [nodes, , onNodesChange] = useNodesState(initialNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges);

  const onConnect = useCallback((params: Edge | Connection) => setEdges((eds) => addEdge(params, eds)), [setEdges]);

  return (
    <div className="w-full h-full flex flex-col bg-slate-950">
      <div className="p-4 border-b border-slate-800 bg-slate-900 flex justify-between items-center">
        <div>
          <h2 className="text-lg font-bold text-slate-100">Hardware Planning Board</h2>
          <p className="text-xs text-slate-400">Drag modules to define logical intent before AI synthesis.</p>
        </div>
        <button className="px-4 py-2 bg-teal-600 hover:bg-teal-500 text-white rounded font-semibold text-sm transition-colors">
          Synthesize to KiCad Canvas
        </button>
      </div>
      <div className="flex-1">
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
          <Controls className="bg-slate-800 text-white border-slate-700" />
        </ReactFlow>
      </div>
    </div>
  );
}
