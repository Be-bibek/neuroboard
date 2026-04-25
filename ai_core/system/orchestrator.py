import math
import logging
from kipy import KiCad
from kipy.board import FootprintInstance, BoardLayer, board_types_pb2 as bt

log = logging.getLogger("Orchestrator")

NM_PER_MM = 1_000_000

def mm(v: float) -> int:
    return int(v * NM_PER_MM)

class PassiveAgent:
    """
    The Passive Agent (Footprint Injector).
    Automatically 'sprinkles' passive components (like decoupling caps)
    around active ICs based on IPC coordinates.
    """
    def __init__(self):
        self.kicad = KiCad()

    def make_fp(self, library: str, entry: str, ref: str, value: str, x_mm: float, y_mm: float, rot_deg: float = 0.0) -> FootprintInstance:
        p = bt.FootprintInstance()
        p.definition.id.library_nickname = library
        p.definition.id.entry_name = entry
        p.position.x_nm = mm(x_mm)
        p.position.y_nm = mm(y_mm)
        p.orientation.value_degrees = float(rot_deg)
        p.layer = BoardLayer.Value("BL_F_Cu")
        p.reference_field.text.text.text = ref
        p.value_field.text.text.text = value
        return FootprintInstance(proto=p)

    def inject_decoupling(self, target_ref: str = "J3"):
        """
        Locates the target component (e.g. M.2 slot), and injects
        decoupling capacitors 2mm away from its power pins.
        """
        try:
            board = self.kicad.get_board()
        except Exception as e:
            log.error(f"KiCad IPC Connection failed: {e}")
            return {"status": "error", "reason": str(e)}

        # Find target footprint
        target_fp = None
        for fp in board.get_footprints():
            try:
                if fp.reference_field.text.value == target_ref:
                    target_fp = fp
                    break
            except AttributeError:
                continue

        if not target_fp:
            return {"status": "error", "reason": f"Target {target_ref} not found on board."}

        base_x = target_fp.position.x / NM_PER_MM
        base_y = target_fp.position.y / NM_PER_MM

        print(f"[PassiveAgent] Found {target_ref} at ({base_x}, {base_y}). Injecting Decoupling...")

        # Inject 4 capacitors, 2mm above the connector
        # (Assuming J3 is horizontally placed at base_y, we place them at base_y - 2mm, spaced by 1.5mm)
        caps = []
        start_x = base_x - 3.0  # start slightly left of center
        
        for i in range(1, 5):
            ref = f"C_DEC_{i}"
            x = start_x + (i * 1.5)
            y = base_y - 3.5  # 3.5mm away to clear pads
            
            # Using our local S-expr warehouse conceptually, but for IPC reliability we push standard KiCad IDs
            fp = self.make_fp("Device", "C_0402_1005Metric", ref, "100nF", x, y, rot_deg=90.0)
            caps.append(fp)
            print(f"  -> Injected {ref} at ({x}, {y})")

        # Push to KiCad
        commit = board.begin_commit()
        created = board.create_items(caps)
        board.push_commit(commit)
        board.save()
        
        return {
            "status": "success", 
            "message": f"Injected {len(created)} decoupling capacitors around {target_ref}.",
            "caps": [c.id for c in created]
        }

    def save_board(self):
        """Forces the live board to save via IPC."""
        try:
            board = self.kicad.get_board()
            board.save()
            return {"status": "success", "message": "Board saved successfully."}
        except Exception as e:
            return {"status": "error", "reason": str(e)}

orchestrator = PassiveAgent()
