import sys
import argparse
sys.path.insert(0, r'C:\Users\Bibek\NeuroBoard\ai_core')
from system.orchestrator import CompilerOrchestrator
from system.logger import log

def main():
    parser = argparse.ArgumentParser(description="NeuroBoard EDA Compiler")
    parser.add_argument("intent", type=str, help="Routing intent description")
    args = parser.parse_args()

    log.info(f"Received High-Level Intent: '{args.intent}'")

    compiler = CompilerOrchestrator(
        board_path="pi-hat.kicad_pcb", 
        config_path=r"C:\Users\Bibek\NeuroBoard\config\design_rules.yaml"
    )

    # Standard testing mapping payload topologically sorted to prevent physical F.Cu crossovers
    src_ref = "FPC-16P-0.5mm"
    dst_ref = "CONN-SMD_APCI0107-P001A"
    mapping = {
        "2": "73",
        "3": "75",
        "5": "67",
        "6": "69"
    }

    try:
        compiler.run_full_pipeline(src_ref, dst_ref, mapping)
        log.info("System Exited Cleanly (0).")
    except Exception as e:
        log.critical(f"FATAL DOMAIN ERROR: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
