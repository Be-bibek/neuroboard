"""
Module Registry for NeuroBoard IPC Engine — Phase 8.3 (Net Connection Engine)

Each module defines:
  footprint    — KiCad library:footprint_name
  required_nets — list of all nets that must exist for this module to function
  pin_map      — maps logical pin names → net names
                 Keys use the KiCad pad number format (string)
                 so they can be passed directly to connect_pin().
"""

MODULES = {
    "GPIO_HEADER": {
        "symbol": "Connector_Generic:Conn_02x20_Odd_Even",
        "footprint": "Connector_PinSocket_2.54mm:PinSocket_2x20_P2.54mm_Vertical",
        "required_nets": ["3V3", "5V", "GND"],
        # RPi 40-pin header — map representative power/ground pads
        "pin_map": {
            "1":  "3V3",   # 3.3V power
            "17": "3V3",   # 3.3V power (second rail)
            "2":  "5V",    # 5V power
            "4":  "5V",    # 5V power (second rail)
            "6":  "GND",
            "9":  "GND",
            "14": "GND",
            "20": "GND",
            "25": "GND",
            "30": "GND",
            "34": "GND",
            "39": "GND",
        },
    },

    "NVME_SLOT": {
        "symbol": "Connector:M.2_M-Key",
        "footprint": "Connector_M.2:M.2_M-Key_2242",
        "required_nets": ["3V3", "GND", "PCIE_TXP", "PCIE_TXN", "PCIE_RXP", "PCIE_RXN"],
        # M.2 M-Key pin assignments (per M.2 spec)
        "pin_map": {
            "72": "3V3",
            "74": "3V3",
            "76": "3V3",
            "2":  "GND",
            "4":  "GND",
            "75": "GND",
            "23": "PCIE_RXP",   # PERp0
            "21": "PCIE_RXN",   # PERn0
            "29": "PCIE_TXP",   # PETp0
            "27": "PCIE_TXN",   # PETn0
        },
    },

    "PCIE_CONNECTOR": {
        "symbol": "Connector_FFC:FFC_16P_0.5mm",
        "footprint": "Connector_FFC-FPC:Horizontal_16P_0.5mm",
        "required_nets": ["3V3", "GND", "PCIE_TXP", "PCIE_TXN", "PCIE_RXP", "PCIE_RXN"],
        # 16-pin FPC cable mapping for PCIe Gen 2 — matches the cable pinout from live_pads_val.json
        "pin_map": {
            "1":  "GND",
            "2":  "PCIE_TXP",
            "3":  "PCIE_TXN",
            "4":  "GND",
            "5":  "PCIE_RXP",
            "6":  "PCIE_RXN",
            "7":  "GND",
            "14": "3V3",
            "15": "3V3",
            "16": "GND",
        },
    },

    "POWER": {
        "symbol": "Power_Management:PMIC",
        "footprint": "Package_TO_SOT_SMD:SOT-223-3_TabPin2",
        "required_nets": ["5V", "3V3", "GND"],
        # SOT-223: pin 1 = output (3V3), pin 2 = GND, pin 3 = input (5V), pin 4 = tab (GND)
        "pin_map": {
            "1": "3V3",
            "2": "GND",
            "3": "5V",
            "4": "GND",
        },
    },

    "LED": {
        "symbol": "Device:LED",
        "footprint": "LED_SMD:LED_0603_1608Metric",
        "required_nets": ["3V3", "GND"],
        # LED 0603: anode = pad 1, cathode = pad 2
        "pin_map": {
            "1": "3V3",
            "2": "GND",
        },
    },
}
