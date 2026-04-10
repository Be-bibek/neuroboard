# NeuroBoard Architecture

## Core Philosophy
NeuroBoard is a scalable, AI-driven PCB design platform built atop the KiCad 10 Native IPC API. 
It preserves the high-performance **Rust grid_router** as the central computational routing constraint engine while loosely integrating various industry-grade open-source solutions to enrich the compilation physics pipeline.

## System Components

### 1. Central Configuration (`config/neuroboard_config.yaml`)
Acts as the single point of truth across the system, guaranteeing deterministic pipeline behavior by maintaining centralized routing, impedance, and stackup constraints.

### 2. Native KiCad 10 IPC (`ai_core/system/ipc_client.py`)
Provides real-time interactive RAM hooks over Protobuf mapping for synchronous geometry read/writes preventing SSD lock deadlocks and ensuring the live editor natively replicates AI-driven updates securely.

### 3. Agentic Orchestration (`ai_core/system/orchestrator.py`)
Integrates LangGraph `StateGraph` workflows bridging strict determinism across parallel execution instances evaluating placement, topology, SI constraints, manufacturability, and Raspberry Pi HAT spec validations.

### 4. Integration Modules
- **scikit-rf** (`ai_core/si/sparameter_analysis.py`): Performs physical transmission line analysis validating `S11` and `S21` S-parameters preventing detrimental return loss over high-frequency nets (e.g. PCIe lanes).
- **PySpice** (`ai_core/power_integrity/pdn_simulator.py`): Establishes NGSpice models estimating IR drop degradation over complex PDN copper pours identifying decoupling capacitor necessity bounds.
- **NetworkX** (`ai_core/routing/bus_hierarchy.py`): Detects semantic structure topology grouping nets algorithmically prior to grid_router mapping.
- **Freerouting Hybrid** (`ai_core/integration/freerouting.py`): Pure benchmark-fallback mechanism using `kicad-cli` extracting `.dsn` files tracking differential fallback telemetry.

### 5. Unified Reporting & Frontend hooks
Provides robust REST APIs via FastAPI (`ai_core/api/server.py`) aggregating data flows down to the JSON compliant `reports/neuroboard_validation.json` directly primed for consumption by the next-gen Tauri GUI frontend architecture. 
