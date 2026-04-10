# NeuroBoard Phase 2 Architecture Definition

## 1. Core Philosophy
NeuroBoard Phase 2 pivots from a purely geometry-driven layout optimizer into a **netlist-driven, schematic-first AI PCB design platform**. Electrical correctness and intentional design start at the schematic level. The geometry optimization engine (Rust grid_router) will operate exclusively as a solver constrained by strict netlist topologies and physical placement requirements.

## 2. System Components

### 2.1 AI-Driven Schematic Generation (SKiDL)
Instead of relying on pre-existing .sch files, NeuroBoard natively generates schematics programmatically using **SKiDL**.
- Parses high-level AI directives into exact electrical pin connections.
- Automates the instantiation of:
  - 40-Pin Raspberry Pi Header
  - AT24C32 EEPROM for HAT ID
  - Power PMICs for regulated Hailo-8 power staging
  - M.2 M/E-Key connector
- Directly outputs an IPC-compliant KiCad Netlist (`.net`), locking down all electrical truths.

### 2.2 Netlist-Driven Routing constraints (Rust Engine)
The Rust computation engine (`grid_router`) transitions into a strict net-follower:
- **Netlist Awareness**: Reads the SKiDL `.net` file mapping logical traces to `fp.position` nodes dynamically via IPC.
- Maintains differential pair tuning, ensuring 45-degree topologies are strictly bound to identical electrical impedance constraints.

### 2.3 KiCad 10 IPC Orchestration (`ai_core/system/ipc_client.py`)
Provides real-time interactive RAM hooks over Protobuf Protoc bridging.
- **Bi-directional sync**: Fetches unrouted nets directly from editor state.
- Employs native `kipy.kicad` for `Board.begin_commit()` and `Board.push_commit()`.

### 2.4 Signal Integrity and Power Integrity Simulation
- **scikit-rf (`ai_core/si/sparameter_analysis.py`)**: S-Parameter validation layer. Approximates high-speed reflections across the PCIe lines.
- **PySpice (`ai_core/power_integrity/pdn_simulator.py`)**: NGSpice integration to detect power rail IR-drop along the 5V and 3.3V lines terminating to the M.2 slot.

### 2.5 Agentic Orchestration (LangGraph)
Employs LangChain's `StateGraph` model to handle the complexity pipeline:
1. `PlacementAgent`: Mechanical dimensional compliance.
2. `RoutingAgent`: Rust computational backend.
3. `SIValidator` & `PDNAgent`: Physics modeling.
4. `HATComplianceAgent`: EEPROM and boundary condition analysis.

### 2.6 Frontend Interfacing (Tauri Preparation)
Exposes the multi-agent pipeline through a FastAPI REST backend (`ai_core/api/server.py`). The eventual Tauri frontend will connect locally to manage prompts, review the netlist, and view real-time feedback visually mirrored by the active KiCad IPC context.
