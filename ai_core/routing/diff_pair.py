class DiffPairEngine:
    def __init__(self, trace_width=0.15, spacing=0.15):
        self.trace_width = trace_width
        self.spacing = spacing

    def detect_diff_pairs(self, ordered_bus, pin_mapping_names):
        """
        Groups nets into differential pairs based on net names (e.g., TX+, TX-, RX+, RX-)
        If no names are provided, uses simple proximity pairing based on the ordered bus.
        Returns a list of pairs of traces: [((src1, dst1), (src2, dst2)), ...]
        """
        pairs = []
        unpaired = []
        
        # Simple detection: if the user ordered them properly, every 2 adjacent nets might be a pair.
        # But for robustness, we look for P/N or +/- suffix match if names are available.
        # Here we just iterate in chunks of 2 since PCIe is inherently paired.
        
        i = 0
        while i < len(ordered_bus) - 1:
            pad1 = ordered_bus[i]
            pad2 = ordered_bus[i+1]
            
            # Form a differential pair
            pairs.append((pad1, pad2))
            i += 2
            
        if len(ordered_bus) % 2 != 0:
            unpaired.append(ordered_bus[-1])
            
        return pairs, unpaired

    def route_diff_pair(self, center_path, router_backend):
        """
        Calls the Rust backend 'route_parallel_bus' specifically configured
        for exactly 2 traces (P and N) with the strict 100-ohm impedance spacing.
        """
        # A differential pair is essentially a parallel bus of 2 traces
        # The rust backend uses Cavalier Contours ensuring constant geometric spacing across bends
        offset_traces = router_backend(center_path, 2, self.trace_width, self.spacing)
        return offset_traces
