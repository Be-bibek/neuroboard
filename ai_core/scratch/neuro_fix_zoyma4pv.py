import sys
sys.path.insert(0, r'C:\Users\Bibek\Documents\KiCad\10.0\3rdparty\Python311\site-packages')
from kipy import KiCad
from kipy.board_types import (
    Net, Track, Via, Zone, board_types_pb2 as bt,
    ZoneType, ZoneBorderStyle, IslandRemovalMode
)
from kipy.geometry import Vector2, PolygonWithHoles, PolyLineNode
from kipy.util.units import from_mm
import math, json, re

_kicad = KiCad()
board  = _kicad.get_board()
NM     = 1_000_000
mm     = lambda v: int(v * NM)

def get_footprint(ref: str):
    for fp in board.get_footprints():
        try:
            if fp.reference_field.text.value == ref:
                return fp
        except Exception:
            continue
    return None

def get_net(name: str):
    return next((n for n in board.get_nets() if n.name == name), None)


# ── USER SCRIPT ──────────────────────────────
print(f'Board connected: {board.name}')
print(f'Nets: {len(list(board.get_nets()))}')