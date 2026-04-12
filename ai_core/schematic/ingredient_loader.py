"""
ai_core/schematic/ingredient_loader.py
========================================
Phase 7: YAML Ingredient Loader

Parses a user/AI-provided YAML design specification into structured
parameters that the DynamicSchematicGenerator can pass to each NeuroModule.

YAML "Ingredients" Schema:
    design:
      name: "AI_Edge_HAT"
      version: "1.0.0"
      seed: 42

    modules:
      - type: gpio_header
      - type: sd_card
        count: 2
        voltage: "3.3V"
      - type: pcie_accelerator
        model: "hailo_8"
        lanes: 1

    constraints:
      profile: raspberry_pi_hat
      hat_compliance: true
"""

from __future__ import annotations

import logging
import random
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

log = logging.getLogger("SystemLogger")


# ---------------------------------------------------------------------------
# Board Profile Definitions
# Maps a profile ID to its hard mechanical constraints.
# Inspired by Atopile's CI/CD-first approach where profiles are declarative.
# ---------------------------------------------------------------------------

BOARD_PROFILES: Dict[str, Dict[str, Any]] = {
    "raspberry_pi_hat": {
        "board_width_mm":  65.0,
        "board_height_mm": 56.5,
        "mounting_holes": [
            {"x": 3.5,  "y": 3.5},
            {"x": 61.5, "y": 3.5},
            {"x": 3.5,  "y": 52.5},
            {"x": 61.5, "y": 52.5},
        ],
        "gpio_anchor": {"x": 29.0, "y": 3.5, "rotation": 0},
        "hat_compliance": True,
    },
    "raspberry_pi_hat_plus": {
        "board_width_mm":  65.0,
        "board_height_mm": 56.5,
        "mounting_holes": [
            {"x": 3.5,  "y": 3.5},
            {"x": 61.5, "y": 3.5},
            {"x": 3.5,  "y": 52.5},
            {"x": 61.5, "y": 52.5},
        ],
        "gpio_anchor":  {"x": 29.0, "y": 3.5, "rotation": 0},
        "pcie_fpc_anchor": {"x": 12.5, "y": 28.0, "rotation": 0},
        "hat_compliance": True,
    },
    "custom": {
        "board_width_mm":  None,    # generative — derive from component hull
        "board_height_mm": None,
        "mounting_holes":  [],
        "hat_compliance":  False,
    },
}


class IngredientLoader:
    """
    Reads a YAML design specification and produces a structured manifest
    that drives the generative schematic synthesis pipeline.

    Example usage:
        loader = IngredientLoader("specs/design.yaml")
        manifest = loader.load()
    """

    def __init__(self, spec_path: str | Path):
        self.spec_path = Path(spec_path)
        self._raw: Dict[str, Any] = {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def load(self) -> Dict[str, Any]:
        """
        Parse the YAML spec file and return a resolved, validated manifest.

        Returns:
            {
              "design":      { name, version, seed }
              "modules":     [ { type, config, count } … ]
              "constraints": { profile, hat_compliance, board_dims, … }
              "seed":        int
            }
        """
        if not self.spec_path.exists():
            raise FileNotFoundError(f"[IngredientLoader] Spec file not found: {self.spec_path}")

        with open(self.spec_path, "r", encoding="utf-8") as fh:
            self._raw = yaml.safe_load(fh) or {}

        log.info(f"[IngredientLoader] Loaded spec: {self.spec_path}")

        manifest = {
            "design":      self._parse_design(),
            "modules":     self._parse_modules(),
            "constraints": self._parse_constraints(),
        }
        manifest["seed"] = manifest["design"].get("seed", 42)

        # Seed global PRNG for deterministic netlisting
        random.seed(manifest["seed"])

        log.info(
            f"[IngredientLoader] Manifest ready — "
            f"{len(manifest['modules'])} modules, "
            f"profile='{manifest['constraints'].get('profile', 'custom')}', "
            f"seed={manifest['seed']}"
        )
        return manifest

    # ------------------------------------------------------------------
    # Parsing helpers
    # ------------------------------------------------------------------

    def _parse_design(self) -> Dict[str, Any]:
        raw = self._raw.get("design", {})
        return {
            "name":    raw.get("name", "NeuroBoard_Design"),
            "version": raw.get("version", "0.1.0"),
            "seed":    raw.get("seed", 42),
        }

    def _parse_modules(self) -> List[Dict[str, Any]]:
        raw_mods = self._raw.get("modules", [])
        modules: List[Dict[str, Any]] = []

        for entry in raw_mods:
            mod_type = entry.get("type")
            if not mod_type:
                log.warning("[IngredientLoader] Skipping module entry with no 'type'.")
                continue

            mod_config = {k: v for k, v in entry.items() if k != "type"}
            count = mod_config.pop("count", 1)

            modules.append({
                "type":   mod_type,
                "count":  count,
                "config": mod_config,
            })
            log.debug(f"[IngredientLoader] Module: {mod_type} ×{count} → {mod_config}")

        return modules

    def _parse_constraints(self) -> Dict[str, Any]:
        raw_con = self._raw.get("constraints", {})
        profile_id = raw_con.get("profile", "custom")
        profile = BOARD_PROFILES.get(profile_id, BOARD_PROFILES["custom"]).copy()

        # User YAML can override individual profile fields
        for key, val in raw_con.items():
            if key != "profile":
                profile[key] = val

        profile["profile"] = profile_id
        return profile

    # ------------------------------------------------------------------
    # Convenience: load from a raw dict (AI-generated specs, no file I/O)
    # ------------------------------------------------------------------

    @classmethod
    def from_dict(cls, spec: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process an in-memory spec dict instead of a YAML file.
        Useful when the LLM generates the spec programmatically.
        """
        import tempfile, json, yaml as _yaml
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml",
                                         delete=False, encoding="utf-8") as tmp:
            _yaml.dump(spec, tmp)
            tmp_path = tmp.name

        loader = cls(tmp_path)
        return loader.load()
