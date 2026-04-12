"""
ai_core/copilot/intent_parser.py
=================================
Natural Language → Structured Hardware Specification.

Takes a user prompt like:
  "Create a Raspberry Pi AI HAT with Hailo-8 and dual SD card slots"

And produces a deterministic JSON spec:
  {
    "form_factor": "raspberry_pi_hat",
    "accelerator": "hailo_8",
    "features": ["dual_sd_card"],
    ...
  }

This is a rule-based + keyword extraction parser.
For production, this would be replaced with LLM-backed intent extraction.
"""

import re
import logging
from typing import Dict, List, Any

log = logging.getLogger("SystemLogger")


# ---------------------------------------------------------------------------
# Knowledge base: keyword → structured mapping
# ---------------------------------------------------------------------------

FORM_FACTORS = {
    "raspberry pi hat":  {"id": "raspberry_pi_hat",  "board_w": 65.0, "board_h": 56.5},
    "rpi hat":           {"id": "raspberry_pi_hat",  "board_w": 65.0, "board_h": 56.5},
    "pi hat":            {"id": "raspberry_pi_hat",  "board_w": 65.0, "board_h": 56.5},
    "hat+":              {"id": "raspberry_pi_hat_plus", "board_w": 65.0, "board_h": 56.5},
    "hat plus":          {"id": "raspberry_pi_hat_plus", "board_w": 65.0, "board_h": 56.5},
    "arduino shield":    {"id": "arduino_shield",    "board_w": 68.6, "board_h": 53.3},
}

ACCELERATORS = {
    "hailo-8":   {"id": "hailo_8",  "tops": 26, "interface": "PCIe_Gen3_x1", "package": "BGA"},
    "hailo 8":   {"id": "hailo_8",  "tops": 26, "interface": "PCIe_Gen3_x1", "package": "BGA"},
    "hailo-8l":  {"id": "hailo_8l", "tops": 13, "interface": "PCIe_Gen3_x1", "package": "BGA"},
    "hailo 8l":  {"id": "hailo_8l", "tops": 13, "interface": "PCIe_Gen3_x1", "package": "BGA"},
    "coral tpu": {"id": "coral_tpu","tops": 4,  "interface": "PCIe_Gen2_x1", "package": "M.2"},
}

FEATURES = {
    "sd card":       {"id": "sd_card_slot",   "count": 1},
    "dual sd":       {"id": "sd_card_slot",   "count": 2},
    "two sd":        {"id": "sd_card_slot",   "count": 2},
    "micro sd":      {"id": "sd_card_slot",   "count": 1},
    "usb":           {"id": "usb_port",       "count": 1},
    "dual usb":      {"id": "usb_port",       "count": 2},
    "ethernet":      {"id": "ethernet_port",  "count": 1},
    "wifi":          {"id": "wifi_module",     "count": 1},
    "bluetooth":     {"id": "bluetooth_module","count": 1},
    "display":       {"id": "display_connector","count": 1},
    "camera":        {"id": "camera_connector","count": 1},
    "led":           {"id": "status_led",     "count": 1},
    "fan":           {"id": "fan_connector",  "count": 1},
    "heatsink":      {"id": "heatsink_pad",   "count": 1},
    "poe":           {"id": "poe_module",     "count": 1},
    "rtc":           {"id": "rtc_module",     "count": 1},
    "m.2":           {"id": "m2_connector",   "count": 1},
}


class IntentParser:
    """
    Deterministic rule-based intent parser.
    Extracts form factor, accelerator, features, and constraints
    from a natural language hardware design prompt.
    """

    def parse(self, prompt: str) -> Dict[str, Any]:
        """Parse a natural language prompt into a structured hardware specification."""
        prompt_lower = prompt.lower().strip()
        log.info(f"[IntentParser] Parsing: '{prompt[:80]}...'")

        spec = {
            "raw_prompt": prompt,
            "form_factor": None,
            "accelerator": None,
            "features": [],
            "interfaces": [],
            "power_requirements": ["5V", "3.3V"],  # Default for RPi HATs
            "constraints": {},
            "mandatory_components": [],   # Always required for the form factor
        }

        # --- 1. Detect Form Factor ---
        for keyword, info in FORM_FACTORS.items():
            if keyword in prompt_lower:
                spec["form_factor"] = info
                # HAT form factors always need these
                spec["mandatory_components"] = [
                    "40pin_gpio_header",
                    "hat_eeprom",
                    "id_pullup_resistors",
                    "mounting_holes",
                    "decoupling_caps",
                ]
                spec["constraints"] = {
                    "board_width_mm": info["board_w"],
                    "board_height_mm": info["board_h"],
                    "impedance_differential_ohm": 100,
                    "mounting_holes": [
                        {"x": 3.5, "y": 3.5},
                        {"x": 61.5, "y": 3.5},
                        {"x": 3.5, "y": 52.5},
                        {"x": 61.5, "y": 52.5},
                    ],
                }
                break

        # --- 2. Detect Accelerator ---
        for keyword, info in ACCELERATORS.items():
            if keyword in prompt_lower:
                spec["accelerator"] = info
                spec["interfaces"].append("PCIe")
                # Hailo connects via FPC on the real AI HAT+
                if "hailo" in keyword:
                    spec["mandatory_components"].append("pcie_fpc_connector")
                break

        # --- 3. Detect Additional Features ---
        detected_features = []
        seen_feat_ids: dict = {}  # feat_id → highest count seen so far
        # Sort by keyword length descending so "dual sd" beats "sd card"
        for keyword in sorted(FEATURES.keys(), key=len, reverse=True):
            info = FEATURES[keyword]
            if keyword in prompt_lower:
                feat_id = info["id"]
                count   = info["count"]
                existing = seen_feat_ids.get(feat_id, 0)
                if count > existing:
                    seen_feat_ids[feat_id] = count

        for feat_id, count in seen_feat_ids.items():
            src = next(v for v in FEATURES.values() if v["id"] == feat_id)
            detected_features.append({**src, "count": count})

        spec["features"] = detected_features

        # --- 4. Infer Interfaces ---
        if any(f["id"] == "sd_card_slot" for f in detected_features):
            if "SDIO" not in spec["interfaces"]:
                spec["interfaces"].append("SDIO")
        if any(f["id"] == "usb_port" for f in detected_features):
            if "USB" not in spec["interfaces"]:
                spec["interfaces"].append("USB")
        if spec["accelerator"]:
            if "PCIe" not in spec["interfaces"]:
                spec["interfaces"].append("PCIe")

        # --- 5. Default form factor if none detected ---
        if spec["form_factor"] is None:
            log.warning("[IntentParser] No form factor detected. Defaulting to Raspberry Pi HAT.")
            spec["form_factor"] = FORM_FACTORS["raspberry pi hat"]
            spec["mandatory_components"] = [
                "40pin_gpio_header", "hat_eeprom",
                "id_pullup_resistors", "mounting_holes", "decoupling_caps",
            ]
            spec["constraints"] = {
                "board_width_mm": 65.0,
                "board_height_mm": 56.5,
                "impedance_differential_ohm": 100,
            }

        log.info(f"[IntentParser] Extracted: form={spec['form_factor']['id']}, "
                 f"accel={spec['accelerator']['id'] if spec['accelerator'] else 'none'}, "
                 f"features={[f['id'] for f in spec['features']]}")
        return spec
