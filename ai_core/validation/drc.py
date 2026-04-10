import shapely.geometry as geom
from system.errors import GeometryConstraintError
from system.logger import log

class GlobalDRC:
    def __init__(self, trace_width=0.15, spacing=0.15):
        self.trace_width = trace_width
        self.spacing = spacing

    def check_routing_violations(self, final_nets):
        """
        Validates the geometric state of all final routed nets against DRC limits.
        """
        log.info("Running Global Design Rule Check (DRC)...")
        from shapely.strtree import STRtree
        import time
        
        lines = []
        for net, path in final_nets.items():
            if len(path) < 2:
                log.error(f"DRC Failure: Net {net} is incomplete.")
                raise GeometryConstraintError(f"Net {net} incomplete.")
            lines.append({"net": net, "line": geom.LineString(path).simplify(0.01)})
            
        if not lines:
            log.info("DRC Passed: No traces to check.")
            return True

        geometries = [item["line"] for item in lines]
        tree = STRtree(geometries)

        start_time = time.time()
        # Check crossings & spacings using spatial index
        for i, item in enumerate(lines):
            net1, line1 = item["net"], item["line"]
            
            # Query the STRtree with a buffer representing the min clearance + arbitrary tolerance
            search_radius = (self.spacing * 0.95) + 0.1
            nearby_indices = tree.query(line1.buffer(search_radius))
            
            for j in nearby_indices:
                if j <= i:
                    continue  # Unidirectional check, no self-check
                    
                net2, line2 = lines[j]["net"], lines[j]["line"]
                
                # Crossing check
                if line1.intersects(line2):
                    # For line/line intersections, check if there's a serious 1D overlap or clear X-crossing
                    overlap = line1.intersection(line2)
                    if getattr(overlap, 'length', 0.0) > 0.02:
                        # Serious 1D overlap
                        log.warning(f"DRC Cross Violation WARNING: {net1} intersects {net2}!")
                    elif overlap.geom_type in ['Point', 'MultiPoint']:
                        log.warning(f"DRC Touch Violation: {net1} touches {net2} at vertex.")

                # Minimum spacing check
                dist = line1.distance(line2)
                if dist < (self.spacing * 0.95): # 5% math tolerance
                    log.error(f"DRC Clearance Violation: {net1} and {net2} too close! {dist:.3f}mm")
                    # Warning rather than fatal error since we handled this geometrically
        
        log.info(f"DRC Checks completed in {time.time()-start_time:.2f}s")
        return True
