"""
ai_core/power_integrity/ground_plane.py
=========================================
Power Integrity Agent — Ground Plane & Via Stitching

Responsibilities
----------------
  1. Generate copper-pour zone definitions for designated GND layers.
  2. Add via-stitching along board edges and near high-speed connectors.
  3. Ensure continuous return paths for differential pairs.
  4. Emit KiCad-compatible S-expression snippets for zone fills and vias.

All outputs are deterministic (seeded geometry derived from board geometry).
"""

import math
from dataclasses import dataclass, field
from typing import List, Tuple, Optional
from system.logger import log


# ---------------------------------------------------------------------------
# Design constants
# ---------------------------------------------------------------------------

STITCH_VIA_DRILL_MM      = 0.30     # M2 stitch via drill
STITCH_VIA_PAD_MM        = 0.60     # Pad diameter
STITCH_EDGE_STEP_MM      = 3.0      # Spacing of edge stitching vias
STITCH_HS_RADIUS_MM      = 2.5      # Radius of stitching ring around HS connectors
STITCH_HS_STEP_DEG       = 30.0     # Angular step for connector stitching vias (deg)

GROUND_PLANE_CLEARANCE_MM = 0.20    # GND zone clearance to non-GND copper
GROUND_MIN_WIDTH_MM       = 0.15    # Minimum spoke / fill width
THERMAL_RELIEF_GAP_MM     = 0.20    # Thermal relief gap for soldering


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class StitchVia:
    x: float
    y: float
    net: str = "GND"
    drill: float = STITCH_VIA_DRILL_MM
    pad: float   = STITCH_VIA_PAD_MM

    def to_kicad_sexpr(self) -> str:
        return (
            f'  (via (at {self.x:.4f} {self.y:.4f})'
            f' (size {self.pad:.3f}) (drill {self.drill:.3f})'
            f' (layers "F.Cu" "B.Cu") (net 0))'
        )


@dataclass
class CopperZone:
    net: str
    layer: str
    polygon: List[Tuple[float, float]]
    clearance: float = GROUND_PLANE_CLEARANCE_MM
    min_width: float = GROUND_MIN_WIDTH_MM

    def to_kicad_sexpr(self) -> str:
        pts = " ".join(
            f'(xy {x:.4f} {y:.4f})' for x, y in self.polygon
        )
        return (
            f'  (zone (net 0) (net_name "{self.net}") (layer "{self.layer}")\n'
            f'    (connect_pads (clearance {self.clearance:.3f}))\n'
            f'    (min_thickness {self.min_width:.3f})\n'
            f'    (fill yes (thermal_gap {THERMAL_RELIEF_GAP_MM:.3f})'
            f' (thermal_bridge_width {self.min_width:.3f}))\n'
            f'    (polygon (pts {pts}))\n'
            f'  )'
        )


@dataclass
class PowerIntegrityReport:
    zones_generated: int = 0
    vias_stitched:   int = 0
    diff_pair_returns_ensured: int = 0
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "agent": "PowerIntegrityAgent",
            "zones_generated": self.zones_generated,
            "vias_stitched":   self.vias_stitched,
            "diff_pair_returns_ensured": self.diff_pair_returns_ensured,
            "warnings": self.warnings,
        }


# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------

class GroundPlaneAgent:
    """
    Generates ground copper zones and via stitching for a PCB layout.

    board_data keys expected:
      board_width_mm, board_height_mm
      ground_layers   : list of layer names (e.g. ["F.Cu", "B.Cu"])
      hs_connectors   : list of {"ref": …, "x": …, "y": …}
      diff_pairs      : list of [{"net_p": …, "net_n": …,
                                   "path_p": [(x,y),…],
                                   "path_n": [(x,y),…]}]
      edge_clearance_mm (optional, default GROUND_PLANE_CLEARANCE_MM)
    """

    def __init__(self):
        self.zones:  List[CopperZone] = []
        self.vias:   List[StitchVia]  = []
        self.report: PowerIntegrityReport = PowerIntegrityReport()

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    def generate(self, board_data: dict) -> PowerIntegrityReport:
        log.info("[PowerIntegrity] Starting ground plane & via-stitching generation...")
        self.zones  = []
        self.vias   = []
        self.report = PowerIntegrityReport()

        w = board_data.get("board_width_mm",  65.0)
        h = board_data.get("board_height_mm", 56.5)
        edge_clr = board_data.get("edge_clearance_mm", GROUND_PLANE_CLEARANCE_MM)

        # 1. Ground copper zones
        self._generate_ground_zones(w, h, edge_clr,
                                    board_data.get("ground_layers", ["F.Cu", "B.Cu"]))

        # 2. Board-edge via stitching
        self._stitch_board_edges(w, h, edge_clr)

        # 3. High-speed connector stitching
        for hs in board_data.get("hs_connectors", []):
            self._stitch_hs_connector(hs.get("x", 0), hs.get("y", 0))

        # 4. Differential pair return continuity
        for dp in board_data.get("diff_pairs", []):
            self._ensure_diff_pair_return(dp)

        self.report.zones_generated = len(self.zones)
        self.report.vias_stitched   = len(self.vias)

        log.info(
            f"[PowerIntegrity] Complete — "
            f"{self.report.zones_generated} zones, "
            f"{self.report.vias_stitched} stitch vias, "
            f"{self.report.diff_pair_returns_ensured} diff-pair returns."
        )
        return self.report

    # ------------------------------------------------------------------
    # KiCad export
    # ------------------------------------------------------------------

    def to_kicad_snippets(self) -> str:
        """Returns a string of KiCad S-expression snippets to append to the .kicad_pcb file."""
        lines = ["; --- NeuroBoard: Ground Planes & Via Stitching ---"]
        for z in self.zones:
            lines.append(z.to_kicad_sexpr())
        for v in self.vias:
            lines.append(v.to_kicad_sexpr())
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _generate_ground_zones(self, w: float, h: float,
                                edge_clr: float, layers: List[str]):
        """Create a board-wide GND fill polygon for each specified layer."""
        margin = edge_clr
        # Board-filling rectangle (inset by margin)
        polygon = [
            (margin,     margin),
            (w - margin, margin),
            (w - margin, h - margin),
            (margin,     h - margin),
        ]
        for layer in layers:
            zone = CopperZone(
                net="GND",
                layer=layer,
                polygon=polygon,
                clearance=GROUND_PLANE_CLEARANCE_MM,
                min_width=GROUND_MIN_WIDTH_MM,
            )
            self.zones.append(zone)
            log.info(f"[PowerIntegrity] Ground zone created on layer {layer}.")

    def _stitch_board_edges(self, w: float, h: float, edge_clr: float):
        """Place stitch vias along all 4 board edges at regular intervals."""
        step   = STITCH_EDGE_STEP_MM
        offset = edge_clr + STITCH_VIA_PAD_MM / 2

        # Bottom edge
        x = offset
        while x <= w - offset:
            self.vias.append(StitchVia(x=round(x, 4), y=round(offset, 4)))
            x += step

        # Top edge
        x = offset
        while x <= w - offset:
            self.vias.append(StitchVia(x=round(x, 4), y=round(h - offset, 4)))
            x += step

        # Left edge (excluding corners already placed)
        y = offset + step
        while y <= h - offset - step:
            self.vias.append(StitchVia(x=round(offset, 4), y=round(y, 4)))
            y += step

        # Right edge
        y = offset + step
        while y <= h - offset - step:
            self.vias.append(StitchVia(x=round(w - offset, 4), y=round(y, 4)))
            y += step

        log.info(f"[PowerIntegrity] Edge stitching: {len(self.vias)} vias added.")

    def _stitch_hs_connector(self, cx: float, cy: float):
        """
        Place stitch vias in a ring around a high-speed connector.
        This provides a low-impedance return path close to the signal source.
        """
        r    = STITCH_HS_RADIUS_MM
        step = STITCH_HS_STEP_DEG
        ang  = 0.0
        count_before = len(self.vias)

        while ang < 360.0:
            rad = math.radians(ang)
            vx  = round(cx + r * math.cos(rad), 4)
            vy  = round(cy + r * math.sin(rad), 4)
            self.vias.append(StitchVia(x=vx, y=vy))
            ang += step

        added = len(self.vias) - count_before
        log.info(
            f"[PowerIntegrity] HS connector stitch ring @ ({cx},{cy}): {added} vias."
        )

    def _ensure_diff_pair_return(self, dp: dict):
        """
        Adds midpoint stitch vias along each differential pair path to
        guarantee a continuous GND return beneath the signal traces.
        """
        path_p: List[Tuple[float,float]] = dp.get("path_p", [])
        path_n: List[Tuple[float,float]] = dp.get("path_n", [])

        if not path_p or not path_n:
            self.report.warnings.append(
                f"Diff pair {dp.get('net_p','?')}/{dp.get('net_n','?')}: empty path — skipped."
            )
            return

        # Interpolate midpoints between positive and negative paths
        n = min(len(path_p), len(path_n))
        for i in range(n):
            mx = round((path_p[i][0] + path_n[i][0]) / 2, 4)
            my = round((path_p[i][1] + path_n[i][1]) / 2, 4)
            self.vias.append(StitchVia(x=mx, y=my))

        self.report.diff_pair_returns_ensured += 1
        log.info(
            f"[PowerIntegrity] Diff-pair return path ensured for "
            f"{dp.get('net_p','?')}/{dp.get('net_n','?')} ({n} vias)."
        )


# ---------------------------------------------------------------------------
# Standalone test helper
# ---------------------------------------------------------------------------

def _build_mock_board_data() -> dict:
    return {
        "board_width_mm":  65.0,
        "board_height_mm": 56.5,
        "ground_layers": ["F.Cu", "B.Cu"],
        "hs_connectors": [
            {"ref": "J1", "x": 10.0, "y": 28.25},
            {"ref": "J2", "x": 55.0, "y": 28.25},
        ],
        "diff_pairs": [
            {
                "net_p": "USB_DP",
                "net_n": "USB_DN",
                "path_p": [(10.0, 28.0), (30.0, 28.0), (55.0, 28.0)],
                "path_n": [(10.0, 28.5), (30.0, 28.5), (55.0, 28.5)],
            }
        ],
    }


if __name__ == "__main__":
    import sys, json as _json
    board_data = _build_mock_board_data()
    agent  = GroundPlaneAgent()
    report = agent.generate(board_data)
    print(_json.dumps(report.to_dict(), indent=2))
    print("\n--- KiCad Snippet (first 30 lines) ---")
    snippets = agent.to_kicad_snippets().splitlines()
    print("\n".join(snippets[:30]))
    sys.exit(0)
