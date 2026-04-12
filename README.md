# NeuroBoard

> **An Intelligent, AI-Native PCB Compiler & Copilot using KiCad 10 Native IPC**

![Python](https://img.shields.io/badge/Python-3.x-blue.svg)
![Rust](https://img.shields.io/badge/Rust-High%20Performance-orange.svg)
![KiCad](https://img.shields.io/badge/KiCad-10.0-purple.svg)
![React](https://img.shields.io/badge/React-18.x-blue.svg)
![Tauri](https://img.shields.io/badge/Tauri-Cross%20Platform-orange.svg)
![Status](https://img.shields.io/badge/Status-Phase%208.1%20Hardened-brightgreen.svg)

---

## 📖 Overview

NeuroBoard is a production-grade PCB design platform that bridges the gap between AI intent and professional hardware engineering. Now in **Phase 8.1 (Hardened IPC-First)**, the platform has evolved into a full-stack **Prompt-to-Hardware Compiler**. It enables real-time, bidirectional synchronization between an AI design agent and the KiCad 10 UI, featuring a transactional design system with full rollback support.

### 🌐 [Live Demo & Digital Twin](https://Be-bibek.github.io/neuroboard/)
The **NeuroBoard Digital Twin** is our new flagship interface. Built with **Tauri + React + Vite**, it provides a real-time visual cockpit for monitoring AI synthesis, manual edit detection, and electrical health checks. 

[![NeuroBoard UI Preview](https://raw.githubusercontent.com/Be-bibek/neuroboard/main/docs/ui_preview.webp)](https://Be-bibek.github.io/neuroboard/)

### 📥 [Download Desktop App](https://github.com/Be-bibek/neuroboard/releases/latest)
Get the high-performance Tauri desktop application for Windows, macOS, and Linux to enable full KiCad 10 IPC integration.

---

## ⚡ Key Features (Phase 8.1 - Hardened)

### 🏗️ Production IPC-First Architecture
- 🌐 **Real-Time ki-link**: RAM-to-RAM synchronization using KiCad 10's `api.sock`.
- 🔄 **Transactional Rollback**: Atomic design commits. If synthesis fails, the canvas reverts to its previous stable state automatically.
- 🧪 **Execution Modes**: Seamless switching between `IPC` (Live UI), `Headless` (Fast Synthesis), and `Simulation` (Logic Verification).

### 🧠 Intelligent Design DSL & Orchestration
- 📐 **NeuroModule DSL**: An Atopile-inspired hardware-as-code layer with built-in electrical constraints.
- ⚡ **Constraint-Aware Synthesis**: Automatic impedance matching, voltage domain validation, and frequency-aware routing.
- 🔍 **Delta-Based Monitoring**: Detects manual user edits (moves/adds/deletes) and provides real-time AI feedback or validation triggers.

### 🛰️ Integrated Digital Twin
- 🖥️ **Tauri Desktop App**: High-performance UI for monitoring the AI's "thought process" and hardware health.
- 📡 **Live Telemetry**: Real-time ERC/DRC reporting and Signal Integrity heatmaps within the dashboard.

---

## 🏗️ Hardware DSL Workflow

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

<h2 align="center">⚒️ Tech Stack ⚒️</h2>
<br/>
<table align="center">
  <tr>
    <td align="center" width="300">
      <img src="https://media4.giphy.com/media/v1.Y2lkPTc5MGI3NjExZW9lY2xmbnFiemlrc3BpbHJpZHlhYmMwc3N0bXk5eWhsajJwemtpaCZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/78XCFBGOlS6keY1Bil/giphy.gif" width="250" alt="Coding Ninja" />
    </td>
    <td align="center">
      <h3>AI Core & Pipeline</h3>
      <img src="https://skillicons.dev/icons?i=python,rust,bash,git,github,fastapi,docker" />
      <h3>Frontend & Digital Twin (v1)</h3>
      <img src="https://skillicons.dev/icons?i=react,typescript,tailwind,vite,html,css" />
      <h3>EDA & Simulation</h3>
      <img src="https://skillicons.dev/icons?i=anaconda,numpy,vscode" />
    </td>
  </tr>
</table>

---

## 🚀 Getting Started

### 1. Prerequisites
- **KiCad 10.0+**
- **Node.js & npm** (for the Digital Twin)
- **Python 3.12+**
- **Rust (Cargo/rustup)**

### 2. Installation
```bash
git clone https://github.com/Be-bibek/neuroboard.git
cd neuroboard
pip install -r requirements.txt
```

### 3. Launch the Digital Twin
```bash
cd frontend
npm install
npm run tauri dev
```

### 4. Run the Compiler
```bash
python main.py "build schematic"
```

---

## 📂 Project Structure

```text
NeuroBoard/
├── ai_core/               # AI-First EDA Logic
│   ├── schematic/         # NeuroModule DSL & Synthesis
│   ├── system/            # IPC Client, State Manager, Orchestrator
│   └── routing/           # Route Topology & Bus Engines
├── frontend/              # Digital Twin (v1) - Tauri + React
├── config/                # Central neuroboard_config.yaml
├── docs/                  # Phase 8.1 Specs & Architecture
├── engines/               # Rust Core Router & Solvers
└── reports/               # Master Validation JSONs
```

---

## 🤝 Roadmap
- [x] Phase 8.1: Hardened IPC Architecture & Transactional Safety
- [ ] Phase 8.2: Multi-Sheet Orchestration & DataCursor Expansion
- [ ] Phase 9.0: Fully Heterogeneous Board Synthesis (Pi HAT+ Complete)

---

## 📄 License

Distributed under the MIT License. See `LICENSE` for more information.

---

**Author**: Bibek ([@Be-bibek](https://github.com/Be-bibek))
