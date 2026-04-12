"""
ai_core/placement/semantic_placement.py
=========================================
Constraint-Driven Semantic Placement Engine — Phase 6

Enforces Raspberry Pi HAT+ mechanical and electrical constraints:
  - Board: 65.0 mm × 56.5 mm
  - M2.5 Mounting holes at exact RPi spec positions
  - 40-pin GPIO Header aligned to top edge
  - EEPROM near ID_SD/ID_SC (GPIO pins 27/28)
  - M.2 connector centred for thermal/SI headroom
  - FPC PCIe connector minimising diff-pair length
  - Decoupling caps as close to their IC as possible

All coordinates are derived from config — no hardcoded positions.
"""

import time
import logging
from pathlib import Path
from typing import List, Tuple, Dict, Any

log = logging.getLogger("SystemLogger")

# ---------------------------------------------------------------------------
# Raspberry Pi HAT+ specification constants (mm, from official drawings)
# ---------------------------------------------------------------------------
HAT_SPEC = {
    "board_width_mm":  65.0,
    "board_height_mm": 56.5,
    # M2.5 mounting holes — (x, y) from board origin (bottom-left)
    "mounting_holes":  [
        (3.5,  3.5),
        (61.5, 3.5),
        (3.5,  52.5),
        (61.5, 52.5),
    ],
    # 40-pin GPIO header: pin 1 at this position, 0° rotation
    "gpio_header": {
        "position":    (29.0, 3.5),
        "rotation_deg": 0,
        "footprint":   "Connector_PinHeader_2.54mm:PinHeader_2x20_P2.54mm_Vertical",
    },
    # EEPROM: just below GPIO, near ID_SD/ID_SC (pins 27/28 → ~x=52mm from header pin 1)
    "eeprom": {
        "position":    (54.0, 11.0),
        "rotation_deg": 90,
        "footprint":   "Package_SO:SOIC-8_3.9x4.9mm_P1.27mm",
    },
    # M.2 2242 slot — centred, leaves room for PCIe FPC above and SD below
    "m2_slot": {
        "position":    (32.5, 30.0),
        "rotation_deg": 0,
        "footprint":   "Connector_PinHeader_2.54mm:PinHeader_1x04_P2.54mm_Vertical",  # placeholder
    },
    # FPC PCIe connector — lateral, minimises diff-pair trace length to M.2
    "fpc_pcie": {
        "position":    (12.5, 30.0),
        "rotation_deg": 0,
        "footprint":   "Connector_FFC-FPC:Hirose_FH12-16S-0.5SH_1x16-1MP_P0.5mm_Horizontal",
    },
    # Decoupling capacitors — scattered near power pins
    "decoupling_offsets": [(2.0, 0.0), (-2.0, 0.0), (0.0, 2.0), (0.0, -2.0)],

    # Keep-out radius around each mounting hole (mm)
    "keepout_radius_mm": 3.5,
}


class SemanticPlacer:
    """
    Intelligent placement engine that enforces HAT+ mechanical constraints
    via the KiCad 10 IPC bridge.

    Usage:
        placer = SemanticPlacer(ipc_client)
        placer.place_components()
    """

    def __init__(self, ipc_client, spec: Dict = None):
        self.ipc  = ipc_client
        self.spec = spec or HAT_SPEC

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    def place_components(self) -> bool:
        """
        Enforce all mechanical constraints on the currently loaded board.
        Returns True on success, False on failure.
        """
        if not self.ipc.board:
            if not self.ipc.connect():
                log.error("[Placement] Cannot connect to KiCad IPC.")
                return False

        log.info("[Placement] Starting constraint-driven placement...")

        # Index all footprints on the board by reference
        fp_map = self._build_footprint_map()
        log.info(f"[Placement] Found {len(fp_map)} footprints on board.")

        commit = self.ipc.begin_commit()

        try:
            self._place_gpio_header(fp_map)
            self._place_eeprom(fp_map)
            self._place_m2(fp_map)
            self._place_fpc(fp_map)
            self._place_mounting_holes(fp_map)
            self._place_decoupling_caps(fp_map)

            self.ipc.push_commit(commit, "AI Semantic Placement — HAT+ Constraints")
            log.info("[Placement] ✅ All components placed successfully.")
            return True

        except Exception as e:
            log.error(f"[Placement] Failed: {e}")
            self.ipc._safe_cancel_commit()
            return False

    # ------------------------------------------------------------------
    # Per-component placement helpers
    # ------------------------------------------------------------------

    def _place_gpio_header(self, fp_map: Dict):
        """40-pin GPIO header — top edge alignment per HAT spec."""
        for ref in self._candidates(fp_map, ["J1", "P1", "GPIO"]):
            fp = fp_map[ref]
            x, y = self.spec["gpio_header"]["position"]
            rot  = self.spec["gpio_header"]["rotation_deg"]
            self._move(fp, x, y, rot)
            log.info(f"[Placement] GPIO header ({ref}) → ({x}, {y})°{rot}")
            return
        log.warning("[Placement] No GPIO header footprint found.")

    def _place_eeprom(self, fp_map: Dict):
        """EEPROM near ID_SD/ID_SC."""
        for ref in self._candidates(fp_map, ["U1", "IC1", "EEPROM"]):
            fp = fp_map[ref]
            x, y = self.spec["eeprom"]["position"]
            rot  = self.spec["eeprom"]["rotation_deg"]
            self._move(fp, x, y, rot)
            log.info(f"[Placement] EEPROM ({ref}) → ({x}, {y})°{rot}")
            return
        log.warning("[Placement] No EEPROM footprint found.")

    def _place_m2(self, fp_map: Dict):
        """M.2 connector — central for SI and thermal headroom."""
        for ref in self._candidates(fp_map, ["J2", "M2", "HAILO"]):
            fp = fp_map[ref]
            x, y = self.spec["m2_slot"]["position"]
            rot  = self.spec["m2_slot"]["rotation_deg"]
            self._move(fp, x, y, rot)
            log.info(f"[Placement] M.2 ({ref}) → ({x}, {y})°{rot}")
            return
        log.warning("[Placement] No M.2 footprint found.")

    def _place_fpc(self, fp_map: Dict):
        """FPC PCIe connector — lateral to minimise diff-pair trace."""
        for ref in self._candidates(fp_map, ["J3", "FPC", "PCIE"]):
            fp = fp_map[ref]
            x, y = self.spec["fpc_pcie"]["position"]
            rot  = self.spec["fpc_pcie"]["rotation_deg"]
            self._move(fp, x, y, rot)
            log.info(f"[Placement] FPC PCIe ({ref}) → ({x}, {y})°{rot}")
            return
        log.warning("[Placement] No FPC connector footprint found.")

    def _place_mounting_holes(self, fp_map: Dict):
        """Place M2.5 mounting holes at exact HAT spec positions."""
        hole_refs = sorted([
            ref for ref in fp_map
            if any(k in ref.upper() for k in ["H", "MH", "HOLE"])
        ])
        positions = self.spec["mounting_holes"]
        for i, (x, y) in enumerate(positions):
            if i >= len(hole_refs):
                log.warning(f"[Placement] Only {len(hole_refs)} holes found, need 4.")
                break
            fp = fp_map[hole_refs[i]]
            self._move(fp, x, y, 0)
            log.info(f"[Placement] Mounting hole ({hole_refs[i]}) → ({x}, {y})")

    def _place_decoupling_caps(self, fp_map: Dict):
        """
        Spread decoupling caps around the EEPROM and GPIO header.
        Simple heuristic: place pairs near known IC positions.
        """
        cap_refs = sorted([
            ref for ref in fp_map
            if ref.upper().startswith("C")
        ])
        if not cap_refs:
            log.warning("[Placement] No decoupling capacitors found.")
            return

        anchor_x, anchor_y = self.spec["eeprom"]["position"]
        offsets = self.spec["decoupling_offsets"]
        for i, ref in enumerate(cap_refs[:len(offsets)]):
            dx, dy = offsets[i % len(offsets)]
            self._move(fp_map[ref], anchor_x + dx, anchor_y + dy, 0)
            log.debug(f"[Placement] Cap ({ref}) → near EEPROM offset ({dx}, {dy})")

    # ------------------------------------------------------------------
    # Utilities
    # ------------------------------------------------------------------

    def _build_footprint_map(self) -> Dict[str, Any]:
        """Collect all footprints keyed by their reference designator."""
        fp_map = {}
        try:
            for fp in self.ipc.board.get_footprints():
                ref = ""
                if getattr(fp, "reference_field", None):
                    ref = fp.reference_field.text.value
                if ref:
                    fp_map[ref] = fp
        except Exception as e:
            log.warning(f"[Placement] Could not read footprints: {e}")
        return fp_map

    def _candidates(self, fp_map: Dict, keys: List[str]) -> List[str]:
        """Return refs from fp_map that match any hint in `keys`."""
        result = []
        for ref in fp_map:
            for k in keys:
                if k.upper() in ref.upper():
                    result.append(ref)
                    break
        return result

    def _move(self, footprint, x_mm: float, y_mm: float, rot_deg: float):
        """Move a footprint to the given coordinate."""
        from kipy.geometry import Vector2  # type: ignore
        footprint.position = Vector2.from_xy_mm(x_mm, y_mm)
        footprint.orientation.degrees = rot_deg

    # ------------------------------------------------------------------
    # Simulation mode (no IPC)
    # ------------------------------------------------------------------

    def dry_run(self) -> List[Dict]:
        """
        Returns the planned placement as a list of dicts without
        touching any live board.  Useful for unit tests.
        """
        plan = []
        plan.append({
            "ref": "J1 (GPIO Header)",
            **self.spec["gpio_header"]
        })
        plan.append({
            "ref": "U1 (EEPROM)",
            **self.spec["eeprom"]
        })
        plan.append({
            "ref": "J2 (M.2 Slot)",
            **self.spec["m2_slot"]
        })
        plan.append({
            "ref": "J3 (FPC PCIe)",
            **self.spec["fpc_pcie"]
        })
        for i, (x, y) in enumerate(self.spec["mounting_holes"]):
            plan.append({
                "ref": f"H{i+1} (Mounting Hole)",
                "position": (x, y),
                "rotation_deg": 0,
            })
        return plan
