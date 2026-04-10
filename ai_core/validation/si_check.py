import math
from system.errors import ImpedanceViolationError
from system.logger import log
import shapely.geometry as geom

class SignalIntegrityValidator:
    def __init__(self, target_zdiff=100.0, tolerance_skew=0.1):
        self.target_zdiff = target_zdiff
        self.tolerance_skew = tolerance_skew

    def validate_diff_pair(self, net_p_name, path_p, net_n_name, path_n):
        """
        Validates the geometric structural integrity of a paired trace.
        """
        log.info(f"Validating Signal Integrity for pair: {net_p_name} / {net_n_name}")
        line_p = geom.LineString(path_p)
        line_n = geom.LineString(path_n)
        
        # 1. Length mismatch
        len_p = line_p.length
        len_n = line_n.length
        mismatch = abs(len_p - len_n)
        
        pass_skew = mismatch <= self.tolerance_skew
        if not pass_skew:
            log.warning(f"SI Violation: Phase skew {mismatch:.3f}mm exceeds {self.tolerance_skew}mm limit!")
        else:
            log.info(f" SI Skew OK: {mismatch:.3f}mm mismatch.")
            
        # 2. Constant differential spacing
        # Sample points along the longer line to ensure constant separation
        # This checks the freespace distance between the traces
        num_samples = 20
        spacing_violations = 0
        min_dist = float('inf')
        max_dist = 0.0
        
        for i in range(num_samples):
            pt = line_p.interpolate(i / float(num_samples - 1), normalized=True)
            dist = pt.distance(line_n)
            
            min_dist = min(min_dist, dist)
            max_dist = max(max_dist, dist)
            
        # Allowed variance in spacing
        spacing_variance = max_dist - min_dist
        pass_spacing = spacing_variance <= 0.05  # 0.05mm tolerance
        
        if not pass_spacing:
            log.warning(f"SI Violation: Inconsistent diff pair spacing. Variance: {spacing_variance:.3f}mm (target <= 0.05mm)")
        else:
            log.info(f" SI Spacing OK: Variance {spacing_variance:.3f}mm across trace length.")

        return {
            "skew_mm": round(mismatch, 4),
            "spacing_variance_mm": round(spacing_variance, 4),
            "passed": pass_skew and pass_spacing
        }
