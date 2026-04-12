"""
ai_core/schematic/examples/pi_hat.py
======================================
Example of a Raspberry Pi HAT module defined using the new Atopile-inspired DSL.
Demonstrates hierarchical composition and interface-based connectivity.
"""

import logging
from typing import Any, Dict, Optional
from schematic.foundation import NeuroModule, Interface, PowerDomain

log = logging.getLogger("SystemLogger")

class EepromModule(NeuroModule):
    """CAT24C32 EEPROM for RPi HAT ID."""
    def build(self) -> None:
        # Define I2C Interface
        self.interfaces["i2c"] = Interface("I2C", ["SDA", "SCL"], self.name)
        
        # Power & GND
        v3v3 = self._power("V3V3")
        gnd  = self._power("GND")
        
        # Parts — try Device:EEPROM as a safe universal fallback
        u1 = self._part("Memory_EEPROM", "AT24C32",
                         "Package_SO:SOIC-8_3.9x4.9mm_P1.27mm",
                         value="HAT_ID", lcsc="C232230")
        
        # Wiring
        u1["VCC"] += v3v3
        u1["GND"] += gnd
        u1["WP"]  += gnd
        
        u1["SDA"] += self.interfaces["i2c"]["SDA"]
        u1["SCL"] += self.interfaces["i2c"]["SCL"]
        
        self._add_decoupling("V3V3", count=1)

class PiHatModule(NeuroModule):
    """Top-level Pi HAT module composing EEPROM and GPIO."""
    def build(self) -> None:
        # 1. Instantiate Sub-modules
        self.submodules["eeprom"] = EepromModule("HAT_EEPROM")
        
        # 2. GPIO Header
        gpio = self._part("Connector", "Raspberry_Pi_2_3_Plus", "Connector_PinHeader_2.54mm:PinHeader_2x20_P2.54mm_Vertical")
        
        # 3. Connect EEPROM I2C to specific GPIO pins (ID_SD/ID_SC are I2C0)
        # In Hat spec: ID_SD = Pin 27, ID_SC = Pin 28
        gpio["27"] += self.submodules["eeprom"].interfaces["i2c"]["SDA"]
        gpio["28"] += self.submodules["eeprom"].interfaces["i2c"]["SCL"]
        
        # 4. Power LED circuit
        self._add_power_led(gpio)
        
    def _add_power_led(self, gpio: Any) -> None:
        v3v3 = self._power("V3V3")
        gnd  = self._power("GND")
        
        r1 = self._part("Device", "R", "Resistor_SMD:R_0603_1608Metric", value="330")
        d1 = self._part("Device", "LED", "LED_SMD:LED_0603_1608Metric", value="PWR")
        
        # Connect: +3.3V -> R1 -> D1 -> GND
        # Using GPIO Pin 1 for 3V3
        gpio["1"] += v3v3
        v3v3 += r1["1"]
        r1["2"] += d1["1"]
        d1["2"] += gnd
