"""
ai_core/schematic/modules.py
==============================
Phase 7: Parametric Hardware DSL Modules

Each class is a self-contained "Recipe" that:
  1. Instantiates the required Parts via SKiDL.
  2. Wires them to global power nets from PowerDomain.
  3. Exposes net names and placement metadata to downstream engines.

Adding a new peripheral = adding a new subclass here.
No changes required to the generator or orchestrator.

Inspired by:
  - SKiDL (schematic-as-code): https://github.com/devbisme/skidl
  - Atopile (hardware-as-code philosophy): https://github.com/atopile/atopile
"""

from __future__ import annotations

import logging
from typing import Any, Dict

from .foundation import NeuroModule, PowerDomain, SKIDL_OK, _MockPart

log = logging.getLogger("SystemLogger")

# Guard for SKiDL imports
if SKIDL_OK:
    from skidl import Part, Net  # type: ignore


# ===========================================================================
# 1. GPIO Header — Raspberry Pi 40-pin (mandatory for all HAT profiles)
# ===========================================================================

class GPIOHeaderModule(NeuroModule):
    """
    Raspberry Pi 2×20 50-pin GPIO header.
    Hard-anchored to the top edge of the board per HAT+ spec.

    Placement: ANCHORED (never moved by the physics solver)
    Thermal:   LOW
    Interface: GPIO / SPI / I2C / UART
    """

    def build(self) -> None:
        self._set_metadata(
            placement_hint = "anchor_top_edge",
            thermal_class  = "low",
            interface      = "GPIO",
            anchor_x_mm    = 29.0,   # HAT+ spec: pin-1 centre from left edge
            anchor_y_mm    = 3.5,    # HAT+ spec: pin-1 centre from top edge
        )

        if not SKIDL_OK:
            log.debug(f"[{self.name}] MOCK GPIO header created.")
            return

        j = Part(
            "Connector_Generic", "Conn_02x20_Odd_Even",
            footprint="Connector_PinSocket_2.54mm:PinSocket_2x20_P2.54mm_Vertical"
        )
        j.ref = "J1"

        pwr_5v   = PowerDomain.get("+5V")
        pwr_3v3  = PowerDomain.get("+3V3")
        gnd      = PowerDomain.get("GND")
        id_sd_n  = PowerDomain.get("ID_SD")
        id_sc_n  = PowerDomain.get("ID_SC")

        pwr_5v  += j["2"], j["4"]
        pwr_3v3 += j["1"], j["17"]
        for p in ["6", "9", "14", "20", "25", "30", "34", "39"]:
            gnd += j[p]
        id_sd_n += j["27"]
        id_sc_n += j["28"]

        self.parts.append(j)
        self.metadata["net_names"] = ["ID_SD", "ID_SC", "+3V3", "+5V", "GND"]
        log.info(f"[{self.name}] GPIO header (J1) placed.")


# ===========================================================================
# 2. HAT EEPROM — mandatory for HAT+ identification
# ===========================================================================

class HATEepromModule(NeuroModule):
    """
    AT24C32 I2C EEPROM wired to ID_SD / ID_SC pins.
    Must be present for the Raspberry Pi to recognise the HAT.

    Includes 3.9 kΩ pull-up resistors as specified in the HAT spec.
    """

    def build(self) -> None:
        self._set_metadata(
            placement_hint = "near_gpio",
            thermal_class  = "low",
            interface      = "I2C",
        )

        if not SKIDL_OK:
            log.debug(f"[{self.name}] MOCK EEPROM created.")
            return

        eeprom = Part(
            "Memory_EEPROM", "24LC32",
            footprint="Package_SO:SOIC-8_3.9x4.9mm_P1.27mm",
            value="24LC32"
        )
        eeprom.ref = "U1"

        pwr_3v3  = PowerDomain.get("+3V3")
        gnd      = PowerDomain.get("GND")
        id_sd_n  = PowerDomain.get("ID_SD")
        id_sc_n  = PowerDomain.get("ID_SC")
        pwr_3v3 += eeprom["8"]
        gnd     += eeprom["1"], eeprom["2"], eeprom["3"], eeprom["4"], eeprom["7"]
        id_sd_n += eeprom["5"]
        id_sc_n += eeprom["6"]

        # 3.9 kΩ pull-up resistors (HAT spec mandatory)
        for net_name in ["ID_SD", "ID_SC"]:
            r = Part("Device", "R", footprint="Resistor_SMD:R_0402_1005Metric", value="3.9k")
            r_pwr = PowerDomain.get("+3V3")
            r_sig = PowerDomain.get(net_name)
            r_pwr += r["1"]
            r_sig += r["2"]
            self.parts.append(r)

        self._add_decoupling("+3V3", count=1)
        self.parts.insert(0, eeprom)
        log.info(f"[{self.name}] EEPROM (U1) + pull-ups placed.")


# ===========================================================================
# 3. SD Card Module — parametric (count=1 or 2)
# ===========================================================================

class SDCardModule(NeuroModule):
    """
    MicroSD card slot using SDIO interface.

    YAML config keys:
        count:   1 or 2 (default 1)
        voltage: "3.3V" (default)
    """

    def build(self) -> None:
        count = self.config.get("count", 1)
        self._set_metadata(
            placement_hint = "edge_bottom",
            thermal_class  = "low",
            interface      = "SDIO",
            slot_count     = count,
        )

        for idx in range(count):
            slot_name = f"SD{idx+1}"
            self._build_single_slot(slot_name, idx)

    def _build_single_slot(self, name: str, idx: int) -> None:
        if not SKIDL_OK:
            log.debug(f"[{self.name}] MOCK SD slot '{name}' created.")
            return

        slot = Part(
            "Connector", "Micro_SD_Card",
            footprint="Connector_Card:microSD_HC_Molex_104031-0811",
            value="MicroSD"
        )
        slot.ref = f"J{10 + idx}"   # J10, J11 for dual SD

        prefix = f"{name}_"
        gnd     = PowerDomain.get("GND")
        pwr_3v3 = PowerDomain.get("+3V3")
        for signal, pin in {"DAT0": "7", "DAT1": "8", "DAT2": "1",
                             "DAT3": "2", "CMD": "3", "CLK": "5"}.items():
            sig_net = PowerDomain.get(prefix + signal)
            sig_net += slot[pin]

        pwr_3v3 += slot["4"]
        gnd     += slot["6"]

        self._add_decoupling("+3V3", count=2, value="100nF")
        self.parts.append(slot)
        log.info(f"[{self.name}] SD card slot '{name}' (ref {slot.ref}) placed.")


# ===========================================================================
# 4. PCIe Accelerator Module — Hailo-8 / Coral TPU via FPC + M.2
# ===========================================================================

class PCIeAcceleratorModule(NeuroModule):
    """
    Dual-interface PCIe accelerator block:
      - FPC connector for direct RPi5 PCIe ribbon cable
      - M.2 M-Key socket for plug-in AI accelerators (Hailo-8. etc.)

    YAML config keys:
        model:  "hailo_8" | "coral_tpu" (default hailo_8)
        lanes:  1 (Gen 3 x1 for Hailo-8)

    Signal integrity notes:
      - Differential pairs (TX+/TX-, RX+/RX-) share a 100 Ω impedance net class.
      - Placed as close to the FPC edge as possible (physics solver: high-weight spring).

    Inspired by the Raspberry Pi AI HAT+ reference design:
      https://www.raspberrypi.com/documentation/accessories/ai-hat-plus.html
    """

    _DIFF_PAIR_MODEL = {
        "hailo_8":  {"interface": "PCIe_Gen3_x1", "tops": 26},
        "hailo_8l": {"interface": "PCIe_Gen3_x1", "tops": 13},
        "coral_tpu":{"interface": "PCIe_Gen2_x1", "tops": 4},
    }

    def build(self) -> None:
        model  = self.config.get("model", "hailo_8")
        lanes  = self.config.get("lanes", 1)
        model_info = self._DIFF_PAIR_MODEL.get(model, self._DIFF_PAIR_MODEL["hailo_8"])

        self._set_metadata(
            placement_hint = "edge_left",        # FPC must face the RPi5 PCIe port
            thermal_class  = "high",
            interface      = model_info["interface"],
            impedance_ohm  = 100,               # differential pair target
            skew_budget_ps = 5.0,               # max intra-pair skew (picoseconds)
            model          = model,
            tops           = model_info["tops"],
        )

        self._build_fpc_connector()
        self._build_m2_socket()

    def _build_fpc_connector(self) -> None:
        """16-pin 0.5 mm FPC for Raspberry Pi 5 PCIe ribbon."""
        if not SKIDL_OK:
            log.debug(f"[{self.name}] MOCK FPC connector created.")
            return

        fpc = Part(
            "Connector_Generic", "Conn_01x16",
            footprint="Connector_FFC-FPC:Hirose_FH12-16S-0.5SH_1x16-1MP_P0.50mm_Horizontal",
            value="FPC_PCIe"
        )
        fpc.ref = "J2"

        gnd_net = PowerDomain.get("GND")
        gnd_net += fpc["1"], fpc["16"]

        # Differential pairs — using SKiDL net naming convention for router
        for pair, pins in {"PCIE_TX": ("4", "5"), "PCIE_RX": ("7", "8")}.items():
            p_net = PowerDomain.get(f"{pair}_P")
            n_net = PowerDomain.get(f"{pair}_N")
            p_net += fpc[pins[0]]
            n_net += fpc[pins[1]]
            self.metadata["net_names"] += [f"{pair}_P", f"{pair}_N"]

        self.parts.append(fpc)
        log.info(f"[{self.name}] FPC PCIe connector (J2) placed.")

    def _build_m2_socket(self) -> None:
        """M.2 M-Key socket for AI accelerator module."""
        if not SKIDL_OK:
            log.debug(f"[{self.name}] MOCK M.2 socket created.")
            return

        m2 = Part(
            "Connector_Generic", "Conn_02x38_Odd_Even",
            footprint="Connector:M.2_M_Key",
            value="M2_M_Key"
        )
        m2.ref = "J3"

        pwr_3v3 = PowerDomain.get("+3V3")
        gnd     = PowerDomain.get("GND")
        for p in ["2", "4", "70", "72", "74"]:
            pwr_3v3 += m2[p]
        for p in ["1", "3", "5", "33", "39", "45", "51", "57", "71", "73", "75"]:
            gnd += m2[p]

        # Bridge PCIe differential pairs from FPC to M.2
        for pair, pins in {"PCIE_TX": ("41", "43"), "PCIE_RX": ("47", "49")}.items():
            p_net = PowerDomain.get(f"{pair}_P")
            n_net = PowerDomain.get(f"{pair}_N")
            p_net += m2[pins[0]]
            n_net += m2[pins[1]]

        self._add_decoupling("+3V3", count=4, value="100nF")
        self._add_decoupling("+3V3", count=2, value="10uF",
                              footprint="Capacitor_SMD:C_0805_2012Metric")
        self.parts.append(m2)
        log.info(f"[{self.name}] M.2 M-Key socket (J3) placed.")


# ===========================================================================
# 5. Power Status LED
# ===========================================================================

class StatusLEDModule(NeuroModule):
    """
    Status + Activity LEDs with current-limiting resistors.

    YAML config keys:
        color:  "green" | "red" | "blue" (default green)
        count:  1 or 2 (default 1 — power LED; 2 adds activity LED)
    """

    # Forward voltage and resistor value per colour
    _VF: Dict[str, float] = {"green": 2.1, "red": 2.0, "blue": 3.2}

    def build(self) -> None:
        color = self.config.get("color", "green")
        count = self.config.get("count", 1)
        self._set_metadata(placement_hint="edge_left", thermal_class="low", interface="none")

        labels = ["PWR", "ACT"]
        for i in range(count):
            self._build_led(f"LED_{labels[i]}", color, i)

    def _build_led(self, label: str, color: str, index: int) -> None:
        if not SKIDL_OK:
            log.debug(f"[{self.name}] MOCK LED '{label}' created.")
            return

        led = Part("Device", "LED",
                   footprint="LED_SMD:LED_0402_1005Metric", value=color.capitalize())
        led.ref = f"D{index+1}"

        res = Part("Device", "R",
                   footprint="Resistor_SMD:R_0402_1005Metric", value="330")
        res.ref = f"R{10+index}"

        net     = Net(f"{label}_NET")
        pwr_net = PowerDomain.get("+3V3")
        gnd_net = PowerDomain.get("GND")
        pwr_net += res["1"]
        net     += res["2"]
        net     += led["A"]
        gnd_net += led["K"]

        self.parts += [led, res]
        self.metadata["net_names"].append(f"{label}_NET")
        log.info(f"[{self.name}] LED ({label}) + resistor placed.")


# ===========================================================================
# 6. Mounting Holes (Mechanical — no electrical function)
# ===========================================================================

class MountingHolesModule(NeuroModule):
    """
    Four M2.5 mounting holes at standard RPi HAT+ corner positions.
    Always anchored — excluded from the physics solver.
    """

    _HAT_HOLES = [
        (3.5,  3.5),
        (61.5, 3.5),
        (3.5,  52.5),
        (61.5, 52.5),
    ]

    def build(self) -> None:
        positions = self.config.get("positions_mm", self._HAT_HOLES)
        self._set_metadata(
            placement_hint = "corners_anchored",
            thermal_class  = "none",
            interface      = "mechanical",
            positions_mm   = positions,
        )

        for i, (x, y) in enumerate(positions):
            if SKIDL_OK:
                hole = Part("Mechanical", "MountingHole",
                            footprint="MountingHole:MountingHole_2.7mm_M2.5")
                hole.ref = f"H{i+1}"
                self.parts.append(hole)
            log.debug(f"[{self.name}] Mounting hole H{i+1} at ({x}, {y}) mm.")

        log.info(f"[{self.name}] {len(positions)} mounting holes defined.")


# ===========================================================================
# Module Registry — maps YAML 'type' strings to NeuroModule subclasses
# Adding new peripherals = add one line here + one new class above.
# ===========================================================================

MODULE_REGISTRY: Dict[str, type] = {
    "gpio_header":       GPIOHeaderModule,
    "hat_eeprom":        HATEepromModule,
    "sd_card":           SDCardModule,
    "pcie_accelerator":  PCIeAcceleratorModule,
    "status_led":        StatusLEDModule,
    "mounting_holes":    MountingHolesModule,
}
