"""
Corrected Raspberry Pi M.2 HAT+ Routing
Official RPi5 PCIe FFC 16-pin pinout (J20):
  Pin 1  = +5V
  Pin 2  = +5V
  Pin 3  = GND
  Pin 4  = PCIE_TX_P
  Pin 5  = PCIE_TX_N
  Pin 6  = GND
  Pin 7  = PCIE_RX_P
  Pin 8  = PCIE_RX_N
  Pin 9  = GND
  Pin 10 = PCIE_REFCLK_P
  Pin 11 = PCIE_REFCLK_N
  Pin 12 = GND
  Pin 13 = PCIE_PERST_N
  Pin 14 = PCIE_PWR_EN
  Pin 15 = PCIE_DET_WAKE
  Pin 16 = GND
  SH1/SH2 = GND (mechanical shield)

M.2 M-Key PCIe x1 signals (Amphenol MDT420M03001):
  Pad positions read from board:
    Odd  pins (right rail): X=129.28, Y = 62.25 + ((n-1)//2)*0.5
    Even pins (left rail):  X=121.72, Y = 62.50 + ((n-2)//2)*0.5
  
  Power: pins 1,2,3,4 = +3V3_SSD
  PCIe TX (host→device): pins 49(+), 51(-) 
  PCIe RX (device→host): pins 43(+), 41(-)
  REFCLK: pins 53(+), 55(-)
  PERST#: pin 59 (odd, right rail)
  CLKREQ#: pin 61 (odd, right rail)
"""

import sys
sys.path.insert(0, r'C:\Users\Bibek\Documents\KiCad\10.0\3rdparty\Python311\site-packages')

from kipy import KiCad
from kipy.board_types import Net, Track, Via, Zone, board_types_pb2 as bt, ZoneType, ZoneBorderStyle, IslandRemovalMode
from kipy.geometry import Vector2, PolygonWithHoles, PolyLineNode
from kipy.util.units import from_mm

NM = 1_000_000

def mm(v):
    return int(v * NM)

def m2_pin_pos(n):
    n = int(n)
    if n % 2 == 1:
        return (129.28, 62.25 + ((n-1)//2)*0.5)
    else:
        return (121.72, 62.50 + ((n-2)//2)*0.5)

# Official FFC pinout
FFC_NETS = {
    '1': '+5V', '2': '+5V', '3': 'GND',
    '4': 'PCIE_TX_P', '5': 'PCIE_TX_N', '6': 'GND',
    '7': 'PCIE_RX_P', '8': 'PCIE_RX_N', '9': 'GND',
    '10': 'PCIE_REFCLK_P', '11': 'PCIE_REFCLK_N', '12': 'GND',
    '13': 'PCIE_PERST_N', '14': 'PCIE_PWR_EN', '15': 'PCIE_DET_WAKE', '16': 'GND',
    'SH1': 'GND', 'SH2': 'GND',
}

# M.2 pin net mapping
M2_NETS = {
    '1': '+3V3_SSD', '2': '+3V3_SSD', '3': '+3V3_SSD', '4': '+3V3_SSD',
    '41': 'PCIE_RX_N', '43': 'PCIE_RX_P',
    '49': 'PCIE_TX_P', '51': 'PCIE_TX_N',
    '53': 'PCIE_REFCLK_P', '55': 'PCIE_REFCLK_N',
    '59': 'PCIE_PERST_N', '61': 'PCIE_CLKREQ_N',
}
# All remaining M.2 pins → GND
for i in range(1, 76):
    if str(i) not in M2_NETS:
        M2_NETS[str(i)] = 'GND'

def run():
    print("Connecting to KiCad...")
    k = KiCad()
    board = k.get_board()

    net_cache = {n.name: n for n in board.get_nets()}

    def get_net(name):
        if name in net_cache:
            return net_cache[name]
        n = Net(); n.name = name
        net_cache[name] = n
        return n

    commit = board.begin_commit()

    # ── STEP 1: Remove old incorrect tracks ──
    print("[1] Removing old tracks...")
    old_signal_nets = {
        'PCIE_TX_P','PCIE_TX_N','PCIE_RX_P','PCIE_RX_N',
        'PCIE_REFCLK_P','PCIE_REFCLK_N','PCIE_PERST','PCIE_CLKREQ',
        'PCIE_WAKE','+3V3','LED_PWR','LED_ACT','/ID_SDA','/ID_SCL'
    }
    old_tracks = [t for t in board.get_tracks() if t.net.name in old_signal_nets]
    if old_tracks:
        board.remove_items(old_tracks)
    print(f"   Removed {len(old_tracks)} old tracks")

    # ── STEP 2: Assign correct nets to all pads ──
    print("[2] Assigning official nets...")
    updated = []

    for fp in board.get_footprints():
        try: ref = fp.reference_field.text.value
        except: ref = ''

        if ref == 'J_PCIE':
            for pad in fp.definition.pads:
                net = FFC_NETS.get(pad.number)
                if net: pad.net = get_net(net)
            updated.append(fp)

        elif ref == 'J_SSD':
            for pad in fp.definition.pads:
                net = M2_NETS.get(pad.number)
                if net: pad.net = get_net(net)
            updated.append(fp)

        elif ref == 'U1':  # Buck converter: 5V→3.3V for SSD
            for pad in fp.definition.pads:
                if pad.number == '1': pad.net = get_net('+5V')
                elif pad.number == '2': pad.net = get_net('GND')
                elif pad.number in ('3','5'): pad.net = get_net('+3V3_SSD')
                elif pad.number == '4': pad.net = get_net('GND')
            updated.append(fp)

        elif ref == 'L1':
            for pad in fp.definition.pads:
                pad.net = get_net('+3V3_SSD')
            updated.append(fp)

        elif ref in ('C3','C4','C_DEC_1','C_DEC_2','C_DEC_3','C_DEC_4'):
            for pad in fp.definition.pads:
                if pad.number == '1': pad.net = get_net('+3V3_SSD')
                elif pad.number == '2': pad.net = get_net('GND')
            updated.append(fp)

        elif ref == 'U2':  # EEPROM
            for pad in fp.definition.pads:
                if pad.number in ('1','2','3','4'): pad.net = get_net('GND')
                elif pad.number in ('5','8'): pad.net = get_net('+3V3_SSD')
                elif pad.number == '6': pad.net = get_net('/ID_SDA')
                elif pad.number == '7': pad.net = get_net('/ID_SCL')
            updated.append(fp)

        elif ref == 'R1':
            for pad in fp.definition.pads:
                if pad.number == '1': pad.net = get_net('+3V3_SSD')
                elif pad.number == '2': pad.net = get_net('LED_PWR')
            updated.append(fp)

        elif ref == 'D1':
            for pad in fp.definition.pads:
                if pad.number == '1': pad.net = get_net('GND')
                elif pad.number == '2': pad.net = get_net('LED_PWR')
            updated.append(fp)

        elif ref == 'R2':
            for pad in fp.definition.pads:
                if pad.number == '1': pad.net = get_net('+3V3_SSD')
                elif pad.number == '2': pad.net = get_net('LED_ACT')
            updated.append(fp)

        elif ref == 'D2':
            for pad in fp.definition.pads:
                if pad.number == '1': pad.net = get_net('GND')
                elif pad.number == '2': pad.net = get_net('LED_ACT')
            updated.append(fp)

    board.update_items(updated)
    print(f"   Updated {len(updated)} footprints")

    # ── STEP 3: Route all traces ──
    print("[3] Routing copper traces...")
    tracks = []
    vias = []

    def seg(x1,y1,x2,y2,net,w=0.2,layer=bt.BL_F_Cu):
        t = Track()
        t.start = Vector2.from_xy(mm(x1),mm(y1))
        t.end   = Vector2.from_xy(mm(x2),mm(y2))
        t.width = mm(w); t.layer = layer
        t.net   = get_net(net)
        tracks.append(t)

    def add_via(x,y,net,d=0.8,dr=0.4):
        v = Via()
        v.position = Vector2.from_xy(mm(x),mm(y))
        v.net = get_net(net)
        v.diameter = mm(d); v.drill_diameter = mm(dr)
        vias.append(v)

    # J_PCIE pad Y positions (pin 1 at Y=75.75, increments -0.5 per pin)
    # IMPORTANT: Our pads are ordered 1-16, so:
    def ffc_y(pin): return 75.75 - (int(pin)-1)*0.5
    FX = 106.75  # FFC connector pad X

    # ─── POWER: 5V from FFC pins 1,2 → Buck converter U1 ───
    # U1 @ (149.8, 53.5) — run 5V bus
    seg(FX, ffc_y(1), 108.0, ffc_y(1), '+5V', 1.0)
    seg(FX, ffc_y(2), 108.0, ffc_y(2), '+5V', 1.0)
    seg(108.0, ffc_y(1), 108.0, 52.0, '+5V', 1.0)
    seg(108.0, 52.0,     149.8, 52.0, '+5V', 1.0)  # to U1 pin 1

    # 3.3V from U1 → L1 → C3,C4 → M.2 power pins
    seg(149.8, 54.0, 144.8, 54.0, '+3V3_SSD', 1.0)  # U1→L1
    seg(144.8, 54.0, 139.8, 54.0, '+3V3_SSD', 1.0)  # L1→C3
    seg(139.8, 54.0, 134.8, 54.0, '+3V3_SSD', 1.0)  # C3→C4
    seg(134.8, 54.0, 130.0, 54.0, '+3V3_SSD', 1.0)  # C4→M.2 area
    # Down to M.2 pin 1 (right rail)
    m2_1x, m2_1y = m2_pin_pos(1)
    m2_2x, m2_2y = m2_pin_pos(2)
    m2_3x, m2_3y = m2_pin_pos(3)
    m2_4x, m2_4y = m2_pin_pos(4)
    seg(130.0, 54.0, 130.0, m2_1y, '+3V3_SSD', 1.0)
    seg(130.0, m2_1y, m2_1x, m2_1y, '+3V3_SSD', 1.0)
    seg(130.0, m2_2y, m2_2x, m2_2y, '+3V3_SSD', 1.0)
    seg(130.0, m2_3y, m2_3x, m2_3y, '+3V3_SSD', 1.0)
    seg(130.0, m2_4y, m2_4x, m2_4y, '+3V3_SSD', 1.0)

    # PCIE_PWR_EN (FFC pin 14 → U1 enable pin, or EEPROM)
    seg(FX, ffc_y(14), 112.0, ffc_y(14), 'PCIE_PWR_EN', 0.2)

    # PCIE_DET_WAKE (FFC pin 15 → detection resistor / board ID)
    seg(FX, ffc_y(15), 112.0, ffc_y(15), 'PCIE_DET_WAKE', 0.2)

    # ─── DIFFERENTIAL PAIRS (0.15mm, 90Ω) ───
    W = 0.15  # diff pair width

    def route_pair(net_p, net_n, ffc_pin_p, ffc_pin_n, m2_pin_p, m2_pin_n):
        y_p = ffc_y(ffc_pin_p)
        y_n = ffc_y(ffc_pin_n)
        m2x_p, m2y_p = m2_pin_pos(m2_pin_p)
        m2x_n, m2y_n = m2_pin_pos(m2_pin_n)

        # Horizontal out from FFC
        turn_x = 110.5
        seg(FX, y_p, turn_x, y_p, net_p, W)
        seg(FX, y_n, turn_x, y_n, net_n, W)

        # Route to M.2 side — go horizontal to near M.2, then vertical to pin
        seg(turn_x, y_p, m2x_p - 2, y_p, net_p, W)
        seg(m2x_p - 2, y_p, m2x_p - 2, m2y_p, net_p, W)
        seg(m2x_p - 2, m2y_p, m2x_p, m2y_p, net_p, W)

        seg(turn_x, y_n, m2x_n - 2, y_n, net_n, W)
        seg(m2x_n - 2, y_n, m2x_n - 2, m2y_n, net_n, W)
        seg(m2x_n - 2, m2y_n, m2x_n, m2y_n, net_n, W)

    # TX: FFC pin4(+),5(-) → M.2 pin49(+),51(-)
    route_pair('PCIE_TX_P','PCIE_TX_N', 4,5, 49,51)
    # RX: FFC pin7(+),8(-) → M.2 pin43(+),41(-)
    route_pair('PCIE_RX_P','PCIE_RX_N', 7,8, 43,41)
    # REFCLK: FFC pin10(+),11(-) → M.2 pin53(+),55(-)
    route_pair('PCIE_REFCLK_P','PCIE_REFCLK_N', 10,11, 53,55)

    # ─── CONTROL SIGNALS ───
    m2x_59, m2y_59 = m2_pin_pos(59)
    seg(FX, ffc_y(13), 116.0, ffc_y(13), 'PCIE_PERST_N', 0.2)
    seg(116.0, ffc_y(13), 116.0, m2y_59, 'PCIE_PERST_N', 0.2)
    seg(116.0, m2y_59, m2x_59, m2y_59, 'PCIE_PERST_N', 0.2)

    m2x_61, m2y_61 = m2_pin_pos(61)
    seg(117.0, m2y_61, m2x_61, m2y_61, 'PCIE_CLKREQ_N', 0.2)

    # ─── LED STUBS ───
    seg(110.45, 60.0, 110.45, 65.0, 'LED_PWR', 0.15)
    seg(110.45, 75.0, 110.45, 70.0, 'LED_ACT', 0.15)

    # ─── EEPROM I2C ───
    seg(137.4, 58.1,  137.4, 48.77, '/ID_SDA', 0.2)
    seg(137.4, 48.77, 145.77, 48.77, '/ID_SDA', 0.2)
    seg(137.4, 59.35, 136.0, 59.35, '/ID_SCL', 0.2)
    seg(136.0, 59.35, 136.0, 46.23, '/ID_SCL', 0.2)
    seg(136.0, 46.23, 145.77, 46.23, '/ID_SCL', 0.2)

    # ─── GND STITCHING VIAS ───
    gnd_via_pts = [
        (108.5,74.25),(108.5,72.75),(108.5,71.25),(108.5,70.0),
        (113.0,63.0),(118.0,63.0),(123.0,63.0),(128.0,63.0),
        (113.0,82.0),(118.0,82.0),(123.0,82.0),(128.0,82.0),
        (131.5,65.0),(131.5,70.0),(131.5,75.0),(131.5,80.0),
    ]
    for vx,vy in gnd_via_pts:
        add_via(vx,vy,'GND')

    board.create_items(tracks)
    board.create_items(vias)
    print(f"   {len(tracks)} traces, {len(vias)} GND vias")

    # ── STEP 4: B.Cu Ground Plane ──
    print("[4] Adding B.Cu GND ground plane...")
    zone = Zone()
    zone.type = ZoneType.ZT_COPPER
    zone.layers = [bt.BL_B_Cu]
    zone.net = get_net('GND')
    zone.min_thickness = from_mm(0.25)
    zone.island_mode = IslandRemovalMode.IRM_ALWAYS
    zone.border_style = ZoneBorderStyle.ZBS_DIAGONAL_EDGE

    poly = PolygonWithHoles()
    for cx,cy in [(104.5,48.5),(161.0,48.5),(161.0,97.0),(104.5,97.0)]:
        poly.outline.append(PolyLineNode.from_point(Vector2.from_xy(mm(cx),mm(cy))))
    poly.outline.closed = True
    zone.outline = poly
    board.create_items([zone])

    board.push_commit(commit)
    board.save()

    print("\n✅ COMPLETE: Official RPi5 M.2 HAT+ routing applied!")
    print("   FFC Pin mapping: OFFICIAL (pins 1-2=5V, 4-5=TX, 7-8=RX, 10-11=CLK)")
    print("   Run Inspect → DRC in KiCad to validate")
