"""
ai_core/copilot/component_intelligence.py
==========================================
Component Intelligence Engine.

Takes a structured hardware specification (from IntentParser)
and returns the EXACT list of electronic components needed,
with real part numbers, footprints, and connection metadata.

This is the "knowledge base" of NeuroBoard — it knows what
components are needed for each type of design, how they connect,
and what constraints they impose.
"""

import logging
from typing import Dict, List, Any

log = logging.getLogger("SystemLogger")


# ---------------------------------------------------------------------------
# Component Database — Real parts with real footprints
# ---------------------------------------------------------------------------

COMPONENT_DB = {

    # ── GPIO Header ─────────────────────────────────────────────────────
    "40pin_gpio_header": {
        "description": "Raspberry Pi 40-pin GPIO Header (2x20, 2.54mm pitch)",
        "ref_prefix": "J",
        "skidl_lib": "Connector_Generic",
        "skidl_symbol": "Conn_02x20_Odd_Even",
        "footprint": "Connector_PinSocket_2.54mm:PinSocket_2x20_P2.54mm_Vertical",
        "value": "GPIO_40",
        "category": "connector",
        "placement": {"edge": "top", "x_offset_mm": 29.0, "y_offset_mm": 3.5},
        "power_pins": {"5V": ["2", "4"], "3V3": ["1", "17"],
                       "GND": ["6", "9", "14", "20", "25", "30", "34", "39"]},
        "signal_pins": {"ID_SD": "27", "ID_SC": "28"},
    },

    # ── HAT EEPROM ──────────────────────────────────────────────────────
    "hat_eeprom": {
        "description": "AT24C32 / 24LC32 I2C EEPROM for HAT identification",
        "ref_prefix": "U",
        "skidl_lib": "Memory_EEPROM",
        "skidl_symbol": "24LC32",
        "footprint": "Package_SO:SOIC-8_3.9x4.9mm_P1.27mm",
        "value": "24LC32",
        "category": "ic",
        "placement": {"near": "gpio_header", "distance_mm": 8.0},
        "connections": {
            "SDA": {"pin": "5", "net": "ID_SD"},
            "SCL": {"pin": "6", "net": "ID_SC"},
            "VCC": {"pin": "8", "net": "+3.3V"},
            "GND": {"pins": ["1", "2", "3", "4"], "net": "GND"},
            "WP":  {"pin": "7", "net": "GND"},
        },
    },

    # ── I2C Pull-up Resistors ───────────────────────────────────────────
    "id_pullup_resistors": {
        "description": "3.9kΩ pull-up resistors for ID_SD and ID_SC (HAT spec mandatory)",
        "ref_prefix": "R",
        "skidl_lib": "Device",
        "skidl_symbol": "R",
        "footprint": "Resistor_SMD:R_0402_1005Metric",
        "value": "3.9k",
        "category": "passive",
        "count": 2,
        "connections": [
            {"pin1_net": "+3.3V", "pin2_net": "ID_SD"},
            {"pin1_net": "+3.3V", "pin2_net": "ID_SC"},
        ],
    },

    # ── Decoupling Capacitors ───────────────────────────────────────────
    "decoupling_caps": {
        "description": "100nF decoupling capacitors for power rails",
        "ref_prefix": "C",
        "skidl_lib": "Device",
        "skidl_symbol": "C",
        "footprint": "Capacitor_SMD:C_0402_1005Metric",
        "value": "100nF",
        "category": "passive",
        "count": 4,
        "connections": [
            {"pin1_net": "+5V",   "pin2_net": "GND"},
            {"pin1_net": "+3.3V", "pin2_net": "GND"},
            {"pin1_net": "+3.3V", "pin2_net": "GND"},
            {"pin1_net": "+5V",   "pin2_net": "GND"},
        ],
    },

    # ── Mounting Holes ──────────────────────────────────────────────────
    "mounting_holes": {
        "description": "M2.5 mounting holes at HAT standard positions",
        "ref_prefix": "H",
        "skidl_lib": "Mechanical",
        "skidl_symbol": "MountingHole",
        "footprint": "MountingHole:MountingHole_2.7mm_M2.5",
        "value": "MountingHole",
        "category": "mechanical",
        "count": 4,
        "positions_mm": [
            {"x": 3.5, "y": 3.5},
            {"x": 61.5, "y": 3.5},
            {"x": 3.5, "y": 52.5},
            {"x": 61.5, "y": 52.5},
        ],
    },

    # ── PCIe FPC Connector ──────────────────────────────────────────────
    "pcie_fpc_connector": {
        "description": "16-pin 0.5mm FPC connector for Raspberry Pi 5 PCIe ribbon cable",
        "ref_prefix": "J",
        "skidl_lib": "Connector_Generic",
        "skidl_symbol": "Conn_01x16",
        "footprint": "Connector_FFC-FPC:Hirose_FH12-16S-0.5SH_1x16-1MP_P0.50mm_Horizontal",
        "value": "FPC_PCIe",
        "category": "connector",
        "placement": {"edge": "left", "x_offset_mm": 0.0, "y_offset_mm": 21.0},
        "differential_pairs": {
            "PCIE_TX": {"pos_pin": "4", "neg_pin": "5"},
            "PCIE_RX": {"pos_pin": "7", "neg_pin": "8"},
        },
        "power_pins": {"GND": ["1", "16"]},
    },

    # ── M.2 M-Key Connector ────────────────────────────────────────────
    "m2_connector": {
        "description": "M.2 M-Key connector for AI accelerator module",
        "ref_prefix": "J",
        "skidl_lib": "Connector_Generic",
        "skidl_symbol": "Conn_02x38_Odd_Even",
        "footprint": "Connector:M.2_M_Key",
        "value": "M2_M_Key",
        "category": "connector",
        "placement": {"center": True, "x_offset_mm": 32.5, "y_offset_mm": 25.0},
        "differential_pairs": {
            "PCIE_TX": {"pos_pin": "41", "neg_pin": "43"},
            "PCIE_RX": {"pos_pin": "47", "neg_pin": "49"},
        },
        "power_pins": {
            "3V3": ["2", "4", "70", "72", "74"],
            "GND": ["1", "3", "5", "33", "39", "45", "51", "57", "71", "73", "75"],
        },
    },

    # ── SD Card Slot ────────────────────────────────────────────────────
    "sd_card_slot": {
        "description": "Micro SD card slot with SDIO interface",
        "ref_prefix": "J",
        "skidl_lib": "Connector",
        "skidl_symbol": "Micro_SD_Card",
        "footprint": "Connector_Card:microSD_HC_Molex_104031-0811",
        "value": "MicroSD",
        "category": "connector",
        "placement": {"edge": "bottom"},
        "signal_pins": {
            "DAT0": "7", "DAT1": "8", "DAT2": "1", "DAT3": "2",
            "CMD": "3", "CLK": "5",
        },
        "power_pins": {"3V3": ["4"], "GND": ["6"]},
    },

    # ── Status LED ──────────────────────────────────────────────────────
    "status_led": {
        "description": "Green indicator LED with current-limiting resistor",
        "ref_prefix": "D",
        "skidl_lib": "Device",
        "skidl_symbol": "LED",
        "footprint": "LED_SMD:LED_0402_1005Metric",
        "value": "Green",
        "category": "passive",
        "series_resistor": {"value": "330", "footprint": "Resistor_SMD:R_0402_1005Metric"},
    },

    # ── Fan Connector ───────────────────────────────────────────────────
    "fan_connector": {
        "description": "2-pin fan connector for active cooling",
        "ref_prefix": "J",
        "skidl_lib": "Connector_Generic",
        "skidl_symbol": "Conn_01x02",
        "footprint": "Connector_PinHeader_2.54mm:PinHeader_1x02_P2.54mm_Vertical",
        "value": "FAN",
        "category": "connector",
        "power_pins": {"5V": ["1"], "GND": ["2"]},
    },
}


class ComponentIntelligence:
    """
    Takes a structured hardware specification and determines the exact
    list of components needed, with full metadata for schematic generation.
    """

    def __init__(self):
        self.db = COMPONENT_DB

    def suggest_components(self, spec: Dict[str, Any]) -> Dict[str, Any]:
        """
        Given a parsed intent specification, return a full component manifest.

        Returns:
            {
                "components": [...],        # List of component dicts with metadata
                "bom_preview": [...],       # Human-readable BOM
                "total_count": int,
                "interfaces_used": [...],
                "warnings": [...]
            }
        """
        components = []
        warnings = []

        # 1. Add all mandatory components for the form factor
        for comp_id in spec.get("mandatory_components", []):
            if comp_id in self.db:
                entry = dict(self.db[comp_id])
                entry["component_id"] = comp_id
                entry["source"] = "mandatory"
                components.append(entry)
            else:
                warnings.append(f"Unknown mandatory component: {comp_id}")

        # 2. Add accelerator-specific components
        accel = spec.get("accelerator")
        if accel:
            # The real AI HAT+ has the Hailo chip ON the board (BGA),
            # but our design uses M.2 or FPC for modularity.
            if accel.get("package") == "BGA":
                # For FPC-based connection (like the real AI HAT+)
                if "pcie_fpc_connector" not in [c.get("component_id") for c in components]:
                    entry = dict(self.db["pcie_fpc_connector"])
                    entry["component_id"] = "pcie_fpc_connector"
                    entry["source"] = "accelerator_interface"
                    components.append(entry)

        # 3. Add feature-requested components
        for feature in spec.get("features", []):
            feat_id = feature.get("id")
            count   = feature.get("count", 1)
            if feat_id in self.db:
                # Add a single entry carrying the resolved count
                entry = dict(self.db[feat_id])
                entry["component_id"] = feat_id
                entry["count"]        = count   # override db default
                entry["source"]       = "user_feature"
                components.append(entry)
            else:
                warnings.append(f"No component mapping for feature: {feat_id}")

        # 4. Generate BOM preview
        bom = []
        ref_counters = {}
        for comp in components:
            prefix = comp.get("ref_prefix", "X")
            count = comp.get("count", 1)
            ref_counters[prefix] = ref_counters.get(prefix, 0) + count

            bom.append({
                "component": comp.get("description", comp.get("component_id")),
                "quantity": count,
                "footprint": comp.get("footprint", "TBD"),
                "value": comp.get("value", ""),
            })

        result = {
            "components": components,
            "bom_preview": bom,
            "total_count": sum(c.get("count", 1) for c in components),
            "interfaces_used": spec.get("interfaces", []),
            "warnings": warnings,
        }

        log.info(f"[ComponentIntelligence] Suggested {result['total_count']} components "
                 f"across {len(components)} entries. Warnings: {len(warnings)}")
        return result

    def get_component(self, component_id: str) -> Dict[str, Any]:
        """Fetch a single component definition by ID."""
        return self.db.get(component_id)
