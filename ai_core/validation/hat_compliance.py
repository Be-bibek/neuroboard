"""
ai_core/validation/hat_compliance.py
=====================================
Raspberry Pi HAT Compliance Agent

Validates the existing PCB design against the official Raspberry Pi HAT
mechanical and electrical specifications:
  - Board dimensions: 65 mm x 56.5 mm
  - Mounting hole positions (per RPI HAT spec Rev 1.0)
  - 40-pin GPIO header placement and orientation
  - HAT EEPROM footprint connected to ID_SD / ID_SC
  - Edge clearance rules for connectors

All checks are deterministic and reproducible given the same input.
"""

import math
import json
from dataclasses import dataclass, field
from typing import List, Optional, Tuple
from system.logger import log


# ---------------------------------------------------------------------------
# Constants — Raspberry Pi HAT specification Rev 1.0
# ---------------------------------------------------------------------------

# Board outline (mm)
HAT_BOARD_WIDTH_MM  = 65.0
HAT_BOARD_HEIGHT_MM = 56.5
HAT_DIM_TOLERANCE_MM = 0.20   # ±0.20 mm fabrication tolerance

# Mounting holes (X, Y) measured from bottom-left corner in mm
# Reference: https://github.com/raspberrypi/hats/blob/master/hat-board-mechanical.pdf
HAT_MOUNTING_HOLES: List[Tuple[float, float]] = [
    (3.5,  3.5),          # H1 — bottom-left
    (61.5, 3.5),          # H2 — bottom-right
    (3.5,  52.5),         # H3 — top-left
    (61.5, 52.5),         # H4 — top-right
]
HAT_HOLE_DIAMETER_MM     = 2.75   # M2.5 clearance
HAT_HOLE_TOLERANCE_MM    = 0.25   # positional tolerance

# 40-pin GPIO header position (pin 1 centre, from board corner)
GPIO_HEADER_PIN1_X_MM   = 32.5
GPIO_HEADER_PIN1_Y_MM   = 52.5   # near top edge
GPIO_HEADER_TOLERANCE_MM = 0.50
GPIO_HEADER_EXPECTED_PINS = 40

# EEPROM presence check
EEPROM_EXPECTED_NETS = {"ID_SD", "ID_SC"}

# Edge clearance
EDGE_CLEARANCE_MIN_MM = 0.50   # minimum copper-to-edge
CONNECTOR_EDGE_CLEARANCE_WARN_MM = 1.0


# ---------------------------------------------------------------------------
# Result dataclasses
# ---------------------------------------------------------------------------

@dataclass
class ComplianceViolation:
    rule: str
    severity: str   # "ERROR" | "WARNING" | "INFO"
    message: str
    suggestion: str = ""


@dataclass
class HATComplianceReport:
    passed: bool = False
    violations: List[ComplianceViolation] = field(default_factory=list)
    checks_run: int = 0
    checks_passed: int = 0

    def add_violation(self, rule: str, severity: str, message: str, suggestion: str = ""):
        self.violations.append(ComplianceViolation(rule, severity, message, suggestion))
        if severity == "ERROR":
            self.passed = False

    def to_dict(self) -> dict:
        return {
            "agent": "HATComplianceAgent",
            "passed": self.passed,
            "checks_run": self.checks_run,
            "checks_passed": self.checks_passed,
            "violations": [
                {
                    "rule":       v.rule,
                    "severity":   v.severity,
                    "message":    v.message,
                    "suggestion": v.suggestion,
                }
                for v in self.violations
            ],
        }


# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------

class HATComplianceAgent:
    """
    Validates a NeuroBoard PCB design description against the Raspberry Pi HAT
    specification.  Accepts a board-info dictionary produced by the orchestrator
    (or from live_pads_val.json / MCP get_board_info output).
    """

    def __init__(self):
        self.report = HATComplianceReport(passed=True)

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    def validate(self, board_info: dict) -> HATComplianceReport:
        """
        Run all compliance checks and return a HATComplianceReport.

        board_info keys used:
          board_width_mm, board_height_mm
          mounting_holes : list of {"x": ..., "y": ...}
          gpio_header    : {"pin1_x": ..., "pin1_y": ..., "pin_count": ...}
          components     : list of {"ref": ..., "nets": [...], "x": ..., "y": ...}
          edge_items     : list of {"type": "connector"|"trace", "x": ..., "y": ...,
                                    "dist_to_edge_mm": ...}
        """
        log.info("[HATCompliance] Starting Raspberry Pi HAT compliance validation...")
        self.report = HATComplianceReport(passed=True)

        self._check_board_dimensions(board_info)
        self._check_mounting_holes(board_info)
        self._check_gpio_header(board_info)
        self._check_eeprom_presence(board_info)
        self._check_edge_clearances(board_info)

        # Tally
        total_violations = len(self.report.violations)
        errors = sum(1 for v in self.report.violations if v.severity == "ERROR")
        self.report.passed = (errors == 0)
        self.report.checks_passed = self.report.checks_run - total_violations

        status = "PASS" if self.report.passed else "FAIL"
        log.info(
            f"[HATCompliance] Validation complete — {status}  "
            f"({self.report.checks_passed}/{self.report.checks_run} checks passed, "
            f"{errors} error(s))."
        )
        return self.report

    # ------------------------------------------------------------------
    # Check 1 — Board dimensions
    # ------------------------------------------------------------------

    def _check_board_dimensions(self, board_info: dict):
        self.report.checks_run += 1
        w = board_info.get("board_width_mm", None)
        h = board_info.get("board_height_mm", None)

        if w is None or h is None:
            self.report.add_violation(
                rule="BOARD_DIMENSIONS",
                severity="ERROR",
                message="Board width/height not found in board_info.",
                suggestion="Ensure board_info contains 'board_width_mm' and 'board_height_mm'.",
            )
            return

        w_ok = abs(w - HAT_BOARD_WIDTH_MM)  <= HAT_DIM_TOLERANCE_MM
        h_ok = abs(h - HAT_BOARD_HEIGHT_MM) <= HAT_DIM_TOLERANCE_MM

        if not w_ok:
            self.report.add_violation(
                rule="BOARD_DIMENSIONS",
                severity="ERROR",
                message=f"Board width {w:.2f} mm deviates from HAT spec {HAT_BOARD_WIDTH_MM} mm "
                        f"(delta {abs(w - HAT_BOARD_WIDTH_MM):.2f} mm).",
                suggestion=f"Resize the board outline to exactly {HAT_BOARD_WIDTH_MM} mm wide.",
            )

        if not h_ok:
            self.report.add_violation(
                rule="BOARD_DIMENSIONS",
                severity="ERROR",
                message=f"Board height {h:.2f} mm deviates from HAT spec {HAT_BOARD_HEIGHT_MM} mm "
                        f"(delta {abs(h - HAT_BOARD_HEIGHT_MM):.2f} mm).",
                suggestion=f"Resize the board outline to exactly {HAT_BOARD_HEIGHT_MM} mm tall.",
            )

        if w_ok and h_ok:
            log.info(f"[HATCompliance] [OK] Board dimensions OK ({w}[XX]{h} mm).")

    # ------------------------------------------------------------------
    # Check 2 — Mounting holes
    # ------------------------------------------------------------------

    def _check_mounting_holes(self, board_info: dict):
        self.report.checks_run += 1
        holes = board_info.get("mounting_holes", [])

        if not holes:
            self.report.add_violation(
                rule="MOUNTING_HOLES",
                severity="ERROR",
                message="No mounting holes found in board layout.",
                suggestion="Add 4[XX] M2.5 mounting holes at the standard HAT corner positions.",
            )
            return

        if len(holes) < 4:
            self.report.add_violation(
                rule="MOUNTING_HOLES",
                severity="ERROR",
                message=f"Only {len(holes)} mounting hole(s) found; HAT spec requires 4.",
                suggestion="Add the missing mounting hole(s) at the standard HAT corner positions.",
            )

        # Match detected holes to expected positions (nearest-neighbour)
        matched = set()
        for expected in HAT_MOUNTING_HOLES:
            ex, ey = expected
            best_dist = float("inf")
            best_idx  = -1
            for idx, h in enumerate(holes):
                if idx in matched:
                    continue
                d = math.hypot(h.get("x", 0) - ex, h.get("y", 0) - ey)
                if d < best_dist:
                    best_dist = d
                    best_idx  = idx

            if best_dist <= HAT_HOLE_TOLERANCE_MM:
                matched.add(best_idx)
                log.info(f"[HATCompliance] [OK] Mounting hole at ({ex},{ey}) OK (Δ={best_dist:.3f} mm).")
            else:
                self.report.add_violation(
                    rule="MOUNTING_HOLES",
                    severity="ERROR",
                    message=f"No mounting hole within {HAT_HOLE_TOLERANCE_MM} mm of expected "
                            f"position ({ex},{ey}) mm.  Nearest is {best_dist:.3f} mm away.",
                    suggestion=f"Move or add a mounting hole to ({ex},{ey}) mm from the board origin.",
                )

    # ------------------------------------------------------------------
    # Check 3 — 40-pin GPIO header
    # ------------------------------------------------------------------

    def _check_gpio_header(self, board_info: dict):
        self.report.checks_run += 1
        gpio = board_info.get("gpio_header", None)

        if gpio is None:
            self.report.add_violation(
                rule="GPIO_HEADER",
                severity="ERROR",
                message="GPIO header not found in board_info.",
                suggestion="Place a 2[XX]20, 2.54 mm pitch GPIO header near the top edge of the board.",
            )
            return

        pin_count = gpio.get("pin_count", 0)
        if pin_count != GPIO_HEADER_EXPECTED_PINS:
            self.report.add_violation(
                rule="GPIO_HEADER",
                severity="ERROR",
                message=f"GPIO header has {pin_count} pins; HAT spec requires {GPIO_HEADER_EXPECTED_PINS}.",
                suggestion="Replace with a 2[XX]20 (40-pin) 2.54 mm pitch header.",
            )

        p1x = gpio.get("pin1_x", None)
        p1y = gpio.get("pin1_y", None)
        if p1x is not None and p1y is not None:
            dx = abs(p1x - GPIO_HEADER_PIN1_X_MM)
            dy = abs(p1y - GPIO_HEADER_PIN1_Y_MM)
            if dx > GPIO_HEADER_TOLERANCE_MM or dy > GPIO_HEADER_TOLERANCE_MM:
                self.report.add_violation(
                    rule="GPIO_HEADER",
                    severity="ERROR",
                    message=f"GPIO header pin-1 at ({p1x:.2f},{p1y:.2f}) mm; "
                            f"expected ({GPIO_HEADER_PIN1_X_MM},{GPIO_HEADER_PIN1_Y_MM}) mm "
                            f"(Δx={dx:.2f}, Δy={dy:.2f}).",
                    suggestion="Align the GPIO header so that pin 1 matches the HAT mechanical spec.",
                )
            else:
                log.info("[HATCompliance] [OK] GPIO header position OK.")

        # Orientation check
        orientation = gpio.get("orientation_deg", None)
        if orientation is not None and orientation not in (0.0, 180.0):
            self.report.add_violation(
                rule="GPIO_HEADER",
                severity="WARNING",
                message=f"GPIO header orientation is {orientation}°; expected 0° or 180°.",
                suggestion="Rotate the GPIO header to 0° (pin 1 at top-left) per HAT spec.",
            )

    # ------------------------------------------------------------------
    # Check 4 — EEPROM presence and net connectivity
    # ------------------------------------------------------------------

    def _check_eeprom_presence(self, board_info: dict):
        self.report.checks_run += 1
        components = board_info.get("components", [])

        eeprom_found = False
        id_sd_connected = False
        id_sc_connected = False

        for comp in components:
            ref  = comp.get("ref", "")
            nets = set(comp.get("nets", []))
            val  = comp.get("value", "").upper()

            if "EEPROM" in val or ref.startswith("U") and "EEPROM" in str(comp).upper():
                eeprom_found = True
                if "ID_SD" in nets:
                    id_sd_connected = True
                if "ID_SC" in nets:
                    id_sc_connected = True

        if not eeprom_found:
            self.report.add_violation(
                rule="EEPROM_PRESENCE",
                severity="ERROR",
                message="HAT EEPROM footprint not found on the board.",
                suggestion="Add a 24Cxx-compatible EEPROM (e.g. CAT24C32) connected to ID_SD and ID_SC.",
            )
            return

        if not id_sd_connected:
            self.report.add_violation(
                rule="EEPROM_NETS",
                severity="ERROR",
                message="EEPROM is not connected to 'ID_SD' net.",
                suggestion="Connect EEPROM SDA pin to the ID_SD net from the GPIO header (pin 27).",
            )

        if not id_sc_connected:
            self.report.add_violation(
                rule="EEPROM_NETS",
                severity="ERROR",
                message="EEPROM is not connected to 'ID_SC' net.",
                suggestion="Connect EEPROM SCL pin to the ID_SC net from the GPIO header (pin 28).",
            )

        if eeprom_found and id_sd_connected and id_sc_connected:
            log.info("[HATCompliance] [OK] EEPROM present and correctly connected to ID_SD / ID_SC.")

    # ------------------------------------------------------------------
    # Check 5 — Edge clearance
    # ------------------------------------------------------------------

    def _check_edge_clearances(self, board_info: dict):
        self.report.checks_run += 1
        edge_items = board_info.get("edge_items", [])

        if not edge_items:
            self.report.add_violation(
                rule="EDGE_CLEARANCE",
                severity="INFO",
                message="No edge items provided; edge clearance check skipped.",
                suggestion="Supply 'edge_items' in board_info for complete edge clearance validation.",
            )
            return

        for item in edge_items:
            dist = item.get("dist_to_edge_mm", float("inf"))
            item_type = item.get("type", "unknown")
            ref  = item.get("ref", "?")

            if dist < EDGE_CLEARANCE_MIN_MM:
                self.report.add_violation(
                    rule="EDGE_CLEARANCE",
                    severity="ERROR",
                    message=f"{item_type} '{ref}' is {dist:.3f} mm from board edge "
                            f"(minimum {EDGE_CLEARANCE_MIN_MM} mm).",
                    suggestion=f"Move '{ref}' at least {EDGE_CLEARANCE_MIN_MM} mm from the board edge.",
                )
            elif dist < CONNECTOR_EDGE_CLEARANCE_WARN_MM and item_type == "connector":
                self.report.add_violation(
                    rule="EDGE_CLEARANCE",
                    severity="WARNING",
                    message=f"Connector '{ref}' is only {dist:.3f} mm from board edge "
                            f"(recommended ≥{CONNECTOR_EDGE_CLEARANCE_WARN_MM} mm).",
                    suggestion="Move connector further from edge to improve mechanical robustness.",
                )
            else:
                log.info(f"[HATCompliance] [OK] Edge clearance OK for {item_type} '{ref}' ({dist:.2f} mm).")


# ---------------------------------------------------------------------------
# Standalone test helper (not part of normal orchestrator flow)
# ---------------------------------------------------------------------------

def _build_mock_board_info(board_path: Optional[str] = None) -> dict:
    """
    Builds a synthetic board_info for CI / offline validation.
    In production the orchestrator would populate this from the KiCad file.
    """
    return {
        "board_width_mm":  65.0,
        "board_height_mm": 56.5,
        "mounting_holes": [
            {"x": 3.5,  "y": 3.5},
            {"x": 61.5, "y": 3.5},
            {"x": 3.5,  "y": 52.5},
            {"x": 61.5, "y": 52.5},
        ],
        "gpio_header": {
            "pin_count": 40,
            "pin1_x": 32.5,
            "pin1_y": 52.5,
            "orientation_deg": 0.0,
        },
        "components": [
            {
                "ref": "U1",
                "value": "CAT24C32-EEPROM",
                "nets": ["ID_SD", "ID_SC", "VCC", "GND"],
                "x": 55.0,
                "y": 10.0,
            }
        ],
        "edge_items": [
            {"type": "connector", "ref": "J1",  "dist_to_edge_mm": 2.0},
            {"type": "trace",     "ref": "N/A", "dist_to_edge_mm": 0.8},
        ],
    }


if __name__ == "__main__":
    import sys
    board_info = _build_mock_board_info()
    agent  = HATComplianceAgent()
    report = agent.validate(board_info)

    import json as _json
    print(_json.dumps(report.to_dict(), indent=2))
    sys.exit(0 if report.passed else 1)
