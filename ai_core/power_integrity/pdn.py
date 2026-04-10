"""
ai_core/power_integrity/pdn.py
=========================================
Power Delivery Network (PDN) Agent

Responsibilities
----------------
  1. Generate continuous ground and power copper pours.
  2. Add via stitching along board edges and near high-speed connectors.
  3. Implement decoupling capacitor placement heuristics near power pins.
  4. Estimate IR drop using simplified resistance models.
  5. Validate return-path continuity for differential pairs.

This integrates with the GroundPlaneAgent and extends it for full PDN support.
"""

import math
from dataclasses import dataclass, field
from typing import List, Tuple, Dict, Any
from system.logger import log

from power_integrity.ground_plane import GroundPlaneAgent

@dataclass
class DecapPlacement:
    ref: str
    x: float
    y: float
    target_pin: str
    distance_mm: float

@dataclass
class IRDropEstimate:
    net: str
    source_node: str
    sink_node: str
    estimated_drop_mv: float
    resistance_mohm: float

@dataclass
class PDNReport:
    agent: str = "PDNAgent"
    passed: bool = True
    zones_generated: int = 0
    vias_stitched: int = 0
    decaps_placed: int = 0
    ir_drop_estimates: List[Dict] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "agent": self.agent,
            "passed": self.passed,
            "zones_generated": self.zones_generated,
            "vias_stitched": self.vias_stitched,
            "decaps_placed": self.decaps_placed,
            "ir_drop_estimates": self.ir_drop_estimates,
            "warnings": self.warnings,
        }

class PDNAgent:
    """
    Manages the Power Delivery Network logic, decoupling capacitors, IR drop,
    and delegates ground plane tasks to the GroundPlaneAgent.
    """
    def __init__(self):
        self.ground_agent = GroundPlaneAgent()
        self.decaps: List[DecapPlacement] = []
        self.ir_drops: List[IRDropEstimate] = []
        self.report = PDNReport()

    def generate(self, pdn_data: dict) -> PDNReport:
        """
        Runs the full PDN rules and estimation.
        pdn_data keys expected:
          board_width_mm, board_height_mm
          ground_layers   : list of layer names (e.g. ["F.Cu", "B.Cu"])
          power_layers    : list of layer names (e.g. ["In1.Cu"])
          hs_connectors   : list of {"ref": …, "x": …, "y": …}
          diff_pairs      : list of diff pair route data
          power_pins      : list of {"ref": "U1", "pin": "VCC", "x": ..., "y": ..., "net": "3V3", "current_draw_a": ...}
          power_sources   : list of {"net": "3V3", "x": ..., "y": ..., "voltage": 3.3}
        """
        log.info("[PDN] Starting Power Delivery Network analysis and generation...")
        
        # 1. Ground and Power Pours + 2. Via Stitching + 5. Return Continuity
        gp_report = self.ground_agent.generate(pdn_data)
        
        # Merge ground report into our PDN report
        self.report.zones_generated = gp_report.zones_generated
        self.report.vias_stitched = gp_report.vias_stitched
        self.report.warnings.extend(gp_report.warnings)

        # Generate Power pours (simplified assumption: inner layer pours if defined)
        power_layers = pdn_data.get("power_layers", [])
        if power_layers:
            w = pdn_data.get("board_width_mm", 65.0)
            h = pdn_data.get("board_height_mm", 56.5)
            self.ground_agent._generate_ground_zones(w, h, 0.20, power_layers) # Reusing zone builder internally
            self.report.zones_generated += len(power_layers)

        # 3. Decoupling Capacitor Placement Heuristics
        self._place_decoupling_capacitors(pdn_data.get("power_pins", []))

        # 4. Estimate IR Drop
        self._estimate_ir_drop(pdn_data.get("power_sources", []), pdn_data.get("power_pins", []))

        # Compile final status
        if self.report.warnings:
            self.report.passed = False  # Strict fail if there are any PDN warnings

        log.info(f"[PDN] Complete — {self.report.decaps_placed} decaps evaluated, {len(self.ir_drops)} IR drop paths analyzed.")
        return self.report

    def _place_decoupling_capacitors(self, power_pins: List[dict]):
        """
        Heuristic: Ensure a decap is placed within 2.0mm of every critical power pin.
        In a real generator, this would evaluate component coordinates or modify the netlist.
        """
        for i, pin in enumerate(power_pins):
            # Recommend placing a 100nF decap near this pin
            cap_ref = f"C_DEC_{pin.get('ref', 'U')}_{i}"
            dist = 1.5 # mm mocked placement distance
            
            placement = DecapPlacement(
                ref=cap_ref,
                x=pin.get("x", 0.0) + 1.5,
                y=pin.get("y", 0.0),
                target_pin=f"{pin.get('ref')}-{pin.get('pin')}",
                distance_mm=dist
            )
            self.decaps.append(placement)
            
            if dist > 2.0:
                self.report.warnings.append(f"Decap {cap_ref} is {dist}mm away from {placement.target_pin}. Target is < 2.0mm.")
                
        self.report.decaps_placed = len(self.decaps)

    def _estimate_ir_drop(self, sources: List[dict], sinks: List[dict]):
        """
        Simplified DC IR drop estimation: R = rho * (L / (W * T)). 
        Assumes 1oz copper (0.035mm thickness), rho approx 1.7e-8 ohm*m.
        """
        COPPER_RHO_MOHM_MM = 17.0  # roughly 17 mohm * mm for 1mm^2 cross section
        COPPER_THICKNESS_MM = 0.035
        # Assume an effective plane width of 10mm for generic planes
        EFFECTIVE_WIDTH_MM = 10.0 
        
        for sink in sinks:
            net = sink.get("net", "UNKNOWN")
            current_A = sink.get("current_draw_a", 0.1)
            
            # Find closest source for this net
            matching_sources = [s for s in sources if s.get("net") == net]
            if not matching_sources:
                self.report.warnings.append(f"No power source found for net {net} at {sink.get('ref')}")
                continue
                
            source = matching_sources[0]
            dist_mm = math.hypot(sink.get("x", 0) - source.get("x", 0), sink.get("y", 0) - source.get("y", 0))
            
            # Resistance = rho * L / (W * T)
            # rho in mohm*mm.
            res_mohm = COPPER_RHO_MOHM_MM * dist_mm / (EFFECTIVE_WIDTH_MM * COPPER_THICKNESS_MM)
            
            # V = I * R -> drop in mV
            drop_mv = current_A * res_mohm
            
            self.ir_drops.append(IRDropEstimate(net=net, source_node=net, sink_node=f"{sink.get('ref')}-{sink.get('pin')}", estimated_drop_mv=drop_mv, resistance_mohm=res_mohm))
            self.report.ir_drop_estimates.append({
                "sink": f"{sink.get('ref')}-{sink.get('pin')}",
                "drop_mv": round(drop_mv, 3),
                "res_mohm": round(res_mohm, 3)
            })
            
            if drop_mv > 50.0:  # Arbitrary strict 50mV drop limit
                self.report.warnings.append(f"IR Drop Violation: {drop_mv:.1f}mV at {sink.get('ref')} exceeds 50mV tolerance.")
