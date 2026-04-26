import ReactFlow, { Background, Controls } from 'reactflow';
import 'reactflow/dist/style.css';
import { Activity } from 'lucide-react';

const initialNodes = [
  { id: '1', position: { x: 50, y: 0 }, data: { label: 'LLM Reasoning' }, type: 'input', style: { background: 'rgba(99, 102, 241, 0.2)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '12px', color: 'white', fontSize: '10px', fontWeight: 'bold' } },
  { id: '2', position: { x: 50, y: 80 }, data: { label: 'Schematic Logic' }, style: { background: 'rgba(255, 255, 255, 0.05)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '12px', color: 'white', fontSize: '10px', fontWeight: 'bold' } },
  { id: '3', position: { x: 50, y: 160 }, data: { label: 'Semantic Placement' }, style: { background: 'rgba(255, 255, 255, 0.05)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '12px', color: 'white', fontSize: '10px', fontWeight: 'bold' } },
  { id: '4', position: { x: 50, y: 240 }, data: { label: 'Adaptive Router' }, style: { background: 'rgba(255, 255, 255, 0.05)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '12px', color: 'white', fontSize: '10px', fontWeight: 'bold' } },
  { id: '5', position: { x: 50, y: 320 }, data: { label: 'Physics Validation' }, type: 'output', style: { background: 'rgba(16, 185, 129, 0.2)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '12px', color: 'white', fontSize: '10px', fontWeight: 'bold' } },
];

const initialEdges = [
  { id: 'e1-2', source: '1', target: '2', animated: true, style: { stroke: 'rgba(99, 102, 241, 0.5)' } },
  { id: 'e2-3', source: '2', target: '3', animated: true, style: { stroke: 'rgba(255,255,255,0.2)' } },
  { id: 'e3-4', source: '3', target: '4', animated: true, style: { stroke: 'rgba(255,255,255,0.2)' } },
  { id: 'e4-5', source: '4', target: '5', animated: true, style: { stroke: 'rgba(16, 185, 129, 0.5)' } },
];

export function WorkflowGraph() {
  return (
    <div className="h-full w-full flex flex-col">
       <div className="flex items-center gap-2 mb-4 px-1">
          <Activity size={16} className="text-indigo-400" />
          <h3 className="text-sm font-bold text-white/90 tracking-tight uppercase">Agent Workflow</h3>
       </div>
       <div className="flex-1 min-h-0 relative">
          <ReactFlow 
            nodes={initialNodes} 
            edges={initialEdges} 
            fitView
            style={{ background: 'transparent' }}
          >
            <Background color="#ffffff" gap={20} size={1} opacity={0.05} />
            <Controls className="!bg-white/5 !border-white/10 !fill-white/40 !shadow-none rounded-xl overflow-hidden" />
          </ReactFlow>
       </div>
    </div>
  );
}
