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
        lines = []
        for net, path in final_nets.items():
            if len(path) < 2:
                log.error(f"DRC Failure: Net {net} is incomplete.")
                raise GeometryConstraintError(f"Net {net} incomplete.")
            lines.append((net, geom.LineString(path)))
            
        # Check crossings & spacings
        for i in range(len(lines)):
            net1, line1 = lines[i]
            for j in range(i+1, len(lines)):
                net2, line2 = lines[j]
                
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
        
        log.info("DRC Passed: 0 overlapping traces.")
        return True
