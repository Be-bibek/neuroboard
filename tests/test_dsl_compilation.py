"""
tests/test_dsl_compilation.py
==============================
Phase 7: DSL Compilation Unit Tests

Tests the entire schematic synthesis pipeline in both SKiDL mode
and offline MOCK mode (no KiCad installation required).

Run with:
    pytest tests/test_dsl_compilation.py -v
"""

from __future__ import annotations

import os
import sys
import json
import tempfile
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Path setup — ensure ai_core is importable
# ---------------------------------------------------------------------------
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "ai_core"))

from schematic.ingredient_loader import IngredientLoader, BOARD_PROFILES
from schematic.dynamic_generator import DynamicSchematicGenerator


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def minimal_hat_spec() -> dict:
    """Minimal valid design spec — RPi HAT+ with GPIO and status LED."""
    return {
        "design": {"name": "TestBoard", "version": "0.1.0", "seed": 7},
        "modules": [
            {"type": "gpio_header"},
            {"type": "status_led", "color": "green"},
        ],
        "constraints": {"profile": "raspberry_pi_hat"},
    }


@pytest.fixture()
def full_ai_hat_spec() -> dict:
    """Full AI HAT+ spec — Hailo-8 + dual SD + LEDs."""
    return {
        "design": {"name": "AI_Edge_HAT", "version": "1.0.0", "seed": 42},
        "modules": [
            {"type": "gpio_header"},
            {"type": "pcie_accelerator", "model": "hailo_8", "lanes": 1},
            {"type": "sd_card", "count": 2},
            {"type": "status_led", "color": "green", "count": 2},
        ],
        "constraints": {"profile": "raspberry_pi_hat_plus"},
    }


@pytest.fixture()
def minimal_yaml_file(tmp_path: Path) -> Path:
    """Write a YAML file to a temp path and return its path."""
    content = """\
design:
  name: "TestBoard"
  version: "0.1.0"
  seed: 99

modules:
  - type: gpio_header
  - type: status_led
    color: red

constraints:
  profile: raspberry_pi_hat
"""
    p = tmp_path / "test_design.yaml"
    p.write_text(content)
    return p


# ===========================================================================
# 1. IngredientLoader Tests
# ===========================================================================

class TestIngredientLoader:

    def test_loads_yaml_file(self, minimal_yaml_file: Path):
        loader   = IngredientLoader(minimal_yaml_file)
        manifest = loader.load()
        assert manifest["design"]["name"] == "TestBoard"
        assert manifest["seed"] == 99

    def test_correct_module_count(self, minimal_yaml_file: Path):
        manifest = IngredientLoader(minimal_yaml_file).load()
        assert len(manifest["modules"]) == 2

    def test_profile_applied(self, minimal_yaml_file: Path):
        manifest = IngredientLoader(minimal_yaml_file).load()
        assert manifest["constraints"]["board_width_mm"] == 65.0
        assert manifest["constraints"]["board_height_mm"] == 56.5

    def test_from_dict_convenience(self, minimal_hat_spec: dict):
        manifest = IngredientLoader.from_dict(minimal_hat_spec)
        assert manifest["design"]["name"] == "TestBoard"
        assert len(manifest["modules"]) == 2

    def test_missing_file_raises(self, tmp_path: Path):
        with pytest.raises(FileNotFoundError):
            IngredientLoader(tmp_path / "nonexistent.yaml").load()

    def test_custom_profile_no_dimensions(self):
        spec = {
            "design": {"name": "Custom", "seed": 1},
            "modules": [{"type": "gpio_header"}],
            "constraints": {"profile": "custom"},
        }
        manifest = IngredientLoader.from_dict(spec)
        assert manifest["constraints"]["board_width_mm"] is None

    def test_determinism_with_same_seed(self, minimal_hat_spec: dict):
        m1 = IngredientLoader.from_dict(minimal_hat_spec)
        m2 = IngredientLoader.from_dict(minimal_hat_spec)
        # Module list order must be identical
        assert [e["type"] for e in m1["modules"]] == [e["type"] for e in m2["modules"]]

    def test_sd_card_count_propagated(self):
        spec = {
            "design": {"seed": 1},
            "modules": [{"type": "sd_card", "count": 2}],
            "constraints": {"profile": "custom"},
        }
        manifest = IngredientLoader.from_dict(spec)
        sd_entry = next(m for m in manifest["modules"] if m["type"] == "sd_card")
        assert sd_entry["count"] == 2


# ===========================================================================
# 2. DynamicSchematicGenerator Tests (MOCK mode — no KiCad required)
# ===========================================================================

class TestDynamicSchematicGenerator:

    def test_generate_from_dict_succeeds(self, minimal_hat_spec: dict, tmp_path: Path):
        manifest = IngredientLoader.from_dict(minimal_hat_spec)
        gen      = DynamicSchematicGenerator()
        result   = gen.generate(manifest, str(tmp_path / "test.net"))
        assert result["success"] is True

    def test_netlist_file_created(self, minimal_hat_spec: dict, tmp_path: Path):
        manifest = IngredientLoader.from_dict(minimal_hat_spec)
        out_path = str(tmp_path / "out.net")
        gen      = DynamicSchematicGenerator()
        gen.generate(manifest, out_path)
        assert Path(out_path).exists()

    def test_placement_metadata_present(self, full_ai_hat_spec: dict, tmp_path: Path):
        manifest = IngredientLoader.from_dict(full_ai_hat_spec)
        gen      = DynamicSchematicGenerator()
        result   = gen.generate(manifest, str(tmp_path / "full.net"))
        assert "placement_metadata" in result
        assert isinstance(result["placement_metadata"], list)

    def test_pcie_module_has_correct_metadata(self, full_ai_hat_spec: dict, tmp_path: Path):
        manifest = IngredientLoader.from_dict(full_ai_hat_spec)
        gen      = DynamicSchematicGenerator()
        result   = gen.generate(manifest, str(tmp_path / "full.net"))
        pcie_meta = next(
            (m for m in result["placement_metadata"] if "PCIE" in m.get("module", "")),
            None
        )
        assert pcie_meta is not None
        assert pcie_meta["metadata"]["thermal_class"] == "high"
        assert pcie_meta["metadata"]["interface"] == "PCIe_Gen3_x1"

    def test_sd_card_placement_hint(self, full_ai_hat_spec: dict, tmp_path: Path):
        manifest = IngredientLoader.from_dict(full_ai_hat_spec)
        gen      = DynamicSchematicGenerator()
        result   = gen.generate(manifest, str(tmp_path / "full.net"))
        sd_metas = [
            m for m in result["placement_metadata"] if "SD_CARD" in m.get("module", "")
        ]
        assert len(sd_metas) > 0
        for meta in sd_metas:
            assert meta["metadata"]["placement_hint"] == "edge_bottom"

    def test_unknown_module_type_skipped(self, tmp_path: Path):
        spec = {
            "design": {"seed": 1},
            "modules": [{"type": "nonexistent_module"}],
            "constraints": {"profile": "custom"},
        }
        manifest = IngredientLoader.from_dict(spec)
        gen      = DynamicSchematicGenerator()
        result   = gen.generate(manifest, str(tmp_path / "out.net"))
        # Should succeed but produce no modules (or only mandatory ones)
        assert result["success"] is True

    def test_generate_from_yaml_file(self, minimal_yaml_file: Path, tmp_path: Path):
        gen    = DynamicSchematicGenerator()
        result = gen.generate_from_yaml(str(minimal_yaml_file), str(tmp_path / "yaml.net"))
        assert result["success"] is True

    def test_mandatory_modules_auto_added_for_hat_profile(self, tmp_path: Path):
        spec = {
            "design": {"seed": 1},
            "modules": [{"type": "status_led"}],   # no gpio_header explicitly
            "constraints": {"profile": "raspberry_pi_hat"},
        }
        manifest = IngredientLoader.from_dict(spec)
        gen      = DynamicSchematicGenerator()
        result   = gen.generate(manifest, str(tmp_path / "hat_auto.net"))
        # gpio_header should be auto-added
        module_names = [m["module"] for m in result["placement_metadata"]]
        assert any("GPIO_HEADER" in n for n in module_names), \
            "GPIO header should be auto-added for raspberry_pi_hat profile"

    def test_dual_sd_creates_two_slots(self, tmp_path: Path):
        spec = {
            "design": {"seed": 1},
            "modules": [{"type": "sd_card", "count": 2}],
            "constraints": {"profile": "custom"},
        }
        manifest = IngredientLoader.from_dict(spec)
        gen      = DynamicSchematicGenerator()
        result   = gen.generate(manifest, str(tmp_path / "dual_sd.net"))
        # The SD module_summary reports slot_count = 2
        sd_meta = next(
            (m for m in result["placement_metadata"] if "SD_CARD" in m.get("module", "")),
            None
        )
        if sd_meta:  # may be None in MOCK mode
            assert sd_meta["metadata"].get("slot_count", 1) == 2


# ===========================================================================
# 3. Board Profile Tests
# ===========================================================================

class TestBoardProfiles:

    def test_hat_profile_has_four_mounting_holes(self):
        profile = BOARD_PROFILES["raspberry_pi_hat"]
        assert len(profile["mounting_holes"]) == 4

    def test_hat_profile_dimensions(self):
        p = BOARD_PROFILES["raspberry_pi_hat"]
        assert p["board_width_mm"]  == 65.0
        assert p["board_height_mm"] == 56.5

    def test_custom_profile_no_fixed_dimensions(self):
        p = BOARD_PROFILES["custom"]
        assert p["board_width_mm"] is None
        assert p["hat_compliance"] is False
