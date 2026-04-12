# NeuroBoard Frontend Architecture

The NeuroBoard frontend is a native desktop application built using **Tauri 2.0**, providing a high-performance, secure, and reactive "Command Center" for AI-driven PCB design.

## Tech Stack
- **Shell**: Tauri (Rust-based)
- **Framework**: React 18 + TypeScript
- **Styling**: TailwindCSS + shadcn/ui
- **Icons**: Lucide-react
- **Visuals**: React Flow (Execution graph), HTML5 Canvas (2D PCB Preview)
- **Communication**: Axios (REST) + WebSockets (Real-time board state)

## Core Components
1. **CommandPrompt.tsx**: Captures natural language intent and communicates with the LangGraph orchestrator.
2. **PCBViewer2D.tsx**: Renders the KiCad PCB in real-time by consuming a WebSocket stream from the Python backend.
3. **WorkflowGraph.tsx**: Visualizes the agentive execution pipeline (Schematic -> Placement -> Routing -> Validation).
4. **ValidationPanel.tsx**: Real-time display of Signal Integrity (SI), Power Delivery (PDN), and DRC metrics.
5. **ComponentLibrary.tsx**: Managed list of AI-selected and user-specified components.

## Communication Logic
### REST Endpoints (FastAPI)
- `POST /api/v1/copilot/prompt`: Sends the user's NLP intent to the backend.
- `GET /api/v1/validation/report`: Fetches the latest physics-aware validation JSON.

### WebSocket (FastAPI)
- `WS /api/v1/live_stream`: Receives continuous JSON updates of the KiCad board state (tracks, footprints, vias) for the digital twin viewer.

## Directory Structure
```
frontend/
├── src/
│   ├── components/      # UI Blocks (CommandPrompt, PCBViewer, etc.)
│   ├── lib/             # Utilities (cn helper)
│   ├── App.tsx          # Main Layout
│   ├── main.tsx         # Entry Point
│   └── index.css        # Global Styles/Tailwind
├── src-tauri/          # Rust Desktop logic
```

## Setup & Development
1. **Start Backend**: `python ai_core/api/server.py`
2. **Start Frontend (Web)**: `cd frontend && npm run dev`
3. **Start Native Desktop**: `cd frontend && npm run tauri dev`
