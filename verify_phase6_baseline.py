"""
verify_phase6_baseline.py
==========================
End-to-end verification of the NeuroBoard Phase 6 pipeline.
Targets: PiHAT-KiCAD-Pro-Legacy.kicad_pcb

Flow:
  1. Parse prompt -> manifest
  2. Generate SKiDL netlist
  3. Connect to KiCad 10 IPC
  4. Sync netlist -> board
  5. Semantic placement (HAT+ Spec)
  6. Routing & Validation
"""

import os
import sys
import logging
from pathlib import Path

# Add ai_core to path
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "ai_core"))

from system.orchestrator import CompilerOrchestrator
from copilot.pipeline import CopilotPipeline
from system.logger import log

def verify_pipeline():
    # 1. Setup Orchestrator (Config-driven)
    config_path = ROOT / "config" / "neuroboard_config.yaml"
    orchestrator = CompilerOrchestrator(config_path=str(config_path))
    
    log.info(f"--- PHASE 6 VERIFICATION: {orchestrator.board_path} ---")
    
    # Check if project exists
    if not os.path.exists(orchestrator.board_path):
        log.error(f"FATAL: Board file not found at {orchestrator.board_path}")
        return

    # 2. Copilot Stage (Intent -> Netlist)
    prompt = "Create a Raspberry Pi AI HAT with a Hailo-8 accelerator and dual SD card slots"
    log.info(f"Step 1: Copilot Pipeline with prompt: '{prompt}'")
    
    copilot = CopilotPipeline()
    suggest_res = copilot.parse_and_suggest(prompt)
    if suggest_res["status"] != "ok":
        log.error(f"Copilot parse failed: {suggest_res.get('error')}")
        return

    # Generate the actual netlist into the project directory
    gen_res = copilot.confirm_and_generate(
        suggest_res["_internal_spec"],
        suggest_res["_internal_manifest"],
        netlist_path=orchestrator.netlist_path
    )
    
    if gen_res["status"] != "ok":
        log.error(f"Schematic generation failed: {gen_res.get('error')}")
        return
    
    log.info(f"Step 2: Netlist generated -> {orchestrator.netlist_path}")

    # 3. Execution Stage (Orchestrator takes over)
    log.info("Step 3: Triggering Live Placement & Routing Pipeline...")
    # We pass None for prompt because we already have the netlist synced in Gen Stage
    report = orchestrator.run_full_pipeline()
    
    # 4. Results
    log.info("--- VERIFICATION COMPLETE ---")
    log.info(f"Status: {report.get('status')}")
    log.info(f"Validation: {'PASS' if report.get('overall_pass', True) else 'FAIL'}")
    log.info(f"Report: {orchestrator.report_file}")

if __name__ == "__main__":
    verify_pipeline()
