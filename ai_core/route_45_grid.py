import sys, json, math

sys.path.insert(0, r'C:\Users\Bibek\NeuroBoard\engines\routing\rust_router')
import grid_router

BOARD_PATH = r"C:\Users\Bibek\Documents\pi-hat\pi-hat.kicad_pcb"

with open(r'C:\Users\Bibek\NeuroBoard\ai_core\live_pads_val.json', 'r') as f:
    d = json.load(f)

fpc = d['FPC-16P-0.5mm']['pads']
m2 = d['CONN-SMD_APCI0107-P001A']['pads']

GRID_RES = 0.05 # fine resolution for 45 deg angles
GAP_MM = 0.15

def get_pads(pad_dict, *pnums):
    for p in pnums:
        if p in pad_dict:
            return float(pad_dict[p][0]), float(pad_dict[p][1])
    return None

tx_p_src = get_pads(fpc, '2')
tx_n_src = get_pads(fpc, '3')
rx_p_dst = get_pads(m2, '75')
rx_n_dst = get_pads(m2, '73')

# we also route M.2 TX to FPC RX
tx_p_src2 = get_pads(m2, '69')
tx_n_src2 = get_pads(m2, '67')
rx_p_dst2 = get_pads(fpc, '5')
rx_n_dst2 = get_pads(fpc, '6')

class SimpleDiffRouter:
    def __init__(self, res=0.05):
        self.res = res
        # High trace crossing penalty via 1000 turn cost and track margin
        self.router = grid_router.GridRouter(via_cost=50, h_weight=1.5, turn_cost=30)
        self.obstacles = grid_router.GridObstacleMap(2)
        
    def mm_to_gx(self, x, y):
        return int(round(x / self.res)), int(round(y / self.res))

    def gx_to_mm(self, gx, gy):
        return gx * self.res, gy * self.res

    def block_path(self, path, clearance_mm):
        margin = int(math.ceil(clearance_mm / self.res))
        for (gx, gy, l) in path:
            for dx in range(-margin, margin+1):
                for dy in range(-margin, margin+1):
                   if dx*dx + dy*dy <= margin*margin + 1: # circle roughly
                       self.obstacles.add_blocked_cell(gx + dx, gy + dy, l)
                       
    def route_single(self, src_mm, dst_mm):
        sg = self.mm_to_gx(*src_mm)
        dg = self.mm_to_gx(*dst_mm)
        
        path, _, _ = self.router.route_multi(
            self.obstacles, 
            [(sg[0], sg[1], 0)], 
            [(dg[0], dg[1], 0)], 
            100000, 
            False, 
            0,
            None,
            None,
            2,
            0
        )
        if not path:
            return []
        
        # Simplify path nicely
        simple_path_mm = []
        for p in path:
            simple_path_mm.append(self.gx_to_mm(p[0], p[1]))
        return path, simple_path_mm

# Execute sequential routing
router = SimpleDiffRouter(GRID_RES)

# Add generic bounding block between the two connectors if needed 
# But A* with straight lines is fine

# Route Pair 1
p1_path, tx_p_mm = router.route_single(tx_p_src, rx_p_dst)
if p1_path:
    router.block_path(p1_path, GAP_MM)
p2_path, tx_n_mm = router.route_single(tx_n_src, rx_n_dst)
if p2_path:
    router.block_path(p2_path, GAP_MM + 0.15) # wide block for other pairs

# Route Pair 2
p3_path, rx_p_mm = router.route_single(tx_p_src2, rx_p_dst2)
if p3_path:
    router.block_path(p3_path, GAP_MM)
p4_path, rx_n_mm = router.route_single(tx_n_src2, rx_n_dst2)

print("A* routing completed.")

# Append cleanly to board
segments_str = ""
for net, path_mm in [('PCIe_TX_P', tx_p_mm), ('PCIe_TX_N', tx_n_mm), ('PCIe_RX_P', rx_p_mm), ('PCIe_RX_N', rx_n_mm)]:
    if len(path_mm) < 2: 
        print(f"Failed to route {net}")
        continue
    for i in range(len(path_mm)-1):
        x1, y1 = path_mm[i]
        x2, y2 = path_mm[i+1]
        segments_str += f'\n  (segment (start {x1:.4f} {y1:.4f}) (end {x2:.4f} {y2:.4f}) (width 0.15) (layer "F.Cu") (net 0))'

with open(BOARD_PATH, 'r', encoding='utf-8') as f:
    board_str = f.read()

board_str = board_str.rstrip()
if board_str.endswith(')'):
    board_str = board_str[:-1].rstrip()

board_str = board_str + segments_str + "\n)\n"

with open(BOARD_PATH, 'w', encoding='utf-8') as f:
    f.write(board_str)

print("Successfully injected A* 45-degree snapped routes into pi-hat.kicad_pcb.")
