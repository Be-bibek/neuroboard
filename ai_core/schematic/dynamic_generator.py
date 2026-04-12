"""
ai_core/schematic/dynamic_generator.py
========================================
Phase 7: Refactored Generative Schematic Engine

Architecture:
  - Schema-First: No PCB operations until ERC passes.
  - Module-Driven: Instantiates NeuroModule subclasses dynamically from a manifest.
  - Bidirectional: Exports enhanced metadata for downstream placement + routing engines,
    and accepts "Refinement Requests" from the layout engine to update the schematic.

Flow:
    manifest (from IngredientLoader)
        ↓ _build_modules()
    NeuroModule instances (wired via SKiDL + PowerDomain)
        ↓ _run_erc()
    ERC gate → PASS: export netlist / FAIL: return diagnostics
        ↓ generate_netlist()
    Enhanced netlist dict (path + module metadata for GenerativePlacer)
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

log = logging.getLogger("SystemLogger")

# ---------------------------------------------------------------------------
# SKiDL environment (must happen before any skidl imports)
# ---------------------------------------------------------------------------
os.environ.setdefault("KICAD_SYMBOL_DIR",  r"C:\Program Files\KiCad\10.0\share\kicad\symbols")
os.environ.setdefault("KICAD8_SYMBOL_DIR", r"C:\Program Files\KiCad\10.0\share\kicad\symbols")
os.environ.setdefault("SKIDL_NOUI", "1")

try:
    from skidl import (              # type: ignore
        Net, Part, generate_netlist,
        set_default_tool, KICAD8,
        lib_search_paths, ERC, reset,
    )
    lib_search_paths[KICAD8].append(r"C:\Program Files\KiCad\10.0\share\kicad\symbols")
    SKIDL_OK = True
except ImportError:
    SKIDL_OK = False
    log.warning("[DynGen] SKiDL not installed — operating in MOCK mode.")

from .foundation import PowerDomain
from .modules import MODULE_REGISTRY
from .ingredient_loader import IngredientLoader


class DynamicSchematicGenerator:
    """
    Orchestrates the AI-driven schematic synthesis pipeline.

    Usage:
        gen = DynamicSchematicGenerator()

        # From YAML file:
        result = gen.generate_from_yaml("specs/design.yaml", "output/neuro.net")

        # From in-memory manifest dict:
        result = gen.generate(manifest, "output/neuro.net")
    """

    def __init__(self):
        self._modules:  List[Any]       = []   # instantiated NeuroModule objects
        self._metadata: List[Dict]      = []   # aggregated placement metadata

    # ------------------------------------------------------------------
    # Primary entry points
    # ------------------------------------------------------------------

    def generate_from_yaml(self, spec_path: str,
                            output_path: str = "neuroboard.net") -> Dict[str, Any]:
        """Load a YAML spec and synthesize a validated schematic."""
        loader   = IngredientLoader(spec_path)
        manifest = loader.load()
        return self.generate(manifest, output_path)

    def generate(self, manifest: Dict[str, Any],
                  output_path: str = "neuroboard.net") -> Dict[str, Any]:
        """
        Full synthesis pipeline from a pre-parsed manifest dict.

        Returns a result dict consumed by the orchestrator:
          { success, netlist_path, module_count, net_count,
            erc_warnings, erc_errors, placement_metadata,
            error (only on failure) }
        """
        if not SKIDL_OK:
            log.warning("[DynGen] SKiDL unavailable — falling back to MOCK generation.")
            return self._mock_generate(manifest, output_path)

        try:
            # ── Reset SKiDL + PowerDomain for a clean run ──
            reset()
            set_default_tool(KICAD8)
            PowerDomain.reset()
            self._modules  = []
            self._metadata = []

            # ── Phase 1: Instantiate Modules ──────────────
            log.info("[DynGen] Phase 1: Building NeuroModules...")
            self._build_modules(manifest)

            # ── Phase 2: ERC Gate ─────────────────────────
            log.info("[DynGen] Phase 2: Running Electrical Rule Check (ERC)...")
            erc_result = self._run_erc()

            if erc_result["errors"] > 0:
                log.error(
                    f"[DynGen] ❌ ERC FAILED — {erc_result['errors']} error(s). "
                    "Aborting PCB synthesis. Fix the schematic first."
                )
                return {
                    "success":    False,
                    "error":      "ERC failed — see erc_diagnostics for details.",
                    "erc_errors": erc_result["errors"],
                    "erc_diagnostics": erc_result["diagnostics"],
                    "netlist_path": None,
                    "placement_metadata": self._metadata,
                }

            # ── Phase 3: Export Netlist ────────────────────
            log.info(f"[DynGen] Phase 3: Exporting KiCad netlist → {output_path}")
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            generate_netlist(file_=output_path)

            result = {
                "success":            True,
                "netlist_path":       output_path,
                "module_count":       len(self._modules),
                "erc_warnings":       erc_result["warnings"],
                "erc_errors":         0,
                "placement_metadata": self._metadata,
            }
            log.info(
                f"[DynGen] ✅ Schematic synthesis complete — "
                f"{len(self._modules)} modules, "
                f"{erc_result['warnings']} ERC warning(s)."
            )
            return result

        except Exception as exc:
            log.exception(f"[DynGen] Fatal synthesis error: {exc}")
            return {
                "success": False,
                "error":   str(exc),
                "netlist_path": None,
                "erc_errors": -1,
                "placement_metadata": self._metadata,
            }

    # ------------------------------------------------------------------
    # Bidirectional refinement API
    # (Called by layout engine when a constraint cannot be satisfied)
    # ------------------------------------------------------------------

    def apply_refinement(self, refinement: Dict[str, Any],
                          output_path: str = "neuroboard_refined.net") -> Dict[str, Any]:
        """
        Accept a "Refinement Request" from the placement or routing engine.

        Example refinement dict:
            {
              "action": "swap_gpio_pins",
              "module": "SD_PRIMARY",
              "from_net": "SD1_DAT0",
              "to_net":   "SD1_DAT1",
              "reason":   "Crossing traces between GPIO header and M.2"
            }

        Returns the new synthesis result after re-running the pipeline.
        This is the "bidirectional" loop — schematic updates propagate to PCB.
        """
        log.info(f"[DynGen] Bidirectional refinement received: {refinement}")
        # TODO (Phase 8): Apply pin-swap, net-rename, or component-substitution
        # For now, re-synthesise the stored manifest with the logged request.
        log.warning("[DynGen] Refinement application is staged for Phase 8.")
        return {"success": False, "error": "Refinement not yet implemented — Phase 8."}

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _build_modules(self, manifest: Dict[str, Any]) -> None:
        """Instantiate NeuroModule subclasses from the manifest module list."""
        for entry in manifest.get("modules", []):
            mod_type = entry.get("type")
            config   = entry.get("config", {})
            count    = entry.get("count", 1)

            # Pass count into config so modules handle their own repetition
            config["count"] = count

            module_class = MODULE_REGISTRY.get(mod_type)
            if module_class is None:
                log.warning(f"[DynGen] Unknown module type '{mod_type}' — skipping.")
                continue

            mod_name = f"{mod_type.upper()}_{len(self._modules)+1:02d}"
            instance = module_class(name=mod_name, config=config)
            self._modules.append(instance)
            self._metadata.append(instance.summary())
            log.info(f"[DynGen] ✓ Module '{mod_name}' instantiated.")

        # Mandatory modules always added if not explicitly listed
        self._ensure_mandatory(manifest)

    def _ensure_mandatory(self, manifest: Dict[str, Any]) -> None:
        """
        Ensure that all HAT-mandatory modules are present in the synthesis.
        Inspired by Atopile's 'required' interface mechanism.
        """
        from .ingredient_loader import BOARD_PROFILES
        profile_id = manifest.get("constraints", {}).get("profile", "custom")
        if profile_id not in ("raspberry_pi_hat", "raspberry_pi_hat_plus"):
            return

        present_types = {entry.get("type") for entry in manifest.get("modules", [])}

        mandatory = {
            "gpio_header":   {},
            "hat_eeprom":    {},
            "mounting_holes": {},
        }

        for mod_type, config in mandatory.items():
            if mod_type not in present_types:
                module_class = MODULE_REGISTRY[mod_type]
                mod_name     = f"{mod_type.upper()}_AUTO"
                instance     = module_class(name=mod_name, config=config)
                self._modules.append(instance)
                self._metadata.append(instance.summary())
                log.info(f"[DynGen] Auto-added mandatory module '{mod_type}'.")

    def _run_erc(self) -> Dict[str, Any]:
        """
        Run SKiDL Electrical Rule Check.
        Returns a structured result rather than raising on warning.
        """
        if not SKIDL_OK:
            return {"errors": 0, "warnings": 0, "diagnostics": []}

        import io, contextlib
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            ERC()

        output = buf.getvalue()
        lines  = output.splitlines()

        errors   = sum(1 for ln in lines if "error" in ln.lower())
        warnings = sum(1 for ln in lines if "warning" in ln.lower())

        return {
            "errors":      errors,
            "warnings":    warnings,
            "diagnostics": lines,
        }

    def _mock_generate(self, manifest: Dict[str, Any],
                        output_path: str) -> Dict[str, Any]:
        """Fallback when SKiDL is not installed — writes a placeholder netlist."""
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        Path(output_path).write_text(
            f"; NeuroBoard Mock Netlist\n"
            f"; Design: {manifest.get('design', {}).get('name', 'unknown')}\n"
            f"; Modules: {[e.get('type') for e in manifest.get('modules', [])]}\n"
        )
        return {
            "success":    True,
            "netlist_path": output_path,
            "module_count": len(manifest.get("modules", [])),
            "erc_errors": 0,
            "erc_warnings": 0,
            "placement_metadata": [],
            "mock": True,
        }
