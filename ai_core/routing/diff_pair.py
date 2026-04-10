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
        
        # Build mapping of net names to pad geometry coordinates
        pad_map = {}
        for idx, pad in enumerate(ordered_bus):
            # If names exist use them, else use index based fallback
            name = pin_mapping_names[idx] if idx < len(pin_mapping_names) else f"NET_{idx}"
            pad_map[name] = pad

        # Step 1: Detect specific differential pair name patterns
        import re
        diff_pattern = re.compile(r"^(.*?)([-_+PN])([_]?)(.*)$", re.IGNORECASE)
        
        paired_names = set()
        
        # Look for explicit suffixes +/-, P/N
        for name in pad_map.keys():
            if name in paired_names: continue
            
            if name.endswith('+') or name.endswith('P'):
                base = name[:-1]
                target_n = base + ('-' if name.endswith('+') else 'N')
                if target_n in pad_map and target_n not in paired_names:
                    pairs.append((pad_map[name], pad_map[target_n]))
                    paired_names.update([name, target_n])
                    continue
            
            # Explicit D+/D- matching or TX+/TX- via fallback (e.g., USB_D+, USB_D-)
            if "D+" in name:
                target_n = name.replace("D+", "D-")
                if target_n in pad_map and target_n not in paired_names:
                    pairs.append((pad_map[name], pad_map[target_n]))
                    paired_names.update([name, target_n])
                    continue

        # Step 2: Fallback to proximity coupling for any leftovers (Legacy behaviour handling)
        remaining = [p for n, p in pad_map.items() if n not in paired_names]
        i = 0
        while i < len(remaining) - 1:
            pairs.append((remaining[i], remaining[i+1]))
            i += 2
            
        if len(remaining) % 2 != 0:
            unpaired.append(remaining[-1])
            
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
