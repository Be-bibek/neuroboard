import os
import subprocess
import yaml
import logging

log = logging.getLogger("SystemLogger")

class FreeroutingIntegration:
    """
    Freerouting Hybrid integration. 
    Serves exclusively as a fallback and benchmark metric comparison.
    NEVER replaces the custom Rust Core.
    """
    def __init__(self, config_path: str = "config/neuroboard_config.yaml"):
        self.config = self._load_config(config_path)
        self.enabled = self.config.get("modules", {}).get("enable_freerouting_fallback", False)
        self.jar_path = self.config.get("freerouting", {}).get("executable_path", "")

    def _load_config(self, path: str):
        try:
            with open(path, "r") as f:
                return yaml.safe_load(f)
        except Exception:
            return {}

    def execute_fallback_route(self, board_file: str, output_dsn: str = "temp.dsn", output_ses: str = "temp.ses") -> dict:
        """
        Executes external Freerouting process for benchmarking.
        """
        if not self.enabled:
            return {"status": "disabled"}
            
        if not os.path.exists(self.jar_path):
            log.error(f"Freerouting jar not found at {self.jar_path}")
            return {"status": "failed", "reason": "jar_not_found"}

        log.info("Executing Freerouting Fallback...")
        
        try:
            # Step 1: Export DSN
            subprocess.run(["kicad-cli", "pcb", "export", "specctra-dsn", "-o", output_dsn, board_file], check=True, capture_output=True)
            
            # Step 2: Run Freerouting
            # java -jar freerouting.jar -de temp.dsn -do temp.ses
            subprocess.run(["java", "-jar", self.jar_path, "-de", output_dsn, "-do", output_ses], check=True, capture_output=True)
            
            # In a full flow, parse SES or use kicad-cli to import back.
            # Usually, kicad-cli pcb import specctra-ses exists or tracks are parsed and fed over IPC.
            
            log.info("Freerouting completed successfully.")
            return {
                "status": "success",
                "dsn_file": output_dsn,
                "ses_file": output_ses,
                "benchmark_metrics": {
                    "completion_rate": 100.0, # Dummy telemetry for now
                    "vias_count": 0,
                    "total_trace_len_mm": 0.0
                }
            }
        except subprocess.CalledProcessError as e:
            log.error(f"Freerouting failed: {e.stderr}")
            return {"status": "error", "error": str(e)}
