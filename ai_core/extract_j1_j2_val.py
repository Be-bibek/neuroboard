import sys, math, re

BOARD_PATH = r"C:\Users\Bibek\Documents\pi-hat\pi-hat.kicad_pcb"

with open(BOARD_PATH, "r", encoding="utf-8") as f:
    text = f.read()

pads_info = {}

for fp_match in re.finditer(r'\(footprint\s+"([^"]+)"(.*?)\n\s*\)(?=\n\s*\((?:footprint|segment|via|track|zone|$))', text, re.DOTALL):
    fp_name = fp_match.group(1)
    fp_content = fp_match.group(2)
    
    val_match = re.search(r'\(property\s+"Value"\s+"([^"]+)"', fp_content)
    if not val_match: continue
    val = val_match.group(1)
    
    # We want FPC-16P-0.5mm and CONN-SMD_APCI0107
    if "FPC-16" not in val and "APCI0107" not in fp_name and "C841661" not in val and "M.2" not in val:
        continue
    
    # get body pos
    at_m = re.search(r'\(at\s+([\-\d.]+)\s+([\-\d.]+)(?:\s+([\-\d.]+))?\)', fp_content)
    if not at_m: continue
    fp_x, fp_y = float(at_m.group(1)), float(at_m.group(2))
    fp_rot = float(at_m.group(3)) if at_m.group(3) else 0.0
    rot_rad = math.radians(fp_rot)
    cos_r, sin_r = math.cos(rot_rad), math.sin(rot_rad)
    
    pads_info[val] = {'pos': (fp_x, fp_y), 'rot': fp_rot, 'pads': {}}
    
    # find pads
    for p_m in re.finditer(r'\(pad\s+"?([^"\s]+)"?\s+smd\s+rect\s+\(at\s+([\-\d.]+)\s+([\-\d.]+)', fp_content):
        pnum = p_m.group(1)
        lx, ly = float(p_m.group(2)), float(p_m.group(3))
        
        wx = fp_x + lx * cos_r - ly * sin_r
        wy = fp_y + lx * sin_r + ly * cos_r
        pads_info[val]['pads'][pnum] = (round(wx, 4), round(wy, 4))
        
print("Extracted Data:")
for val, data in pads_info.items():
    print(f"--- {val} at {data['pos']} rot {data['rot']} ---")
    keys = sorted(data['pads'].keys(), key=lambda x: int(x) if x.isdigit() else 999)
    for k in keys[:5]:
        print(f"Pad {k}: {data['pads'][k]}")

import json
with open(r'C:\Users\Bibek\NeuroBoard\ai_core\live_pads_val.json', 'w') as f:
    json.dump(pads_info, f, indent=2)

