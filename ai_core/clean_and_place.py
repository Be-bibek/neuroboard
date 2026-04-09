import pcbnew
import sys
import os

BOARD_PATH = r'C:\Users\Bibek\Documents\pi-hat\pi-hat.kicad_pcb'
LIB_DIR = r'C:\Users\Bibek\NeuroBoard\lib\footprint'

board = getattr(pcbnew, "GetBoard", lambda: None)()
if not board:
    try:
        board = pcbnew.LoadBoard(BOARD_PATH)
    except Exception as e:
        board = pcbnew.LoadBoard(BOARD_PATH)

if not board:
    print('Failed to load board in KiCad standalone python')
    sys.exit(1)

# Remove all existing J1 and J2
for fp in list(board.Footprints()):
    if fp.GetReference() in ['J1', 'J2']:
        board.Remove(fp)

# M.2 Connector
m2_path = LIB_DIR
m2_name = 'CONN-SMD_APCI0107-P001A'
fp_m2 = pcbnew.FootprintLoad(m2_path, m2_name)
if fp_m2:
    fp_m2.SetReference('J2')
    fp_m2.SetValue('M.2_Key-M_Hailo8')
    fp_m2.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(125.0), pcbnew.FromMM(85.0)))
    fp_m2.SetLayer(pcbnew.F_Cu)
    board.Add(fp_m2)
    print("Placed J2 (M.2)")
else:
    print("Failed to load M.2 footprint")

# Find FPC Connector NAME
fpc_name = None
for f in os.listdir(LIB_DIR):
    if 'C2935243' in f:
        fpc_name = f.replace('.kicad_mod', '')
        break
if not fpc_name:
    # Just grab any other file
    for f in os.listdir(LIB_DIR):
        if 'APCI0107' not in f and f.endswith('.kicad_mod'):
            fpc_name = f.replace('.kicad_mod', '')
            break

if fpc_name:
    fp_fpc = pcbnew.FootprintLoad(LIB_DIR, fpc_name)
    if fp_fpc:
        fp_fpc.SetReference('J1')
        fp_fpc.SetValue('FPC_16P_PCIe')
        fp_fpc.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(110.0), pcbnew.FromMM(120.0)))
        fp_fpc.SetLayer(pcbnew.F_Cu)
        board.Add(fp_fpc)
        print(f"Placed J1 (FPC) from {fpc_name}")
else:
    print("Failed to load FPC footprint")

board.Save(BOARD_PATH)
print("Saved to:", BOARD_PATH)

results = {}
for fp in board.Footprints():
    ref = fp.GetReference()
    if ref in ['J1', 'J2']:
        pads = {}
        for pad in fp.Pads():
            p = pad.GetPosition()
            pads[pad.GetName()] = {
                'x': pcbnew.ToMM(p.x),
                'y': pcbnew.ToMM(p.y)
            }
        results[ref] = pads

import json
with open(r'C:\Users\Bibek\NeuroBoard\ai_core\live_pads_kicad.json', 'w') as f:
    json.dump(results, f, indent=2)

print("Coordinate Extraction Complete.")
