import json
import re
import sys
import os
import math

sys.path.insert(0, r'C:\Users\Bibek\NeuroBoard\engines\routing\rust_router')
import grid_router

J1_X = 110.0
J1_Y = 120.0
J2_X = 125.0
J2_Y = 85.0

LIB_DIR = r'C:\Users\Bibek\NeuroBoard\lib\footprint'

def get_pads(fp_name):
    match = None
    for f in os.listdir(LIB_DIR):
        if fp_name in f and f.endswith('.kicad_mod'):
            match = os.path.join(LIB_DIR, f)
            break
    if not match: return {}
    with open(match, "r", encoding="utf-8") as f:
        content = f.read()
    
    pads = {}
    for pad_m in re.finditer(r'\(pad\s+(?:"([^"]+)"|([^\s"]+))\s+[^\)]*(?:\(at\s+([\-\d.]+)\s+([\-\d.]+)\))', content):
        pnum = pad_m.group(1) if pad_m.group(1) else pad_m.group(2)
        lx, ly = float(pad_m.group(3)), float(pad_m.group(4))
        pads[pnum] = (lx, ly)
    return pads

j1_pads = get_pads('C2935243') or get_pads('FPC')
j2_pads = get_pads('APCI0107') or get_pads('C841661')

def world_pos(pads, pnum, ox, oy):
    p = pads.get(pnum)
    if not p:
        p = list(pads.values())[0] if pads else (0, 0)
    return (ox + p[0], oy + p[1])

print(f"J1 pads count: {len(j1_pads)}")
print(f"J2 pads count: {len(j2_pads)}")

j1_tx_p = world_pos(j1_pads, '2', J1_X, J1_Y)
j1_tx_n = world_pos(j1_pads, '3', J1_X, J1_Y)
j1_rx_p = world_pos(j1_pads, '5', J1_X, J1_Y)
j1_rx_n = world_pos(j1_pads, '6', J1_X, J1_Y)

j2_rx_p = world_pos(j2_pads, '11', J2_X, J2_Y)
j2_rx_n = world_pos(j2_pads, '13', J2_X, J2_Y)
j2_tx_p = world_pos(j2_pads, '17', J2_X, J2_Y)
j2_tx_n = world_pos(j2_pads, '19', J2_X, J2_Y)

print(f"J1_TX_P = {j1_tx_p}, J1_TX_N = {j1_tx_n}")
print(f"J2_RX_P = {j2_rx_p}, J2_RX_N = {j2_rx_n}")
print(f"J2_TX_P = {j2_tx_p}, J2_TX_N = {j2_tx_n}")
print(f"J1_RX_P = {j1_rx_p}, J1_RX_N = {j1_rx_n}")

width_gap_mm = 0.15

print("Routing J1_TX -> J2_RX pair...")
path_tx_p, path_tx_n = grid_router.route_differential_pair(
    j1_tx_p, j1_tx_n, j2_rx_p, j2_rx_n, width_gap_mm
)

print("Routing J2_TX -> J1_RX pair...")
path_rx_p, path_rx_n = grid_router.route_differential_pair(
    j2_tx_p, j2_tx_n, j1_rx_p, j1_rx_n, width_gap_mm
)

with open(r'C:\Users\Bibek\NeuroBoard\ai_core\final_routes.json', 'w') as f:
    json.dump({
        'tx_p': path_tx_p, 'tx_n': path_tx_n,
        'rx_p': path_rx_p, 'rx_n': path_rx_n
    }, f)

print("SUCCESS: Routes calculated and saved.")
