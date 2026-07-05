import math
from typing import List, Tuple

class Obstacle2D:
    def __init__(self, x: float, y: float, radius: float, clearance: float = 0.2):
        self.x = x
        self.y = y
        self.radius = radius + clearance

def calculate_wrapped_path(start: Tuple[float, float], end: Tuple[float, float], obstacles: List[Obstacle2D]) -> List[Tuple[float, float]]:
    """
    Pure arithmetic trace wrapper. Bends the line dynamically 
    around circular obstacles (vias/pads/footprints).
    """
    path = [start]
    current_pos = start

    # Sort obstacles by distance to the current position to handle them sequentially
    # This prevents zigzagging if obstacles are out of order
    sorted_obstacles = sorted(obstacles, key=lambda o: math.sqrt((o.x - current_pos[0])**2 + (o.y - current_pos[1])**2))

    for obs in sorted_obstacles:
        dx = end[0] - current_pos[0]
        dy = end[1] - current_pos[1]
        
        length = math.sqrt(dx**2 + dy**2)
        if length == 0:
            continue
            
        # Check if obstacle is roughly between current_pos and end
        # We use dot product to ensure the obstacle is "forward"
        obs_dx = obs.x - current_pos[0]
        obs_dy = obs.y - current_pos[1]
        dot_product = (obs_dx * dx + obs_dy * dy) / (length * length)
        
        if dot_product < 0 or dot_product > 1:
            continue # Obstacle is behind us or past the end point
            
        # Check distance from the obstacle center to the line
        dist_to_obs = abs(dy * obs.x - dx * obs.y + end[0] * current_pos[1] - end[1] * current_pos[0]) / length
        
        if dist_to_obs < obs.radius:
            # We hit an obstruction! Calculate the tangent angle to wrap around it
            angle_to_obs = math.atan2(obs.y - current_pos[1], obs.x - current_pos[0])
            
            # Determine which side is shorter to detour (left or right)
            # Use cross product to check which side the end point is on relative to the obstacle
            cross_product = (end[0] - obs.x) * math.sin(angle_to_obs) - (end[1] - obs.y) * math.cos(angle_to_obs)
            sign = 1 if cross_product > 0 else -1
            
            detour_x = obs.x + obs.radius * math.cos(angle_to_obs + sign * math.pi/2)
            detour_y = obs.y + obs.radius * math.sin(angle_to_obs + sign * math.pi/2)
            
            path.append((detour_x, detour_y))
            current_pos = (detour_x, detour_y)
            
    path.append(end)
    return path


# ==============================================================================
# PRETEXT-STYLE AABB COMPONENT PACKING ENGINE
# Treats each PCB footprint as an Axis-Aligned Bounding Box (AABB).
# Uses 1D interval overlap math to snap overlapping components to the nearest
# safe geometric edge — no slow spiral loops, no circular approximations.
# ==============================================================================

class ComponentBox2D:
    """
    Represents the real-world rectangular bounding box of a PCB footprint,
    with an additional DRC clearance margin on all four sides.
    """
    def __init__(self, ref: str, x: float, y: float, width: float, height: float, clearance: float = 0.5):
        self.ref = ref
        # Expand the bounding box outward by clearance on all sides
        self.width = width + (clearance * 2)
        self.height = height + (clearance * 2)
        self.x_min = x - (self.width / 2)
        self.x_max = x + (self.width / 2)
        self.y_min = y - (self.height / 2)
        self.y_max = y + (self.height / 2)

    @property
    def center_x(self) -> float:
        return (self.x_min + self.x_max) / 2

    @property
    def center_y(self) -> float:
        return (self.y_min + self.y_max) / 2

    def translate(self, new_cx: float, new_cy: float):
        """Recalculate boundaries after a position shift."""
        self.x_min = new_cx - (self.width / 2)
        self.x_max = new_cx + (self.width / 2)
        self.y_min = new_cy - (self.height / 2)
        self.y_max = new_cy + (self.height / 2)


def resolve_aabb_collision(moving_box: ComponentBox2D, obstacles: List[ComponentBox2D]) -> Tuple[float, float]:
    """
    Pretext Box-Slicing Shift — pure 1D interval overlap resolution.

    For each obstacle the moving component overlaps, this function:
    1. Calculates the penetration depth on all 4 sides (Left, Right, Top, Bottom).
    2. Identifies the axis of minimum penetration (path of least resistance).
    3. Instantly snaps the moving component to that safe edge + clearance.
    4. Immediately updates the moving_box boundaries for cascading multi-obstacle resolution.

    This is O(n) time — one pass, no loops, no floating-point spirals.
    Perfect for real-time 10Hz live-sync contexts.
    """
    resolved_cx = moving_box.center_x
    resolved_cy = moving_box.center_y

    for obs in obstacles:
        if obs.ref == moving_box.ref:
            continue  # Never check a component against itself

        # Fast AABB intersection test — bail out immediately if no overlap
        if not (moving_box.x_min < obs.x_max and
                moving_box.x_max > obs.x_min and
                moving_box.y_min < obs.y_max and
                moving_box.y_max > obs.y_min):
            continue

        # --- COLLISION DETECTED ---
        # Calculate penetration depth on all 4 sides
        overlap_push_left   = moving_box.x_max - obs.x_min  # push moving box LEFT
        overlap_push_right  = obs.x_max - moving_box.x_min  # push moving box RIGHT
        overlap_push_up     = moving_box.y_max - obs.y_min  # push moving box UP
        overlap_push_down   = obs.y_max - moving_box.y_min  # push moving box DOWN

        # Snap along the path of minimum resistance
        min_overlap = min(overlap_push_left, overlap_push_right, overlap_push_up, overlap_push_down)

        if min_overlap == overlap_push_left:
            resolved_cx -= overlap_push_left
        elif min_overlap == overlap_push_right:
            resolved_cx += overlap_push_right
        elif min_overlap == overlap_push_up:
            resolved_cy -= overlap_push_up
        else:  # overlap_push_down
            resolved_cy += overlap_push_down

        # Immediately recalculate the moving box boundaries for subsequent checks
        # (cascading multi-obstacle resolution)
        moving_box.translate(resolved_cx, resolved_cy)

    return resolved_cx, resolved_cy
