import sys, json
sys.path.insert(0, r'C:\Users\Bibek\NeuroBoard')
sys.path.insert(0, r'C:\Users\Bibek\NeuroBoard\engines\routing\rust_router')
import grid_router

J1_P = (108.22, 49.00)
J1_N = (105.68, 49.00)
J2_P = (115.75, 80.725)
J2_N = (116.25, 80.725)
gap  = 0.15

path_p, path_n = grid_router.route_differential_pair(J1_P, J1_N, J2_P, J2_N, gap)

print('PATH_P:', path_p)
print('PATH_N:', path_n)

with open(r'C:\Users\Bibek\NeuroBoard\ai_core\route_plan.json', 'w') as f:
    json.dump({'path_p': path_p, 'path_n': path_n, 'width_mm': 0.15, 'layer': 'F.Cu'}, f, indent=2)
print('DONE')
