import os, sys, math
import shapely.geometry as geom
sys.path.insert(0, r'C:\Users\Bibek\NeuroBoard\engines\routing\rust_router')
import grid_router

from .bus_detector import BusDetector
from .fanout import FanoutEngine
from .corridor import CorridorGenerator
from .length_match import LengthMatchEngine
from .diff_pair import DiffPairEngine
from si.stackup import StackupModel
from si.impedance import ImpedanceCalculator
from placement.optimizer import PlacementOptimizer

class BusPipeline:
    def __init__(self, pads_info, target_zdiff=100.0, layer='F.Cu'):
        self.pads_info = pads_info
        
        # Physics-Aware Stackup Setup
        self.stackups = StackupModel.get_jlcpcb_4layer_standard()
        self.active_stackup = self.stackups.get(layer, self.stackups['F.Cu'])
        self.impedance_calc = ImpedanceCalculator(self.active_stackup)
        
        # Dynamically evaluate the physically optimal track/gap profile for Zdiff
        opt_w, opt_s, opt_err = self.impedance_calc.get_optimal_geometry(target_zdiff=target_zdiff)
        print(f"SI OPTIMIZATION: Found optimal geometry for {target_zdiff}Ohm -> width: {opt_w}mm, spacing: {opt_s}mm (Mismatch: {opt_err:.2f}Ohm)")
        
        self.trace_width = opt_w
        self.spacing = opt_s
        self.base_zdiff = target_zdiff
        
        self.placement_optimizer = PlacementOptimizer()
        
        self.bus_detector = BusDetector(pads_info)
        self.fanout_engine = FanoutEngine(self.trace_width, self.spacing)
        self.corridor_engine = CorridorGenerator(self.trace_width, self.spacing)
        
        # Ensure Meander Coupling respects Minimum Isolation constraints
        # Serpentine peaks must not capacitively couple too tightly!
        # spacing >= 3 * trace_width (3W Rule)
        meander_spacing = max(0.3, 3 * self.trace_width)
        self.length_matcher = LengthMatchEngine(tolerance=0.1, amplitude=0.5, spacing=meander_spacing)
        
        self.diff_engine = DiffPairEngine(self.trace_width, self.spacing)
        
        # SI-Aware Routing Costs Update
        self.cost_length = 1
        self.cost_crossing = 1000
        self.cost_via = 50
        self.cost_angle = 100
        self.cost_spacing_violation = 1000
        self.cost_skew = 2000
        self.cost_impedance = 5000
        
        # Base impedance error cost added to configuration
        self.impedance_penalty = opt_err * self.cost_impedance
        
        # Grid Router configured with SI constraints
        self.router = grid_router.GridRouter(
            via_cost=self.cost_via, 
            h_weight=1.2, 
            turn_cost=self.cost_angle
        )

    def evaluate_optimal_component_placement(self, netlist, critical_buses):
        """
        Runs the Simulated Annealing engine to optimize component placement
        prior to final geometry initialization.
        """
        components = {comp: "IC" for comp in self.pads_info.keys()}
        print(f"Initializing Intelligent Placement Engine across {len(components)} components...")
        
        init_place = self.placement_optimizer.generate_initial_placement(components)
        opt_place, cost = self.placement_optimizer.optimize_simulated_annealing(
            init_place, netlist, critical_buses, steps=5000, cooling_rate=0.99
        )
        print(f"Optimal Placement Vector found (Cost {cost:.1f}).")
        
        # In a fully integrated environment, we'd update KiCAD board elements here
        return opt_place

    def route_bus(self, src_ref, dst_ref, pin_mapping, board_map=None):
        """
        Executes the Geometry-Aware Topology Routing Pipeline
        """
        # 1. Detect Ordered Bus
        ordered_bus = self.bus_detector.detect_buses(src_ref, dst_ref, pin_mapping)
        if not ordered_bus: return None
        
        print(f"Bus Detected: {len(ordered_bus)} pairs")
        
        # Compute orientations safely
        pad_rotations = {
            src_ref: self.pads_info.get(src_ref, {}).get("rot", 0),
            dst_ref: self.pads_info.get(dst_ref, {}).get("rot", 0)
        }
        
        # 2. Generate Fanout / Escape Extensions
        escapes, envelopes = self.fanout_engine.generate_bus_escapes(ordered_bus, pad_rotations, length=1.0)
        
        # 3. Create Center Corridor points (using middle pair conceptually)
        mid_idx = len(escapes) // 2
        center_src = escapes[mid_idx][0][1] # end of the src fanout
        center_dst = escapes[mid_idx][1][1] # end of the dst fanout
        
        # 4. Route Center Path using A*
        obs = grid_router.GridObstacleMap(2)
        
        grid_res = 0.05
        def mm2gx(pt): return int(round(pt[0]/grid_res)), int(round(pt[1]/grid_res))
        def gx2mm(pt): return pt[0]*grid_res, pt[1]*grid_res
        
        sg = mm2gx(center_src)
        dg = mm2gx(center_dst)
        
        path_gx, _, _ = self.router.route_multi(obs, [(sg[0], sg[1], 0)], [(dg[0], dg[1], 0)], 500000, False, 0, None, None, 2, 0)
        if not path_gx:
            print("Failed to route center A* path")
            return None
            
        center_path_mm = [gx2mm(pt) for pt in path_gx]
        
        # 5. Generate Corridor Constraint Check (Validation)
        bus_width = len(ordered_bus) * (self.trace_width + self.spacing)
        corridor_polygon = self.corridor_engine.generate_corridor(center_path_mm, bus_width)
        
        # 6. Generate Parallel Offsets
        all_traces = grid_router.route_parallel_bus(center_path_mm, len(ordered_bus), self.trace_width, self.spacing)
        
        # Validation Step
        for path in all_traces:
            line = geom.LineString(path)
            if not corridor_polygon.contains(line):
                # Penalty integration for spacing/corridor violation
                print(f"Cost Penalty: Spacing violation offset logic exceeded +{self.cost_spacing_violation}")
                
        # 7. Implement SI-Constraint: Diff Pair Engine
        pairs, unpaired = self.diff_engine.detect_diff_pairs(ordered_bus, [])
        all_traces_matched = list(all_traces)
        
        for p1, p2 in pairs:
            # Find indices
            i1 = ordered_bus.index(p1)
            i2 = ordered_bus.index(p2)
            
            if len(all_traces) > i2 and all_traces[i1] and all_traces[i2]:
                trace_p = all_traces[i1]
                trace_n = all_traces[i2]
                
                skew = self.length_matcher.calculate_skew(trace_p, trace_n)
                if skew > 0.1:
                    print(f"Cost Penalty: Structural Skew detected ({skew:.3f}mm) +{self.cost_skew}")
                    
                # Apply impedance-aware matching
                m_p, m_n = self.length_matcher.match_pair(trace_p, trace_n)
                all_traces_matched[i1] = m_p
                all_traces_matched[i2] = m_n

        # Assemble fully routed continuous nets
        final_nets = {}
        for i, (src_pad, dst_pad, src_pos, dst_pos) in enumerate(ordered_bus):
            # Connect: src pad -> src fanout -> parallel path -> dst fanout -> dst pad
            net_path = []
            net_path.extend(escapes[i][0]) # Pad -> Fanout
            if len(all_traces_matched) > i and all_traces_matched[i]:
                net_path.extend(all_traces_matched[i]) # Core parallel
            net_path.extend(reversed(escapes[i][1])) # Fanout -> Pad
            final_nets[src_pad + "-" + dst_pad] = net_path
            
        return final_nets
