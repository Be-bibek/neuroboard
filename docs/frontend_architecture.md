# NeuroBoard Digital Twin UI Architecture

This document describes the system-level frontend architecture for NeuroBoard, designed as a Tauri-based real-time command center for the AI-driven PCB compiler.

## 1. Folder Structure

```text
frontend/
├── src/
│   ├── components/
│   │   ├── panels/
│   │   │   ├── IntentConsole/
│   │   │   ├── ExecutionGraph/
│   │   │   ├── DigitalTwin/
│   │   │   └── SystemInspector/
│   │   ├── ui/               # shadcn/ui generic components
│   │   └── layout/           # Dashboard grid & layout shell
│   ├── store/
│   │   ├── useUIStore.ts     # Ephemeral UI state (open panels, zoom)
│   │   ├── usePcbState.ts    # Normalized PCB datastore
│   │   └── usePipeline.ts    # AI execution & Intent state
│   ├── network/
│   │   ├── wamp.ts           # WebSocket/Tauri event ingestion layer
│   │   └── actions.ts        # Typed dispatch events 
│   ├── types/
│   │   ├── pcb.ts            # Interfaces for tracks, vias, modules
│   │   └── events.ts         # Server-to-Client payloads
│   ├── App.tsx
│   └── main.tsx
├── src-tauri/                # Rust backend shell
│   ├── src/
│   │   ├── main.rs
│   │   └── ipc_bridge.rs     # Routes local ZeroMQ/api.sock traffic to Tauri Emitters
└── package.json
```

## 2. Global State Model (Zustand)

We decouple the **Engine State** from the **UI State** to prevent massive re-renders when a track delta arrives.

### State Schema (Types)

```typescript
// types/pcb.ts
export type ExecutionMode = 'IPC' | 'HEADLESS' | 'SIMULATION';

export interface PcbDelta {
  type: 'COMPONENT_ADD' | 'COMPONENT_MOVE' | 'NET_ROUTED';
  payload: any;
}

export interface IntentContext {
  prompt: string;
  parsedModules: string[];
  executionStatus: 'IDLE' | 'COMPILING' | 'ROUTING' | 'VALIDATING';
  logs: string[];
}
```

### Store Implementation

```typescript
// store/usePcbState.ts
import { create } from 'zustand';

interface PcbState {
  mode: ExecutionMode;
  components: Record<string, ComponentData>;
  nets: Record<string, NetData>;
  violations: ConstraintViolation[];
  updateFromDelta: (delta: PcbDelta) => void;
  overrideConstraint: (netId: string, rule: any) => void;
}

export const usePcbState = create<PcbState>((set) => ({
  mode: 'SIMULATION',
  components: {},
  nets: {},
  violations: [],
  updateFromDelta: (delta) => set((state) => {
    // Immer-style or localized mutation
    const newComponents = { ...state.components };
    if (delta.type === 'COMPONENT_ADD') {
      newComponents[delta.payload.ref] = delta.payload;
    }
    return { components: newComponents };
  }),
  overrideConstraint: (netId, rule) => { /* Intercept via WebSocket */ }
}));
```

## 3. WebSocket Event Ingestion Layer

The UI never polls the backend directly. Instead, Tauri emits events that the React app listens for.

```typescript
// network/wamp.ts
import { listen } from '@tauri-apps/api/event';
import { usePcbState } from '../store/usePcbState';
import { usePipeline } from '../store/usePipeline';

export async function initializeEventIngestion() {
  await listen('DELTA_UPDATE', (event) => {
    const delta = event.payload as PcbDelta;
    usePcbState.getState().updateFromDelta(delta);
  });

  await listen('VALIDATION_UPDATE', (event) => {
    usePcbState.setState({ violations: event.payload.violations });
  });

  await listen('EXECUTION_STATUS', (event) => {
    usePipeline.getState().setStatus(event.payload.status);
    usePipeline.getState().appendLog(event.payload.message);
  });
}
```

## 4. The 4 Core Panels

### (A) Intent Console
The interaction nexus for the AI Copilot.

```tsx
export function IntentConsole() {
  const { prompt, logs, setPrompt, submitIntent } = usePipeline();

  return (
    <div className="flex flex-col h-full bg-slate-900 border-r">
      <div className="flex-1 overflow-y-auto font-mono text-sm">
        {logs.map(log => <LogLine msg={log} />)}
      </div>
      <CommandInput 
         value={prompt} 
         onChange={(e) => setPrompt(e.target.value)} 
         onSubmit={submitIntent} 
         placeholder="e.g. Route I2C bus with 400kHz limits..." 
      />
    </div>
  );
}
```

### (B) Execution Graph (React Flow)
Visualizes `SKiDL Schematic -> Semantic Placement -> Rust Router -> Validation`.

```tsx
import ReactFlow from 'reactflow';
import 'reactflow/dist/style.css';

export function ExecutionGraph() {
  const status = usePipeline(state => state.executionStatus);
  const nodes = useMemo(() => computeNodesFromStatus(status), [status]);

  return (
    <div className="h-64 border-b border-slate-800">
      <ReactFlow nodes={nodes} fitView>
        <Background gap={12} size={1} />
      </ReactFlow>
    </div>
  );
}
```

### (C) Digital Twin PCB Viewer
Uses generic HTML5 Canvas or an optimized library (like PixiJS) to prevent React node blow-out when rendering 10,000 trace segments.

```tsx
export function DigitalTwinCanvas() {
  const components = usePcbState(state => state.components);
  const nets = usePcbState(state => state.nets);
  const canvasRef = useRef<HTMLCanvasElement>(null);

  // We use a strict useEffect to draw directly to Canvas context.
  // This avoids React DOM overhead for the physical PCB view.
  useEffect(() => {
    const ctx = canvasRef.current?.getContext('2d');
    if (!ctx) return;
    drawPcbState(ctx, components, nets);
  }, [components, nets]);

  return <canvas ref={canvasRef} className="w-full h-full bg-slate-950" />;
}
```

### (D) System Inspector Panel
Displays constraint allocations and hierarchical data for whatever is selected in the UI.

```tsx
export function SystemInspector() {
  const selectedId = useUIStore(state => state.selectedElementId);
  const elementData = usePcbState(state => 
    state.components[selectedId] || state.nets[selectedId]
  );

  if (!elementData) return <div>Select an element to inspect</div>;

  return (
    <div className="p-4 border-l">
      <h3 className="font-bold">{elementData.name} Properties</h3>
      <dl>
        <dt>Max Freq:</dt> <dd>{elementData.constraints.maxFreq} Hz</dd>
        <dt>Impedance:</dt> <dd>{elementData.constraints.impedance} Ω</dd>
      </dl>
      <OverrideButton id={elementData.id} />
    </div>
  );
}
```

## 5. Performance Considerations
* **Zustand Selectors**: Components must subscribe to *only* the slice of state they need. `usePcbState(state => state.mode)` instead of `usePcbState()`.
* **Direct DOM / PixiJS**: Do not try to render an SVG `<line>` for every single trace via React. The Digital Twin should project data to an HTML Canvas natively.
