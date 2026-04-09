import math

class PlacementCostModel:
    def __init__(self, board_width=150, board_height=150):
        self.board_width = board_width
        self.board_height = board_height

    def evaluate_cost(self, placement_dict, netlist, critical_buses):
        """
        Calculates a global placement cost scalar. Lower is better.
        placement_dict: { "J1": (x, y, rot) ... }
        netlist: [("J1", "J2", weight)]
        critical_buses: {"bus_name": [("J1", "J2")]}
        """
        total_cost = 0.0
        
        # 1. Net Connectivity Distance (HPWL - Half-Perimeter Wirelength approximation)
        for src, dst, weight in netlist:
            if src in placement_dict and dst in placement_dict:
                x1, y1, _ = placement_dict[src]
                x2, y2, _ = placement_dict[dst]
                
                # Manhattan distance weighted by net criticality
                dist = abs(x2 - x1) + abs(y2 - y1)
                total_cost += dist * weight
                
        # 2. Bus Alignment & Diff Pair Alignment
        for bus_name, pairs in critical_buses.items():
            for src, dst in pairs:
                if src in placement_dict and dst in placement_dict:
                    x1, y1, r1 = placement_dict[src]
                    x2, y2, r2 = placement_dict[dst]
                    
                    # Ideal bus is usually physically aligned straight on primary axes X or Y
                    dx = abs(x2 - x1)
                    dy = abs(y2 - y1)
                    
                    # If it's a high-speed diff pair, we heavily penalize diagonal orientation 
                    # and heavily reward them facing each other
                    alignment_penalty = min(dx, dy) * 10.0 # Force one axis to be very small
                    
                    # Rotation alignment (connectors facing each other ideally)
                    rot_penalty = 0
                    if (r1 - r2) % 180 != 0:
                        rot_penalty = 500.0 # High penalty for non-orthogonal mismatches
                        
                    total_cost += (alignment_penalty + rot_penalty)
                    
        # 3. Component Congestion & Overlap (Repulsion)
        comps = list(placement_dict.items())
        for i in range(len(comps)):
            for j in range(i+1, len(comps)):
                c1_x, c1_y, _ = comps[i][1]
                c2_x, c2_y, _ = comps[j][1]
                
                dist = math.hypot(c2_x - c1_x, c2_y - c1_y)
                if dist < 15.0:  # Minimum component clearance (bounding box approx)
                    total_cost += 1000.0 / (dist + 0.1)  # Exponential congestion penalty
                    
        return total_cost
