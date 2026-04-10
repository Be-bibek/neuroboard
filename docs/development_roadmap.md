# NeuroBoard Phase 2 Development Roadmap

This roadmap outlines the milestones for transitioning NeuroBoard into an industry-grade, netlist-driven AI PCB design platform.

## Milestone 1: Schematic Automation (SKiDL Integration)
**Goal:** Programmatic generation of electrically correct netlists.
- [ ] **1.1 Component Library Wrapper:** Create a Python abstraction layer for mapping high-level intents (e.g., "Add RPi GPIO") to SKiDL/KiCad footprints.
- [ ] **1.2 Reference HAT Schematic:** Implement a reference template for the Raspberry Pi AI HAT+ core (M.2, Header, EEPROM).
- [ ] **1.3 Netlist Exporter:** Automated generation of `.net` files for handoff to the routing engine.

## Milestone 2: Netlist-Driven Routing Core
**Goal:** Transform the Rust router into a net-aware solver.
- [ ] **2.1 IPC Net Explorer:** Upgrade the IPC Client to map physical pads to electrical net names in real-time.
- [ ] **2.2 Pad-to-Pad Solver:** Update the Rust routing logic to accept net codes as primary inputs rather than arbitrary coordinates.
- [ ] **2.3 Differential Pair Logic Fix:** Ensure net-based pairs (e.g., `PCIE_TX_P/N`) are automatically detected and routed with length-matching constraints.

## Milestone 3: Physics-Aware Validation (SI/PI)
**Goal:** Integrate simulation-driven feedback.
- [ ] **3.1 scikit-rf SI Analysis:** Fully integrate S-parameter simulation to validate high-speed signal reflections.
- [ ] **3.2 PySpice PDN Analysis:** Implement IR-drop analysis for high-current rails (5V/3.3V) feeding the M.2 slot.
- [ ] **3.3 Active Optimization:** Feed simulation results back to the router to adjust trace widths/gaps dynamically.

## Milestone 4: Agentic Orchestration (LangGraph)
**Goal:** Multi-agent collaboration for complex design tasks.
- [ ] **4.1 Agent Designer:** Implement deterministic agents for Placement, Routing, SI, PI, and DFM.
- [ ] **4.2 Graph Logic:** Define the LangGraph state transitions for iterative "Design -> Simulate -> Correct" loops.
- [ ] **4.3 Error Recovery:** Implement autonomous correction for DRC/SI violations without user intervention.

## Milestone 5: Platform & UI (Tauri)
**Goal:** Transition to a full-stack graphical experience.
- [ ] **5.1 REST API Backend:** Expose the pipeline via FastAPI for frontend consumption.
- [ ] **5.2 Tauri Workspace:** Create the iterative graphical interface for design review and real-time board mirroring.
- [ ] **5.3 Live Debugger:** Visualization of routing corridors and simulation heatmaps directly in the UI.

## Timeline
| Milestone | Duration | Key Deliverable |
|-----------|----------|-----------------|
| M1: Schematics | 2 Weeks | SKiDL-generated HAT schematic |
| M2: Netlist Routing | 3 Weeks | Net-guided traces in KiCad |
| M3: Simulation | 3 Weeks | SI/PI validation reports |
| M4: Agents | 4 Weeks | LangGraph autonomous corrections |
| M5: UI | Ongoing | Tauri Desktop Application |
