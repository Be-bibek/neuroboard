# NeuroBoard

> **An Intelligent PCB Compiler & Future Agentic Digital Twin**

![Python](https://img.shields.io/badge/Python-3.x-blue.svg)
![Rust](https://img.shields.io/badge/Rust-High%20Performance-orange.svg)
![License](https://img.shields.io/badge/License-MIT-green.svg)
![Status](https://img.shields.io/badge/Status-Active%20Development-yellow.svg)

⚠️ **Active Development Notice**: NeuroBoard is currently in **Version 1** and is under active, rapid development. APIs, configuration models, and toolchains are actively being refined as we build towards our ultimate vision.

---

## 📖 Overview

NeuroBoard is an intelligent PCB compiler that transforms high-level design intents into fully routed, production-ready KiCad PCB layouts. By merging highly deterministic electrical engineering algorithms with AI-driven orchestration, it aims to automate and mathematically optimize the most complex portions of hardware drafting.

## ⚡ Key Features (Current Version - v1)

- 🧠 **AI-Assisted PCB Design Pipeline**: Transforms top-level intents directly into orchestrated routing commands.
- 📐 **Intelligent Component Placement**: Leverages Simulated Annealing algorithms to minimize wirelength and topologically align components.
- 🛣️ **Geometry & Topology-Aware Routing**: Implements pathing constraints restricting movements to rigid, industrial limits.
- 🔀 **Differential Pair Routing**: Generates perfectly parallel paired traces natively designed for minimizing transmission skew.
- 📏 **Length Matching**: Incorporates advanced phase tuning and serpentine meander array generation for trace synchronization.
- ⚡ **Physics-Aware Impedance Control**: Actively modulates trace widths and gaps dynamically by evaluating standard 4-layer copper/prepreg stackups.
- ✅ **DRC & SI Validation**: Validates clearances, spacing violations, and absolute path impedance mismatches natively.
- 🦀 **High-Performance Rust Core**: Employs rapid A* graph searching and Cavalier Contours via PyO3 rust bindings safely processing geometry.
- 🐍 **Python Orchestrator**: High-level, modular Python engine coordinating logic flow.
- 📦 **YAML Configuration**: Decoupled rules engine driven by `config/design_rules.yaml`.
- 🖥️ **Command Line Automation**: Orchestrates the entire pipeline straight from the terminal.

## 🏗️ Architecture Stack

```text
[ High-Level Design Intent ] -> CLI
           |
       +---v---+ 
       | Python| -> [ Orchestrator ] -> [ YAML Config ]
       |       | -> [ Simulated Annealing Placement ]
       |       | -> [ Length Matching / Impedance ] -> [ DRC/SI Validation ] 
       +-------+
           | (Bindings)
       +---v---+
       |  Rust | -> [ Grid A* Router Engine ]
       |       | -> [ Parallel Geometry Offset (Cavalier Contours) ]
       +-------+
           |
[ Output: pi-hat.kicad_pcb ] (Native KiCad Layout)
```

## 🛠️ Technology Stack

- **Core Logic & Orchestration**: Python 3
- **Routing & Pathfinding Operations**: Rust (PyO3, cavalier_contours)
- **Geometry Processing**: Shapely (Python)
- **Configuration Parsing**: YAML
- **EDA Target**: KiCad (.kicad_pcb structural API)

## 🚀 Installation Instructions

1. **Clone the Repository**
   ```bash
   git clone https://github.com/Be-bibek/neuroboard.git
   cd neuroboard
   ```

2. **Install Python Dependencies**
   ```bash
   pip install shapely pyyaml networkx
   ```

3. **Compile the Rust Engine**
   Ensure you have Rust and Cargo installed via rustup.
   ```bash
   cd engines/routing/rust_router
   cargo build --release
   # Move/Rename the compiled .dll/.so to grid_router.pyd (Windows) or grid_router.so (Linux)
   ```

## 💻 Usage Example

Execute the comprehensive AI compiling pipeline natively through the CLI:

```bash
python main.py "Design a PCIe interface"
```

## 🔄 Example Workflow

1. **Initialization**: Parser absorbs intent and loads board stackup rules (`config/design_rules.yaml`).
2. **AI Placement**: Simulated Annealing groups components locally to minimize cross-talk and transmission distances.
3. **Trace Orchestration**: Detects differential pairings and forces the Rust backend geometry offsets to construct strict trace groupings limit.
4. **Length & Phase Tuning**: Calculates mismatches and injects meander serpentines to synchronize pairs.
5. **DRC / Finalization**: Checks the array for crossover intersections and writes the geometry payloads back to the KiCad PCB natively.

## 📂 Project Structure

```bash
NeuroBoard/
├── ai_core/               # Python SI, Orchestration, Validation, Placement
│   ├── placement/         # Cost & Sim Annealing logic
│   ├── routing/           # Topology, Corridor generation, Diff pairs
│   ├── si/                # Impedance calculations & stackup models
│   ├── system/            # Error handling, Logging, Orchestrator
│   └── validation/        # DRC & SI checks
├── config/                # Global YAML design rules
├── engines/routing/       # Highly optimized Rust Core algorithms
├── main.py                # Command Line pipeline entry
└── README.md              
```

## 🔮 Roadmap / Future Work

**Transforming into an Agentic Digital Twin for PCB Manufacturing:**
- 🤖 **LangGraph Integration**: Orchestrating complex swarms of AI agents handling explicit disciplines (e.g. signal integrity agent, thermal expert agent).
- 📚 **LangChain RAG Processing**: Automating constraints natively by retrieving and interpreting component datasheet PDFs logically.
- ☁️ **AWS Bedrock Scale**: Powering enterprise-level agent execution logic into a cloud infrastructure.
- 🖥️ **Tauri + React Native Platform**: Leaving the terminal for a full iterative graphical workspace.
- 🧾 **Auto-BOM**: Direct API part fulfillment handling.
- 🏭 **Manufacturing & Analysis**: Full multi-layer Gerber generation simulation checks.
- 📡 **Live KiCad IPC**: Shifting from direct file IO hacking to a fluid KiCad Real-Time binding channel.

## 🤝 Contribution Guidelines

Contributions are incredibly welcome! As we expand from a static compiler to a multi-agent topology, there are multiple avenues for collaboration.
1. Fork the Project.
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`).
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`).
4. Push to the Branch (`git push origin feature/AmazingFeature`).
5. Open a Pull Request.

## 📄 License

Distributed under the MIT License. See `LICENSE` for more information.

## 👤 Author Information

**Bibek**  
- GitHub: [@Be-bibek](https://github.com/Be-bibek)
