import yaml
import logging
import numpy as np

try:
    import skrf as rf
    from skrf.media import Freespace
except ImportError:
    rf = None

log = logging.getLogger("SystemLogger")

class SParameterAnalysis:
    """
    Signal Integrity Validator using scikit-rf (skrf).
    Simulates S-parameters (S11 Return Loss, S21 Insertion Loss) for differential pairs.
    """
    def __init__(self, config_path: str = "config/neuroboard_config.yaml"):
        self.config = self._load_config(config_path)
        self.enabled = self.config.get("modules", {}).get("enable_si_scikit_rf", False)
        
        if self.enabled and rf is None:
            log.error("scikit-rf is not installed, but SI module is enabled. Run: pip install scikit-rf")
            self.enabled = False

    def _load_config(self, path: str):
        try:
            with open(path, "r") as f:
                return yaml.safe_load(f)
        except Exception:
            return {}

    def simulate_differential_pair(self, length_mm: float, frequency_ghz: float = 5.0) -> dict:
        """
        Mock simulation of a simplistic transmission line based on geometry.
        In a full implementation, models a generic microstrip differential line.
        """
        if not self.enabled:
            return {"status": "disabled", "s11": 0.0, "s21": 0.0, "impedance": 0.0}
            
        trace_width = self.config.get("routing", {}).get("trace_width_mm", 0.15)
        clearance = self.config.get("routing", {}).get("clearance_mm", 0.15)
        target_ohm = self.config.get("routing", {}).get("differential_impedance_ohm", 100)
        
        # In a real scikit-rf media application:
        # media = rf.media.DefinedGammaZ0(...)
        # line = media.line(d=length_mm/1000, unit='m')
        
        # Here we do a simplified deterministic heuristic indicating geometry loss:
        # Calculate approximate impedance Z_diff
        # (Assuming FR4, e_r = 4.3, h=0.1mm)
        e_r = self.config.get("stackup", {}).get("dielectric_constant", 4.3)
        h = self.config.get("stackup", {}).get("dielectric_thickness_mm", 0.1)
        
        # Empirical approximation for microstrip diff pairs
        # Very rough estimation just to feed the optimization engine.
        z0 = (87.0 / np.sqrt(e_r + 1.41)) * np.log((5.98 * h) / (0.8 * trace_width))
        z_diff = z0 * (1 - 0.48 * np.exp(-0.96 * (clearance / h)))
        
        # Return Loss (S11) - How much bounces back due to mismatch
        reflection_coeff = abs((z_diff - target_ohm) / (z_diff + target_ohm))
        s11_db = 20 * np.log10(max(reflection_coeff, 1e-6))
        
        # Insertion Loss (S21) - Path loss roughly proportional to length and frequency
        loss_factor = 0.02 * length_mm * (frequency_ghz / 5.0)
        s21_db = -loss_factor

        recommendations = []
        if z_diff > target_ohm + 10:
            recommendations.append("Increase trace width or decrease gap.")
        elif z_diff < target_ohm - 10:
            recommendations.append("Decrease trace width or increase gap.")
            
        result = {
            "status": "success",
            "frequency_ghz": frequency_ghz,
            "simulated_z_diff": round(z_diff, 2),
            "target_z_diff": target_ohm,
            "s11_db": round(s11_db, 2),
            "s21_db": round(s21_db, 2),
            "recommendations": recommendations
        }
        log.info(f"SI Simulation complete: Z_diff={result['simulated_z_diff']} ohm, S11={result['s11_db']} dB")
        return result
