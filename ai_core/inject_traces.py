import json

BOARD_PATH = r'C:\Users\Bibek\Documents\pi-hat\pi-hat.kicad_pcb'
ROUTES_PATH = r'C:\Users\Bibek\NeuroBoard\ai_core\final_routes.json'

with open(ROUTES_PATH, 'r') as f:
    routes = json.load(f)

# Build segment strings
segments_str = ""
for key in ['tx_p', 'tx_n', 'rx_p', 'rx_n']:
    pts = routes.get(key, [])
    if len(pts) < 2: continue
    for i in range(len(pts) - 1):
        x1, y1 = pts[i]
        x2, y2 = pts[i+1]
        width = 0.15
        seg = f'\n  (segment (start {x1:.4f} {y1:.4f}) (end {x2:.4f} {y2:.4f}) (width {width}) (layer "F.Cu") (net 0))'
        segments_str += seg

# Append to board
with open(BOARD_PATH, 'r', encoding='utf-8') as f:
    board_str = f.read()

board_str = board_str.rstrip()
if board_str.endswith(')'):
    board_str = board_str[:-1].rstrip()

board_str = board_str + segments_str + "\n)\n"

with open(BOARD_PATH, 'w', encoding='utf-8') as f:
    f.write(board_str)

print("Successfully appended fully computed PCIe traces to the KiCad board.")
