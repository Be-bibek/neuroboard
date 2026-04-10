"""
ai_core/routing/corridor_optimizer.py
=======================================
Routing Corridor Optimizer

Enforces a strict geometric routing corridor between a source connector and a
destination connector so that every bus trace is physically constrained within
a bounded region.  Integrates with the existing CorridorGenerator (corridor.py),
FanoutEngine (fanout.py), and BusPipeline (bus_pipeline.py).

Responsibilities
----------------
  1. Define a corridor polygon from connector-pair geometry.
  2. Validate that every parallel bus trace lies inside the corridor.
  3. Maintain constant inter-trace spacing across the full routing path.
  4. Report any corridor violations so the orchestrator can penalise them.

Deterministic: no random state; all geometry is derived from input coordinates.
"""

import math
from dataclasses import dataclass, field
from typing import List, Tuple, Optional
import shapely.geometry as geom

from system.logger import log


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------

Point = Tuple[float, float]
Path  = List[Point]


@dataclass
class CorridorViolation:
    trace_index: int
    net: str
    message: str
    severity: str = "WARNING"


@dataclass
class CorridorReport:
    corridor_width_mm:   float = 0.0
    corridor_length_mm:  float = 0.0
    traces_checked:      int   = 0
    traces_compliant:    int   = 0
    violations: List[CorridorViolation] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return all(v.severity != "ERROR" for v in self.violations)

    def to_dict(self) -> dict:
        return {
            "agent": "CorridorOptimizerAgent",
            "passed": self.passed,
            "corridor_width_mm":  self.corridor_width_mm,
            "corridor_length_mm": self.corridor_length_mm,
            "traces_checked":     self.traces_checked,
            "traces_compliant":   self.traces_compliant,
            "violations": [
                {
                    "trace_index": v.trace_index,
                    "net":         v.net,
                    "severity":    v.severity,
                    "message":     v.message,
                }
                for v in self.violations
            ],
        }


# ---------------------------------------------------------------------------
# Corridor Optimizer
# ---------------------------------------------------------------------------

class CorridorOptimizer:
    """
    Validates and enforces the routing corridor for a parallel bus.

    Parameters
    ----------
    trace_width : float
        Width of each individual trace (mm).
    spacing : float
        Edge-to-edge spacing between adjacent traces (mm).
    margin_mm : float
        Extra clearance added to each side of the corridor polygon (mm).
    """

    def __init__(self,
                 trace_width: float = 0.15,
                 spacing:     float = 0.15,
                 margin_mm:   float = 0.50):
        self.trace_width = trace_width
        self.spacing     = spacing
        self.margin_mm   = margin_mm

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def build_corridor(self,
                       src_exit:  Point,
                       dst_entry: Point,
                       bus_count: int) -> geom.Polygon:
        """
        Constructs a rectangular corridor polygon between two connector exit
        / entry points that is wide enough to hold all bus traces.

        The corridor is defined by buffering the centre-line by half the total
        bus width plus the routing margin.
        """
        total_bus_width = (
            bus_count * self.trace_width
            + (bus_count - 1) * self.spacing
        )
        half_width = total_bus_width / 2 + self.margin_mm

        centre_line = geom.LineString([src_exit, dst_entry])
        corridor    = centre_line.buffer(
            half_width,
            cap_style  = 2,   # flat
            join_style = 2,   # mitre
        )
        log.info(
            f"[Corridor] Built corridor: length={centre_line.length:.2f} mm, "
            f"half-width={half_width:.2f} mm, bus_count={bus_count}"
        )
        return corridor

    def validate_traces(self,
                        corridor:     geom.Polygon,
                        all_traces:   List[Path],
                        net_names:    Optional[List[str]] = None) -> CorridorReport:
        """
        Verifies that every trace path lies within the corridor polygon.

        Parameters
        ----------
        corridor    : Shapely Polygon produced by build_corridor().
        all_traces  : Ordered list of (x,y) point-lists, one per bus signal.
        net_names   : Optional friendly names matching all_traces indices.
        """
        report = CorridorReport(
            corridor_width_mm  = corridor.bounds[2] - corridor.bounds[0],
            corridor_length_mm = corridor.length,
            traces_checked     = len(all_traces),
        )

        for i, path in enumerate(all_traces):
            net = (net_names[i] if net_names and i < len(net_names) else f"NET_{i}")
            if len(path) < 2:
                report.violations.append(CorridorViolation(
                    trace_index=i, net=net, severity="WARNING",
                    message=f"Trace '{net}' has fewer than 2 points — skipped.",
                ))
                continue

            line = geom.LineString(path)
            if corridor.contains(line):
                report.traces_compliant += 1
                log.info(f"[Corridor] [OK] Trace '{net}' is inside corridor.")
            else:
                # Compute the out-of-corridor segment length for severity assessment
                outside = line.difference(corridor)
                outside_len = getattr(outside, "length", 0.0)
                severity = "ERROR" if outside_len > 0.5 else "WARNING"
                report.violations.append(CorridorViolation(
                    trace_index=i,
                    net=net,
                    severity=severity,
                    message=(
                        f"Trace '{net}' extends {outside_len:.3f} mm outside the routing corridor."
                    ),
                ))
                log.warning(
                    f"[Corridor] [XX] Trace '{net}': {outside_len:.3f} mm outside corridor ({severity})."
                )

        return report

    def enforce_spacing(self, all_traces: List[Path], net_names: Optional[List[str]] = None) -> List[CorridorViolation]:
        """
        Checks that every pair of adjacent parallel traces maintains the required
        edge-to-edge spacing throughout their entire length.

        Returns a (possibly empty) list of CorridorViolation objects.
        """
        violations: List[CorridorViolation] = []
        for i in range(len(all_traces) - 1):
            n1  = (net_names[i]   if net_names and i   < len(net_names) else f"NET_{i}")
            n2  = (net_names[i+1] if net_names and i+1 < len(net_names) else f"NET_{i+1}")
            if len(all_traces[i]) < 2 or len(all_traces[i+1]) < 2:
                continue

            l1 = geom.LineString(all_traces[i])
            l2 = geom.LineString(all_traces[i+1])

            # Edge-to-edge distance = centreline distance − half-widths
            cl_dist   = l1.distance(l2)
            edge_dist = cl_dist - self.trace_width  # subtract one full trace width (two halves)

            if edge_dist < self.spacing * 0.95:  # 5% arithmetic tolerance
                violations.append(CorridorViolation(
                    trace_index=i,
                    net=f"{n1}/{n2}",
                    severity="ERROR",
                    message=(
                        f"Adjacent traces '{n1}' and '{n2}': "
                        f"edge spacing {edge_dist:.4f} mm < required {self.spacing:.4f} mm."
                    ),
                ))
                log.error(
                    f"[Corridor] Spacing violation: '{n1}'/'{n2}' edge gap {edge_dist:.4f} mm "
                    f"< {self.spacing:.4f} mm."
                )
            else:
                log.info(
                    f"[Corridor] [OK] Spacing OK between '{n1}' and '{n2}' "
                    f"(edge gap {edge_dist:.4f} mm)."
                )
        return violations

    def run(self,
            src_exit:   Point,
            dst_entry:  Point,
            all_traces: List[Path],
            net_names:  Optional[List[str]] = None) -> CorridorReport:
        """
        Convenience wrapper: build corridor → validate containment → enforce spacing.
        Returns a unified CorridorReport.
        """
        if not all_traces:
            log.warning("[Corridor] No traces provided to CorridorOptimizer.run().")
            return CorridorReport()

        corridor = self.build_corridor(src_exit, dst_entry, bus_count=len(all_traces))
        report   = self.validate_traces(corridor, all_traces, net_names)

        spacing_violations = self.enforce_spacing(all_traces, net_names)
        report.violations.extend(spacing_violations)

        status = "PASS" if report.passed else "FAIL"
        log.info(
            f"[Corridor] Corridor check {status} — "
            f"{report.traces_compliant}/{report.traces_checked} traces compliant, "
            f"{len(report.violations)} violation(s)."
        )
        return report


# ---------------------------------------------------------------------------
# Standalone test helper
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys
    import json as _json

    # Simulate a 4-trace bus from left connector exit to right connector entry
    src = (5.0, 28.25)
    dst = (60.0, 28.25)

    # Parallel traces offset by (trace_width + spacing)
    pitch = 0.15 + 0.15   # 0.30 mm
    traces = [
        [(5.0, 28.25 + i * pitch), (60.0, 28.25 + i * pitch)]
        for i in range(4)
    ]
    nets = ["USB_DP", "USB_DN", "I2C_SDA", "I2C_SCL"]

    opt = CorridorOptimizer(trace_width=0.15, spacing=0.15, margin_mm=0.5)
    report = opt.run(src, dst, traces, nets)
    print(_json.dumps(report.to_dict(), indent=2))
    sys.exit(0 if report.passed else 1)
