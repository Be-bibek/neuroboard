import random
import math
from .cost import PlacementCostModel

class PlacementOptimizer:
    def __init__(self, board_width=150, board_height=150):
        self.board_width = board_width
        self.board_height = board_height
        self.cost_model = PlacementCostModel(board_width, board_height)

    def generate_initial_placement(self, components, edges=True):
        """
        Creates an initial heuristic placement.
        Connectors placed at edges, ICs placed centrally.
        """
        placement = {}
        for comp, comp_type in components.items():
            if comp_type == 'CONNECTOR' and edges:
                # Place near an edge randomly
                if random.random() > 0.5:
                    x = random.choice([10, self.board_width - 10])
                    y = random.uniform(20, self.board_height - 20)
                    rot = 90.0 if x == 10 else -90.0
                else:
                    x = random.uniform(20, self.board_width - 20)
                    y = random.choice([10, self.board_height - 10])
                    rot = 0.0 if y == 10 else 180.0
            else:
                # IC or generic component, place centrally
                x = random.uniform(self.board_width/4, 3*self.board_width/4)
                y = random.uniform(self.board_height/4, 3*self.board_height/4)
                rot = random.choice([0.0, 90.0, -90.0, 180.0])
                
            placement[comp] = (x, y, rot)
        return placement

    def optimize_simulated_annealing(self, placement, netlist, critical_buses, steps=5000, initial_temp=1000.0, cooling_rate=0.99):
        """
        Simulated Annealing to minimize component alignment and routing length cost.
        """
        current_placement = dict(placement)
        current_cost = self.cost_model.evaluate_cost(current_placement, netlist, critical_buses)
        
        best_placement = dict(current_placement)
        best_cost = current_cost
        
        temp = initial_temp
        
        for step in range(steps):
            # Generate neighbor state
            neighbor = dict(current_placement)
            comp = random.choice(list(neighbor.keys()))
            x, y, rot = neighbor[comp]
            
            # Perturb
            move_type = random.randint(0, 2)
            if move_type == 0:
                # Small XY shift
                x += random.uniform(-5.0, 5.0)
                y += random.uniform(-5.0, 5.0)
            elif move_type == 1:
                # Large XY jump
                x = random.uniform(10, self.board_width - 10)
                y = random.uniform(10, self.board_height - 10)
            else:
                # Rotation change
                rot = (rot + 90.0) % 360.0
                
            # Restrict bounds
            x = max(5, min(self.board_width - 5, x))
            y = max(5, min(self.board_height - 5, y))
            
            neighbor[comp] = (x, y, rot)
            
            # Evaluate
            new_cost = self.cost_model.evaluate_cost(neighbor, netlist, critical_buses)
            
            # Accept or Reject
            if new_cost < current_cost:
                current_placement = neighbor
                current_cost = new_cost
                if new_cost < best_cost:
                    best_placement = dict(neighbor)
                    best_cost = new_cost
            else:
                # Acceptance probability
                try:
                    prob = math.exp((current_cost - new_cost) / temp)
                except OverflowError:
                    prob = 0.0
                    
                if random.random() < prob:
                    current_placement = neighbor
                    current_cost = new_cost
                    
            temp *= cooling_rate
                
        return best_placement, best_cost

    def snap_connectors_to_axis(self,
                                placement: dict,
                                connector_refs: list) -> dict:
        """
        Post-SA refinement: snap connector pairs to share either the same X
        or the same Y coordinate, whichever reduces the misalignment more.
        This minimises the meander the router needs to introduce.
        """
        snapped = dict(placement)
        for i in range(len(connector_refs)):
            for j in range(i + 1, len(connector_refs)):
                c1, c2 = connector_refs[i], connector_refs[j]
                if c1 not in snapped or c2 not in snapped:
                    continue
                x1, y1, r1 = snapped[c1]
                x2, y2, r2 = snapped[c2]

                dx, dy = abs(x2 - x1), abs(y2 - y1)
                # Snap along whichever axis already has less misalignment
                if dx <= dy:
                    # Align on X axis (same column) — snap c2's X to c1's X
                    snapped[c2] = (x1, y2, r2)
                else:
                    # Align on Y axis (same row) — snap c2's Y to c1's Y
                    snapped[c2] = (x2, y1, r2)

        return snapped

    def optimize_with_snap(self,
                           components: dict,
                           netlist: list,
                           critical_buses: dict,
                           connector_refs: list,
                           steps: int = 5000) -> tuple:
        """
        Full optimisation flow: SA → axis snap → final cost evaluation.
        Returns (snapped_placement, final_cost).
        """
        init_place = self.generate_initial_placement(components)
        sa_place, sa_cost = self.optimize_simulated_annealing(
            init_place, netlist, critical_buses, steps=steps
        )
        snapped = self.snap_connectors_to_axis(sa_place, connector_refs)
        final_cost = self.cost_model.evaluate_cost(snapped, netlist, critical_buses)
        return snapped, final_cost
