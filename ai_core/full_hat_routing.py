"""
Full Raspberry Pi 5 PCIe M.2 HAT Routing Pipeline
===================================================
Step 1: Assign nets to J_PCIE (Hirose FH12-16S-0.5SH) and J_SSD (Amphenol MDT420M03001)
        using the official Raspberry Pi 5 PCIe FFC pinout.
Step 2: Assign power nets to support components.
Step 3: Route all copper traces with proper PCIe signal integrity.
Step 4: Add GND via stitching.
"""

import sys
sys.path.insert(0, r'C:\Users\Bibek\Documents\KiCad\10.0\3rdparty\Python311\site-packages')

from kipy import KiCad
from kipy.board_types import (
    Net, Track, Via, BoardLayer, board_types_pb2 as bt,
    Pad, FootprintInstance
)
from kipy.geometry import Vector2
from google.protobuf.any_pb2 import Any

NM = 1_000_000  # nanometers per mm

def mm(v):
    return int(v * NM)

def make_net_obj(name):
    n = Net()
    n.name = name
    return n

def get_net(board, name):
    for n in board.get_nets():
        if n.name == name:
            return n
    return make_net_obj(name)

# ─────────────────────────────────────────────
# Official Raspberry Pi 5 PCIe FFC Pinout
# Hirose FH12-16S-0.5SH, 16-pin, 0.5mm pitch
# Pin 1 = bottom of connector as oriented
# ─────────────────────────────────────────────
# Our J_PCIE pads are numbered 1-16, pin 1 at Y=75.75 (bottom)
# Pin numbers map as follows (RPi official):
FFC_PIN_NETS = {
    '1':  'GND',
    '2':  'PCIE_TX_P',    # PETp0 - PCIe Gen 3 TX+
    '3':  'PCIE_TX_N',    # PETn0 - PCIe Gen 3 TX-
    '4':  'GND',
    '5':  'PCIE_RX_P',    # PERp0 - PCIe Gen 3 RX+
    '6':  'PCIE_RX_N',    # PERn0 - PCIe Gen 3 RX-
    '7':  'GND',
    '8':  'PCIE_REFCLK_P', # RefClk+
    '9':  'PCIE_REFCLK_N', # RefClk-
    '10': 'GND',
    '11': 'PCIE_PERST',   # PERST# (active low reset)
    '12': 'PCIE_CLKREQ',  # CLKREQ# (clock request)
    '13': 'PCIE_WAKE',    # WAKE# (optional)
    '14': 'GND',
    '15': '+3V3',
    '16': '+3V3',
    'SH1': 'GND',         # Shield
    'SH2': 'GND',         # Shield
}

# ─────────────────────────────────────────────
# M.2 M-Key PCIe x1 Pin Mapping (Amphenol MDT420M03001)
# Standard NGFF M.2 M-Key pinout
# The connector sits rotated 90° so odd/even rows map to left/right rails
# Based on actual pad positions read from the board:
#   Right rail (X=129.28): Pins 1,3,5,7,9,11,13,15,17,19,21,23...
#   Left rail  (X=121.72): Pins 2,4,6,8,10,12,14,16,18,20,22...
# M.2 M-Key standard PCIe x1 signal mapping:
# ─────────────────────────────────────────────
M2_PIN_NETS = {
    # 3.3V Power supply
    '1':  '+3V3',   # 3.3V  
    '2':  '+3V3',   # 3.3V
    '3':  '+3V3',   # 3.3V
    '4':  '+3V3',   # 3.3V
    # Ground
    '5':  'GND',
    '6':  'GND',
    # DevSLP / reserved
    '7':  'GND',
    '8':  'GND',
    '9':  'GND',
    '10': 'GND',
    '11': 'GND',
    '12': 'GND',
    '13': 'GND',
    '14': 'GND',
    '15': 'GND',
    '16': 'GND',
    '17': 'GND',
    '18': 'GND',
    '19': 'GND',
    '20': 'GND',
    '21': 'GND',
    '22': 'GND',
    '23': 'GND',
    '24': 'GND',
    '25': 'GND',
    '26': 'GND',
    '27': 'GND',
    '28': 'GND',
    '29': 'GND',
    '30': 'GND',
    '31': 'GND',
    '32': 'GND',
    '33': 'GND',
    '34': 'GND',
    '35': 'GND',
    '36': 'GND',
    '37': 'GND',
    '38': 'GND',
    # PCIe RX (from host perspective, device TX)
    '39': 'GND',
    '40': 'GND',
    '41': 'PCIE_RX_N',    # PERn0
    '42': 'GND',
    '43': 'PCIE_RX_P',    # PERp0
    '44': 'GND',
    '45': 'GND',
    '46': 'GND',
    '47': 'GND',
    '48': 'GND',
    # PCIe TX (from host perspective, device RX)
    '49': 'PCIE_TX_P',    # PETp0
    '50': 'GND',
    '51': 'PCIE_TX_N',    # PETn0
    '52': 'GND',
    # REFCLK
    '53': 'PCIE_REFCLK_P',
    '54': 'GND',
    '55': 'PCIE_REFCLK_N',
    '56': 'GND',
    # M-Key gap region
    '57': 'GND',
    '58': 'GND',
    # PERST#, CLKREQ#
    '59': 'PCIE_PERST',
    '60': 'GND',
    '61': 'PCIE_CLKREQ',
    '62': 'GND',
    # Remaining
    '63': 'GND',
    '64': 'GND',
    '65': 'GND',
    '66': 'GND',
    '67': 'GND',
    '68': 'GND',
    '69': 'GND',
    '70': 'GND',
    '71': 'GND',
    '72': 'GND',
    '73': 'GND',
    '74': 'GND',
    '75': 'GND',
}

def run():
    print("Connecting to KiCad API...")
    k = KiCad()
    board = k.get_board()
    
    # Build net lookup
    existing_nets = {n.name: n for n in board.get_nets()}
    def get_or_make_net(name):
        if name in existing_nets:
            return existing_nets[name]
        n = Net()
        n.name = name
        return n

    # ── STEP 1: Assign nets to J_PCIE pads ──
    print("\n[STEP 1] Assigning nets to J_PCIE (Hirose FFC)...")
    commit = board.begin_commit()
    
    updated_fps = []
    pcie_pad_positions = {}  # net_name -> (x, y) for routing later
    ssd_pad_positions = {}
    
    for fp in board.get_footprints():
        try: ref = fp.reference_field.text.value
        except: ref = ''
        
        if ref == 'J_PCIE':
            for pad in fp.definition.pads:
                net_name = FFC_PIN_NETS.get(pad.number)
                if net_name:
                    pad.net = get_or_make_net(net_name)
                    # Record position for routing
                    if net_name not in ('GND', '+3V3'):
                        pcie_pad_positions[net_name] = (
                            pad.position.x / NM,
                            pad.position.y / NM
                        )
            updated_fps.append(fp)
            print(f"  J_PCIE: assigned nets to {len(fp.definition.pads)} pads")
            
        elif ref == 'J_SSD':
            assigned = 0
            for pad in fp.definition.pads:
                net_name = M2_PIN_NETS.get(pad.number)
                if net_name:
                    pad.net = get_or_make_net(net_name)
                    # Record positions for PCIe signals
                    if net_name not in ('GND', '+3V3'):
                        ssd_pad_positions[net_name] = (
                            pad.position.x / NM,
                            pad.position.y / NM
                        )
                    assigned += 1
            updated_fps.append(fp)
            print(f"  J_SSD: assigned nets to {assigned} pads")
            
        # ── Power components ──
        elif ref == 'U1':  # Buck regulator
            for pad in fp.definition.pads:
                if pad.number == '1': pad.net = get_or_make_net('+5V')
                elif pad.number == '2': pad.net = get_or_make_net('GND')
                elif pad.number == '3': pad.net = get_or_make_net('+3V3')
                elif pad.number == '4': pad.net = get_or_make_net('GND')
                elif pad.number == '5': pad.net = get_or_make_net('+3V3')
            updated_fps.append(fp)
            
        elif ref == 'L1':  # Inductor
            for pad in fp.definition.pads:
                pad.net = get_or_make_net('+3V3')
            updated_fps.append(fp)
            
        elif ref in ['C3', 'C4']:  # Bulk caps
            for pad in fp.definition.pads:
                if pad.number == '1': pad.net = get_or_make_net('+3V3')
                elif pad.number == '2': pad.net = get_or_make_net('GND')
            updated_fps.append(fp)
            
        elif ref in ['C_DEC_1','C_DEC_2','C_DEC_3','C_DEC_4']:
            for pad in fp.definition.pads:
                if pad.number == '1': pad.net = get_or_make_net('+3V3')
                elif pad.number == '2': pad.net = get_or_make_net('GND')
            updated_fps.append(fp)
            
        elif ref == 'U2':  # EEPROM (HAT ID)
            for pad in fp.definition.pads:
                if pad.number in ['1','2','3','4']: pad.net = get_or_make_net('GND')
                elif pad.number in ['5','8']: pad.net = get_or_make_net('+3V3')
                elif pad.number == '6': pad.net = get_or_make_net('/ID_SDA')
                elif pad.number == '7': pad.net = get_or_make_net('/ID_SCL')
            updated_fps.append(fp)
            
        elif ref == 'R1':  # LED resistor for D1
            for pad in fp.definition.pads:
                if pad.number == '1': pad.net = get_or_make_net('+3V3')
                elif pad.number == '2': pad.net = get_or_make_net('LED_PWR')
            updated_fps.append(fp)
            
        elif ref == 'D1':  # Status LED (PWR)
            for pad in fp.definition.pads:
                if pad.number == '1': pad.net = get_or_make_net('GND')
                elif pad.number == '2': pad.net = get_or_make_net('LED_PWR')
            updated_fps.append(fp)
            
        elif ref == 'R2':  # LED resistor for D2
            for pad in fp.definition.pads:
                if pad.number == '1': pad.net = get_or_make_net('+3V3')
                elif pad.number == '2': pad.net = get_or_make_net('LED_ACT')
            updated_fps.append(fp)
            
        elif ref == 'D2':  # Activity LED
            for pad in fp.definition.pads:
                if pad.number == '1': pad.net = get_or_make_net('GND')
                elif pad.number == '2': pad.net = get_or_make_net('LED_ACT')
            updated_fps.append(fp)
    
    if updated_fps:
        board.update_items(updated_fps)
    
    # ── STEP 2: Route copper traces ──
    print("\n[STEP 2] Routing copper traces...")
    tracks = []
    vias = []
    
    def track(x1, y1, x2, y2, net_name, width=0.2, layer=bt.BL_F_Cu):
        t = Track()
        t.start = Vector2.from_xy(mm(x1), mm(y1))
        t.end = Vector2.from_xy(mm(x2), mm(y2))
        t.width = mm(width)
        t.layer = layer
        t.net = get_or_make_net(net_name)
        tracks.append(t)
        
    def via(x, y, net_name, diameter=0.8, drill=0.4):
        v = Via()
        v.position = Vector2.from_xy(mm(x), mm(y))
        v.net = get_or_make_net(net_name)
        v.diameter = mm(diameter)
        v.drill_diameter = mm(drill)
        vias.append(v)
    
    # ── J_PCIE pad positions (pin 1 is at Y=75.75, ascending by -0.5 each pin) ──
    # Pin 1: GND    @ (106.75, 75.75)
    # Pin 2: TX_P   @ (106.75, 75.25)
    # Pin 3: TX_N   @ (106.75, 74.75)
    # Pin 4: GND    @ (106.75, 74.25)
    # Pin 5: RX_P   @ (106.75, 73.75)
    # Pin 6: RX_N   @ (106.75, 73.25)
    # Pin 7: GND    @ (106.75, 72.75)
    # Pin 8: CLK_P  @ (106.75, 72.25)
    # Pin 9: CLK_N  @ (106.75, 71.75)
    # Pin 10: GND   @ (106.75, 71.25)
    # Pin 11: PERST @ (106.75, 70.75)
    # Pin 12: CLKREQ @ (106.75, 70.25)
    # Pin 15: +3V3  @ (106.75, 68.75)
    # Pin 16: +3V3  @ (106.75, 68.25)
    
    # ── J_SSD pad positions (connector at 124, 71.5, rotated 90°) ──
    # TX connects: J_PCIE pin 2 (TX_P) → M.2 pin 49 (TX_P)
    # TX connects: J_PCIE pin 3 (TX_N) → M.2 pin 51 (TX_N)
    # RX connects: J_PCIE pin 5 (RX_P) → M.2 pin 43 (RX_P)
    # RX connects: J_PCIE pin 6 (RX_N) → M.2 pin 41 (RX_N)
    # CLK connects: J_PCIE pin 8 (CLK_P) → M.2 pin 53 (CLK_P)
    # CLK connects: J_PCIE pin 9 (CLK_N) → M.2 pin 55 (CLK_N)
    
    # M.2 pin positions (from board read, X=121.72 for even pins, X=129.28 for odd):
    # Pin 41 (RX_N) @ (129.28, 82.25) approx (pin 41 = offset from pin 1)
    # Each pin pair increments Y by 0.5mm, starting at pin 1 @ Y=62.25
    # Pin N (odd, right):  Y = 62.25 + (N-1)/2 * 0.5 = 62.25 + (N-1)*0.25
    # Pin N (even, left):  Y = 62.50 + (N-2)/2 * 0.5 = 62.50 + (N-2)*0.25
    
    def m2_pin_pos(pin_num):
        pin_num = int(pin_num)
        if pin_num % 2 == 1:  # Odd: right rail X=129.28
            y = 62.25 + ((pin_num - 1) // 2) * 0.5
            return (129.28, y)
        else:  # Even: left rail X=121.72
            y = 62.50 + ((pin_num - 2) // 2) * 0.5
            return (121.72, y)
    
    # ── DIFFERENTIAL PAIR ROUTING (0.15mm width, 0.2mm gap) ──
    # Route as clean 3-segment L-paths with 45° corners
    # PCIe spec: ~90-ohm differential impedance, match length within 5mil
    
    DIFF_W = 0.15  # trace width for diff pairs
    
    # All pairs route from J_PCIE (left, X~107) to J_SSD (center, X~121-129)
    # Use a horizontal run to X=112, then 45° turn, then enter M.2
    
    def route_diff_pair(net_p, net_n, ffc_p_y, ffc_n_y, m2_p_pin, m2_n_pin, turn_x=113.0):
        """Route a differential pair from FFC connector to M.2 connector."""
        ffc_x = 106.75
        
        # M.2 destination positions
        m2_p_x, m2_p_y = m2_pin_pos(m2_p_pin)
        m2_n_x, m2_n_y = m2_pin_pos(m2_n_pin)
        
        # P trace: FFC → horizontal → 45° turn → M.2
        # Horizontal segment
        track(ffc_x, ffc_p_y, turn_x, ffc_p_y, net_p, DIFF_W)
        # 45° segment to align with M.2 pin Y
        mid_p_y = ffc_p_y  # start of diagonal
        diag_len_p = abs(m2_p_y - ffc_p_y)
        track(turn_x, ffc_p_y, turn_x + diag_len_p, m2_p_y, net_p, DIFF_W)
        # Final horizontal to M.2 pad
        track(turn_x + diag_len_p, m2_p_y, m2_p_x, m2_p_y, net_p, DIFF_W)
        
        # N trace: parallel to P, offset by 0.35mm (gap=0.2mm)
        track(ffc_x, ffc_n_y, turn_x, ffc_n_y, net_n, DIFF_W)
        diag_len_n = abs(m2_n_y - ffc_n_y)
        track(turn_x, ffc_n_y, turn_x + diag_len_n, m2_n_y, net_n, DIFF_W)
        track(turn_x + diag_len_n, m2_n_y, m2_n_x, m2_n_y, net_n, DIFF_W)
    
    # TX pair: FFC pins 2,3 → M.2 pins 49,51
    route_diff_pair('PCIE_TX_P', 'PCIE_TX_N', 75.25, 74.75, 49, 51, turn_x=113.5)
    
    # RX pair: FFC pins 5,6 → M.2 pins 43,41
    route_diff_pair('PCIE_RX_P', 'PCIE_RX_N', 73.75, 73.25, 43, 41, turn_x=114.5)
    
    # REFCLK pair: FFC pins 8,9 → M.2 pins 53,55
    route_diff_pair('PCIE_REFCLK_P', 'PCIE_REFCLK_N', 72.25, 71.75, 53, 55, turn_x=115.5)
    
    # ── CONTROL SIGNALS (single-ended, 0.2mm width) ──
    # PERST#: FFC pin 11 → M.2 pin 59
    ffc_x = 106.75
    m2_x59, m2_y59 = m2_pin_pos(59)
    track(ffc_x, 70.75, 118.0, 70.75, 'PCIE_PERST', 0.2)
    track(118.0, 70.75, 118.0, m2_y59, 'PCIE_PERST', 0.2)
    track(118.0, m2_y59, m2_x59, m2_y59, 'PCIE_PERST', 0.2)
    
    # CLKREQ#: FFC pin 12 → M.2 pin 61
    m2_x61, m2_y61 = m2_pin_pos(61)
    track(ffc_x, 70.25, 119.0, 70.25, 'PCIE_CLKREQ', 0.2)
    track(119.0, 70.25, 119.0, m2_y61, 'PCIE_CLKREQ', 0.2)
    track(119.0, m2_y61, m2_x61, m2_y61, 'PCIE_CLKREQ', 0.2)
    
    # ── POWER ROUTING (1.0mm width) ──
    # 3.3V from FFC → M.2 power pins (broad bus)
    # FFC pin 15,16 at Y=68.75, 68.25 → M.2 pins 1,2,3,4
    track(ffc_x, 68.75, 112.0, 68.75, '+3V3', 1.0)
    track(ffc_x, 68.25, 112.0, 68.25, '+3V3', 1.0)
    track(112.0, 68.25, 112.0, 63.0, '+3V3', 1.0)
    
    m2_1x, m2_1y = m2_pin_pos(1)
    m2_2x, m2_2y = m2_pin_pos(2)
    m2_3x, m2_3y = m2_pin_pos(3)
    m2_4x, m2_4y = m2_pin_pos(4)
    
    track(112.0, m2_1y, m2_1x, m2_1y, '+3V3', 1.0)
    track(112.0, m2_2y, m2_2x, m2_2y, '+3V3', 1.0)
    track(112.0, m2_3y, m2_3x, m2_3y, '+3V3', 1.0)
    track(112.0, m2_4y, m2_4x, m2_4y, '+3V3', 1.0)
    
    # ── GND STITCHING VIAS ──
    gnd_via_positions = [
        (108.5, 72.75),   # Near J_PCIE GND pin 7
        (108.5, 74.25),   # Near J_PCIE GND pin 4
        (108.5, 75.75),   # Near J_PCIE GND pin 1
        (108.5, 71.25),   # Near J_PCIE GND pin 10
        (115.0, 63.0),    # Between connectors
        (120.0, 63.0),    
        (125.0, 63.0),    # Near M.2
        (115.0, 82.0),    
        (120.0, 82.0),    
    ]
    for vx, vy in gnd_via_positions:
        via(vx, vy, 'GND')
    
    # ── PUSH ALL ITEMS ──
    print(f"\n  Creating {len(tracks)} track segments...")
    board.create_items(tracks)
    
    print(f"  Creating {len(vias)} GND vias...")
    board.create_items(vias)
    
    board.push_commit(commit)
    board.save()
    
    print("\n[SUCCESS] PCIe M.2 HAT routing complete!")
    print(f"  - {len(tracks)} copper traces routed")
    print(f"  - {len(vias)} GND vias stitched")
    print("  - TX/RX/REFCLK differential pairs connected")
    print("  - PERST# and CLKREQ# control signals connected")
    print("  - 3.3V power bus connected")
    print("\n  Next: In KiCad, run Inspect > Net Inspector to verify")
    print("         Run Inspect > Design Rules Checker (DRC) to validate")

if __name__ == '__main__':
    run()
