import json
import logging
from typing import Dict, List, Tuple
from dataclasses import dataclass
import shapely.geometry as geom
import json
import logging
from typing import Dict, List, Tuple
from dataclasses import dataclass
import shapely.geometry as geom

log = logging.getLogger("SystemLogger")

@dataclass
class ComponentState:
    ref: str
    x: float
    y: float

class LiveStateManager:
    """
    Industrial-Grade State Manager for NeuroBoard using Native KiCad 10 IPC
    """
    def __init__(self):
        self.cache: Dict[str, ComponentState] = {}
        self.manual_edits: Dict[str, ComponentState] = {}

    def fetch_live_state(self) -> Dict[str, ComponentState]:
        try:
            from kipy.kicad import KiCad
            kicad = KiCad(socket_path="ipc:///C:/Users/Bibek/AppData/Local/Temp/kicad/api.sock")
            board = kicad.get_board()
            
            states = {}
            for fp in board.get_footprints():
                pos = fp.position
                ref = fp.reference_field.text.value if getattr(fp, 'reference_field', None) else "UNKNOWN"
                x, y = pos.x / 1000000.0, pos.y / 1000000.0
                states[ref] = ComponentState(ref=ref, x=x, y=y)
            return states
        except Exception as e:
            log.warning(f"[LiveState] IPC Error: Failed to fetch live state via native API: {e}")
            return {}

    def sync(self) -> bool:
        """
        Retrieves the current RAM state via Native IPC and performs Delta Analysis against the AI cache.
        Identifies any 'User Manual Edit'.
        """
        live_state = self.fetch_live_state()
        if not live_state:
            return False

        if not self.cache:
            self.cache = live_state
            return True

        # Delta Analysis
        for ref, live_comp in live_state.items():
            if ref in self.cache:
                cached_comp = self.cache[ref]
                dx = abs(live_comp.x - cached_comp.x)
                dy = abs(live_comp.y - cached_comp.y)
                # If moved by more than 0.01 mm, mark as manual edit
                if dx > 0.01 or dy > 0.01:
                    log.info(f"[LiveState] User Manual Edit detected on {ref}: "
                             f"({cached_comp.x:.2f}, {cached_comp.y:.2f}) -> "
                             f"({live_comp.x:.2f}, {live_comp.y:.2f})")
                    self.manual_edits[ref] = live_comp

        self.cache = live_state
        return True

    def update_cache(self, ref: str, x: float, y: float):
        """Update the AI internal cache after AI performs an automated move."""
        self.cache[ref] = ComponentState(ref=ref, x=x, y=y)

    def route_trace_live(self, x1: float, y1: float, x2: float, y2: float, width_mm: float = 0.15, layer: str = "F.Cu"):
        """
        Pushes a single trace segment to the KiCAD canvas RAM via native IPC.
        Handled collectively in batch via orchestrator.
        """
        pass # Note: Implementation relocated to orchestrator.py for batch commit

    def refresh_ui(self):
        """
        Handled collectively in orchestrator.py.
        """
        pass

    def has_conflict(self, trace_path: List[Tuple[float, float]], clearance_mm: float = 3.0) -> bool:
        """
        Conflict Guard: Check if a planned AI route intersects with a newly moved user component.
        """
        if not self.manual_edits or len(trace_path) < 2:
            return False

        line = geom.LineString(trace_path)
        for ref, comp in self.manual_edits.items():
            pt = geom.Point(comp.x, comp.y)
            if line.distance(pt) < clearance_mm:
                log.warning(f"[LiveState] CONFLICT: AI trace path intersects with manually moved {ref}!")
                return True
        return False
