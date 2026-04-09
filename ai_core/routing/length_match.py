import math
import shapely.geometry as geom

class LengthMatchEngine:
    def __init__(self, tolerance=0.1, amplitude=0.5, spacing=0.3):
        self.tolerance = tolerance # mm
        self.amplitude = amplitude
        self.spacing = spacing

    def measure_length(self, path):
        if len(path) < 2: return 0.0
        return geom.LineString(path).length

    def calculate_skew(self, path_p, path_n):
        return abs(self.measure_length(path_p) - self.measure_length(path_n))

    def generate_meander(self, start_pt, end_pt, required_extra_length):
        """
        Generates serpentine accordion segments between start_pt and end_pt.
        Adds roughly 'required_extra_length'.
        """
        x1, y1 = start_pt
        x2, y2 = end_pt
        
        dx = x2 - x1
        dy = y2 - y1
        segment_len = math.hypot(dx, dy)
        
        if segment_len < self.spacing * 2:
            return None # Segment too short to meander
            
        angle = math.atan2(dy, dx)
        cos_a = math.cos(angle)
        sin_a = math.sin(angle)
        
        # Calculate cycles needed
        hyp = math.hypot(self.amplitude, self.spacing/2)
        added_per_cycle = 2 * hyp - self.spacing
        
        if added_per_cycle <= 0: return None
        
        cycles = math.ceil(required_extra_length / added_per_cycle)
        
        # We must fit 'cycles' within 'segment_len'.
        if cycles * self.spacing > segment_len * 0.8:
            # We can only fit so many cycles
            cycles = int((segment_len * 0.8) / self.spacing)
            
        if cycles <= 0: return None
        
        meander_pts = []
        cx = segment_len / 2 - (cycles * self.spacing) / 2
        cy = 0.0
        
        # Add entry point
        meander_pts.append((0, 0))
        meander_pts.append((cx, 0))
        
        sign = 1
        for _ in range(cycles):
            cx += self.spacing / 2
            meander_pts.append((cx, sign * self.amplitude))
            cx += self.spacing / 2
            meander_pts.append((cx, 0))
            sign *= -1
            
        meander_pts.append((segment_len, 0))
        
        # Rotate and translate into world space
        world_pts = []
        for mx, my in meander_pts:
            wx = x1 + mx * cos_a - my * sin_a
            wy = y1 + mx * sin_a + my * cos_a
            world_pts.append((wx, wy))
            
        return world_pts

    def match_pair(self, path_p, path_n):
        """
        Identifies mismatch and adds serpentine segments to the shorter trace.
        """
        len_p = self.measure_length(path_p)
        len_n = self.measure_length(path_n)
        
        diff = abs(len_p - len_n)
        if diff <= self.tolerance:
            return path_p, path_n  # Already matched
            
        print(f"Skew detected: {diff:.3f} mm. Applying length matching meander.")
        
        shorter_path = path_p if len_p < len_n else path_n
        required_len = diff
        
        # Find the longest segment to splice
        max_len = 0
        max_idx = 0
        for i in range(len(shorter_path)-1):
            l = math.hypot(shorter_path[i+1][0] - shorter_path[i][0], shorter_path[i+1][1] - shorter_path[i][1])
            if l > max_len:
                max_len = l
                max_idx = i
                
        # Generate meander
        meander = self.generate_meander(shorter_path[max_idx], shorter_path[max_idx+1], required_len)
        if meander:
            # Splice
            matched_path = shorter_path[:max_idx] + meander + shorter_path[max_idx+1:]
        else:
            print("Failed to fit meander in trace.")
            matched_path = shorter_path
            
        if len_p < len_n:
            return matched_path, path_n
        else:
            return path_p, matched_path
