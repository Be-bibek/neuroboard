"""
PCB Constraint Engine — Prompt 5
===================================
All engineering parameters are computed from first principles.
AI must NOT guess values. Every output is formula-based.
"""
import math
from dataclasses import dataclass
from typing import Optional


# ─────────────────────────────────────────────
# TRACE WIDTH from IPC-2221 current capacity
# ─────────────────────────────────────────────
@dataclass
class TraceWidthResult:
    width_mm: float
    max_current_a: float
    temperature_rise_c: float
    layer: str


def calc_trace_width(
    current_a: float,
    temp_rise_c: float = 10.0,
    copper_oz: float = 1.0,
    is_external: bool = True
) -> TraceWidthResult:
    """
    IPC-2221 trace width calculator.
    
    Formula: I = k * ΔT^0.44 * A^0.725
    Solved for A (cross-section in mils²), then converted to width.
    
    Args:
        current_a:    Max current in Amperes
        temp_rise_c:  Allowable temp rise above ambient (°C)
        copper_oz:    Copper weight (oz/ft²), typically 1 or 2
        is_external:  True = external layer, False = internal layer
    """
    k = 0.048 if is_external else 0.024  # IPC-2221 constants
    
    # Solve for cross-section area in mils²
    area_mils2 = (current_a / (k * (temp_rise_c ** 0.44))) ** (1 / 0.725)
    
    # Thickness in mils (1 oz copper = 1.37 mils)
    thickness_mils = copper_oz * 1.37
    
    # Width in mils
    width_mils = area_mils2 / thickness_mils
    
    # Convert to mm
    width_mm = width_mils * 0.0254
    
    # Round up to nearest 0.05mm for manufacturability
    width_mm = math.ceil(width_mm / 0.05) * 0.05

    return TraceWidthResult(
        width_mm=max(width_mm, 0.1),  # Minimum 0.1mm
        max_current_a=current_a,
        temperature_rise_c=temp_rise_c,
        layer="external" if is_external else "internal"
    )


# ─────────────────────────────────────────────
# DIFFERENTIAL PAIR IMPEDANCE (Microstrip)
# ─────────────────────────────────────────────
@dataclass
class DiffPairResult:
    trace_width_mm: float
    trace_gap_mm: float
    diff_impedance_ohm: float
    single_ended_z0_ohm: float
    layer: str


def calc_diff_pair_impedance(
    trace_width_mm: float,
    trace_gap_mm: float,
    substrate_h_mm: float = 1.6,
    er: float = 4.5,  # FR4 typical dielectric constant
    copper_t_mm: float = 0.035  # 1oz copper
) -> DiffPairResult:
    """
    Edge-coupled microstrip differential impedance.
    Uses IPC-2141A formulas.
    
    Zdiff = 2 * Z0 * (1 - 0.347 * exp(-2.9 * S/H))
    where Z0 is single-ended microstrip impedance.
    
    Args:
        trace_width_mm:   Width of each trace
        trace_gap_mm:     Gap between P and N traces
        substrate_h_mm:   Dielectric height (PCB thickness / layer stack)
        er:               Relative dielectric constant of substrate
        copper_t_mm:      Copper thickness
    """
    w = trace_width_mm
    h = substrate_h_mm
    t = copper_t_mm
    s = trace_gap_mm
    
    # Effective dielectric constant (Hammerstad)
    er_eff = (er + 1) / 2 + (er - 1) / 2 * (1 + 12 * h / w) ** -0.5
    
    # Single-ended microstrip impedance
    if w / h <= 1:
        z0 = (60 / math.sqrt(er_eff)) * math.log(8 * h / w + w / (4 * h))
    else:
        z0 = (120 * math.pi) / (math.sqrt(er_eff) * (w / h + 1.393 + 0.667 * math.log(w / h + 1.444)))
    
    # Differential impedance (IPC-2141A)
    z_diff = 2 * z0 * (1 - 0.347 * math.exp(-2.9 * s / h))
    
    return DiffPairResult(
        trace_width_mm=trace_width_mm,
        trace_gap_mm=trace_gap_mm,
        diff_impedance_ohm=round(z_diff, 2),
        single_ended_z0_ohm=round(z0, 2),
        layer="microstrip"
    )


def solve_diff_pair_for_impedance(
    target_ohm: float = 90.0,
    substrate_h_mm: float = 1.6,
    er: float = 4.5,
    copper_t_mm: float = 0.035
) -> DiffPairResult:
    """
    Iteratively solve for trace width and gap to hit a target differential impedance.
    Searches width from 0.08 to 0.5mm, gap from 0.1 to 0.5mm.
    """
    best = None
    best_error = float('inf')
    
    for w_step in range(8, 51, 2):   # 0.08 to 0.50 mm
        for g_step in range(10, 51, 5):  # 0.10 to 0.50 mm
            w = w_step / 100.0
            g = g_step / 100.0
            result = calc_diff_pair_impedance(w, g, substrate_h_mm, er, copper_t_mm)
            error = abs(result.diff_impedance_ohm - target_ohm)
            if error < best_error:
                best_error = error
                best = result
    
    return best


# ─────────────────────────────────────────────
# THERMAL VIA ESTIMATION
# ─────────────────────────────────────────────
@dataclass
class ThermalViaResult:
    vias_needed: int
    via_diameter_mm: float
    drill_mm: float
    total_thermal_resistance_c_per_w: float
    single_via_resistance_c_per_w: float


def calc_thermal_vias(
    power_w: float,
    max_temp_rise_c: float = 20.0,
    via_diameter_mm: float = 0.6,
    drill_mm: float = 0.3,
    board_thickness_mm: float = 1.6,
    copper_conductivity: float = 385.0  # W/m·K
) -> ThermalViaResult:
    """
    Estimate the number of thermal vias required to dissipate heat from a component.
    
    R_via = L / (k * A)
    where:
        L = board thickness (thermal path length)
        k = copper thermal conductivity
        A = cross-sectional area of copper in via wall
    """
    wall_thickness_mm = (via_diameter_mm - drill_mm) / 2
    area_m2 = math.pi * (via_diameter_mm / 1000 / 2) ** 2 - math.pi * (drill_mm / 1000 / 2) ** 2
    
    # Single via thermal resistance (K/W)
    r_single = (board_thickness_mm / 1000) / (copper_conductivity * area_m2)
    
    # Target overall resistance
    r_target = max_temp_rise_c / power_w
    
    # Vias in parallel: R_total = R_single / N
    vias_needed = math.ceil(r_single / r_target)
    r_actual = r_single / vias_needed
    
    return ThermalViaResult(
        vias_needed=vias_needed,
        via_diameter_mm=via_diameter_mm,
        drill_mm=drill_mm,
        total_thermal_resistance_c_per_w=round(r_actual, 3),
        single_via_resistance_c_per_w=round(r_single, 3)
    )


# ─────────────────────────────────────────────
# CONVENIENCE: Full constraint pack for a net
# ─────────────────────────────────────────────
def get_pcie_diff_pair_constraints() -> dict:
    """
    Returns the solved physical constraints for RPi5 PCIe Gen 3 diff pairs.
    Target: 90Ω ± 10% on standard 4-layer 1.6mm FR4.
    """
    result = solve_diff_pair_for_impedance(target_ohm=90.0, substrate_h_mm=0.35, er=4.2)
    return {
        "trace_width_mm": result.trace_width_mm,
        "trace_gap_mm": result.trace_gap_mm,
        "diff_impedance_ohm": result.diff_impedance_ohm,
        "tolerance_pct": 10,
        "layer_recommendation": "F.Cu over continuous GND on In1.Cu",
        "max_via_count": 0,  # No vias on diff pairs if possible
        "length_match_tolerance_mm": 0.127  # 5 mil
    }


if __name__ == "__main__":
    print("=== IPC-2221 Trace Width (1A, 10°C rise) ===")
    r = calc_trace_width(1.0)
    print(f"  Width: {r.width_mm}mm")

    print("\n=== PCIe Gen3 90Ω Diff Pair Constraints ===")
    c = get_pcie_diff_pair_constraints()
    for k, v in c.items():
        print(f"  {k}: {v}")

    print("\n=== Thermal Vias (2W, 20°C rise) ===")
    t = calc_thermal_vias(power_w=2.0)
    print(f"  Vias needed: {t.vias_needed}")
    print(f"  R_total: {t.total_thermal_resistance_c_per_w} °C/W")
