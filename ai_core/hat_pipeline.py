"""
Pi 5 AI HAT+ Clone — Full Autonomous Pipeline
Phases 1-4: Fetch → Place → Route → Commit

Pi 5 FPC PCIe connector (16-pin, 0.5mm pitch) pinout (official spec):
  Pin 01: GND
  Pin 02: TX_P   (PCIe TX positive)
  Pin 03: TX_N   (PCIe TX negative)
  Pin 04: GND
  Pin 05: RX_P   (PCIe RX positive)
  Pin 06: RX_N   (PCIe RX negative)
  Pin 07: GND
  Pin 08: REFCLK_P
  Pin 09: REFCLK_N
  Pin 10: GND
  Pin 11: PERST_N
  Pin 12: CLKREQ_N
  Pin 13: PCIE_DET_WAKE
  Pin 14: PCIE_PWR_EN
  Pin 15: 5V
  Pin 16: 5V

M.2 Key-M PCIe x1 lanes (relative to Key-M B pin row, standard pinout):
  Pin 11: PETP0   (TX P from host)
  Pin 13: PETN0   (TX N from host)
  Pin 15: GND
  Pin 17: PERP0   (RX P to host)
  Pin 19: PERN0   (RX N to host)
"""

import sys, json, math, os, re

BOARD_PATH = r'C:\Users\Bibek\Documents\pi-hat\pi-hat.kicad_pcb'
LIB_DIR    = r'C:\Users\Bibek\NeuroBoard\lib'
FP_DIR     = os.path.join(LIB_DIR, 'footprint')
SYM_DIR    = os.path.join(LIB_DIR, 'symbol')
OUT_JSON   = r'C:\Users\Bibek\NeuroBoard\ai_core\live_pads.json'

# Ensure lib dirs exist
for d in [FP_DIR, SYM_DIR, os.path.join(FP_DIR, 'packages3d')]:
    os.makedirs(d, exist_ok=True)

# ─────────────────────────────────────────────────────────────────────────────
# PHASE 1: Fetch parts via JLC2KiCadLib
# ─────────────────────────────────────────────────────────────────────────────
print("=" * 60)
print("PHASE 1: Fetching LCSC parts")
print("=" * 60)

from JLC2KiCadLib import JLC2KiCadLib

parts = {
    'C2935243': 'FPC 16-pin 0.5mm (Pi5 PCIe)',
    'C841661':  'M.2 Key-M connector (Hailo-8)',
}

already_fetched = {}
for lcsc, desc in parts.items():
    # Check if already downloaded
    existing = [f for f in os.listdir(FP_DIR) if not os.path.isdir(os.path.join(FP_DIR, f)) and lcsc in f]
    if existing:
        print("[SKIP] %s (%s) — already in lib/" % (lcsc, desc))
        already_fetched[lcsc] = True
        continue

    print("[FETCH] %s — %s ..." % (lcsc, desc))
    sys.argv = ['JLC2KiCadLib', lcsc, '-dir', LIB_DIR]
    try:
        JLC2KiCadLib.main()
        print("[OK]   %s fetched" % lcsc)
    except SystemExit:
        pass  # JLC2KiCadLib calls sys.exit(0) on success
    already_fetched[lcsc] = False

# List what we have
print("\nLib contents:")
for f in sorted(os.listdir(FP_DIR)):
    fp = os.path.join(FP_DIR, f)
    if os.path.isfile(fp):
        print("  footprint/%s  (%d bytes)" % (f, os.path.getsize(fp)))

# ─────────────────────────────────────────────────────────────────────────────
# PHASE 2: Place footprints into the .kicad_pcb file
# ─────────────────────────────────────────────────────────────────────────────
print("\n" + "=" * 60)
print("PHASE 2: Placing footprints")
print("=" * 60)

# Find downloaded footprint files
fp_files = {f: os.path.join(FP_DIR, f) for f in os.listdir(FP_DIR)
            if f.endswith('.kicad_mod') and os.path.isfile(os.path.join(FP_DIR, f))}

print("Available footprints:", list(fp_files.keys()))

# Map LCSC → footprint file (pick first match)
def find_fp(keyword):
    for name, path in fp_files.items():
        if keyword.lower() in name.lower():
            return name.replace('.kicad_mod', ''), path
    return None, None

fpc_name, fpc_path   = find_fp('C2935243')
m2_name,  m2_path    = find_fp('APCI0107')  # C841661 downloads as APCI0107-P001A

if not fpc_path:
    # Try any FPC-like footprint
    fpc_name, fpc_path = find_fp('FPC')
    if not fpc_path:
        fpc_name, fpc_path = list(fp_files.items())[0] if fp_files else (None, None)
        if fpc_name:
            fpc_name = fpc_name.replace('.kicad_mod', '')

print("FPC footprint : %s" % fpc_name)
print("M.2 footprint : %s" % m2_name)

def read_footprint(fp_path):
    """Read a .kicad_mod file and return its contents."""
    with open(fp_path, 'r', encoding='utf-8') as f:
        return f.read()

def place_footprint_in_pcb(board_path, fp_content, reference, value, x_mm, y_mm, rotation=0.0, layer='F.Cu'):
    """
    Inject a footprint into an existing .kicad_pcb file by appending it before
    the last closing parenthesis. Rewrites the (at ...) and Reference/Value props.
    """
    with open(board_path, 'r', encoding='utf-8') as f:
        board = f.read()

    # Replace the (at ...) in the footprint with the target position
    fp_mod = re.sub(
        r'\(at\s+[\-\d.]+\s+[\-\d.]+(?:\s+[\-\d.]+)?\)',
        '(at %s %s %s)' % (x_mm, y_mm, rotation) if rotation else '(at %s %s)' % (x_mm, y_mm),
        fp_content, count=1
    )

    # Set reference
    fp_mod = re.sub(
        r'(\(property\s+"Reference"\s+)"[^"]*"',
        r'\1"%s"' % reference,
        fp_mod, count=1
    )
    # Set value
    fp_mod = re.sub(
        r'(\(property\s+"Value"\s+)"[^"]*"',
        r'\1"%s"' % value,
        fp_mod, count=1
    )

    # Ensure it has a unique UUID placeholder (strip (uuid ...) blocks so no conflicts)
    # We'll leave UUIDs as-is for simplicity; KiCad handles duplicates on open

    # Indent the footprint block with a tab for PCB top-level
    indented = '\t' + fp_mod.strip().replace('\n', '\n\t')

    # Insert before the final closing paren of the board
    board = board.rstrip()
    if board.endswith(')'):
        board = board[:-1].rstrip() + '\n' + indented + '\n)'
    else:
        board += '\n' + indented

    with open(board_path, 'w', encoding='utf-8') as f:
        f.write(board)

    print("[PLACED] %s at (%.2f, %.2f) rot=%.0f" % (reference, x_mm, y_mm, rotation))

# Place FPC connector at (110, 120)
if fpc_path:
    fp_content = read_footprint(fpc_path)
    place_footprint_in_pcb(BOARD_PATH, fp_content, 'J1', 'FPC_PCIe_16P', 110.0, 120.0, 0.0)
else:
    print("[WARN] FPC footprint not found — skipping J1 placement")

# Place M.2 connector at (125, 85)
if m2_path:
    fp_content = read_footprint(m2_path)
    place_footprint_in_pcb(BOARD_PATH, fp_content, 'J2', 'M2_Key-M_Hailo8', 125.0, 85.0, 0.0)
else:
    print("[WARN] M.2 footprint not found — skipping J2 placement")

# ─────────────────────────────────────────────────────────────────────────────
# PHASE 3a: Parse live board to get pad coordinates
# ─────────────────────────────────────────────────────────────────────────────
print("\n" + "=" * 60)
print("PHASE 3a: Reading live pad coordinates")
print("=" * 60)

with open(BOARD_PATH, 'r', encoding='utf-8') as f:
    raw = f.read()

fp_blocks = re.split(r'\n\t(?=\(footprint )', raw)
results = {}

for block in fp_blocks[1:]:
    ref_match = re.search(r'\(property\s+"Reference"\s+"([^"]+)"', block)
    if not ref_match:
        continue
    ref = ref_match.group(1)
    if ref not in ('J1', 'J2'):
        continue

    at_match = re.search(r'^\s*\(at\s+([\-\d.]+)\s+([\-\d.]+)(?:\s+([\-\d.]+))?\)', block, re.MULTILINE)
    if not at_match:
        continue
    fp_x   = float(at_match.group(1))
    fp_y   = float(at_match.group(2))
    fp_rot = float(at_match.group(3)) if at_match.group(3) else 0.0
    rot_rad = math.radians(fp_rot)
    cos_r, sin_r = math.cos(rot_rad), math.sin(rot_rad)

    pads = {}
    for pad_m in re.finditer(
        r'\(pad\s+"([^"]*)"[^(]*(?:\(at\s+([\-\d.]+)\s+([\-\d.]+)(?:\s+[\-\d.]+)?\))',
        block
    ):
        pnum, lx, ly = pad_m.group(1), float(pad_m.group(2)), float(pad_m.group(3))
        wx = fp_x + lx * cos_r - ly * sin_r
        wy = fp_y + lx * sin_r + ly * cos_r
        pads[pnum] = {'x': round(wx, 4), 'y': round(wy, 4)}

    results[ref] = pads
    sorted_pads = sorted(pads.keys(), key=lambda x: int(x) if x.isdigit() else 999)
    print("%s at (%.3f, %.3f) rot=%.0f° — %d pads" % (ref, fp_x, fp_y, fp_rot, len(pads)))
    for p in sorted_pads[:6]:
        print("  Pad %s: X=%.4f  Y=%.4f" % (p, pads[p]['x'], pads[p]['y']))

with open(OUT_JSON, 'w') as f:
    json.dump(results, f, indent=2)
print("\nLive pads saved: %s" % OUT_JSON)

# ─────────────────────────────────────────────────────────────────────────────
# PHASE 3b: Determine routing anchor pads
# ─────────────────────────────────────────────────────────────────────────────
print("\n" + "=" * 60)
print("PHASE 3b: Selecting TX/RX anchor pads")
print("=" * 60)

# Official Pi5 FPC pinout: Pin2=TX_P, Pin3=TX_N (PCIe signals from Pi perspective)
# M.2 Key-M: Pad 11=PETP0 (RX_P from HAT), Pad 13=PETN0 (RX_N from HAT)
# On the HAT, FPC TX → M.2 RX

def get_pad(ref, pad_num):
    pad_str = str(pad_num)
    if ref not in results:
        return None
    return results[ref].get(pad_str)

# FPC J1 anchors
j1_tx_p = get_pad('J1', 2)   # Pin 2 = TX_P
j1_tx_n = get_pad('J1', 3)   # Pin 3 = TX_N
j1_rx_p = get_pad('J1', 5)   # Pin 5 = RX_P
j1_rx_n = get_pad('J1', 6)   # Pin 6 = RX_N

# M.2 J2 anchors
j2_rx_p = get_pad('J2', 11)  # PETP0
j2_rx_n = get_pad('J2', 13)  # PETN0
j2_tx_p = get_pad('J2', 17)  # PERP0
j2_tx_n = get_pad('J2', 19)  # PERN0

def fallback_pad(ref, start_idx):
    """Return first available pad if specific pad missing."""
    if ref not in results:
        return None
    pads = results[ref]
    for i in range(start_idx, start_idx + 10):
        p = pads.get(str(i))
        if p:
            return p
    return list(pads.values())[0] if pads else None

if not j1_tx_p: j1_tx_p = fallback_pad('J1', 2)
if not j1_tx_n: j1_tx_n = fallback_pad('J1', 3)
if not j2_rx_p: j2_rx_p = fallback_pad('J2', 1)
if not j2_rx_n: j2_rx_n = fallback_pad('J2', 3)

routing = {
    'J1_TX_P': j1_tx_p, 'J1_TX_N': j1_tx_n,
    'J1_RX_P': j1_rx_p, 'J1_RX_N': j1_rx_n,
    'J2_RX_P': j2_rx_p, 'J2_RX_N': j2_rx_n,
    'J2_TX_P': j2_tx_p, 'J2_TX_N': j2_tx_n,
}
for k, v in routing.items():
    print("  %-10s : %s" % (k, v))

with open(r'C:\Users\Bibek\NeuroBoard\ai_core\routing_anchors.json', 'w') as f:
    json.dump(routing, f, indent=2)
print("\nAnchors saved.")
print("\nPIPELINE SCRIPT COMPLETE — ready for Rust router + IPC commit")
