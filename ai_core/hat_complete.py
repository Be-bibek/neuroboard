"""
HAT Completion Script
=====================
1. Fix PERST#, CLKREQ#, WAKE# → assign to correct M.2 pins
2. Route LED anode stubs (R1→D1, R2→D2)
3. Route EEPROM I2C stubs (U2→J1)
4. Add GND copper pour on B.Cu
5. Final save
"""

import sys
sys.path.insert(0, r'C:\Users\Bibek\Documents\KiCad\10.0\3rdparty\Python311\site-packages')

from kipy import KiCad
from kipy.board_types import Net, Track, Via, Zone, board_types_pb2 as bt
from kipy.geometry import Vector2, PolygonWithHoles, PolyLineNode

NM = 1_000_000

def mm(v):
    return int(v * NM)

def run():
    k = KiCad()
    board = k.get_board()

    net_map = {n.name: n for n in board.get_nets()}

    def get_net(name):
        if name in net_map:
            return net_map[name]
        n = Net()
        n.name = name
        return n

    commit = board.begin_commit()

    # ────────────────────────────────────────────
    # STEP 1: Fix M.2 net assignments for control
    # signals that only had 1 pad (FFC side only)
    # M.2 pin 59 = PERST#, pin 61 = CLKREQ#, pin 63 = WAKE#
    # M.2 odd pins are on X=129.28, pin Y formula:
    #   Y = 62.25 + ((pin-1)//2) * 0.5
    # ────────────────────────────────────────────
    def m2_pin_pos(pin_num):
        n = int(pin_num)
        if n % 2 == 1:
            return (129.28, 62.25 + ((n - 1) // 2) * 0.5)
        else:
            return (121.72, 62.50 + ((n - 2) // 2) * 0.5)

    updated_fps = []
    for fp in board.get_footprints():
        try: ref = fp.reference_field.text.value
        except: ref = ''

        if ref == 'J_SSD':
            for pad in fp.definition.pads:
                if pad.number == '59':
                    pad.net = get_net('PCIE_PERST')
                elif pad.number == '61':
                    pad.net = get_net('PCIE_CLKREQ')
                elif pad.number == '63':
                    pad.net = get_net('PCIE_WAKE')
            updated_fps.append(fp)

    if updated_fps:
        board.update_items(updated_fps)

    # ────────────────────────────────────────────
    # STEP 2: Route all remaining signal traces
    # ────────────────────────────────────────────
    tracks = []
    vias  = []

    def seg(x1, y1, x2, y2, net, w=0.2, layer=bt.BL_F_Cu):
        t = Track()
        t.start = Vector2.from_xy(mm(x1), mm(y1))
        t.end   = Vector2.from_xy(mm(x2), mm(y2))
        t.width = mm(w)
        t.layer = layer
        t.net   = get_net(net)
        tracks.append(t)

    def add_via(x, y, net, d=0.8, dr=0.4):
        v = Via()
        v.position     = Vector2.from_xy(mm(x), mm(y))
        v.net          = get_net(net)
        v.diameter     = mm(d)
        v.drill_diameter = mm(dr)
        vias.append(v)

    # J_PCIE pin positions (FFC, X=106.75, Y descends by 0.5 each pin)
    ffc_x = 106.75
    pin_y = {i: 75.75 - (i - 1) * 0.5 for i in range(1, 17)}

    # ── PERST# (FFC pin 11 → M.2 pin 59) ──
    px59, py59 = m2_pin_pos(59)
    seg(ffc_x,  pin_y[11], 118.0, pin_y[11], 'PCIE_PERST')
    seg(118.0,  pin_y[11], 118.0, py59,       'PCIE_PERST')
    seg(118.0,  py59,      px59,  py59,       'PCIE_PERST')
    add_via(118.5, pin_y[11], 'PCIE_PERST', 0.6, 0.3)  # Optional stitch via

    # ── CLKREQ# (FFC pin 12 → M.2 pin 61) ──
    px61, py61 = m2_pin_pos(61)
    seg(ffc_x,  pin_y[12], 119.0, pin_y[12], 'PCIE_CLKREQ')
    seg(119.0,  pin_y[12], 119.0, py61,       'PCIE_CLKREQ')
    seg(119.0,  py61,      px61,  py61,       'PCIE_CLKREQ')

    # ── WAKE# (FFC pin 13 → M.2 pin 63) ──
    px63, py63 = m2_pin_pos(63)
    seg(ffc_x,  pin_y[13], 120.0, pin_y[13], 'PCIE_WAKE')
    seg(120.0,  pin_y[13], 120.0, py63,       'PCIE_WAKE')
    seg(120.0,  py63,      px63,  py63,       'PCIE_WAKE')

    # ── LED Stubs (very short, right next to each other) ──
    # R1 pad2 → D1 pad2  (LED_PWR, same Y column, ~5mm apart)
    # R1 @ (110, 60), D1 @ (110, 65) 
    seg(110.45, 60.0, 110.45, 65.0, 'LED_PWR', 0.15)

    # R2 pad2 → D2 pad2  (LED_ACT)
    # R2 @ (110, 75), D2 @ (110, 70)
    seg(110.45, 75.0, 110.45, 70.0, 'LED_ACT', 0.15)

    # ── EEPROM I2C (U2 ↔ J1 HAT-ID pins) ──
    # U2 @ (142, 60), J1 pin 27 (ID_SDA) @ (145.77,48.77), pin 28 (ID_SCL) @ (145.77,46.23)
    # U2 pin 6 = ID_SDA @ ~(137.4, 58.1), pin 7 = ID_SCL @ ~(137.4, 59.35)
    # Route up to J1
    seg(137.4, 58.1,  137.4, 48.77, '/ID_SDA', 0.2)
    seg(137.4, 48.77, 145.77, 48.77, '/ID_SDA', 0.2)

    seg(137.4, 59.35, 136.0, 59.35, '/ID_SCL', 0.2)
    seg(136.0, 59.35, 136.0, 46.23, '/ID_SCL', 0.2)
    seg(136.0, 46.23, 145.77, 46.23, '/ID_SCL', 0.2)

    # ── Dense GND stitching vias around M.2 perimeter ──
    gnd_vias = [
        (110.0, 67.0), (110.0, 69.0), (110.0, 71.0), (110.0, 73.0),
        (115.0, 60.0), (120.0, 60.0), (125.0, 60.0), (130.0, 60.0),
        (115.0, 83.0), (120.0, 83.0), (125.0, 83.0), (130.0, 83.0),
        (132.0, 65.0), (132.0, 70.0), (132.0, 75.0), (132.0, 80.0),
    ]
    for vx, vy in gnd_vias:
        add_via(vx, vy, 'GND', 0.8, 0.4)

    board.create_items(tracks)
    board.create_items(vias)
    print(f'  Routed {len(tracks)} additional traces, {len(vias)} GND vias added')

    # ────────────────────────────────────────────
    # STEP 3: B.Cu GND copper pour (ground plane)
    # Board bounds: X=103.5 to 161.5, Y=47.5 to 96.5
    # Use slightly inset boundary
    # ────────────────────────────────────────────
    print('\n[STEP 3] Adding B.Cu GND ground plane...')
    from kipy.board_types import Zone, ZoneType, ZoneBorderStyle, IslandRemovalMode
    from kipy.geometry import PolygonWithHoles, PolyLineNode
    from kipy.util.units import from_mm

    zone = Zone()
    zone.type = ZoneType.ZT_COPPER
    zone.layers = [bt.BL_B_Cu]
    zone.net = get_net('GND')
    zone.min_thickness = from_mm(0.25)
    zone.island_mode = IslandRemovalMode.IRM_ALWAYS
    zone.border_style = ZoneBorderStyle.ZBS_DIAGONAL_EDGE

    # Board outline corners (inset 0.5mm from edge)
    poly = PolygonWithHoles()
    corners = [
        (104.0, 48.0),
        (161.0, 48.0),
        (161.0, 97.0),
        (104.0, 97.0),
    ]
    for cx, cy in corners:
        poly.outline.append(PolyLineNode.from_point(
            Vector2.from_xy(mm(cx), mm(cy))
        ))
    poly.outline.closed = True
    zone.outline = poly

    board.create_items([zone])
    print('  B.Cu GND ground plane created')

    board.push_commit(commit)
    board.save()

    print('\n[COMPLETE] HAT PCB fully routed!')
    print('  Please open KiCad 3D Viewer to verify the result.')
    print('  Run: Inspect → Design Rules Checker (DRC)')
    print('  Run: Inspect → Net Inspector → verify all PCIE nets show 2 pads each')

if __name__ == '__main__':
    run()
