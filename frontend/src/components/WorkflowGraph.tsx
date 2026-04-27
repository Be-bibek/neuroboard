import { useState, useEffect } from 'react';
import ReactFlow, { Background, Controls, Node, Edge } from 'reactflow';
import 'reactflow/dist/style.css';
import { Activity } from 'lucide-react';

const baseNodeStyle = {
  background: 'rgba(255, 255, 255, 0.05)',
  border: '1px solid rgba(255,255,255,0.1)',
  borderRadius: '12px',
  color: 'white',
  fontSize: '10px',
  fontWeight: 'bold',
  transition: 'all 0.3s ease',
};

const activeNodeStyle = {
  ...baseNodeStyle,
  background: 'rgba(99, 102, 241, 0.2)',
  border: '1px solid rgba(99, 102, 241, 0.8)',
  boxShadow: '0 0 20px rgba(99, 102, 241, 0.4)',
  transform: 'scale(1.05)',
};

const initialNodes: Node[] = [
  { id: '1', position: { x: 50, y: 0 }, data: { label: 'LLM Reasoning' }, type: 'input', style: baseNodeStyle },
  { id: '2', position: { x: 50, y: 80 }, data: { label: 'Schematic Logic' }, style: baseNodeStyle },
  { id: '3', position: { x: 50, y: 160 }, data: { label: 'Semantic Placement' }, style: baseNodeStyle },
  { id: '4', position: { x: 50, y: 240 }, data: { label: 'Adaptive Router' }, style: baseNodeStyle },
  { id: '5', position: { x: 50, y: 320 }, data: { label: 'Physics Validation' }, type: 'output', style: baseNodeStyle },
];

const initialEdges: Edge[] = [
  { id: 'e1-2', source: '1', target: '2', animated: true, style: { stroke: 'rgba(255,255,255,0.2)' } },
  { id: 'e2-3', source: '2', target: '3', animated: true, style: { stroke: 'rgba(255,255,255,0.2)' } },
  { id: 'e3-4', source: '3', target: '4', animated: true, style: { stroke: 'rgba(255,255,255,0.2)' } },
  { id: 'e4-5', source: '4', target: '5', animated: true, style: { stroke: 'rgba(255,255,255,0.2)' } },
];

export function WorkflowGraph() {
  const [nodes, setNodes] = useState<Node[]>(initialNodes);
  const [edges, setEdges] = useState<Edge[]>(initialEdges);
  const [activeIndex, setActiveIndex] = useState(0);

  useEffect(() => {
    const interval = setInterval(() => {
      setActiveIndex((prev) => (prev + 1) % 5);
    }, 2000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    setNodes((nds) =>
      nds.map((n, i) => ({
        ...n,
        style: i === activeIndex ? activeNodeStyle : baseNodeStyle,
      }))
    );

    setEdges((eds) =>
      eds.map((e, i) => ({
        ...e,
        animated: i === activeIndex,
        style: {
          stroke: i === activeIndex ? 'rgba(99, 102, 241, 0.8)' : 'rgba(255,255,255,0.2)',
          strokeWidth: i === activeIndex ? 2 : 1,
        },
      }))
    );
  }, [activeIndex]);

  return (
    <div className="h-full w-full flex flex-col">
       <div className="flex items-center gap-2 mb-4 px-1">
          <Activity size={16} className="text-indigo-400" />
          <h3 className="text-sm font-bold text-white/90 tracking-tight uppercase">Agent Workflow</h3>
       </div>
       <div className="flex-1 min-h-0 relative">
          <ReactFlow 
            nodes={nodes} 
            edges={edges} 
            fitView
            style={{ background: 'transparent' }}
          >
            <Background variant={'dots' as any} gap={20} size={1} style={{ opacity: 0.05 }} />
            <Controls className="!bg-white/5 !border-white/10 !fill-white/40 !shadow-none rounded-xl overflow-hidden" />
          </ReactFlow>
       </div>
    </div>
  );
}
