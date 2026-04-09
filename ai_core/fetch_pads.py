"""
Closed-loop pad coordinate extractor — pure Python, no pcbnew dependency.
Parses the .kicad_pcb S-expression format to extract live pad positions.
"""
import re, json, sys, math

BOARD_PATH = r'C:\Users\Bibek\Documents\pi-hat\pi-hat.kicad_pcb'
OUTPUT_JSON = r'C:\Users\Bibek\NeuroBoard\ai_core\live_pads.json'

with open(BOARD_PATH, 'r', encoding='utf-8') as f:
    raw = f.read()

# ── Parse footprint blocks ────────────────────────────────────────────────
# Each footprint block: (footprint "lib:name" ... (at X Y ROT) ... (property "Reference" "Jx" ...) ... (pad "N" ...))

def deg2rad(d):
    return math.radians(d)

# Split into footprint blocks by finding (footprint at top-level indent
fp_blocks = re.split(r'\n\t(?=\(footprint )', raw)

results = {}

for block in fp_blocks[1:]:   # skip header
    # Get reference
    ref_match = re.search(r'\(property\s+"Reference"\s+"([^"]+)"', block)
    if not ref_match:
        continue
    ref = ref_match.group(1)
    if ref not in ('J1', 'J2'):
        continue

    # Get footprint position (at X Y [ROT])
    at_match = re.search(r'^\s*\(at\s+([\-\d.]+)\s+([\-\d.]+)(?:\s+([\-\d.]+))?\)', block, re.MULTILINE)
    if not at_match:
        continue
    fp_x   = float(at_match.group(1))
    fp_y   = float(at_match.group(2))
    fp_rot = float(at_match.group(3)) if at_match.group(3) else 0.0

    rot_rad = deg2rad(fp_rot)

    print("%s body: X=%.4f  Y=%.4f  ROT=%.1f deg" % (ref, fp_x, fp_y, fp_rot))

    # Parse each pad
    pads = {}
    for pad_block in re.finditer(
        r'\(pad\s+"([^"]*)"[^(]*(?:\(at\s+([\-\d.]+)\s+([\-\d.]+)(?:\s+[\-\d.]+)?\))',
        block
    ):
        pad_num  = pad_block.group(1)
        local_x  = float(pad_block.group(2))
        local_y  = float(pad_block.group(3))

        # Rotate local coords by footprint rotation, then translate
        cos_r = math.cos(rot_rad)
        sin_r = math.sin(rot_rad)
        world_x = fp_x + local_x * cos_r - local_y * sin_r
        world_y = fp_y + local_x * sin_r + local_y * cos_r

        pads[pad_num] = {
            'x': round(world_x, 4),
            'y': round(world_y, 4),
        }

    results[ref] = pads

# ── Report ────────────────────────────────────────────────────────────────
if 'J1' not in results:
    print("ERROR: J1 not found in board file")
    sys.exit(1)
if 'J2' not in results:
    print("ERROR: J2 not found in board file")
    sys.exit(1)

print("\n=== LIVE J1 PAD COORDS (from .kicad_pcb) ===")
j1_sorted = sorted(results['J1'].keys(), key=lambda x: int(x) if x.isdigit() else 999)
for pin in j1_sorted[:8]:
    c = results['J1'][pin]
    print("  J1 Pin %s: X=%-10s  Y=%s mm" % (pin, c['x'], c['y']))

print("\n=== LIVE J2 PAD COORDS ===")
j2_sorted = sorted(results['J2'].keys(), key=lambda x: int(x) if x.isdigit() else 999)
print("  J2 total pads: %d" % len(j2_sorted))
for pin in j2_sorted[:8]:
    c = results['J2'][pin]
    print("  J2 Pad %s: X=%-10s  Y=%s mm" % (pin, c['x'], c['y']))

# ── Save ──────────────────────────────────────────────────────────────────
with open(OUTPUT_JSON, 'w') as f:
    json.dump(results, f, indent=2)
print("\nSaved full pad data: %s" % OUTPUT_JSON)
