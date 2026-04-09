import sys, json
import urllib.request, time

sys.path.insert(0, r'C:\Users\Bibek\NeuroBoard\engines\routing\rust_router')
import grid_router

with open(r'C:\Users\Bibek\NeuroBoard\ai_core\live_pads_val.json', 'r') as f:
    d = json.load(f)

fpc = d['FPC-16P-0.5mm']['pads']
m2 = d['CONN-SMD_APCI0107-P001A']['pads']

# Convert lists to tuples
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

print(f"Routing FPC_TX to M.2_RX: {tx_p_src} -> {rx_p_dst}")
path_tx_p, path_tx_n = grid_router.route_differential_pair(
    tx_p_src, tx_n_src, rx_p_dst, rx_n_dst, width_gap_mm
)

print(f"Routing M.2_TX to FPC_RX: {tx_p_src2} -> {rx_p_dst2}")
path_rx_p, path_rx_n = grid_router.route_differential_pair(
    tx_p_src2, tx_n_src2, rx_p_dst2, rx_n_dst2, width_gap_mm
)

def push_ipc(start, end, width, net):
    req = urllib.request.Request(
        'http://localhost:3000/api/tool', 
        data=json.dumps({
            'tool': 'route_trace', 
            'params': {
                'start': {'x': start[0], 'y': start[1], 'unit': 'mm'},
                'end': {'x': end[0], 'y': end[1], 'unit': 'mm'},
                'width': width,
                'layer': 'F.Cu',
                'net': net
            }
        }).encode('utf-8'),
        headers={'Content-Type': 'application/json'}
    )
    urllib.request.urlopen(req)

for net, path in [('PCIe_TX_P', path_tx_p), ('PCIe_TX_N', path_tx_n), ('PCIe_RX_P', path_rx_p), ('PCIe_RX_N', path_rx_n)]:
    if len(path) < 2: continue
    for i in range(len(path)-1):
        push_ipc(path[i], path[i+1], width_gap_mm, net)
        # Small delay to avold overloading ipc
        time.sleep(0.01)

print("Pushed all traces via neuro_router IPC.")

req = urllib.request.Request(
    'http://localhost:3000/api/tool', 
    data=json.dumps({'tool': 'refill_zones', 'params': {}}).encode('utf-8'),
    headers={'Content-Type': 'application/json'}
)
urllib.request.urlopen(req)

print("Zone refill triggered.")
