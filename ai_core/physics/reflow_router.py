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
