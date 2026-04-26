# 🧠 NeuroBoard

<p align="center">
  <img src="https://cdn.dribbble.com/userupload/25266435/file/original-80b47ebe181ae73b3afb9098bdaf594a.gif" width="600" alt="NeuroBoard Isometric PCB Animation" />
</p>

<h2 align="center">The World's First Prompt-to-Hardware Compiler</h2>

<p align="center">
  <b>Bridging AI Intent with Professional Engineering through KiCad 10 Native IPC</b>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Status-Phase%208.3%20Net--Engine-brightgreen.svg?style=for-the-badge" alt="Project Status" />
  <img src="https://img.shields.io/badge/KiCad-10.0-purple.svg?style=for-the-badge" alt="KiCad Version" />
  <img src="https://img.shields.io/badge/Python-3.12%2B-blue.svg?style=for-the-badge" alt="Python Version" />
</p>

---

## 🎯 Our Mission: Autonomous Hardware Engineering

NeuroBoard is built with a singular goal: **to transform high-level natural language intent into production-ready PCB designs.** By leveraging an agentic AI orchestration layer and a custom hardware DSL, we eliminate the traditional bottlenecks of manual schematic entry and layout.

### 🌟 Why NeuroBoard is Unique
- 🧠 **AI-Native, Not Just AI-Assisted**: NeuroBoard doesn't just suggest traces; it *synthesizes* entire functional modules from high-level specifications.
- 🔄 **Transactional Design Architecture**: The first solution to implement atomic commits and rollbacks for a live EDA canvas, ensuring your KiCad project is always in a valid state.
- 📡 **Digital Twin Syncing**: A real-time bridge that mirrors your AI's "thought process" on a high-fidelity web dashboard.
- 🏗️ **Native KiCad 10 Integration**: Direct RAM-to-RAM synchronization using `api.sock`. No more file reloads or rescue cycles.

---

## 🌐 Live Experience & Downloads

### 🚀 [Live Experience (Digital Twin)](https://Be-bibek.github.io/neuroboard/)
The interface is now fully responsive. You can interact with the **AI Reasoning** panel on the right to start autonomous PCB routing or open the **Settings** (gear icon) to configure model parameters.

👉 **[CLICK HERE FOR LIVE DEMO](https://Be-bibek.github.io/neuroboard/)**

<p align="center">
  <img src="docs/glass_dashboard.png" width="800" alt="NeuroBoard Glassmorphic Dashboard" />
</p>

<p align="center">
  <img src="docs/glass_settings.png" width="800" alt="NeuroBoard Glassmorphic Settings" />
</p>

### 📥 [Download Desktop Copilot](https://github.com/Be-bibek/neuroboard/releases/latest)
Get the production-ready Tauri application for full KiCad 10 IPC integration.

👉 **[DOWNLOAD FOR WINDOWS/MAC/LINUX](https://github.com/Be-bibek/neuroboard/releases/latest)**

---

## ✨ Features (Phase 8.1 - Hardened)

### 🏗️ Hardware DSL & Synthesis
- **NeuroModule DSL**: Define hardware like software with a native, constraint-aware DSL inspired by Atopile.
- **Neural Part Resolver**: Auto-fetch symbols and footprints from the LCSC database (3M+ parts).
- <p><img src="https://skillicons.dev/icons?i=python,rust,typescript" alt="Languages" /></p>

### 📡 Real-Time IPC Bridge (ki-link)
- **Zero-Latency RAM Sync**: Direct communication via `api.sock` for instant KiCad UI updates.
- **Transactional Pipeline**: Atomic design changes with full rollback support on DRC/ERC failure.
- <p><img src="https://skillicons.dev/icons?i=fastapi,docker,ubuntu" alt="Systems" /></p>

### 🧪 Validation & Health Checks
- **Signal Integrity**: Real-time S-parameter analysis for high-speed differential pairs.
- **Power Integrity**: NGSpice-backed PDN analysis for high-current AI accelerators.
- <p><img src="https://skillicons.dev/icons?i=anaconda,numpy,git" alt="Validation Stack" /></p>

---

<h2 align="center">⚒️ Tech Stack ⚒️</h2>
<br/>
<p align="center">
  <img src="https://skillicons.dev/icons?i=python,rust,typescript,react,tailwind,vite,fastapi,docker,ubuntu,github,vscode,postman,figma" alt="Complete Tech Stack" />
</p>

---

## 🏗️ The Compiler Pipeline

```text
[ Natural Language / Intent ] 
          |
          v
[ NeuroBoard Compiler ] <--- [ Neural Part Resolver (LCSC) ]
          |
          v
[ Hardware DSL (NeuroModule) ] ----> [ Electrical Constraints Check ]
          |
          v
[ KiCad IPC Transaction ] <-----> [ NeuroBoard Digital Twin (v1) ]
          |
          v
[ Live KiCad 10 Canvas ]
```

---

## 📂 Project Structure

```text
NeuroBoard/
├── ai_core/               # AI-First EDA Logic (Python/Rust)
│   ├── schematic/         # NeuroModule DSL & Synthesis
│   ├── system/            # IPC Client, State Manager, Orchestrator
│   └── routing/           # Route Topology & Bus Engines
├── frontend/              # Digital Twin (v2) - Tauri + React + Vite
├── config/                # Central neuroboard_config.yaml
├── docs/                  # Phase 8.1 Specs & Architecture
├── engines/               # Rust Core Router & Solvers
└── reports/               # Master Validation Reports
```

---

## 🤝 Roadmap
- [x] Phase 1-7: Core Routing & Initial IPC
- [x] Phase 8.1: Hardened IPC Architecture & Transactional Safety
- [x] Phase 8.2: End-to-End Vertical Slice (UI -> IPC -> Canvas)
- [x] Phase 8.3: Net Connection Engine & Native KiCad 10 IPC
- [ ] Phase 9.0: Fully Heterogeneous Board Synthesis (Pi HAT+ Complete)

---

**Author**: Bibek ([@Be-bibek](https://github.com/Be-bibek))
