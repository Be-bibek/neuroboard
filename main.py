"""
main.py — NeuroBoard CLI Entry Point (Phase 8.1 Edition)

Usage:
  python main.py "build schematic"             # Live IPC synthesis
  python main.py "validate design"             # Validation pipeline
  python main.py --preflight                   # Dependency & environment check
  python main.py --mode simulation "build schematic"  # Force simulation mode
"""

import os
import sys
import argparse

# Ensure ai_core is in the path
ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT, 'ai_core'))

from system.orchestrator import CompilerOrchestrator
from system.execution_mode import ExecutionMode
from system.logger import log


def _parse_mode(s: str) -> ExecutionMode:
    mapping = {
        "ipc":        ExecutionMode.IPC,
        "headless":   ExecutionMode.HEADLESS,
        "simulation": ExecutionMode.SIMULATION,
        "sim":        ExecutionMode.SIMULATION,
    }
    try:
        return mapping[s.lower()]
    except KeyError:
        raise argparse.ArgumentTypeError(
            f"Unknown mode '{s}'. Choose from: ipc, headless, simulation"
        )


def main():
    parser = argparse.ArgumentParser(
        description="NeuroBoard — AI-native PCB Compiler & Copilot",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    parser.add_argument(
        "intent", nargs="?", default="",
        help="High-level design intent or command"
    )
    parser.add_argument(
        "--mode", "-m", type=_parse_mode, default=None,
        metavar="MODE",
        help="Execution mode: ipc | headless | simulation  (default: auto-detect)"
    )
    parser.add_argument(
        "--preflight", action="store_true",
        help="Run dependency & environment validation then exit"
    )
    args = parser.parse_args()

    config_path = os.path.join(ROOT, "config", "neuroboard_config.yaml")
    log.info(f"--- NEUROBOARD START (Phase 8.1: IPC-First) ---")

    try:
        compiler = CompilerOrchestrator(config_path=config_path, mode=args.mode)

        # ── Preflight / environment check ─────────────────────────────
        if args.preflight:
            log.info("Mode: PREFLIGHT CHECK")
            report = compiler.preflight(strict=False)
            overall = report.get("overall", "?")
            log.info(f"[Preflight] Overall: {overall}")
            sys.exit(0 if overall in ("PASS", "WARN") else 1)

        if not args.intent:
            parser.print_help()
            sys.exit(0)

        log.info(f"Command: '{args.intent}'  |  Mode: {compiler.mode}")
        lower_intent = args.intent.lower()

        # ── Route dispatcher ──────────────────────────────────────────
        if "sync" in lower_intent and "pcb" in lower_intent:
            log.info("Mode: PCB SYNC ONLY")
            compiler.sync_pcb()

        elif "build" in lower_intent and "schematic" in lower_intent:
            log.info("Mode: LIVE SCHEMATIC SYNTHESIS")
            result = compiler.build_live_schematic()
            log.info(f"[Build] Result: {result.get('status')} | "
                     f"Parts: {result.get('parts_generated', '?')}")

        elif "validate" in lower_intent or "check" in lower_intent:
            log.info("Mode: VALIDATION PIPELINE")
            compiler.run_validation_pipeline()

        elif "preflight" in lower_intent or "env" in lower_intent:
            compiler.preflight()

        else:
            log.info("Mode: FULL GENERATIVE PIPELINE")
            compiler.run_full_pipeline(prompt=args.intent)

        log.info("--- SYSTEM EXIT CLEANLY (0) ---")

    except Exception as exc:
        log.critical(f"FATAL: {exc}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
