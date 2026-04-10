import os
import yaml
import logging
from typing import Dict, Any, List

from kipy.kicad import KiCad
from kipy.board import Board
from kipy.board_types import FootprintInstance, Track, Via, BoardShape

log = logging.getLogger("SystemLogger")

class IPCClient:
    def __init__(self, config_path: str = "config/neuroboard_config.yaml"):
        self.config = self._load_config(config_path)
        self.kicad = None
        self.board = None

    def _load_config(self, config_path: str) -> Dict:
        try:
            with open(config_path, "r") as f:
                return yaml.safe_load(f)
        except Exception as e:
            log.warning(f"Failed to load config {config_path}: {e}")
            return {"kicad": {"ipc_socket_path": ""}}

    def connect(self):
        socket_path = self.config.get("kicad", {}).get("ipc_socket_path", "")
        if socket_path:
            self.kicad = KiCad(socket_path=socket_path)
        else:
            self.kicad = KiCad() # use platform default
            
        try:
            self.board = self.kicad.get_board()
            log.info(f"Connected to KiCad IPC. Session: {self.board.name}")
        except Exception as e:
            log.error(f"Failed to connect to IPC socket: {e}")
            raise e

    def get_board_state(self) -> Dict[str, Any]:
        """ Extracts footprint positions, tracks, vias, and board outline metrics. """
        if not self.board:
            self.connect()
            
        state = {
            "footprints": [],
            "tracks": [],
            "vias": [],
            "layer_count": self.board.get_copper_layer_count(),
        }
        
        for fp in self.board.get_footprints():
            ref = fp.reference_field.text.value if getattr(fp, 'reference_field', None) else ""
            pos = fp.position
            rot = fp.orientation.degrees
            x, y = pos.x / 1e6, pos.y / 1e6
            state["footprints"].append({"ref": ref, "x": x, "y": y, "rot": rot})
            
        for track in self.board.get_tracks():
            start_x, start_y = track.start.x / 1e6, track.start.y / 1e6
            end_x, end_y = track.end.x / 1e6, track.end.y / 1e6
            state["tracks"].append({
                "start": (start_x, start_y), 
                "end": (end_x, end_y),
                "width": track.width / 1e6,
                "layer": track.layer
            })
            
        for via in self.board.get_vias():
            x, y = via.position.x / 1e6, via.position.y / 1e6
            state["vias"].append({"x": x, "y": y, "drill": via.drill / 1e6})
            
        return state

    def begin_commit(self):
        if not self.board:
            self.connect()
        return self.board.begin_commit()

    def create_items(self, items: List[Any]):
        if not self.board:
            raise RuntimeError("Board not connected.")
        return self.board.create_items(items)

    def push_commit(self, commit, message: str = "AI Edit"):
        if not self.board:
            raise RuntimeError("Board not connected.")
        self.board.push_commit(commit, message)

    def refresh_ui(self):
        """ Native IPC natively updates the UI upon push_commit, but we'll reserve this hook. """
        pass
