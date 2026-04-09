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
        
        if mismatch > self.tolerance_skew:
            log.warning(f"SI Violation: Phase skew {mismatch:.3f}mm exceeds {self.tolerance_skew}mm limit!")
        else:
            log.info(f" SI Skew OK: {mismatch:.3f}mm mismatch.")
            
        return mismatch
