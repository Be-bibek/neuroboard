import sys
sys.path.insert(0, r'C:\Users\Bibek\NeuroBoard\engines\routing\rust_router')
import grid_router
import json

with open(r'C:\Users\Bibek\NeuroBoard\ai_core\live_pads_fixed.json', 'r') as f:
    results = json.load(f)

print("J1 pads:", len(results.get('J1', {})))
print("J2 pads:", len(results.get('J2', {})))

def safe_pad(ref, pnum, backup):
    pads = results.get(ref, {})
    return pads.get(pnum) or pads.get(backup) or (list(pads.values())[0] if pads else None)

j1_tx_p = safe_pad('J1', '2', '2')
j1_tx_n = safe_pad('J1', '3', '3')
j1_rx_p = safe_pad('J1', '5', '5')
j1_rx_n = safe_pad('J1', '6', '6')

j2_rx_p = safe_pad('J2', '75', '11')
j2_rx_n = safe_pad('J2', '73', '13')
j2_tx_p = safe_pad('J2', '69', '17')
j2_tx_n = safe_pad('J2', '67', '19')

print(f"J1 TX_P: {j1_tx_p}")
print(f"J2 RX_P: {j2_rx_p}")

width_gap_mm = 0.15

if j1_tx_p and j2_rx_p:
    path_tx_p, path_tx_n = grid_router.route_differential_pair(
        (j1_tx_p['x'], j1_tx_p['y']), 
        (j1_tx_n['x'], j1_tx_n['y']), 
        (j2_rx_p['x'], j2_rx_p['y']), 
        (j2_rx_n['x'], j2_rx_n['y']), 
        width_gap_mm
    )
    path_rx_p, path_rx_n = grid_router.route_differential_pair(
        (j2_tx_p['x'], j2_tx_p['y']), 
        (j2_tx_n['x'], j2_tx_n['y']), 
        (j1_rx_p['x'], j1_rx_p['y']), 
        (j1_rx_n['x'], j1_rx_n['y']), 
        width_gap_mm
    )
    with open(r'C:\Users\Bibek\NeuroBoard\ai_core\final_routes.json', 'w') as f:
        json.dump({
            'tx_p': path_tx_p, 'tx_n': path_tx_n,
            'rx_p': path_rx_p, 'rx_n': path_rx_n
        }, f)
    print("SUCCESS")
else:
    print("Missing pads")
