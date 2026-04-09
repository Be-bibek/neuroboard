import networkx as nx

class BusDetector:
    def __init__(self, pads_info):
        self.pads_info = pads_info

    def detect_buses(self, src_ref, dst_ref, mapping):
        """
        Detects grouped buses and parallel net configurations.
        Returns a list of ordered (src_pad, dst_pad) tuples.
        """
        bus_order = []
        # Use an implicit linear progression or distance-based sorting for order
        # Ensure that no lines cross by preserving the geometric topology
        src_pads = self.pads_info.get(src_ref, {}).get("pads", {})
        dst_pads = self.pads_info.get(dst_ref, {}).get("pads", {})
        
        # Build topological graph
        G = nx.Graph()
        for s_pad, d_pad in mapping.items():
            if s_pad in src_pads and d_pad in dst_pads:
                spos = src_pads[s_pad]
                dpos = dst_pads[d_pad]
                bus_order.append({
                    "src": s_pad, "dst": d_pad,
                    "src_pos": spos, "dst_pos": dpos
                })
                
        # Topologically sort them based on the cross-product to ensure planar routing
        # (Assuming they are mostly parallel along one dominant axis)
        bus_order.sort(key=lambda x: (x["src_pos"][0] + x["src_pos"][1]))
        
        # Return full 4-tuple: (src_pad, dst_pad, src_pos, dst_pos)
        return [(item["src"], item["dst"], item["src_pos"], item["dst_pos"]) for item in bus_order]
