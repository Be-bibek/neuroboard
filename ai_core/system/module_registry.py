"""
Module Registry for NeuroBoard IPC Engine
Maps logical high-level component names to actual KiCad footprint IDs and logical nets.
"""

MODULES = {
    "GPIO_HEADER": {
        "symbol": "Connector_Generic:Conn_02x20_Odd_Even",
        "footprint": "Connector_PinSocket_2.54mm:PinSocket_2x20_P2.54mm_Vertical",
        "pins": {
            "1": "3V3", 
            "2": "5V", 
            "6": "GND", 
            "39": "GND"
            # Expansion can explicitly map all exact net relations here
        },
        "required_nets": ["3V3", "5V", "GND"]
    },
    
    "NVME_SLOT": {
        "symbol": "Connector:M.2_M-Key",
        "footprint": "Connector_M.2:M.2_M-Key_2242",  # Defaulting to 2242 sizes as seen in FPC bridges
        "pins": {
            "72": "3V3", 
            "74": "3V3", 
            "75": "GND"
        },
        "required_nets": ["3V3", "GND", "PCIE_TXP", "PCIE_TXN", "PCIE_RXP", "PCIE_RXN"]
    },
    
    "PCIE_CONNECTOR": {
        # Using a representative 16-pin 0.5mm pitch FPC for PCIe Gen 2 routing over flat cable
        "symbol": "Connector_FFC:FFC_16P_0.5mm",
        "footprint": "Connector_FFC-FPC:Horizontal_16P_0.5mm", 
        "required_nets": ["3V3", "GND", "PCIE_TXP", "PCIE_TXN"]
    },
    
    "POWER": {
        # General PMIC block representing the power delivery requirement
        "symbol": "Power_Management:PMIC",
        "footprint": "Package_TO_SOT_SMD:SOT-223-3_TabPin2",
        "required_nets": ["5V", "3V3", "GND"]
    },
    
    "LED": {
        "symbol": "Device:LED",
        "footprint": "LED_SMD:LED_0603_1608Metric",
        "required_nets": ["3V3", "GND"]
    }
}
