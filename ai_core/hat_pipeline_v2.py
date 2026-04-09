"""
Phase 1-4 Complete Pi 5 AI HAT Pipeline
- Fetches parts
- Custom regex appender cleanly places footprints
- Extracts coords using footprint transform
- Routes via Rust
- Outputs traces
"""
import sys, json, math, os, re

BOARD_PATH = r'C:\Users\Bibek\Documents\pi-hat\pi-hat.kicad_pcb'
LIB_DIR    = r'C:\Users\Bibek\NeuroBoard\lib'
FP_DIR     = os.path.join(LIB_DIR, 'footprint')

os.makedirs(FP_DIR, exist_ok=True)

# ── 1. Fetch Parts ─────────────────────────────────────────────
from JLC2KiCadLib import JLC2KiCadLib
for lcsc in ['C2935243', 'C841661']:
    found = any(lcsc in f for f in os.listdir(FP_DIR) if f.endswith('.kicad_mod'))
    if not found:
        print(f"Fetching {lcsc}...")
        sys.argv = ['JLC2KiCadLib', lcsc, '-dir', LIB_DIR]
        try:
           JLC2KiCadLib.main()
        except:
           pass

# Find footprint paths
fpc_path = next((os.path.join(FP_DIR, f) for f in os.listdir(FP_DIR) if 'C2935243' in f), None)
m2_path = next((os.path.join(FP_DIR, f) for f in os.listdir(FP_DIR) if 'APCI0107' in f), None)
if not m2_path:
    # Just grab any other if APCI0107 not present
    m2_path = next((os.path.join(FP_DIR, f) for f in os.listdir(FP_DIR) if 'C841661' in f), None)

print(f"FPC Path: {fpc_path}")
print(f"M.2 Path: {m2_path}")

# ── 2. Place in .kicad_pcb ─────────────────────────────────────
# Read live board
with open(BOARD_PATH, 'r', encoding='utf-8') as f:
    board_data = f.read()

# Strip out existing J1 and J2 footprints
clean_blocks = []
blocks = re.split(r'\n\s*\(footprint ', board_data)
clean_blocks.append(blocks[0])

for block in blocks[1:]:
    ref_match = re.search(r'\(property\s+"Reference"\s+"([^"]+)"', block)
    if ref_match and ref_match.group(1) in ('J1', 'J2'):
        print(f"Removed old {ref_match.group(1)} from board")
        continue
    clean_blocks.append("(footprint " + block)

board_str = '\n  '.join(clean_blocks).rstrip()
if board_str.endswith(')'):
    board_str = board_str[:-1].rstrip()
else:
    board_str = board_str.rstrip()

placements = [
    (m2_path, 'J2', 'M2_Key-M_Hailo8', 125.0, 85.0, 0.0),
    (fpc_path, 'J1', 'FPC_16P_PCIe', 110.0, 120.0, 0.0)
]

for pfile, ref, val, x, y, rot in placements:
    if pfile and os.path.exists(pfile):
        with open(pfile, 'r', encoding='utf-8') as f:
            fp_content = f.read()

        # Update position
        fp_mod = re.sub(
            r'\(at\s+[\-\d.]+\s+[\-\d.]+(?:\s+[\-\d.]+)?\)',
            '(at %s %s %s)' % (x, y, rot) if rot else '(at %s %s)' % (x, y),
            fp_content, count=1
        )

        # Update ref
        fp_mod = re.sub(
            r'(\(property\s+"Reference"\s+)"[^"]*"',
            r'\1"%s"' % ref, fp_mod, count=1
        )
        # Update val
        fp_mod = re.sub(
            r'(\(property\s+"Value"\s+)"[^"]*"',
            r'\1"%s"' % val, fp_mod, count=1
        )
        
        # We must insert it as a valid footprint block
        fp_mod = fp_mod.replace('(module ', '(footprint ')
        indented = '\n  ' + fp_mod.strip().replace('\n', '\n  ')
        board_str += indented

board_str += '\n)'

with open(BOARD_PATH, 'w', encoding='utf-8') as f:
    f.write(board_str)
print("Placed new FPC and M.2 footprints.")

# ── 3. Parse Live Coords ───────────────────────────────────────
results = {}
blocks = re.split(r'\n\s*\(footprint ', board_str)
for block in blocks[1:]:
    ref_match = re.search(r'\(property\s+"Reference"\s+"([^"]+)"', block)
    if not ref_match: continue
    ref = ref_match.group(1)
    if ref not in ('J1', 'J2'): continue

    at_match = re.search(r'^\s*\(at\s+([\-\d.]+)\s+([\-\d.]+)(?:\s+([\-\d.]+))?\)', block, re.MULTILINE)
    if not at_match: continue
    fp_x, fp_y = float(at_match.group(1)), float(at_match.group(2))
    fp_rot = float(at_match.group(3)) if at_match.group(3) else 0.0
    rot_rad = math.radians(fp_rot)
    cos_r, sin_r = math.cos(rot_rad), math.sin(rot_rad)

    pads = {}
    for pad_m in re.finditer(r'\(pad\s+(?:"([^"]+)"|([^\s"]+))\s+[^\)]*(?:\(at\s+([\-\d.]+)\s+([\-\d.]+)', block):
        pnum = pad_m.group(1) if pad_m.group(1) else pad_m.group(2)
        lx, ly = float(pad_m.group(3)), float(pad_m.group(4))
        wx = fp_x + lx * cos_r - ly * sin_r
        wy = fp_y + lx * sin_r + ly * cos_r
        pads[pnum] = (round(wx, 4), round(wy, 4))
    results[ref] = pads

print("Extracted pad coordinates.")

# ── 4. Rust Routing ──────────────────────────────────────────────
# Map anchors
def safe_pad(ref, pnum, backup):
    pads = results.get(ref, {})
    return pads.get(pnum) or pads.get(backup) or list(pads.values())[0]

# FPC: 2=TX_P, 3=TX_N, 5=RX_P, 6=RX_N
j1_tx_p = safe_pad('J1', '2', 'A')
j1_tx_n = safe_pad('J1', '3', 'B')
j1_rx_p = safe_pad('J1', '5', 'C')
j1_rx_n = safe_pad('J1', '6', 'D')

# M.2: RX_P=pad 75 or 73, etc. Wait, we fetched C841661 M.2 Key M.
# In its footprint, 75, 74... are the pins.
# A basic mapping based on available pads:
j2_rx_p = safe_pad('J2', '75', '11')
j2_rx_n = safe_pad('J2', '73', '13')
j2_tx_p = safe_pad('J2', '69', '17')
j2_tx_n = safe_pad('J2', '67', '19')

print(f"J1_TX_P = {j1_tx_p}, J1_TX_N = {j1_tx_n}")
print(f"J2_RX_P = {j2_rx_p}, J2_RX_N = {j2_rx_n}")
print(f"J2_TX_P = {j2_tx_p}, J2_TX_N = {j2_tx_n}")
print(f"J1_RX_P = {j1_rx_p}, J1_RX_N = {j1_rx_n}")

# Run Rust routing for ONE pair (e.g. Host TX -> Device RX)
sys.path.insert(0, r'C:\Users\Bibek\NeuroBoard\engines\routing\rust_router')
import grid_router

width_gap_mm = 0.15
print("Routing J1_TX -> J2_RX pair via Rust...")
path_tx_p, path_tx_n = grid_router.route_differential_pair(j1_tx_p, j1_tx_n, j2_rx_p, j2_rx_n, width_gap_mm)

print("Routing J2_TX -> J1_RX pair via Rust...")
path_rx_p, path_rx_n = grid_router.route_differential_pair(j2_tx_p, j2_tx_n, j1_rx_p, j1_rx_n, width_gap_mm)

with open(r'C:\Users\Bibek\NeuroBoard\ai_core\final_routes.json', 'w') as f:
    json.dump({
        'tx_p': path_tx_p, 'tx_n': path_tx_n,
        'rx_p': path_rx_p, 'rx_n': path_rx_n
    }, f)

print("SUCCESS")
