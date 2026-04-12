"""
ai_core/copilot/pipeline.py
=============================
The Copilot Orchestration Pipeline.

Connects all Phase 5 modules in the correct order:
  1. IntentParser       → structured spec
  2. ComponentIntelligence → component manifest
  3. LibraryFetcher     → ensure assets are local
  4. DynamicGenerator   → SKiDL netlist
  5. NetlistManager     → parse & validate
  6. (Hands off to Phase 2 placement/routing pipeline)
"""

import logging
import os
from pathlib import Path
from typing import Dict, Any

from copilot.intent_parser import IntentParser
from copilot.component_intelligence import ComponentIntelligence
from copilot.library_fetcher import LibraryFetcher
from schematic.dynamic_generator import DynamicSchematicGenerator
from netlist.netlist_manager import NetlistManager

log = logging.getLogger("SystemLogger")

REPO_ROOT    = Path(__file__).resolve().parent.parent.parent
REPORTS_DIR  = REPO_ROOT / "reports"
NETLIST_PATH = str(REPO_ROOT / "pi_hat.net")


class CopilotPipeline:
    """
    End-to-end AI Copilot Pipeline.

    Stage 1  — Parse:      NLP → structured spec
    Stage 2  — Suggest:    spec → component manifest (returned to UI for confirmation)
    Stage 3  — Fetch:      download/verify symbols & footprints
    Stage 4  — Schematic:  generate SKiDL netlist from confirmed manifest
    Stage 5  — Validate:   parse netlist, confirm connectivity
    """

    def __init__(self):
        self.intent_parser  = IntentParser()
        self.comp_intel     = ComponentIntelligence()
        self.lib_fetcher    = LibraryFetcher()
        self.schematic_gen  = DynamicSchematicGenerator()

    # ------------------------------------------------------------------ #
    #  Stage 1+2: Parse prompt and suggest components                     #
    # ------------------------------------------------------------------ #

    def parse_and_suggest(self, prompt: str) -> Dict[str, Any]:
        """
        Called immediately when user submits a Copilot prompt.
        Returns spec + component suggestions without generating anything.
        Fast — no network calls.
        """
        try:
            spec      = self.intent_parser.parse(prompt)
            manifest  = self.comp_intel.suggest_components(spec)

            return {
                "stage": "suggestion",
                "status": "ok",
                "spec": {
                    "form_factor":   spec["form_factor"]["id"],
                    "board_size":    f"{spec['constraints'].get('board_width_mm', 65)}mm x "
                                     f"{spec['constraints'].get('board_height_mm', 56.5)}mm",
                    "accelerator":   spec["accelerator"]["id"] if spec.get("accelerator") else None,
                    "interfaces":    spec.get("interfaces", []),
                    "features":      [f["id"] for f in spec.get("features", [])],
                },
                "bom_preview": manifest["bom_preview"],
                "component_count": manifest["total_count"],
                "warnings": manifest.get("warnings", []),
                "_internal_spec": spec,
                "_internal_manifest": manifest,
            }
        except Exception as e:
            log.error(f"[CopilotPipeline] parse_and_suggest failed: {e}")
            return {"stage": "suggestion", "status": "error", "error": str(e)}

    # ------------------------------------------------------------------ #
    #  Stage 3+4+5: Confirm → fetch → generate → validate                #
    # ------------------------------------------------------------------ #

    def confirm_and_generate(
        self,
        spec: Dict,
        manifest: Dict,
        netlist_path: str = NETLIST_PATH
    ) -> Dict[str, Any]:
        """
        Called after the user confirms the component list.
        Runs the full schematic generation pipeline.
        """
        results: Dict[str, Any] = {
            "stage": "generation",
            "status": "ok",
            "steps": {},
        }

        # — Step 3: Library Fetch ————————————————————————————————————
        log.info("[CopilotPipeline] Stage 3: Fetching libraries...")
        try:
            fetch_report = self.lib_fetcher.fetch_manifest(manifest.get("components", []))
            results["steps"]["library_fetch"] = {
                "status": "ok",
                "cached": len(fetch_report["cached"]),
                "fetched": len(fetch_report["fetched"]),
                "missing": fetch_report["missing"],
            }
        except Exception as e:
            log.warning(f"[CopilotPipeline] Library fetch non-fatal error: {e}")
            results["steps"]["library_fetch"] = {"status": "warning", "error": str(e)}

        # — Step 4: Schematic Generation ——————————————————————————————
        log.info("[CopilotPipeline] Stage 4: Generating SKiDL schematic...")
        try:
            os.makedirs(REPORTS_DIR, exist_ok=True)
            gen_result = self.schematic_gen.generate(manifest, netlist_path)
            results["steps"]["schematic"] = gen_result
            if not gen_result.get("success"):
                results["status"] = "failed"
                results["error"] = gen_result.get("error", "Schematic generation failed")
                return results
        except Exception as e:
            log.error(f"[CopilotPipeline] Schematic generation error: {e}")
            results["status"] = "failed"
            results["error"] = str(e)
            return results

        # — Step 5: Netlist Validation ————————————————————————————————
        log.info("[CopilotPipeline] Stage 5: Validating netlist...")
        try:
            nm = NetlistManager(netlist_path)
            results["steps"]["netlist_validation"] = {
                "status": "ok",
                "net_count": len(nm.nets),
                "diff_pairs": nm.diff_pairs,
                "power_nets": nm.power_nets,
            }
        except Exception as e:
            log.warning(f"[CopilotPipeline] Netlist validation warning: {e}")
            results["steps"]["netlist_validation"] = {"status": "warning", "error": str(e)}

        results["netlist_path"] = netlist_path
        results["ready_for_placement"] = results.get("status") == "ok"

        log.info(f"[CopilotPipeline] Generation complete. "
                 f"status={results['status']}, netlist={netlist_path}")
        return results
