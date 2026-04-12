import logging

log = logging.getLogger("SystemLogger")

class NetlistManager:
    """
    Parses a generated KiCad netlist (.net file) and provides programmatic
    access to electrical logic, categorizing high-speed buses and power nets.
    Must map against the active IPC Client for physical queries.
    """
    def __init__(self, netlist_path: str = "pi_hat.net"):
        self.netlist_path = netlist_path
        self.nets = {}          # Net name -> list of interconnected nodes (ref, pin)
        self.diff_pairs = []    # List of tuples (positive_net, negative_net)
        self.power_nets = []    # List of power delivery net names
        
        self.parse_netlist()

    def parse_netlist(self):
        """
        Parses the raw SKiDL .net output format (S-expression).
        Extracts nets and categorized semantic groups.
        """
        import re
        try:
            with open(self.netlist_path, 'r') as f:
                content = f.read()
        except FileNotFoundError:
            log.warning(f"Netlist {self.netlist_path} not found. Ensure hat_generator.py has been run.")
            return

        # Simple S-expression heuristic parser for nets
        # Looks for: (net (code 1) (name "+3.3V") ... (node (ref "C2") ...))
        net_blocks = re.findall(r'\(net\s+\(code\s+[^)]+\)\s+\(name\s+"([^"]+)"\)(.*?)\)', content, re.DOTALL)
        
        for name, nodes_str in net_blocks:
            nodes = re.findall(r'\(node\s+\(ref\s+"([^"]+)"\)\s+\(pin\s+"([^"]+)"\)', nodes_str)
            self.nets[name] = nodes
            
            # Classification
            if "+5V" in name or "+3.3V" in name or "GND" in name:
                self.power_nets.append(name)

        # Detect Diff pairs
        # Typically suffixes are _P, _N or +, -
        candidates = list(self.nets.keys())
        for c in candidates:
            if c.endswith("_P"):
                neg = c[:-2] + "_N"
                if neg in self.nets:
                    self.diff_pairs.append((c, neg))

        log.info(f"Loaded {len(self.nets)} nets. Detected {len(self.diff_pairs)} differential pairs and {len(self.power_nets)} power nets.")

    def get_routing_pairs(self):
        """ Returns high-speed pairs required to be routed concurrently. """
        return self.diff_pairs

    def map_pads_to_ipc(self, ipc_client):
        """
        Passes the extracted semantic intention into the active IPC layer,
        asking KiCad to return exact (x,y) pad coordinates for the specified nodes.
        """
        pad_coords = {}
        for net_name, nodes in self.nets.items():
            pad_coords[net_name] = ipc_client.get_pad_coordinates_for_nodes(nodes)
            
        return pad_coords
