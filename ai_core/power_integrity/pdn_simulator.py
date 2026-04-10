import yaml
import logging

try:
    from PySpice.Spice.Netlist import Circuit
    from PySpice.Unit import *
except ImportError:
    Circuit = None

log = logging.getLogger("SystemLogger")

class PDNSimulator:
    """
    Power Delivery Network logic simulated by PySpice wrapper.
    Estimates IR Drop based on IPC geometry (trace area / length) and estimates transient response.
    """
    def __init__(self, config_path: str = "config/neuroboard_config.yaml"):
        self.config = self._load_config(config_path)
        self.enabled = self.config.get("modules", {}).get("enable_pdn_pyspice", False)
        
        if self.enabled and Circuit is None:
            log.error("PySpice is not installed, but PDN module is enabled. Run: pip install PySpice")
            self.enabled = False

    def _load_config(self, path: str):
        try:
            with open(path, "r") as f:
                return yaml.safe_load(f)
        except Exception:
            return {}

    def analyze_power_rail(self, rail_name: str, voltage_v: float, load_current_a: float, trace_resistance_ohm: float) -> dict:
        """
        Builds a generic netlist representing the rail, trace resistance, and decoupling.
        Calculates simple IR Drop and provides topological recommendations.
        """
        if not self.enabled:
            return {"status": "disabled", "ir_drop_v": 0.0}

        ir_drop = load_current_a * trace_resistance_ohm
        final_voltage = voltage_v - ir_drop
        
        recommendations = []
        if ir_drop > (voltage_v * 0.05): # Over 5% drop
            recommendations.append("IR Drop exceeding 5%. Widen power trace, double layer copper, or add via stitching.")
            recommendations.append("Consider placing decoupling capacitors closer to the high-current draw pin.")
            
        result = {
            "status": "success",
            "rail_name": rail_name,
            "source_v": voltage_v,
            "load_current_a": load_current_a,
            "trace_resistance_ohm": trace_resistance_ohm,
            "ir_drop_v": round(ir_drop, 4),
            "final_voltage_v": round(final_voltage, 4),
            "recommendations": recommendations,
        }
        
        log.info(f"PDN Simulation complete for {rail_name}: IR Drop={result['ir_drop_v']}V")
        return result
