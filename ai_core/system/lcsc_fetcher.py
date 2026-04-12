"""
ai_core/system/lcsc_fetcher.py
==============================
JLC2KiCadLib integration for automated symbol and footprint retrieval from LCSC.
Exposed for the Tauri UI for downloading arbitrary components.
"""

import os
import logging
import subprocess
from pathlib import Path

log = logging.getLogger("SystemLogger")

import sys
import shutil
import yaml

log = logging.getLogger("SystemLogger")

class LcscFetcher:
    def __init__(self, config_path: str = "config/neuroboard_config.yaml"):
        self.config = self._load_config(config_path)
        
        lib_cfg = self.config.get("library", {})
        self.output_dir = lib_cfg.get("base_path", str(Path(__file__).resolve().parent.parent.parent / "lib"))
        self.tool_path = lib_cfg.get("tools", {}).get("jlc2kicadlib")
        
    def _load_config(self, path: str) -> dict:
        try:
            with open(path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
        except Exception:
            return {}

    def _find_tool(self) -> str:
        """Automatic discovery with fallback to system PATH."""
        if self.tool_path and os.path.exists(self.tool_path):
            return self.tool_path
            
        # Fallback 1: System PATH
        path_tool = shutil.which("JLC2KiCadLib") or shutil.which("JLC2KiCadLib.exe")
        if path_tool:
            return path_tool
            
        # Fallback 2: Common Windows AppData location (specific to the user environment)
        appdata_path = os.path.join(os.environ.get("APPDATA", ""), "Python", "Python314", "Scripts", "JLC2KiCadLib.exe")
        if os.path.exists(appdata_path):
            return appdata_path
            
        return "JLC2KiCadLib" # Last resort: hope it's in path

    def fetch_component(self, lcsc_part_number: str) -> dict:
        """
        Uses JLC2KiCadLib to fetch the component and footprint.
        Returns a dictionary with paths to the downloaded files.
        """
        log.info(f"[LcscFetcher] Fetching LCSC part: {lcsc_part_number}")
        
        # Ensure lib directory exists
        os.makedirs(self.output_dir, exist_ok=True)
        
        tool = self._find_tool()

        try:
            log.debug(f"[LcscFetcher] Using tool: {tool}")
            result = subprocess.run(
                [tool, lcsc_part_number, "-dir", self.output_dir],
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode != 0:
                log.error(f"[LcscFetcher] Failed to fetch {lcsc_part_number}: {result.stderr}")
                return {"status": "error", "error": result.stderr}
                
            log.info(f"[LcscFetcher] Successfully fetched {lcsc_part_number}")
            
            return {
                "status": "success",
                "lcsc_part": lcsc_part_number,
                "output_dir": self.output_dir,
                "tool_used": tool
            }
            
        except Exception as e:
            log.error(f"[LcscFetcher] Exception while fetching {lcsc_part_number}: {e}")
            return {"status": "error", "error": str(e)}
