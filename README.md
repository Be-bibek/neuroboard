# NeuroBoard

> **An Intelligent, Netlist-Driven PCB Design Platform using KiCad 10 Native IPC**

![Python](https://img.shields.io/badge/Python-3.x-blue.svg)
![Rust](https://img.shields.io/badge/Rust-High%20Performance-orange.svg)
![KiCad](https://img.shields.io/badge/KiCad-10.0-purple.svg)
![Status](https://img.shields.io/badge/Status-Phase%202-brightgreen.svg)

---

## 📖 Overview

NeuroBoard is an industry-grade PCB design platform that bridges the gap between AI intent and professional hardware engineering. Transitioning into **Phase 2**, NeuroBoard has evolved from a simple geometry router into a **netlist-driven compiler**. It programmatically generates schematics, simulates signal/power integrity, and interacts with KiCad 10 in real-time via a native IPC bridge.

Our primary goal: **Autonomous generation of complex hardware, starting with the Raspberry Pi AI HAT+ with Hailo-8 acceleration.**

---

## ⚡ Key Features (Phase 2 - Netlist-Driven)

### 🏗️ Intelligent Architecture
- 🌐 **Native KiCad 10 IPC**: Direct RAM-to-RAM synchronization using `api.sock`. No more file reloads or rescue cycles.
- 📐 **Netlist-Driven Routing**: Routes are derived from electrical connectivity (Schematic -> Netlist -> PCB), ensuring production-grade correctness.
- 🧠 **Agentic Orchestration**: Uses **LangGraph** to coordinate specialized agents for placement, routing, SI, PI, and compliance.

### 🛣️ Advanced Routing
- 🦀 **Rust Core Router**: High-performance A* pathfinding and geometric solving with Cavalier Contours.
- 🔀 **Diff-Pair Symmetry**: Strict 100 Ω differential impedance matching with <0.1mm length matching/skew control.
- 🛣️ **Topology Constraints**: Enforced 45° routing, hierarchical bus corridor management, and obstacle-aware avoidance.

### 🧪 Physics & Validation
- 📡 **Signal Integrity (scikit-rf)**: S-parameter (S11/S21) simulation for high-speed PCIe gen 3/4 validation.
- ⚡ **Power Integrity (PySpice)**: NGSpice-backed IR-drop analysis and PDN optimization for high-current AI accelerators.
- ✅ **Automated DRC/DFM**: Real-time 2D/3D collision detection and manufacturability checks.

---

## 🏗️ The Phase 2 Workflow

```text
[ User Intent ] 
      |
      v
[ AI Schematic Gen ] -> (SKiDL) -> [ Netlist (.net) ]
      |                                  |
      v                                  v
[ Placement Agent ] <------- [ IPC RAM Sync ] ------> [ KiCad 10 Editor ]
      |                                  |
      v                                  v
[ Rust Geometry Core ] <---- [ Net-Guided Routing ]
      |
      v
[ SI & PDN Validation ] -> (scikit-rf / PySpice)
      |
      v
[ Final Native Commit ] -> (IPC: push_commit)
```

---

## 🛠️ Technology Stack

- **Orchestration**: Python 3.x, LangGraph, FastAPI
- **Routing Engine**: Rust (PyO3 bindings)
- **Schematic Engine**: SKiDL
- **Simulations**: scikit-rf, PySpice (NGSpice)
- **CAD Bridge**: KiCad 10 Native IPC (`kicad-python`)
- **Frontend (Coming Soon)**: Tauri + React

---

## 🚀 Getting Started

### 1. Prerequisites
- **KiCad 10.0+**
- **Rust (Cargo/rustup)**
- **Python 3.12+**
- **NGSpice** (for PDN simulation)

### 2. Installation
```bash
git clone https://github.com/Be-bibek/neuroboard.git
cd neuroboard
pip install -r requirements.txt
```

### 3. Compile the Solver
```bash
cd engines/routing/rust_router
cargo build --release
# Rename target/release/grid_router.dll to grid_router.pyd (Windows)
```

---

## 📂 Project Structure

```text
NeuroBoard/
├── ai_core/               # Core Intelligence
│   ├── api/               # FastAPI Backend for Tauri
│   ├── schematic/         # SKiDL generation logic
│   ├── si/                # scikit-rf SI simulation
│   ├── power_integrity/   # PySpice PDN analysis
│   ├── system/            # IPC Client, State Manager, Orchestrator
│   └── routing/           # Topology & Bus Hierarchy
├── config/                # Central neuroboard_config.yaml
├── docs/                  # Phase 2 Architecture & Specs
├── engines/routing/       # High-performance Rust Core
└── reports/               # Unified validation JSON exports
```

---

## 🤝 Documentation & Roadmap

- [Architecture Overview](docs/phase2_architecture.md)
- [RPi HAT+ Specification](docs/rpi_hat_spec.md)
- [Development Roadmap](docs/development_roadmap.md)

---

## 📄 License

Distributed under the MIT License. See `LICENSE` for more information.

---

**Author**: Bibek ([@Be-bibek](https://github.com/Be-bibek))
