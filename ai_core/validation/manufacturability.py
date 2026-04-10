"""
ai_core/validation/manufacturability.py
=========================================
Manufacturability Validation Agent

Validates the PCB design for fabrication readiness based on design rules
defined in config/design_rules.yaml.  All checks are deterministic.

Severity levels
---------------
  INFO     — advisory note, no action required
  WARNING  — possible issue; should be reviewed before fabrication
  ERROR    — fabrication will likely fail; correction required

Checks performed
----------------
  1. Minimum annular ring for vias
  2. Trace width compliance (min/max)
  3. Trace-to-trace spacing
  4. Copper-to-board-edge clearance
  5. Silkscreen overlap with solder pads
  6. Solder-mask expansion and clearance
"""

import math
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from system.logger import log


# ---------------------------------------------------------------------------
# Default fabrication limits (JLCPCB standard 4-layer)
# ---------------------------------------------------------------------------

DEFAULT_RULES = {
    # Via geometry
    "via_drill_min_mm":         0.20,
    "via_annular_ring_min_mm":  0.15,      # (pad_diameter - drill) / 2 ≥ this

    # Trace
    "trace_width_min_mm":       0.09,
    "trace_width_max_mm":       3.00,
    "trace_spacing_min_mm":     0.09,

    # Board edge
    "copper_to_edge_min_mm":    0.30,
    "silkscreen_to_pad_min_mm": 0.10,

    # Solder mask
    "solder_mask_expansion_mm": 0.05,      # each side
    "solder_mask_min_bridge_mm": 0.10,     # gap between two mask openings
}


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class DFMViolation:
    rule: str
    severity: str         # "INFO" | "WARNING" | "ERROR"
    message: str
    location: Optional[str] = None
    suggestion: str = ""


@dataclass
class ManufacturabilityReport:
    passed: bool = True
    violations: List[DFMViolation] = field(default_factory=list)
    checks_run: int = 0
    checks_passed: int = 0

    def add_violation(self, rule: str, severity: str, message: str,
                      location: str = "", suggestion: str = ""):
        self.violations.append(DFMViolation(rule, severity, message, location, suggestion))
        if severity == "ERROR":
            self.passed = False

    def to_dict(self) -> dict:
        return {
            "agent": "ManufacturabilityAgent",
            "passed": self.passed,
            "checks_run": self.checks_run,
            "checks_passed": self.checks_passed,
            "violations": [
                {
                    "rule":       v.rule,
                    "severity":   v.severity,
                    "message":    v.message,
                    "location":   v.location,
                    "suggestion": v.suggestion,
                }
                for v in self.violations
            ],
        }


# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------

class ManufacturabilityAgent:
    """
    Validates a PCB design for DFM (Design for Manufacturability) compliance.

    board_data keys expected:
      vias         : list of {"drill_mm": …, "pad_diameter_mm": …, "x": …, "y": …}
      traces       : list of {"width_mm": …, "layer": …,
                               "start": [x,y], "end": [x,y], "net": …}
      pads         : list of {"ref": …, "x": …, "y": …,
                               "width_mm": …, "height_mm": …, "dist_to_edge_mm": …}
      silkscreen   : list of {"x": …, "y": …, "width_mm": …, "height_mm": …}
      solder_masks : list of {"pad_width_mm": …, "pad_height_mm": …,
                               "clearance_mm": …, "expansion_mm": …,
                               "neighbour_clearance_mm": …}
    """

    def __init__(self, design_rules: Optional[dict] = None):
        self.rules = {**DEFAULT_RULES, **(design_rules or {})}
        self.report = ManufacturabilityReport()

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    def validate(self, board_data: dict) -> ManufacturabilityReport:
        log.info("[Manufacturability] Starting DFM validation...")
        self.report = ManufacturabilityReport()

        self._check_via_annular_rings(board_data.get("vias", []))
        self._check_trace_widths(board_data.get("traces", []))
        self._check_trace_spacing(board_data.get("traces", []))
        self._check_copper_to_edge(board_data.get("pads", []))
        self._check_silkscreen_overlap(
            board_data.get("silkscreen", []),
            board_data.get("pads", []),
        )
        self._check_solder_mask(board_data.get("solder_masks", []))

        errors   = sum(1 for v in self.report.violations if v.severity == "ERROR")
        warnings = sum(1 for v in self.report.violations if v.severity == "WARNING")
        self.report.checks_passed = self.report.checks_run - len(self.report.violations)
        self.report.passed = (errors == 0)

        status = "PASS" if self.report.passed else "FAIL"
        log.info(
            f"[Manufacturability] Validation complete — {status}  "
            f"({self.report.checks_passed}/{self.report.checks_run} checks, "
            f"{errors} error(s), {warnings} warning(s))."
        )
        return self.report

    # ------------------------------------------------------------------
    # Check 1 — Via annular ring
    # ------------------------------------------------------------------

    def _check_via_annular_rings(self, vias: list):
        min_ring = self.rules["via_annular_ring_min_mm"]
        for v in vias:
            self.report.checks_run += 1
            drill = v.get("drill_mm", 0.0)
            pad_d = v.get("pad_diameter_mm", 0.0)
            ring  = (pad_d - drill) / 2.0
            loc   = f"via@({v.get('x',0):.2f},{v.get('y',0):.2f})"

            if drill < self.rules["via_drill_min_mm"]:
                self.report.add_violation(
                    rule="VIA_DRILL",
                    severity="ERROR",
                    message=f"Via drill {drill:.3f} mm is below minimum {self.rules['via_drill_min_mm']} mm.",
                    location=loc,
                    suggestion=f"Increase via drill to at least {self.rules['via_drill_min_mm']} mm.",
                )
            elif ring < min_ring:
                self.report.add_violation(
                    rule="VIA_ANNULAR_RING",
                    severity="ERROR",
                    message=f"Via annular ring {ring:.3f} mm < minimum {min_ring} mm "
                            f"(drill={drill:.3f}, pad={pad_d:.3f}).",
                    location=loc,
                    suggestion=f"Increase pad diameter to at least {drill + 2*min_ring:.3f} mm.",
                )
            else:
                log.info(f"[Manufacturability] [OK] Via ring OK ({ring:.3f} mm) {loc}")

    # ------------------------------------------------------------------
    # Check 2 — Trace width
    # ------------------------------------------------------------------

    def _check_trace_widths(self, traces: list):
        w_min = self.rules["trace_width_min_mm"]
        w_max = self.rules["trace_width_max_mm"]
        for t in traces:
            self.report.checks_run += 1
            w   = t.get("width_mm", 0.0)
            net = t.get("net", "?")
            loc = f"trace '{net}' @ {t.get('start','?')}"

            if w < w_min:
                self.report.add_violation(
                    rule="TRACE_WIDTH_MIN",
                    severity="ERROR",
                    message=f"Trace '{net}' width {w:.4f} mm < minimum {w_min} mm.",
                    location=loc,
                    suggestion=f"Widen trace to at least {w_min} mm.",
                )
            elif w > w_max:
                self.report.add_violation(
                    rule="TRACE_WIDTH_MAX",
                    severity="WARNING",
                    message=f"Trace '{net}' width {w:.4f} mm > recommended max {w_max} mm.",
                    location=loc,
                    suggestion="Verify current-carrying requirements; reduce width if possible.",
                )
            else:
                log.info(f"[Manufacturability] [OK] Trace width OK ({w:.4f} mm) {loc}")

    # ------------------------------------------------------------------
    # Check 3 — Trace spacing
    # ------------------------------------------------------------------

    def _check_trace_spacing(self, traces: list):
        """Check minimum spacing between same-layer trace segments."""
        import shapely.geometry as geom
        from shapely.strtree import STRtree
        import time

        spacing_min = self.rules["trace_spacing_min_mm"]
        # Group by layer
        by_layer: Dict[str, list] = {}
        for t in traces:
            layer = t.get("layer", "F.Cu")
            by_layer.setdefault(layer, []).append(t)

        for layer, layer_traces in by_layer.items():
            lines = []
            for t in layer_traces:
                s, e = t.get("start", [0, 0]), t.get("end", [0, 0])
                line = geom.LineString([s, e]).simplify(0.01) # Geometry simplification
                lines.append({
                    "net": t.get("net", "?"),
                    "line": line,
                    "width": t.get("width_mm", 0)
                })

            if not lines:
                continue

            geometries = [item["line"] for item in lines]
            tree = STRtree(geometries)

            log.info(f"[Manufacturability] Checking spacing for {len(lines)} traces on layer {layer}...")
            start_time = time.time()
            checks_done = 0
            total_checks = len(lines)

            # Query the STRtree with a buffer
            for i, line_item in enumerate(lines):
                n1, l1, w1 = line_item["net"], line_item["line"], line_item["width"]
                
                # Query tree for geometries that could be within spacing_min + w1/2 + max_w/2
                # Instead of max_w/2, we can just use a large enough buffer, or query and check.
                search_radius = spacing_min + (w1 / 2.0) + (self.rules.get("trace_width_max_mm", 3.0) / 2.0)
                query_geom = l1.buffer(search_radius)
                
                nearby_indices = tree.query(query_geom)
                
                for j in nearby_indices:
                    if j <= i:  # Avoid duplicate and self-checks
                        continue
                        
                    self.report.checks_run += 1
                    n2, l2, w2 = lines[j]["net"], lines[j]["line"], lines[j]["width"]

                    # Edge-to-edge distance = centreline distance - half-widths
                    cl_dist = l1.distance(l2)
                    edge_dist = cl_dist - (w1 / 2) - (w2 / 2)

                    if edge_dist < spacing_min:
                        self.report.add_violation(
                            rule="TRACE_SPACING",
                            severity="ERROR",
                            message=(
                                f"Traces '{n1}' and '{n2}' on {layer}: "
                                f"edge-to-edge gap {edge_dist:.4f} mm < minimum {spacing_min} mm."
                            ),
                            suggestion=f"Increase gap between '{n1}' and '{n2}' to ≥ {spacing_min} mm.",
                        )
                
                checks_done += 1
                if checks_done % max(1, total_checks // 10) == 0:
                    log.info(f"[Manufacturability] Layer {layer}: Trace spacing progress {checks_done}/{total_checks} ({(checks_done/total_checks)*100:.1f}%)")

            log.info(f"[Manufacturability] Completed trace spacing on {layer} in {time.time()-start_time:.2f}s")

    # ------------------------------------------------------------------
    # Check 4 — Copper-to-board-edge clearance
    # ------------------------------------------------------------------

    def _check_copper_to_edge(self, pads: list):
        min_clr = self.rules["copper_to_edge_min_mm"]
        for p in pads:
            self.report.checks_run += 1
            dist = p.get("dist_to_edge_mm", float("inf"))
            loc  = f"pad '{p.get('ref','?')}'"

            if dist < min_clr:
                self.report.add_violation(
                    rule="COPPER_TO_EDGE",
                    severity="ERROR",
                    message=f"{loc} copper is {dist:.3f} mm from board edge (min {min_clr} mm).",
                    location=loc,
                    suggestion=f"Move {loc} at least {min_clr} mm from the board edge.",
                )
            else:
                log.info(f"[Manufacturability] [OK] Copper-edge clearance OK ({dist:.3f} mm) {loc}")

    # ------------------------------------------------------------------
    # Check 5 — Silkscreen overlap with pads
    # ------------------------------------------------------------------

    def _check_silkscreen_overlap(self, silkscreen: list, pads: list):
        import shapely.geometry as geom

        min_gap = self.rules["silkscreen_to_pad_min_mm"]
        for silk in silkscreen:
            sx, sy = silk.get("x", 0), silk.get("y", 0)
            sw, sh = silk.get("width_mm", 1), silk.get("height_mm", 0.2)
            silk_rect = geom.box(sx - sw / 2, sy - sh / 2, sx + sw / 2, sy + sh / 2)

            for p in pads:
                self.report.checks_run += 1
                px, py = p.get("x", 0), p.get("y", 0)
                pw, ph = p.get("width_mm", 0), p.get("height_mm", 0)
                pad_rect = geom.box(px - pw / 2, py - ph / 2, px + pw / 2, py + ph / 2)

                dist = silk_rect.distance(pad_rect)
                if dist < min_gap:
                    overlap = silk_rect.intersection(pad_rect)
                    severity = "ERROR" if not overlap.is_empty else "WARNING"
                    self.report.add_violation(
                        rule="SILKSCREEN_OVERLAP",
                        severity=severity,
                        message=(
                            f"Silkscreen element overlaps pad '{p.get('ref','?')}' "
                            f"(gap={dist:.3f} mm < {min_gap} mm)."
                        ),
                        suggestion="Move silkscreen away from pad copper area.",
                    )
                else:
                    log.info(
                        f"[Manufacturability] [OK] Silk-pad clearance OK ({dist:.3f} mm) "
                        f"pad '{p.get('ref','?')}'"
                    )

    # ------------------------------------------------------------------
    # Check 6 — Solder mask expansion and bridge
    # ------------------------------------------------------------------

    def _check_solder_mask(self, solder_masks: list):
        exp_min    = self.rules["solder_mask_expansion_mm"]
        bridge_min = self.rules["solder_mask_min_bridge_mm"]
        for sm in solder_masks:
            self.report.checks_run += 1
            exp   = sm.get("expansion_mm", 0.0)
            bridge = sm.get("neighbour_clearance_mm", float("inf"))

            if exp < exp_min:
                self.report.add_violation(
                    rule="SOLDER_MASK_EXPANSION",
                    severity="WARNING",
                    message=f"Solder mask expansion {exp:.3f} mm < recommended {exp_min} mm.",
                    suggestion=f"Set solder mask expansion to ≥ {exp_min} mm per side.",
                )
            if bridge < bridge_min:
                self.report.add_violation(
                    rule="SOLDER_MASK_BRIDGE",
                    severity="ERROR",
                    message=f"Solder mask bridge between adjacent openings {bridge:.3f} mm < "
                            f"minimum {bridge_min} mm.",
                    suggestion=f"Ensure at least {bridge_min} mm soldermask bridge remains between pads.",
                )
            else:
                log.info(
                    f"[Manufacturability] [OK] Solder mask OK "
                    f"(expansion={exp:.3f}, bridge={bridge:.3f} mm)"
                )


# ---------------------------------------------------------------------------
# Standalone test helper
# ---------------------------------------------------------------------------

def _build_mock_board_data() -> dict:
    """Returns a synthetic board_data dict suitable for offline testing."""
    return {
        "vias": [
            {"drill_mm": 0.30, "pad_diameter_mm": 0.60, "x": 10.0, "y": 10.0},
            {"drill_mm": 0.15, "pad_diameter_mm": 0.35, "x": 20.0, "y": 10.0},  # ring = 0.10 < 0.15 → ERROR
        ],
        "traces": [
            {"net": "GND", "layer": "F.Cu", "width_mm": 0.25,
             "start": [5.0,  5.0], "end": [15.0, 5.0]},
            {"net": "3V3", "layer": "F.Cu", "width_mm": 0.15,
             "start": [5.0,  5.4], "end": [15.0, 5.4]},   # edge-to-edge 0.025 mm < 0.09 → ERROR
        ],
        "pads": [
            {"ref": "J1-1", "x": 5.0,  "y": 5.0,  "width_mm": 1.5, "height_mm": 1.5,
             "dist_to_edge_mm": 1.2},
            {"ref": "R1-1", "x": 64.5, "y": 5.0,  "width_mm": 0.8, "height_mm": 0.8,
             "dist_to_edge_mm": 0.25},   # < 0.30 → ERROR
        ],
        "silkscreen": [
            {"x": 5.1, "y": 5.05, "width_mm": 2.0, "height_mm": 0.3},  # overlaps J1-1 → ERROR
        ],
        "solder_masks": [
            {"expansion_mm": 0.05, "neighbour_clearance_mm": 0.12},
            {"expansion_mm": 0.03, "neighbour_clearance_mm": 0.08},  # WARNING + ERROR
        ],
    }


if __name__ == "__main__":
    import sys, json as _json, yaml, os
    rules_path = os.path.join(
        os.path.dirname(__file__), "..", "..", "config", "design_rules.yaml"
    )
    design_rules = {}
    if os.path.exists(rules_path):
        with open(rules_path) as f:
            cfg = yaml.safe_load(f)
        r = cfg.get("routing", {})
        design_rules = {
            "trace_width_min_mm":  r.get("trace_width_min", DEFAULT_RULES["trace_width_min_mm"]),
            "trace_width_max_mm":  r.get("trace_width_max", DEFAULT_RULES["trace_width_max_mm"]),
            "trace_spacing_min_mm": r.get("spacing_min", DEFAULT_RULES["trace_spacing_min_mm"]),
        }

    board_data = _build_mock_board_data()
    agent  = ManufacturabilityAgent(design_rules)
    report = agent.validate(board_data)
    print(_json.dumps(report.to_dict(), indent=2))
    sys.exit(0 if report.passed else 1)
