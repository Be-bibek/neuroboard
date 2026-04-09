import sys
sys.path.insert(0, r'C:\Users\Bibek\NeuroBoard\ai_core')
from placement.optimizer import PlacementOptimizer

# Definition of the board state
components = {
    "J1_FPC": "CONNECTOR",
    "J2_M2": "CONNECTOR",
    "U1_MCU": "IC",
    "U2_PMIC": "IC"
}

# Critical high-speed netlist (e.g. PCIe traces)
netlist = [
    ("J1_FPC", "J2_M2", 10.0), # PCIe diff pairs (High weight)
    ("U1_MCU", "J1_FPC", 2.0),
    ("U2_PMIC", "J2_M2", 5.0)  # Power nets (Moderate weight)
]

# Diff pair / Bus groupings mapped for spatial alignment enforcement
critical_buses = {
    "PCIe_Lanes": [
        ("J1_FPC", "J2_M2")
    ]
}

print("Initialize Placement Optimizer: Board 100x100mm")
optimizer = PlacementOptimizer(board_width=100, board_height=100)

print("\n--- Initial Placement ---")
initial_place = optimizer.generate_initial_placement(components)
for comp, (x, y, rot) in initial_place.items():
    print(f" {comp}: X={x:.2f}, Y={y:.2f}, Rot={rot:.1f} deg")

print("\nRunning Simulated Annealing Optimization Engine...")
optimal_place, final_cost = optimizer.optimize_simulated_annealing(
    initial_place, 
    netlist, 
    critical_buses, 
    steps=10000, 
    cooling_rate=0.995
)

print(f"\n--- Optimal Placement (Cost: {final_cost:.2f}) ---")
for comp, (x, y, rot) in optimal_place.items():
    print(f" {comp}: X={x:.2f}, Y={y:.2f}, Rot={rot:.1f} deg")
    
# Specifically show how J1 and J2 aligned
j1_coord = optimal_place["J1_FPC"]
j2_coord = optimal_place["J2_M2"]
dx = abs(j1_coord[0] - j2_coord[0])
dy = abs(j1_coord[1] - j2_coord[1])
print(f"\nJ1/J2 Axis Alignment Test: dx={dx:.2f}mm, dy={dy:.2f}mm (One should be close to 0!)")
print(f"J1/J2 Rotation Check: rot1={j1_coord[2]} deg, rot2={j2_coord[2]} deg")
