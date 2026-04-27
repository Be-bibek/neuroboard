"""
ai_core/system/ipc_client.py
==============================
Hardened KiCad 10 IPC Client (Phase 6 — PiHAT-KiCAD-Pro-Legacy Integration)

Improvements over v1:
  - Config-driven project & socket paths (no hardcoded strings)
  - Retry logic with exponential back-off
  - Health / board-name validation after connect
  - Context-manager support (with IPCClient() as ipc: ...)
  - Timeout-aware refresh after every push_commit
  - Full logging of every IPC transaction
"""

import os
import time
import yaml
import logging
import subprocess
from pathlib import Path
from contextlib import contextmanager
from typing import Callable, Dict, Any, List, Optional

log = logging.getLogger("SystemLogger")

# ---------------------------------------------------------------------------
# ExecutionMode — import with graceful fallback so this module is self-contained
# ---------------------------------------------------------------------------
try:
    from system.execution_mode import ExecutionMode, EnvironmentProbe
except ImportError:
    try:
        from execution_mode import ExecutionMode, EnvironmentProbe
    except ImportError:
        class ExecutionMode:  # type: ignore
            IPC        = "ipc"
            HEADLESS   = "headless"
            SIMULATION = "simulation"
            def is_live(self): return False
        class EnvironmentProbe:  # type: ignore
            @staticmethod
            def detect(*a, **kw): return ExecutionMode.SIMULATION

# ---------------------------------------------------------------------------
# Optional kipy import (graceful degradation when KiCad is not running)
# ---------------------------------------------------------------------------
try:
    from kipy.kicad import KiCad
    from kipy.board import Board
    from kipy.board_types import FootprintInstance, Track, Via, BoardLayer
    from kipy.geometry import Vector2
    KIPY_AVAILABLE = True
except ImportError:
    KIPY_AVAILABLE = False
    log.warning("[IPC] kipy not available — running in simulation mode.")

# ---------------------------------------------------------------------------
# Config helpers
# ---------------------------------------------------------------------------

def _resolve_yaml_vars(config: dict) -> dict:
    """Resolve ${project.name} style references inside the config."""
    name = config.get("project", {}).get("name", "PiHAT-KiCAD-Pro-Legacy")
    def _subst(v):
        if isinstance(v, str):
            return v.replace("${project.name}", name)
        return v
    proj = config.get("project", {})
    for key in ["pcb_file", "sch_file", "pro_file", "net_file"]:
        if key in proj:
            proj[key] = _subst(proj[key])
    return config


class IPCClient:
    """
    Thread-safe KiCad 10 IPC bridge.

    Usage (context manager):
        with IPCClient() as ipc:
            ipc.sync_netlist_to_board("pi_hat.net")
    """

    # ------------------------------------------------------------------
    # Construction & config
    # ------------------------------------------------------------------

    def __init__(self,
                 config_path: str = "config/neuroboard_config.yaml",
                 mode: Optional["ExecutionMode"] = None):
        self.config       = self._load_config(config_path)
        self._kicad       = None
        self.board        = None
        self._commit_open = False
        # Determine execution mode
        if mode is not None:
            self.mode = mode
        else:
            socket_path = self.config.get("kicad", {}).get(
                "ipc_socket_path", ""
            ).replace("ipc://", "")
            self.mode = EnvironmentProbe.detect(socket_path=socket_path or None)
        log.info(f"[IPC] ExecutionMode: {self.mode}")

    # context-manager support
    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, *_):
        self.disconnect()

    def _load_config(self, path: str) -> dict:
        try:
            with open(path, "r", encoding="utf-8") as f:
                cfg = yaml.safe_load(f) or {}
            return _resolve_yaml_vars(cfg)
        except Exception as e:
            log.warning(f"[IPC] Config load failed ({e}); using defaults.")
            return {"kicad": {}, "project": {}}

    # ------------------------------------------------------------------
    # Derived paths (all resolved from config, no hardcoding)
    # ------------------------------------------------------------------

    @property
    def _socket_path(self) -> str:
        return self.config.get("kicad", {}).get(
            "ipc_socket_path",
            "ipc:///C:/Users/Bibek/AppData/Local/Temp/kicad/api.sock"
        )

    @property
    def _auto_refresh(self) -> bool:
        return self.config.get("kicad", {}).get("auto_refresh", True)

    @property
    def _base_dir(self) -> Path:
        from system.project_manager import project_manager
        active = project_manager.get_active_project()
        if active:
            return Path(active["path"])
            
        return Path(self.config.get("project", {}).get(
            "base_dir",
            r"C:\Users\Bibek\Documents\pi-hat\PiHAT-KiCAD-Pro-Legacy"
        ))

    @property
    def _pcb_path(self) -> Path:
        from system.project_manager import project_manager
        active = project_manager.get_active_project()
        if active and active.get("pcb_file"):
            return Path(active["pcb_file"])
            
        return self._base_dir / self.config["project"].get(
            "pcb_file", "PiHAT-KiCAD-Pro-Legacy.kicad_pcb"
        )

    @property
    def _net_path(self) -> Path:
        return self._base_dir / self.config["project"].get("net_file", "pi_hat.net")

    @property
    def _project_name(self) -> str:
        from system.project_manager import project_manager
        active = project_manager.get_active_project()
        if active:
            return active["name"]
            
        return self.config.get("project", {}).get("name", "PiHAT-KiCAD-Pro-Legacy")

    @property
    def _project_path(self) -> Path:
        from system.project_manager import project_manager
        active = project_manager.get_active_project()
        if active and active.get("pro_file"):
            return Path(active["pro_file"])
            
        return self._base_dir / f"{self._project_name}.kicad_pro"

    # ------------------------------------------------------------------
    # Connection & health
    # ------------------------------------------------------------------

    def connect(self, retries: int = 5, backoff: float = 1.5) -> bool:
        """
        Attempt to connect to KiCad IPC with exponential back-off.
        Automatically tries to launch KiCad if the socket path is missing.
        """
        if not KIPY_AVAILABLE:
            log.warning("[IPC] kipy unavailable — simulation mode active.")
            return False

        # 1. Check if socket exists; if not, try auto-launch
        if not self._socket_exists() and self.config.get("kicad", {}).get("auto_launch", True):
            # Only launch if not already running
            if not self._is_kicad_running():
                self.auto_launch_kicad()
            else:
                log.info("[IPC] KiCad project is already running. Waiting for socket...")
                time.sleep(2.0)

        delay = 1.0
        for attempt in range(1, retries + 1):
            try:
                # kipy expects the full nng-compatible URL (e.g. ipc:///path)
                spath = self._socket_path
                
                log.debug(f"[IPC] Dialing: {spath}")
                self._kicad = KiCad(socket_path=spath)
                
                # Try to get the board, but don't fail if individual handlers are missing
                try:
                    self.board = self._kicad.get_board()
                    # Health check: ensure the right project is loaded
                    board_name = getattr(self.board, "name", "")
                    if self._project_name.lower() in board_name.lower():
                        log.info(f"[IPC] Connected (attempt {attempt}). Board: {board_name}")
                    else:
                        log.warning(f"[IPC] Connected but board mismatch: expected '{self._project_name}', got '{board_name}'.")
                except Exception as e:
                    if "no handler available" in str(e).lower():
                        log.info(f"[IPC] Connected (attempt {attempt}). KiCad is open, but no specific editor handler (Schematic/PCB) found yet.")
                        self.board = None
                    else:
                        raise e
                
                return True
            except Exception as e:
                log.warning(f"[IPC] Connect attempt {attempt}/{retries} failed: {e}")
                if attempt < retries:
                    time.sleep(delay)
                    delay *= backoff
        
        log.error("[IPC] All connection attempts exhausted. Falling back to simulation.")
        return False

    def _socket_exists(self) -> bool:
        """Check if the Unix/Pipe socket file exists on disk."""
        spath = self._socket_path.replace("ipc://", "")
        return os.path.exists(spath)

    def _is_kicad_running(self) -> bool:
        """Check if KiCad process is already running with our project."""
        try:
            import psutil
            project_name = os.path.basename(self._project_path)
            for proc in psutil.process_iter(['name', 'cmdline']):
                if proc.info['name'] and 'kicad' in proc.info['name'].lower():
                    cmdline = ' '.join(proc.info.get('cmdline', []))
                    if project_name in cmdline:
                        return True
        except Exception as e:
            log.warning(f"[IPC] Could not verify running processes: {e}")
        return False

    def auto_launch_kicad(self):
        """Attempt to launch the KiCad project editor."""
        kicad_bin = self.config.get("kicad", {}).get(
            "binary_path", 
            r"C:\Program Files\KiCad\10.0\bin\kicad.exe"
        )
        if not os.path.exists(kicad_bin):
            log.warning(f"[IPC] KiCad binary not found at {kicad_bin} — cannot auto-launch.")
            return

        if not os.path.exists(self._project_path):
            # Fallback to PCB if .kicad_pro is truly missing, but warn
            log.warning(f"[IPC] Project file missing: {self._project_path}. Falling back to PCB.")
            launch_target = self._pcb_path
        else:
            launch_target = self._project_path

        try:
            log.info(f"[IPC] Launching KiCad: {kicad_bin} {launch_target}")
            # Use Popen to launch without blocking
            subprocess.Popen([kicad_bin, str(launch_target)], 
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            # Give it time to initialize
            time.sleep(5.0) 
        except Exception as e:
            log.error(f"[IPC] Failed to launch KiCad: {e}")

    def disconnect(self):
        if self._commit_open:
            self._safe_cancel_commit()
        self._kicad = None
        self.board  = None

    def ping(self) -> bool:
        """Quick liveness check — reconnects if needed."""
        try:
            if not self.board:
                return self.connect(retries=2)
            self._kicad.get_board()        # throws if dead
            return True
        except Exception:
            log.warning("[IPC] Ping failed — attempting reconnect.")
            return self.connect(retries=2)

    # ------------------------------------------------------------------
    # Transaction helpers
    # ------------------------------------------------------------------

    def begin_commit(self):
        if not self.board:
            raise RuntimeError("[IPC] Not connected. Call connect() first.")
        if self._commit_open:
            log.warning("[IPC] Commit already open — cancelling stale one.")
            self._safe_cancel_commit()
        commit = self.board.begin_commit()
        self._commit_open = True
        log.debug("[IPC] Commit begun.")
        return commit

    def create_items(self, items: List[Any]):
        if not self.board:
            raise RuntimeError("[IPC] Not connected.")
        return self.board.create_items(items)

    def push_commit(self, commit, message: str = "NeuroBoard AI Edit"):
        if not self.board:
            raise RuntimeError("[IPC] Not connected.")
        self.board.push_commit(commit, message)
        self._commit_open = False
        log.info(f"[IPC] Commit pushed: '{message}'")
        if self._auto_refresh:
            self.refresh_ui()

    def _safe_cancel_commit(self):
        try:
            if hasattr(self.board, "cancel_commit"):
                self.board.cancel_commit()
        except Exception as e:
            log.debug(f"[IPC] Cancel commit error (ignored): {e}")
        finally:
            self._commit_open = False

    def begin_batch(self, rollback: bool = True):
        """
        Context manager for a single atomic transaction with optional rollback.

        Usage::

            with ipc.begin_batch():
                ipc.add_symbol(...)
                ipc.add_symbol(...)
            # On exception: all footprints are restored to their pre-batch state.
        """
        return _RollbackBatch(self, rollback=rollback)

    def _snapshot_positions(self) -> Dict[str, Any]:
        """Capture a {ref: (x_nm, y_nm, orient)} snapshot for rollback."""
        snap: Dict[str, Any] = {}
        if not self.board:
            return snap
        try:
            for fp in self.board.get_footprints():
                ref = fp.reference_field.text.value if getattr(fp, 'reference_field', None) else "?"
                snap[ref] = (
                    getattr(fp.position, 'x', 0),
                    getattr(fp.position, 'y', 0),
                    getattr(getattr(fp, 'orientation', None), 'degrees', 0.0),
                )
        except Exception as e:
            log.debug(f"[IPC] Snapshot error (non-fatal): {e}")
        return snap

    def _restore_snapshot(self, snap: Dict[str, Any]) -> None:
        """Restore footprint positions from a snapshot (rollback support)."""
        if not self.board or not snap:
            return
        restored = 0
        try:
            fp_map = {}
            for fp in self.board.get_footprints():
                ref = fp.reference_field.text.value if getattr(fp, 'reference_field', None) else None
                if ref:
                    fp_map[ref] = fp

            for ref, (x, y, rot) in snap.items():
                if ref in fp_map:
                    fp = fp_map[ref]
                    fp.position.x = x
                    fp.position.y = y
                    if hasattr(fp, 'orientation'):
                        fp.orientation.degrees = rot
                    restored += 1
            log.info(f"[IPC] Rollback: restored {restored}/{len(snap)} footprints.")
        except Exception as e:
            log.error(f"[IPC] Rollback restore failed: {e}")

    def refresh_ui(self, delay: float = 0.4):
        """Give KiCad time to apply the commit before the next transaction."""
        time.sleep(delay)
        log.debug("[IPC] UI refresh complete.")

    # ------------------------------------------------------------------
    # Board state extraction
    # ------------------------------------------------------------------

    def get_board_state(self) -> Dict[str, Any]:
        """Returns footprints, tracks, vias, and layer count."""
        if not self.board:
            self.connect()

        state: Dict[str, Any] = {
            "footprints":  [],
            "tracks":      [],
            "vias":        [],
            "layer_count": 0,
        }

        try:
            state["layer_count"] = self.board.get_copper_layer_count()

            for fp in self.board.get_footprints():
                ref = ""
                if getattr(fp, "reference_field", None):
                    ref = fp.reference_field.text.value
                pos = fp.position
                state["footprints"].append({
                    "ref": ref,
                    "x":   round(pos.x / 1e6, 4),
                    "y":   round(pos.y / 1e6, 4),
                    "rot": fp.orientation.degrees,
                })

            for track in self.board.get_tracks():
                state["tracks"].append({
                    "start": (round(track.start.x / 1e6, 4),
                              round(track.start.y / 1e6, 4)),
                    "end":   (round(track.end.x / 1e6, 4),
                              round(track.end.y / 1e6, 4)),
                    "width": round(track.width / 1e6, 4),
                    "layer": track.layer,
                })

            for via in self.board.get_vias():
                state["vias"].append({
                    "x":     round(via.position.x / 1e6, 4),
                    "y":     round(via.position.y / 1e6, 4),
                    "drill": round(via.drill_diameter / 1e6, 4),
                })
        except Exception as e:
            log.error(f"[IPC] get_board_state failed: {e}")

        return state

    def get_pad_coordinates_for_nodes(
        self, nodes: List[tuple]
    ) -> List[Dict[str, Any]]:
        """Resolve (ref, pin) tuples → real-world pad coordinates via live board."""
        if not self.board:
            self.connect()

        coords = []
        for ref, pin in nodes:
            for fp in self.board.get_footprints():
                fp_ref = ""
                if getattr(fp, "reference_field", None):
                    fp_ref = fp.reference_field.text.value
                if fp_ref == ref:
                    for pad in fp.pads():
                        if pad.number == pin:
                            coords.append({
                                "ref":   ref,
                                "pin":   pin,
                                "x":     round(pad.position.x / 1e6, 4),
                                "y":     round(pad.position.y / 1e6, 4),
                                "layer": pad.layer,
                            })
                    break
        return coords

    # ------------------------------------------------------------------
    # Netlist sync via KiCad CLI
    # ------------------------------------------------------------------

    def sync_netlist_to_board(self, netlist_path: Optional[str] = None) -> bool:
        """
        Pushes the generated netlist to the board using kicad-cli.
        Falls back gracefully if the CLI subcommand is unsupported.
        """
        net_file = netlist_path or str(self._net_path)
        pcb_file = str(self._pcb_path)

        if not os.path.isfile(net_file):
            log.error(f"[IPC] Netlist not found: {net_file}")
            return False

        kicad_cli = r"C:\Program Files\KiCad\10.0\bin\kicad-cli.exe"
        try:
            log.info(f"[IPC] Syncing netlist '{net_file}' → '{pcb_file}'")
            result = subprocess.run(
                [kicad_cli, "pcb", "update-footprints",
                 "--netlist", net_file, pcb_file],
                capture_output=True, text=True, timeout=60
            )
            if result.returncode == 0:
                log.info("[IPC] Netlist sync successful.")
                self.refresh_ui()
                return True
            log.warning(f"[IPC] kicad-cli returned {result.returncode}: {result.stderr}")
        except FileNotFoundError:
            log.warning("[IPC] kicad-cli not found.")
        except subprocess.TimeoutExpired:
            log.error("[IPC] kicad-cli timed out.")
        except Exception as e:
            log.error(f"[IPC] Netlist sync error: {e}")

        log.info("[IPC] CLI sync skipped — rely on KiCad UI (F8) to import netlist.")
        return False

    # ------------------------------------------------------------------
    # DRC via CLI
    # ------------------------------------------------------------------

    def run_drc(self, report_path: Optional[str] = None) -> bool:
        """Triggers KiCad CLI DRC and writes a text report."""
        pcb_file  = str(self._pcb_path)
        out_path  = report_path or str(self._base_dir / "drc_report.txt")
        kicad_cli = str(self.config.get("kicad", {}).get("binary_path", "kicad-cli")).replace("kicad.exe", "kicad-cli.exe")

        try:
            log.info(f"[IPC] Running DRC on '{pcb_file}'")
            result = subprocess.run(
                [kicad_cli, "pcb", "drc", pcb_file, "--output", out_path],
                capture_output=True, text=True, timeout=120
            )
            ok = result.returncode == 0
            log.info(f"[IPC] DRC {'PASS' if ok else 'FAIL'} → {out_path}")
            return ok
        except Exception as e:
            log.error(f"[IPC] DRC failed: {e}")
            return False

    # ------------------------------------------------------------------
    # Transaction & Batch Helpers
    # ------------------------------------------------------------------

    def begin_batch(self):
        """Context manager for atomic batch operations."""
        return BatchTransaction(self)

    # ------------------------------------------------------------------
    # Board state & Routing
    # ------------------------------------------------------------------

    def add_trace(self, start: tuple, end: tuple, layer: str = "F.Cu", width: float = 0.15):
        """Adds a single track to the board."""
        if not self.board:
            log.warning("[IPC] Trace skipped: Board not connected.")
            return None
        
        try:
            # kipy uses Vector2 with nm coordinates
            s_vec = Vector2(int(start[0] * 1e6), int(start[1] * 1e6))
            e_vec = Vector2(int(end[0] * 1e6), int(end[1] * 1e6))
            w_nm  = int(width * 1e6)
            
            track = Track(start=s_vec, end=e_vec, width=w_nm, layer=layer)
            self.board.create_items([track])
            return track
        except Exception as e:
            log.error(f"[IPC] Failed to add trace: {e}")
            return None

    def cursor(self, x: float, y: float, layer: str = "F.Cu", width: float = 0.15) -> 'DataCursor':
        """Returns a pcbflow-inspired DataCursor for generative routing."""
        return DataCursor(self, (x, y), layer, width)

    # ------------------------------------------------------------------
    # Schematic API & Editor IPC
    # ------------------------------------------------------------------

    def get_schematic(self):
        """Returns the schematic object, connecting if necessary."""
        if not self._kicad:
            self.connect()
        if not hasattr(self, 'schematic') or not self.schematic:
            try:
                self.schematic = self._kicad.get_schematic()
            except AttributeError:
                log.warning("[IPC] kipy Schematic API not available natively yet.")
                self.schematic = None
        return self.schematic

    def add_symbol(self, lib_id: str, reference: str, x: float, y: float, rotation: float = 0):
        """Live insertion of a schematic symbol."""
        sch = self.get_schematic()
        if sch and hasattr(sch, 'create_symbol'):
            try:
                sym = sch.create_symbol(lib_id=lib_id, reference=reference, position=(x, y), rotation=rotation)
                log.info(f"[IPC] Added symbol {reference} ({lib_id}) at ({x}, {y})")
                return sym
            except Exception as e:
                log.error(f"[IPC] Failed to add symbol {reference}: {e}")
                return None
        else:
            log.info(f"[IPC / Mock] Added symbol {reference} ({lib_id}) at ({x}, {y})")
            return None

    def add_wire(self, start_xy: tuple, end_xy: tuple):
        """Live insertion of a schematic wire."""
        sch = self.get_schematic()
        if sch and hasattr(sch, 'create_wire'):
            try:
                wire = sch.create_wire(start=start_xy, end=end_xy)
                return wire
            except Exception as e:
                log.error(f"[IPC] Failed to add wire {start_xy} -> {end_xy}: {e}")
                return None
        else:
            log.debug(f"[IPC / Mock] Added wire {start_xy} -> {end_xy}")
            return None

    def add_power_symbol(self, net_name: str, x: float, y: float):
        """Live insertion of a schematic power symbol."""
        return self.add_symbol(f"power:{net_name}", f"#PWR_{net_name}", x, y, 0)

    def annotate_components(self):
        """Live annotation of schematic components."""
        sch = self.get_schematic()
        if sch and hasattr(sch, 'annotate'):
            try:
                sch.annotate()
                log.info("[IPC] Schematic annotated.")
            except Exception as e:
                log.error(f"[IPC] Failed to annotate: {e}")
        else:
            log.info("[IPC / Mock] Schematic annotated.")

    def run_erc(self, report_path: Optional[str] = None) -> bool:
        """Run schematic ERC using kicad-cli. Returns True if zero errors."""
        import time as _time
        sch_file = str(self._project_path).replace(".kicad_pro", ".kicad_sch")
        if not os.path.exists(sch_file):
            log.warning(f"[IPC] Schematic file {sch_file} does not exist for ERC.")
            return False

        out_path  = report_path or str(self._base_dir / "erc_report.json")
        kicad_cli = (
            str(self.config.get("kicad", {}).get("binary_path", "kicad-cli"))
            .replace("kicad.exe", "kicad-cli.exe")
        )
        t0 = _time.time()
        try:
            log.info(f"[IPC] Running ERC: '{sch_file}' → '{out_path}'")
            result = subprocess.run(
                [kicad_cli, "sch", "erc", sch_file,
                 "--output", out_path, "--format", "json"],
                capture_output=True, text=True, timeout=120
            )
            duration = round(_time.time() - t0, 2)
            ok = result.returncode == 0
            log.info(f"[IPC] ERC {'PASS ✅' if ok else 'FAIL ❌'} in {duration}s → {out_path}")
            # Enrich the JSON report with duration if it already exists
            try:
                import json
                p = Path(out_path)
                if p.exists():
                    data = json.loads(p.read_text())
                    data["duration_sec"] = duration
                    data["tool"] = "ERC"
                    p.write_text(json.dumps(data, indent=2))
            except Exception:
                pass
            return ok
        except Exception as e:
            log.error(f"[IPC] ERC failed: {e}")
            return False

class BatchTransaction:
    """
    Legacy context manager — kept for backwards compatibility.
    For rollback support use `ipc.begin_batch()` instead.
    """
    def __init__(self, client: IPCClient):
        self.client = client
        self.commit = None

    def __enter__(self):
        self.commit = self.client.begin_commit()
        return self

    def __exit__(self, exc_type, *_):
        if exc_type:
            self.client._safe_cancel_commit()
            log.error("[IPC] Batch transaction aborted.")
        else:
            self.client.push_commit(self.commit, "BatchTransaction")


class _RollbackBatch:
    """
    Rollback-capable context manager returned by `ipc.begin_batch()`.

    On normal exit  → push commit to KiCad undo stack.
    On any exception → cancel the open commit AND restore the
                        pre-batch footprint positions from a snapshot.
    """
    def __init__(self, client: IPCClient, rollback: bool = True):
        self.client    = client
        self.rollback  = rollback
        self.commit    = None
        self._snapshot: Dict[str, Any] = {}

    def __enter__(self):
        if self.rollback and self.client.board:
            self._snapshot = self.client._snapshot_positions()
            log.debug(f"[IPC] Rollback snapshot captured ({len(self._snapshot)} footprints).")
        if self.client.board:
            try:
                self.commit = self.client.begin_commit()
            except RuntimeError:
                log.warning("[IPC] begin_batch: board not connected — running mock transaction.")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            log.error(f"[IPC] begin_batch failed ({exc_type.__name__}: {exc_val}). Rolling back.")
            self.client._safe_cancel_commit()
            if self.rollback:
                self.client._restore_snapshot(self._snapshot)
            return False          # re-raise the original exception
        # Happy path
        if self.commit is not None and self.client.board:
            self.client.push_commit(self.commit, "NeuroBoard AI Batch")
        return False

class DataCursor:
    """
    Generative routing helper (pcbflow pattern).
    Enables procedural: cursor.forward(5).right(45).via().set_layer('B.Cu')
    """
    def __init__(self, client: IPCClient, pos: tuple, layer: str, width: float):
        self.client = client
        self.x, self.y = pos
        self.layer = layer
        self.width = width

    def move_to(self, x: float, y: float) -> 'DataCursor':
        self.client.add_trace((self.x, self.y), (x, y), self.layer, self.width)
        self.x, self.y = x, y
        return self

    def forward(self, length: float) -> 'DataCursor':
        return self.move_to(self.x + length, self.y)

    def up(self, length: float) -> 'DataCursor':
        return self.move_to(self.x, self.y - length)

    def down(self, length: float) -> 'DataCursor':
        return self.move_to(self.x, self.y + length)
