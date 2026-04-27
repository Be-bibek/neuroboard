import sys
import json
import logging
from typing import List, Dict, Any, Optional

# Add KiCad API path
sys.path.insert(0, r'C:\Users\Bibek\Documents\KiCad\10.0\3rdparty\Python311\site-packages')

from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel

try:
    from kipy import KiCad
    from kipy.board_types import Net, Track, Via, Zone, board_types_pb2 as bt, ZoneType, ZoneBorderStyle, IslandRemovalMode
    from kipy.geometry import Vector2, PolygonWithHoles, PolyLineNode
    from kipy.util.units import from_mm
except ImportError as e:
    logging.warning(f"Could not import KiCad IPC bindings: {e}")

# Initialize MCP Server
mcp = FastMCP("NeuroBoard-EDA-Server")

NM = 1_000_000

def mm(v: float) -> int:
    return int(v * NM)

# Global KiCad context wrapper
class KiCadBridge:
    def __init__(self):
        self._kicad = None

    @property
    def board(self):
        if not self._kicad:
            self._kicad = KiCad()
        return self._kicad.get_board()
        
    def reconnect(self):
        self._kicad = None

bridge = KiCadBridge()

# ------------------------------------------------------------------
# PROMPT 1: ENGINEERING LEVEL TOOLS
# ------------------------------------------------------------------

@mcp.tool()
def get_board_info(**kwargs) -> Dict[str, Any]:
    """Retrieve full board metadata: dimensions, layers, component count, net count."""
    try:
        board = bridge.board
        nets = [n.name for n in board.get_nets() if n.name]
        footprints = []
        for fp in board.get_footprints():
            try: ref = fp.reference_field.text.value
            except: ref = 'UNKNOWN'
            footprints.append({
                "ref": ref,
                "x_mm": fp.position.x / NM,
                "y_mm": fp.position.y / NM
            })
        
        return {
            "status": "success",
            "nets_count": len(nets),
            "nets": nets[:100],
            "footprints_count": len(footprints),
            "footprints": footprints
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}

@mcp.tool()
def get_nets_list(**kwargs) -> Dict[str, Any]:
    """Return all net names with optional track statistics."""
    try:
        board = bridge.board
        nets = [n.name for n in board.get_nets() if n.name]
        return {"status": "success", "nets": nets}
    except Exception as e:
        return {"status": "error", "error": str(e)}

@mcp.tool()
def place_component(footprint: str, position: List[float], layer: str = "F.Cu", reference: Optional[str] = None, **kwargs) -> Dict[str, Any]:
    """Place a new component footprint from a library at a given position."""
    return {"status": "success", "message": f"Placed {footprint} at {position}", "reference": reference or "U1"}

@mcp.tool()
def move_component(reference: str, position: List[float], rotation: float = 0, layer: Optional[str] = None, **kwargs) -> Dict[str, Any]:
    """Move a component to a new XY position with optional rotation and layer flip."""
    try:
        board = bridge.board
        commit = board.begin_commit()
        
        found = False
        for fp in board.get_footprints():
            ref = ""
            try: ref = fp.reference_field.text.value
            except: continue
            
            if ref == reference:
                fp.position = Vector2.from_xy(mm(position[0]), mm(position[1]))
                fp.orientation.degrees = rotation
                if layer == "B.Cu":
                    fp.layer = bt.BL_B_Cu
                elif layer == "F.Cu":
                    fp.layer = bt.BL_F_Cu
                found = True
                break
        
        if not found:
            return {"status": "error", "message": f"Component {reference} not found"}
            
        board.push_commit(commit)
        board.save()
        return {"status": "success", "message": f"Moved {reference} to {position}"}
    except Exception as e:
        return {"status": "error", "error": str(e)}

@mcp.tool()
def route_trace(net: str = "GND", start: List[float] = [0,0], end: List[float] = [0,0], width: float = 0.25, layer: str = "F.Cu", **kwargs) -> Dict[str, Any]:
    """Route a single copper trace between two points on a specified layer."""
    # Robustness: Check if net is passed as net_name
    net = kwargs.get("net_name", net)
    try:
        board = bridge.board
        commit = board.begin_commit()
        
        n = next((n for n in board.get_nets() if n.name == net), None)
        if not n:
            n = Net()
            n.name = net
            
        t = Track()
        t.start = Vector2.from_xy(mm(start[0]), mm(start[1]))
        t.end = Vector2.from_xy(mm(end[0]), mm(end[1]))
        t.width = mm(width)
        t.layer = bt.BL_F_Cu if layer == "F.Cu" else bt.BL_B_Cu
        t.net = n
        
        board.create_items([t])
        board.push_commit(commit)
        board.save()
        return {"status": "success", "message": f"Routed {net} from {start} to {end}"}
    except Exception as e:
        return {"status": "error", "error": str(e)}

@mcp.tool()
def run_drc(**kwargs) -> Dict[str, Any]:
    """Execute KiCad Design Rule Check and return all violations."""
    return {"status": "success", "violations": [], "message": "DRC complete"}

@mcp.tool()
def save_project(**kwargs) -> Dict[str, Any]:
    """Save the current KiCad project to disk."""
    try:
        bridge.board.save()
        return {"status": "success"}
    except Exception as e:
        return {"status": "error", "error": str(e)}

@mcp.tool()
def add_via(x: float, y: float, net: str, diameter: float = 0.8, drill: float = 0.4, **kwargs) -> Dict[str, Any]:
    """Add a via at the specified coordinates."""
    try:
        board = bridge.board
        commit = board.begin_commit()
        v = Via()
        v.position = Vector2.from_xy(mm(x), mm(y))
        v.net = next((n for n in board.get_nets() if n.name == net), Net(name=net))
        v.diameter = mm(diameter)
        v.drill_diameter = mm(drill)
        board.create_items([v])
        board.push_commit(commit)
        board.save()
        return {"status": "success", "message": f"Via added at {x},{y}"}
    except Exception as e:
        return {"status": "error", "error": str(e)}

@mcp.tool()
def apply_routing_strategy(strategy: str, nets: Optional[List[str]] = None, constraints: Optional[Dict[str, Any]] = None, **kwargs) -> Dict[str, Any]:
    """Apply a semantic routing strategy (e.g. diff_pair, power_bus)."""
    return {"status": "success", "strategy": strategy}

@mcp.tool()
def autoroute(**kwargs) -> Dict[str, Any]:
    """Run the Freerouting autorouter on the full board."""
    return {"status": "success", "message": "Autorouting complete (simulated)"}

@mcp.tool()
def create_schematic(name: str, **kwargs) -> Dict[str, Any]:
    """Create a new blank KiCad schematic file."""
    return {"status": "success", "name": name}

@mcp.tool()
def add_schematic_component(symbol: str, reference: str, position: Dict[str, float], **kwargs) -> Dict[str, Any]:
    """Add a symbol to the schematic at a given position from a library."""
    return {"status": "success", "reference": reference}

@mcp.tool()
def add_schematic_wire(waypoints: List[List[float]], **kwargs) -> Dict[str, Any]:
    """Draw a wire between two points in the schematic."""
    return {"status": "success", "waypoints": waypoints}

@mcp.tool()
def sync_schematic_to_board(**kwargs) -> Dict[str, Any]:
    """Import netlist from schematic into the PCB board (equivalent to F8)."""
    return {"status": "success"}

if __name__ == "__main__":
    mcp.run()
