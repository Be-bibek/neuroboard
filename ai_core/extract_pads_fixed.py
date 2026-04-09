import re, math, json, os

BOARD_PATH = r'C:\Users\Bibek\Documents\pi-hat\pi-hat.kicad_pcb'
OUT_JSON = r'C:\Users\Bibek\NeuroBoard\ai_core\live_pads_fixed.json'
ANCHORS_JSON = r'C:\Users\Bibek\NeuroBoard\ai_core\routing_anchors.json'

with open(BOARD_PATH, 'r', encoding='utf-8') as f:
    raw = f.read()

fp_blocks = re.split(r'\n\s*\(footprint ', raw)
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
    # regex matches both (pad "1" ...) and (pad 1 ...)
    for pad_m in re.finditer(
        r'\(pad\s+(?:"([^"]+)"|([^\s"]+))\s+[^\)]*(?:\(at\s+([\-\d.]+)\s+([\-\d.]+)(?:\s+[\-\d.]+)?\))',
        block
    ):
        pnum = pad_m.group(1) if pad_m.group(1) is not None else pad_m.group(2)
        lx, ly = float(pad_m.group(3)), float(pad_m.group(4))
        wx = fp_x + lx * cos_r - ly * sin_r
        wy = fp_y + lx * sin_r + ly * cos_r
        pads[pnum] = {'x': round(wx, 4), 'y': round(wy, 4)}

    results[ref] = pads
    print("%s at (%.3f, %.3f) rot=%.0f° — %d pads" % (ref, fp_x, fp_y, fp_rot, len(pads)))

with open(OUT_JSON, 'w') as f:
    json.dump(results, f, indent=2)
print("Live pads saved.")

def get_pad(ref, pad_num_str):
    if ref not in results:
        return None
    return results[ref].get(pad_num_str)

# Map TX/RX pins
routing = {
    'J1_TX_P': get_pad('J1', '2'),
    'J1_TX_N': get_pad('J1', '3'),
    'J1_RX_P': get_pad('J1', '5'),
    'J1_RX_N': get_pad('J1', '6'),
    # For M.2, mapping assumes standard pad numbers
    'J2_RX_P': get_pad('J2', '75'),  # Just picking sample pads for M.2 if not found
    'J2_RX_N': get_pad('J2', '73'),
    'J2_TX_P': get_pad('J2', '69'),
    'J2_TX_N': get_pad('J2', '67'),
}

with open(ANCHORS_JSON, 'w') as f:
    json.dump(routing, f, indent=2)
print("Anchors saved.")
for k, v in routing.items():
    print(f"  {k}: {v}")
