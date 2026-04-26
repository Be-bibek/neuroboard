import json
import os
import logging

SETTINGS_FILE = "neuroboard_settings.json"

DEFAULT_SETTINGS = {
    "agent": {
        "strict_mode": True,
        "review_policy": "auto",
        "max_iterations": 5,
        "tool_execution_mode": "auto"
    },
    "models": {
        "default_model": "Gemini 1.5 Flash",
        "fast_model": "Gemini 1.5 Flash",
        "reasoning_model": "Claude 3.5 Sonnet",
        "temperature": 0.2,
        "max_tokens": 4096
    },
    "pcb": {
        "default_trace_width": 0.25,
        "impedance_target": "90ohm",
        "power_trace_min_width": 0.5,
        "via_stitch_density": "medium",
        "signal_types": ["power", "diff_pair", "control"],
        "constraint_mode": "strict_physics"
    }
}

class SettingsManager:
    def __init__(self):
        self.settings = DEFAULT_SETTINGS.copy()
        self.load()

    def load(self):
        if os.path.exists(SETTINGS_FILE):
            try:
                with open(SETTINGS_FILE, "r") as f:
                    data = json.load(f)
                    self._merge(self.settings, data)
            except Exception as e:
                logging.error(f"Failed to load settings: {e}")

    def save(self):
        try:
            with open(SETTINGS_FILE, "w") as f:
                json.dump(self.settings, f, indent=2)
        except Exception as e:
            logging.error(f"Failed to save settings: {e}")

    def _merge(self, base, update):
        for k, v in update.items():
            if isinstance(v, dict) and k in base:
                self._merge(base[k], v)
            else:
                base[k] = v

    def update(self, new_settings):
        self._merge(self.settings, new_settings)
        self.save()

    def get(self):
        return self.settings

settings_manager = SettingsManager()
