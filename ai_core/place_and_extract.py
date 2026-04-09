import pcbnew
import sys
import os
import math

BOARD_PATH = r'C:\Users\Bibek\Documents\pi-hat\pi-hat.kicad_pcb'
LIB_DIR = r'C:\Users\Bibek\NeuroBoard\lib\footprint'

board = pcbnew.LoadBoard(BOARD_PATH)
if not board:
    print('Failed to load board')
    sys.exit(1)

# Remove existing J1 and J2 if they exist
for ref in ['J1', 'J2']:
    fp = board.FindFootprintByReference(ref)
    if fp:
        board.Remove(fp)

# Load FPC Footprint (C2935243 -> Assuming 'FPC' or whatever its name is)
fpc_name = None
m2_name = None
for f in os.listdir(LIB_DIR):
    if f.endswith('.kicad_mod'):
        if 'C2935243' in f:
            fpc_name = f.replace('.kicad_mod', '')
        elif 'APCI0107' in f:
            m2_name = f.replace('.kicad_mod', '')

if not fpc_name:
    # try to find anything starting with FPC
    for f in os.listdir(LIB_DIR):
        if 'FPC' in f.upper() and f.endswith('.kicad_mod'):
            fpc_name = f.replace('.kicad_mod', '')
            break

print(f"Using FPC Footprint: {fpc_name}")
print(f"Using M2 Footprint: {m2_name}")

if fpc_name:
    fp_fpc = pcbnew.FootprintLoad(LIB_DIR, fpc_name)
    if fp_fpc:
        fp_fpc.SetReference('J1')
        fp_fpc.SetValue('FPC_16P_PCIe')
        fp_fpc.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(110.0), pcbnew.FromMM(120.0)))
        fp_fpc.SetLayer(pcbnew.F_Cu)
        board.Add(fp_fpc)

if m2_name:
    fp_m2 = pcbnew.FootprintLoad(LIB_DIR, m2_name)
    if fp_m2:
        fp_m2.SetReference('J2')
        fp_m2.SetValue('M.2_Key-M_Hailo8')
        fp_m2.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(125.0), pcbnew.FromMM(85.0)))
        fp_m2.SetLayer(pcbnew.F_Cu)
        board.Add(fp_m2)

board.Save(BOARD_PATH)
print("Board saved with new footprints J1 and J2.")

# Now extract live pad coordinates
results = {}
for fp in board.Footprints():
    ref = fp.GetReference()
    if ref in ['J1', 'J2']:
        pads = {}
        for pad in fp.Pads():
            p = pad.GetPosition()
            pads[pad.GetNumber()] = {
                'x': pcbnew.ToMM(p.x),
                'y': pcbnew.ToMM(p.y)
            }
        results[ref] = pads

import json
with open(r'C:\Users\Bibek\NeuroBoard\ai_core\live_pads_kicad.json', 'w') as f:
    json.dump(results, f, indent=2)

print("Saved pad coordinates.")
