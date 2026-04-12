import ReactFlow, { Background, Controls } from 'reactflow';
import 'reactflow/dist/style.css';

const initialNodes = [
  { id: '1', position: { x: 50, y: 50 }, data: { label: 'LangGraph LLM Parser' }, type: 'input' },
  { id: '2', position: { x: 50, y: 150 }, data: { label: 'SKiDL Schematic Generation' } },
  { id: '3', position: { x: 50, y: 250 }, data: { label: 'KiCad Semantic Placement' } },
  { id: '4', position: { x: 50, y: 350 }, data: { label: 'Rust Native Router' } },
  { id: '5', position: { x: 50, y: 450 }, data: { label: 'Physics Validation (SI / PDN)' }, type: 'output' },
];

const initialEdges = [
  { id: 'e1-2', source: '1', target: '2', animated: true },
  { id: 'e2-3', source: '2', target: '3', animated: true },
  { id: 'e3-4', source: '3', target: '4', animated: true },
  { id: 'e4-5', source: '4', target: '5', animated: true },
];

export function WorkflowGraph() {
  return (
    <div style={{ height: '300px', width: '100%' }} className="rounded-lg border border-slate-700 bg-slate-900 overflow-hidden">
      <ReactFlow 
        nodes={initialNodes} 
        edges={initialEdges} 
        fitView
      >
        <Background color="#334155" gap={16} />
        <Controls className="bg-slate-800 border-none fill-slate-300" />
      </ReactFlow>
    </div>
  );
}
