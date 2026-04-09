class RoutingError(Exception): pass
class PlacementConflictError(Exception): pass
class ImpedanceViolationError(Exception): pass
class GeometryConstraintError(Exception): pass

class FallbackStrategy:
    @staticmethod
    def adjust_spacing(current_spacing, min_spacing):
        """Attempts to relax spacing limits by 20% but keeping above minimum"""
        return max(min_spacing, current_spacing * 1.2)
        
    @staticmethod
    def relax_impedance_target(target_z, current_error):
        """Allows a wider impedance tolerance before throwing error"""
        return target_z * 1.1 # 10% relaxation
