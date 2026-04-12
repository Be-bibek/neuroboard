import os
import logging

# We set the environment blocks before importing SKiDL so it catches them
os.environ["KICAD_SYMBOL_DIR"] = r"C:\Program Files\KiCad\10.0\share\kicad\symbols"
os.environ["KICAD8_SYMBOL_DIR"] = r"C:\Program Files\KiCad\10.0\share\kicad\symbols"

from skidl import Net, Part, generate_netlist, set_default_tool, KICAD8, lib_search_paths

log = logging.getLogger("SystemLogger")
if not log.handlers:
    logging.basicConfig(level=logging.INFO)

# Inject path directly as well
lib_search_paths[KICAD8].append(r"C:\Program Files\KiCad\10.0\share\kicad\symbols")

def generate_pi_hat_schematic(output_filename: str = "pi_hat.net"):
    """
    Programmatically generates the Raspberry Pi AI HAT+ schematic using SKiDL.
    Connects the standard 40-pin Raspberry Pi GPIO header, HAT EEPROM circuitry,
    an M.2 M-Key connector for the Hailo-8 AI accelerator, and an FPC inlet.
    """
    # Instruct SKiDL to generate a KiCad-formatted netlist
    set_default_tool(KICAD8)
    
    # ----------------------------------------------------
    # Power and Ground Nets
    # ----------------------------------------------------
    gnd = Net('GND')
    v5 = Net('+5V')
    v3v3 = Net('+3.3V')

    # ----------------------------------------------------
    # Critical Components Instantiation
    # ----------------------------------------------------
    
    # 1. Raspberry Pi 40-Pin Header
    # Using generic 2x20 connector symbol and footprint
    rpi_header = Part('Connector_Generic', 'Conn_02x20_Odd_Even', 
                      footprint='Connector_PinSocket_2.54mm:PinSocket_2x20_P2.54mm_Vertical')
    rpi_header.ref = 'J1'

    # Power connections on standard Raspberry Pi header
    v5 += rpi_header['2', '4']
    v3v3 += rpi_header['1', '17']
    gnd += rpi_header['6', '9', '14', '20', '25', '30', '34', '39']

    # 2. HAT Identification EEPROM (AT24C32 or generic 24xx32 type)
    # SOIC-8 standard packaging
    eeprom = Part('Memory_EEPROM', '24LC32', footprint='Package_SO:SOIC-8_3.9x4.9mm_P1.27mm')
    eeprom.ref = 'U1'
    
    # EEPROM Power & Ground
    v3v3 += eeprom['8']  # VCC
    gnd += eeprom['1', '2', '3', '4']  # A0, A1, A2, GND (Typical hardwired address 0x50)
    gnd += eeprom['7']  # WP (Write Protect disable for now)

    # 3. Pull-up Resistors for I2C (ID_SD, ID_SC)
    # The Raspberry Pi spec mandates ~3.9k pull-ups on GPIO0 and GPIO1 for HAT detection.
    r_pu_sda = Part('Device', 'R', footprint='Resistor_SMD:R_0402_1005Metric')
    r_pu_sda.value = '3.9k'
    r_pu_scl = Part('Device', 'R', footprint='Resistor_SMD:R_0402_1005Metric')
    r_pu_scl.value = '3.9k'

    # Connect I2C SDA (GPIO0 corresponds to Header Pin 27, SCL is Pin 28)
    id_sd_net = Net('ID_SD')
    id_sc_net = Net('ID_SC')
    
    rpi_header['27'] += id_sd_net
    rpi_header['28'] += id_sc_net
    
    eeprom['5'] += id_sd_net # SDA
    eeprom['6'] += id_sc_net # SCL
    
    # Pull-ups to 3.3V
    v3v3 += r_pu_sda['1']
    id_sd_net += r_pu_sda['2']
    
    v3v3 += r_pu_scl['1']
    id_sc_net += r_pu_scl['2']

    # 4. M.2 M-Key Connector for Hailo-8 AI Module
    # (Typically 67+8 pins, symbol is connector generic or specific M.2 symbol)
    # We will use a generic connector here as a robust proxy for the true SKiDL generic connector
    m2_slot = Part('Connector_Generic', 'Conn_02x38_Odd_Even', footprint='Connector_AMPHENOL:AMPHENOL_MDTE_M2_Socket')
    m2_slot.ref = 'J2'
    
    # Basic M.2 Power allocation (3.3V to standard PCIe power pins)
    v3v3 += m2_slot['2', '4', '70', '72', '74']
    gnd += m2_slot['1', '3', '5', '33', '39', '45', '51', '57', '71', '73', '75']

    # 5. FPC Connector for PCIe (e.g., 16-pin FPC from Raspberry Pi 5 PCIe cable)
    fpc_pcie = Part('Connector_Generic', 'Conn_01x16', footprint='Connector_FFC-FPC:FPC_16P_0.5mm')
    fpc_pcie.ref = 'J3'
    
    gnd += fpc_pcie['1', '16']
    
    # High-Speed Net declarations for differential pair grouping
    pcie_tx_p = Net('PCIE_TX_P')
    pcie_tx_n = Net('PCIE_TX_N')
    pcie_rx_p = Net('PCIE_RX_P')
    pcie_rx_n = Net('PCIE_RX_N')
    
    # Connect FPC directly to M.2 slot (Example mapping)
    fpc_pcie['4'] += pcie_tx_p
    fpc_pcie['5'] += pcie_tx_n
    m2_slot['41'] += pcie_tx_p
    m2_slot['43'] += pcie_tx_n

    fpc_pcie['7'] += pcie_rx_p
    fpc_pcie['8'] += pcie_rx_n
    m2_slot['47'] += pcie_rx_p
    m2_slot['49'] += pcie_rx_n

    # 6. Decoupling Capacitors for Power Rails
    c_dec1 = Part('Device', 'C', footprint='Capacitor_SMD:C_0402_1005Metric')
    c_dec1.value = '100nF'
    c_dec2 = Part('Device', 'C', footprint='Capacitor_SMD:C_0402_1005Metric')
    c_dec2.value = '100nF'
    
    v5 += c_dec1['1']
    gnd += c_dec1['2']
    
    v3v3 += c_dec2['1']
    gnd += c_dec2['2']

    # ----------------------------------------------------
    # Export
    # ----------------------------------------------------
    # Checks internal ERC issues if desired and compiles the actual netlist file.
    log.info("Generating netlist with SKiDL...")
    generate_netlist(file_=output_filename)
    log.info(f"Netlist generated successfully: {output_filename}")

if __name__ == "__main__":
    generate_pi_hat_schematic()
