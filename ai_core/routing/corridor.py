import shapely.geometry as geom
from .bus_detector import BusDetector
from .fanout import FanoutEngine

class CorridorGenerator:
    def __init__(self, trace_width=0.15, clearance=0.15):
        self.trace_width = trace_width
        self.clearance = clearance

    def generate_corridor(self, center_path_mm, bus_width):
        """
        Creates a routing corridor between connectors using a buffered center path.
        Returns a Shapely Polygon.
        """
        if len(center_path_mm) < 2:
            return None
        
        linestring = geom.LineString(center_path_mm)
        # Corridor width = bus_width + 1.0mm margin
        corridor = linestring.buffer(bus_width/2 + 1.0, join_style=2, cap_style=2)
        return corridor
