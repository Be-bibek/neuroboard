import sys
sys.path.insert(0, r'C:\Users\Bibek\NeuroBoard\engines\routing\rust_router')
import grid_router

with open('api.txt', 'w') as f:
    f.write(grid_router.GridObstacleMap.__doc__ or 'No doc')
    f.write('\n\n')
    f.write(grid_router.GridRouter.__doc__ or 'No doc')
