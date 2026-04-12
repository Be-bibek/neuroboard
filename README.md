# 🧠 NeuroBoard

<p align="center">
  <img src="https://media4.giphy.com/media/v1.Y2lkPTc5MGI3NjExZW9lY2xmbnFiemlrc3BpbHJpZHlhYmMwc3N0bXk5eWhsajJwemtpaCZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/78XCFBGOlS6keY1Bil/giphy.gif" width="300" alt="NeuroBoard Logo Animation" />
</p>

<h3 align="center">The World's First Prompt-to-Hardware Compiler</h3>

<p align="center">
  <b>Bridging AI Intent with Professional Engineering through KiCad 10 Native IPC</b>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Status-Phase%208.1%20Hardened-brightgreen.svg?style=for-the-badge" alt="Project Status" />
  <img src="https://img.shields.io/badge/KiCad-10.0-purple.svg?style=for-the-badge" alt="KiCad Version" />
  <img src="https://img.shields.io/badge/Python-3.12%2B-blue.svg?style=for-the-badge" alt="Python Version" />
</p>

---

## 🎯 Our Mission: Autonomous Hardware Engineering

NeuroBoard is built with a singular goal: **to transform high-level natural language intent into production-ready PCB designs.** By leveraging an agentic AI orchestration layer and a custom hardware DSL, we eliminate the traditional bottlenecks of manual schematic entry and layout.

### 🌟 Why NeuroBoard is Unique
- **AI-Native, Not Just AI-Assisted**: NeuroBoard doesn't just suggest traces; it *synthesizes* entire functional modules from high-level specifications.
- **Transactional Design Architecture**: The first solution to implement atomic commits and rollbacks for a live EDA canvas, ensuring your KiCad project is always in a valid state.
- **Digital Twin Syncing**: A real-time bridge that mirrors your AI's "thought process" on a high-fidelity web dashboard.

---

## 🌐 Live Experience & Downloads

### 🚀 [Live Demo Component (Digital Twin)]
Experience the NeuroBoard interface in your browser. Monitor real-time synthesis, manual edit detection, and validation reports.

👉 **[CLICK HERE FOR LIVE DEMO](https://Be-bibek.github.io/neuroboard/)**

### 📥 [Download Desktop Copilot]
Get the production-ready Tauri application for full KiCad 10 IPC integration.

👉 **[DOWNLOAD FOR WINDOWS/MAC/LINUX](https://github.com/Be-bibek/neuroboard/releases/latest)**

---

## ✨ Features (Phase 8.1 - Hardened)

### 🏗️ Hardware DSL & Synthesis
- **NeuroModule DSL**: Define hardware like software with a native, constraint-aware DSL inspired by Atopile.
- **Neural Part Resolver**: Auto-fetch symbols and footprints from the LCSC database (3M+ parts).
- <p><img src="https://skillicons.dev/icons?i=python,rust" alt="Languages" /></p>

### 📡 Real-Time IPC Bridge (ki-link)
- **Zero-Latency RAM Sync**: Direct communication via `api.sock` for instant KiCad UI updates.
- **Transactional Pipeline**: Atomic design changes with full rollback support on DRC/ERC failure.

### 🧪 Validation & Health Checks
- **Signal Integrity**: Real-time S-parameter analysis for high-speed differential pairs.
- **Power Integrity**: NGSpice-backed PDN analysis for high-current AI accelerators.
- <p><img src="https://skillicons.dev/icons?i=anaconda,numpy,fastapi" alt="Validation Stack" /></p>

---

## 🛠️ Technology Stack

<p align="center">
  <img src="https://skillicons.dev/icons?i=python,rust,typescript,react,tailwind,vite,fastapi,docker,ubuntu,github,vscode" alt="Complete Tech Stack" />
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
├── frontend/              # Digital Twin (v1) - Tauri + React + Vite
├── config/                # Central neuroboard_config.yaml
├── docs/                  # Phase 8.1 Specs & Architecture
├── engines/               # Rust Core Router & Solvers
└── reports/               # Master Validation Reports
```

---

## 🤝 Roadmap
- [x] Phase 1-7: Core Routing & Initial IPC
- [x] Phase 8.1: Hardened IPC Architecture & Transactional Safety
- [ ] Phase 8.2: Multi-Sheet Orchestration & Targeted Routing
- [ ] Phase 9.0: Fully Heterogeneous Board Synthesis (Pi HAT+ Complete)

---

**Author**: Bibek ([@Be-bibek](https://github.com/Be-bibek))
