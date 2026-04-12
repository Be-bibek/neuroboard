import yaml
import logging

log = logging.getLogger("SystemLogger")

class ConstraintManager:
    """
    Manages routing and electrical constraints for the NeuroBoard pipeline.
    Loads configurations from the YAML stackup file and exposes properties
    for the routing engine, DRC, and SI validation logic.
    """

    def __init__(self, config_path: str = "config/stackup.yaml"):
        self.config_path = config_path
        self.stackup = {}
        self.impedance_targets = {}
        self.routing_rules = {}
        self._load_config()

    def _load_config(self):
        try:
            with open(self.config_path, "r") as f:
                config_data = yaml.safe_load(f)

            if config_data:
                self.stackup = config_data.get("stackup", {})
                self.impedance_targets = config_data.get("impedance_targets", {})
                self.routing_rules = config_data.get("routing_rules", {})
                log.info(f"Loaded constraints from {self.config_path}")
        except Exception as e:
            log.error(f"Failed to load constraint configuration from {self.config_path}: {e}")

    @property
    def diff_impedance_target(self) -> float:
        return self.impedance_targets.get("differential", {}).get("target_ohm", 100.0)

    @property
    def diff_trace_width(self) -> float:
        return self.impedance_targets.get("differential", {}).get("trace_width_mm", 0.15)

    @property
    def diff_trace_spacing(self) -> float:
        return self.impedance_targets.get("differential", {}).get("trace_spacing_mm", 0.15)

    @property
    def single_ended_impedance_target(self) -> float:
        return self.impedance_targets.get("single_ended", {}).get("target_ohm", 50.0)

    @property
    def min_clearance(self) -> float:
        return self.routing_rules.get("min_clearance_mm", 0.15)

    @property
    def length_matching_tolerance(self) -> float:
        return self.routing_rules.get("length_matching_tolerance_mm", 0.1)

    @property
    def via_drill(self) -> float:
        return self.routing_rules.get("via_drill_mm", 0.3)

    @property
    def via_pad(self) -> float:
        return self.routing_rules.get("via_pad_mm", 0.6)

    def get_layer_count(self) -> int:
        return self.stackup.get("layer_count", 4)
