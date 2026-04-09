import math
import shapely.geometry as geom

class FanoutEngine:
    def __init__(self, trace_width=0.15, clearance=0.15):
        self.trace_width = trace_width
        self.clearance = clearance

    def generate_escape_points(self, pad_pos, orientation_deg, length=1.0):
        """
        Computes the escape segment from a pad avoiding overlaps.
        Returns a line segment (start_xy, end_xy) and the buffered envelope.
        """
        x, y = pad_pos
        rad = math.radians(orientation_deg)
        
        ex = x + length * math.cos(rad)
        ey = y + length * math.sin(rad)
        
        segment = geom.LineString([(x, y), (ex, ey)])
        
        # Buffer the segment to ensure structural clearance
        envelope = segment.buffer(self.trace_width/2 + self.clearance)
        
        return [(x, y), (ex, ey)], envelope

    def generate_bus_escapes(self, ordered_bus, pad_rotations, length=1.0):
        escapes = []
        envelopes = []
        for src_ref, dst_ref, src_pos, dst_pos in ordered_bus:
            # Assuming fanout outwards based on connector orientation (here roughly 90 or 0)
            src_seg, src_env = self.generate_escape_points(src_pos, pad_rotations.get(src_ref, 90.0), length)
            dst_seg, dst_env = self.generate_escape_points(dst_pos, pad_rotations.get(dst_ref, -90.0), length)
            
            escapes.append((src_seg, dst_seg))
            envelopes.extend([src_env, dst_env])
            
        return escapes, envelopes
