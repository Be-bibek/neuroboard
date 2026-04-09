import sys, json

sys.path.insert(0, r'C:\Users\Bibek\NeuroBoard\engines\routing\rust_router')
import grid_router

BOARD_PATH = r"C:\Users\Bibek\Documents\pi-hat\pi-hat.kicad_pcb"

with open(r'C:\Users\Bibek\NeuroBoard\ai_core\live_pads_val.json', 'r') as f:
    d = json.load(f)

fpc = d['FPC-16P-0.5mm']['pads']
m2 = d['CONN-SMD_APCI0107-P001A']['pads']

def pt(val):
    return (float(val[0]), float(val[1]))

tx_p_src = pt(fpc['2'])
tx_n_src = pt(fpc['3'])
rx_p_dst = pt(m2['75'])
rx_n_dst = pt(m2['73'])

tx_p_src2 = pt(m2['69'])
tx_n_src2 = pt(m2['67'])
rx_p_dst2 = pt(fpc['5'])
rx_n_dst2 = pt(fpc['6'])

width_gap_mm = 0.15

path_tx_p, path_tx_n = grid_router.route_differential_pair(
    tx_p_src, tx_n_src, rx_p_dst, rx_n_dst, width_gap_mm
)

path_rx_p, path_rx_n = grid_router.route_differential_pair(
    tx_p_src2, tx_n_src2, rx_p_dst2, rx_n_dst2, width_gap_mm
)

segments_str = ""
for net, path in [('PCIe_TX_P', path_tx_p), ('PCIe_TX_N', path_tx_n), ('PCIe_RX_P', path_rx_p), ('PCIe_RX_N', path_rx_n)]:
    if len(path) < 2: continue
    for i in range(len(path)-1):
        x1, y1 = path[i]
        x2, y2 = path[i+1]
        segments_str += f'\n  (segment (start {x1:.4f} {y1:.4f}) (end {x2:.4f} {y2:.4f}) (width {width_gap_mm}) (layer "F.Cu") (net 0))'

with open(BOARD_PATH, 'r', encoding='utf-8') as f:
    board_str = f.read()

board_str = board_str.rstrip()
if board_str.endswith(')'):
    board_str = board_str[:-1].rstrip()

board_str = board_str + segments_str + "\n)\n"

with open(BOARD_PATH, 'w', encoding='utf-8') as f:
    f.write(board_str)

print("SUCCESS: IPC fallback completed. Traces saved directly to pi-hat.kicad_pcb")
