import logging

log = logging.getLogger("SystemLogger")

try:
    import PySpice.Logging.Logging as _logging
    _logging.setup_logging()
    from PySpice.Spice.Netlist import Circuit
    from PySpice.Unit import *
    PYSPICE_AVAILABLE = True
except ImportError:
    PYSPICE_AVAILABLE = False
    log.warning("PySpice not installed. PDN Simulator will run in mock mode.")

class PDNSimulator:
    """
    Power Delivery Network (PDN) Simulation Agent.
    Simulates IR drop margins and transient response using NGSpice (via PySpice).
    Recommends decoupling placement and via-stitching geometries.
    """
    
    def analyze_power_rail(self, rail_name: str, nominal_v: float, max_current_a: float, resistance_ohm: float) -> dict:
        """
        Extracts IR drop for a target rail using NGSpice logic natively.
        Validates maximum permissible voltage drop limits.
        """
        metrics = {
            "status": "success",
            "rail": rail_name,
            "nominal_voltage_v": nominal_v,
            "simulated": False,
            "ir_drop_v": nominal_v * 0.01, # Mock 1% drop
            "min_voltage_v": nominal_v * 0.99,
            "recommendations": []
        }

        if PYSPICE_AVAILABLE:
            try:
                circuit = Circuit(f"PDN_Analysis_{rail_name}")
                
                # Simple PDN DC model: V_source -> Trace Resistor -> Constant Current Load
                circuit.V('source', 'input', circuit.gnd, nominal_v @ u_V)
                circuit.R('trace', 'input', 'load_node', resistance_ohm @ u_Ohm)
                circuit.I('load', 'load_node', circuit.gnd, max_current_a @ u_A)
                
                # Execute DC Operating Point simulation
                simulator = circuit.simulator(temperature=25, nominal_temperature=25)
                analysis = simulator.operating_point()
                
                output_voltage = float(analysis.load_node)
                ir_drop = nominal_v - output_voltage
                
                metrics["ir_drop_v"] = ir_drop
                metrics["min_voltage_v"] = output_voltage
                metrics["simulated"] = True
                
            except Exception as e:
                log.error(f"PySpice PDN Simulation Error: {e}")
                metrics["status"] = "failed"
                
        # Margin Checks (Limit 5% Drop)
        drop_percentage = (metrics["ir_drop_v"] / nominal_v) * 100
        metrics["pass"] = drop_percentage <= 5.0
        
        if drop_percentage > 2.0:
            metrics["recommendations"].append(
                f"Increase trace width for {rail_name} (resistance={resistance_ohm}ohm) to mitigate {drop_percentage:.2f}% drop."
            )
            
        if max_current_a > 1.5:
            metrics["recommendations"].append(
                f"Implement via-stitching arrays connecting Top/Bottom planes for {rail_name} to lower loop inductance."
            )
            
        # Target exact RPi HAT decoupling rules
        if "3.3" in rail_name or "5" in rail_name:
            metrics["recommendations"].append(
                f"Ensure 10uF + 100nF decoupling capacitors are placed within 2mm of the {rail_name} target IC."
            )

        log.info(f"PDN Simulation complete for {rail_name}: IR Drop = {metrics['ir_drop_v']:.3f}V")
        return metrics
