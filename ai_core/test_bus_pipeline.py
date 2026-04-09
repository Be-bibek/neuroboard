import sys, json

sys.path.insert(0, r'C:\Users\Bibek\NeuroBoard\ai_core')
from routing.bus_pipeline import BusPipeline

with open(r'C:\Users\Bibek\NeuroBoard\ai_core\live_pads_val.json', 'r') as f:
    pads_info = json.load(f)
    
src_ref = "FPC-16P-0.5mm"
dst_ref = "CONN-SMD_APCI0107-P001A"

mapping = {
    "2": "75",
    "3": "73",
    "5": "69",
    "6": "67"
}

pipeline = BusPipeline(pads_info, target_zdiff=100.0, layer='F.Cu')
routes = pipeline.route_bus(src_ref, dst_ref, mapping)

if routes:
    print(f"Successfully generated PHYSICS-AWARE TOPOLOGY ROUTING!")
    for net, path in routes.items():
        print(f" Net {net} routed with {len(path)} geometric segments.")
else:
    print("Geometry pipeline failed.")
