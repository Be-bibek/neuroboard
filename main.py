"""
main.py — NeuroBoard CLI Entry Point

Usage
-----
  # Validate existing Pi HAT design (no routing):
  python main.py "Validate existing Raspberry Pi HAT design"

  # Full routing compilation pipeline:
  python main.py "Route existing design"
"""

import sys
import argparse
sys.path.insert(0, r'C:\Users\Bibek\NeuroBoard\ai_core')

from system.orchestrator import CompilerOrchestrator
from system.logger import log

# ---------------------------------------------------------------------------
# Intent classification
# ---------------------------------------------------------------------------

VALIDATE_KEYWORDS = {"validate", "validation", "check", "verify", "benchmark"}

def _is_validation_intent(intent: str) -> bool:
    """Return True when the user intent describes a validation/benchmarking run."""
    lower = intent.lower()
    return any(kw in lower for kw in VALIDATE_KEYWORDS)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="NeuroBoard EDA Compiler & Validator")
    parser.add_argument("intent", type=str, help="High-level design intent or command")
    args = parser.parse_args()

    log.info(f"Received High-Level Intent: '{args.intent}'")

    compiler = CompilerOrchestrator(
        board_path   = "pi-hat.kicad_pcb",
        config_path  = r"C:\Users\Bibek\NeuroBoard\config\design_rules.yaml",
    )

    try:
        if _is_validation_intent(args.intent):
            # ── VALIDATION MODE ────────────────────────────────────────────
            log.info("Mode: VALIDATION PIPELINE (no new routing will be generated).")
            report = compiler.run_validation_pipeline()

            overall = "PASS" if report.get("overall_pass") else "FAIL"
            log.info(f"Validation complete — Overall: {overall}")
            log.info(
                f"  HAT Compliance  : {'PASS' if report['hat_compliance']['passed'] else 'FAIL'}"
            )
            log.info(
                f"  Manufacturability: {'PASS' if report['manufacturability']['passed'] else 'FAIL'}"
            )
            pi = report["power_integrity"]
            log.info(
                f"  Power Integrity : {pi['zones_generated']} zones, "
                f"{pi['vias_stitched']} stitch vias"
            )
            log.info(
                "  Report saved  -> reports/pi_hat_validation_report.json"
            )
        else:
            # ── ROUTING MODE ───────────────────────────────────────────────
            log.info("Mode: FULL ROUTING PIPELINE.")
            src_ref = "FPC-16P-0.5mm"
            dst_ref = "CONN-SMD_APCI0107-P001A"
            mapping = {
                "2": "73",
                "3": "75",
                "5": "67",
                "6": "69",
            }
            compiler.run_full_pipeline(src_ref, dst_ref, mapping)

        log.info("System Exited Cleanly (0).")

    except Exception as exc:
        log.critical(f"FATAL DOMAIN ERROR: {exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()
