import os, sys, yaml, json, random
from system.logger import log
from system.errors import *
from routing.bus_pipeline import BusPipeline
from placement.optimizer import PlacementOptimizer
from validation.drc import GlobalDRC
from validation.si_check import SignalIntegrityValidator

class CompilerOrchestrator:
    def __init__(self, board_path="pi-hat.kicad_pcb", config_path="../config/design_rules.yaml"):
        # Determinism Config (Phase 2)
        random.seed(42)
        
        self.board_path = board_path
        self.config = self.load_config(config_path)
        self.drc = GlobalDRC(self.config['routing']['trace_width_min'], self.config['routing']['spacing_min'])
        self.si_validator = SignalIntegrityValidator()
        self.cache = {} # Phase 7: Caching

    def load_config(self, config_path):
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)

    def load_pads(self):
        # Retrieve mocked or fetched layout padding coordinates
        if 'pads' in self.cache: return self.cache['pads']
        with open(r'C:\Users\Bibek\NeuroBoard\ai_core\live_pads_val.json', 'r') as f:
            pads = json.load(f)
        self.cache['pads'] = pads
        return pads

    def run_full_pipeline(self, src_ref, dst_ref, pin_mapping):
        log.info("--- NEUROBOARD COMPLETION RUN ---")
        pads_info = self.load_pads()
        
        # 1-6. Placed onto a BusPipeline
        pipeline = BusPipeline(pads_info, target_zdiff=self.config['routing']['impedance_target_diff'])
        
        # Phase 3 & 4: Placement Engine Integration 
        # Mock Netlist linking
        netlist = [(src_ref, dst_ref, 10.0)]
        critical_buses = {"HIGH_SPEED": [(src_ref, dst_ref)]}
        opt_placement = pipeline.evaluate_optimal_component_placement(netlist, critical_buses)
        
        # Phase 8: Execution
        log.info("Executing Differential Spine Router...")
        try:
            final_nets = pipeline.route_bus(src_ref, dst_ref, pin_mapping)
        except Exception as e:
            raise RoutingError(f"Engine failed to resolve topology: {e}")

        # Phase 9: Verification
        self.drc.check_routing_violations(final_nets)
        
        # Phase 10: SI
        paths = list(final_nets.values())
        if len(paths) >= 2:
            self.si_validator.validate_diff_pair("TX+", paths[0], "TX-", paths[1])

        # Output payload
        log.info("Writing payload segments to KiCAD buffer...")
        self.commit_to_kicad(final_nets)
        
        log.info("BOARD COMPILED SUCCESSFULLY.")
        
    def commit_to_kicad(self, final_nets):
        # We append direct trace outputs exactly like previous live_commit steps.
        segments_str = ""
        for net_name, path_mm in final_nets.items():
            for i in range(len(path_mm)-1):
                x1, y1 = path_mm[i]
                x2, y2 = path_mm[i+1]
                segments_str += f'\n  (segment (start {x1:.4f} {y1:.4f}) (end {x2:.4f} {y2:.4f}) (width 0.15) (layer "F.Cu") (net 0))'
                
        parent_dir = os.path.dirname(os.path.abspath(__file__))
        target_path = os.path.join(parent_dir, "../../Documents/pi-hat/", self.board_path)
        
        # Fallback for direct testing in case paths mismatch
        target_path = r"C:\Users\Bibek\Documents\pi-hat\pi-hat.kicad_pcb"
        
        with open(target_path, 'r', encoding='utf-8') as f:
            board_str = f.read()

        board_str = board_str.rstrip()
        if board_str.endswith(')'):
            board_str = board_str[:-1].rstrip()

        board_str = board_str + segments_str + "\n)\n"

        with open(target_path, 'w', encoding='utf-8') as f:
            f.write(board_str)
