"""
ai_core/system/state_manager.py
================================
Phase 8.1 Enhancement 6: Delta-Based Design State Manager

Implements a complete event-driven state synchronization engine:
  - DesignSnapshot  — immutable board position record
  - DesignDelta     — typed change record (MOVE / ADD / DELETE / NET_EDIT)
  - DeltaAnalyzer   — compares two snapshots and emits typed deltas
  - LiveStateManager — orchestrates polling, caching, and ERC triggers
"""

from __future__ import annotations

import json
import logging
import os
import threading
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from typing import Callable, Dict, List, Optional, Set, Tuple

import shapely.geometry as geom

log = logging.getLogger("SystemLogger")


# ---------------------------------------------------------------------------
# Data Types
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ComponentState:
    """Immutable record of a single component's position on the board."""
    ref: str
    x:   float    # mm
    y:   float    # mm
    rot: float = 0.0  # degrees
    layer: str = "F.Cu"


class DeltaType(Enum):
    MANUAL_MOVE   = "MANUAL_MOVE"    # Component moved by ≥ threshold
    USER_ADD      = "USER_ADD"       # Ref appeared in live state but not in cache
    USER_DELETE   = "USER_DELETE"    # Ref present in cache but gone from live state
    NET_EDIT      = "NET_EDIT"       # Net list change detected (schematic only)


@dataclass
class DesignDelta:
    """A single typed change detected between two snapshots."""
    delta_type:  DeltaType
    ref:         str
    before:      Optional[ComponentState] = None
    after:       Optional[ComponentState] = None
    timestamp:   str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict:
        d = asdict(self)
        d["delta_type"] = self.delta_type.value
        return d

    def __str__(self) -> str:
        if self.delta_type == DeltaType.MANUAL_MOVE:
            dx = round((self.after.x - self.before.x), 3)
            dy = round((self.after.y - self.before.y), 3)
            return f"[MOVE] {self.ref}: Δ({dx:+.3f}, {dy:+.3f}) mm"
        if self.delta_type == DeltaType.USER_ADD:
            return f"[ADD]  {self.ref} at ({self.after.x:.2f}, {self.after.y:.2f})"
        if self.delta_type == DeltaType.USER_DELETE:
            return f"[DEL]  {self.ref} removed from ({self.before.x:.2f}, {self.before.y:.2f})"
        return f"[{self.delta_type.value}] {self.ref}"


Snapshot = Dict[str, ComponentState]


# ---------------------------------------------------------------------------
# DeltaAnalyzer
# ---------------------------------------------------------------------------

class DeltaAnalyzer:
    """
    Compares two Snapshot dicts and returns a list of typed DesignDeltas.

    Args:
        move_threshold_mm: Minimum distance (mm) to classify as a manual move.
    """

    def __init__(self, move_threshold_mm: float = 0.1):
        self.threshold = move_threshold_mm

    def diff(self, old: Snapshot, new: Snapshot) -> List[DesignDelta]:
        deltas: List[DesignDelta] = []

        old_refs: Set[str] = set(old)
        new_refs: Set[str] = set(new)

        # 1. MOVE — ref in both but position changed
        for ref in old_refs & new_refs:
            o, n = old[ref], new[ref]
            dist = ((n.x - o.x) ** 2 + (n.y - o.y) ** 2) ** 0.5
            if dist > self.threshold:
                deltas.append(DesignDelta(
                    delta_type=DeltaType.MANUAL_MOVE,
                    ref=ref,
                    before=o,
                    after=n,
                ))

        # 2. USER_ADD — in new but not old
        for ref in new_refs - old_refs:
            deltas.append(DesignDelta(
                delta_type=DeltaType.USER_ADD,
                ref=ref,
                after=new[ref],
            ))

        # 3. USER_DELETE — in old but not new
        for ref in old_refs - new_refs:
            deltas.append(DesignDelta(
                delta_type=DeltaType.USER_DELETE,
                ref=ref,
                before=old[ref],
            ))

        return deltas


# ---------------------------------------------------------------------------
# LiveStateManager
# ---------------------------------------------------------------------------

class LiveStateManager:
    """
    Industrial-grade state manager for NeuroBoard using KiCad 10 IPC.

    Features:
    - Delta analysis with typed DesignDelta events
    - Event callbacks: register_on_delta(fn) → called on every detected change
    - Auto-ERC trigger on NET_EDIT events
    - Conflict detection between AI routes and user-moved components
    - Optional background polling thread
    """

    # Default IPC socket path
    _SOCKET = "ipc:///C:/Users/Bibek/AppData/Local/Temp/kicad/api.sock"

    def __init__(self,
                 move_threshold_mm: float = 0.1,
                 ipc_client=None):
        self.cache:        Snapshot = {}
        self.manual_edits: Dict[str, ComponentState] = {}
        self.last_deltas:  List[DesignDelta] = []
        self.analyzer      = DeltaAnalyzer(move_threshold_mm)
        self._callbacks:   List[Callable[[List[DesignDelta]], None]] = []
        self._ipc          = ipc_client   # optional pre-connected IPCClient
        self._poll_thread: Optional[threading.Thread] = None
        self._stop_event   = threading.Event()

    # ------------------------------------------------------------------
    # Callback registration
    # ------------------------------------------------------------------

    def register_on_delta(self, fn: Callable[[List[DesignDelta]], None]) -> None:
        """Register a callback to be invoked whenever deltas are detected."""
        self._callbacks.append(fn)

    def _fire(self, deltas: List[DesignDelta]) -> None:
        for cb in self._callbacks:
            try:
                cb(deltas)
            except Exception as e:
                log.warning(f"[LiveState] Callback error: {e}")

    # ------------------------------------------------------------------
    # IPC helpers
    # ------------------------------------------------------------------

    def fetch_live_state(self) -> Snapshot:
        """Pull current board state from running KiCad via IPC."""
        try:
            if self._ipc and self._ipc.board:
                board = self._ipc.board
            else:
                from kipy.kicad import KiCad  # type: ignore
                kicad = KiCad(socket_path=self._SOCKET)
                board = kicad.get_board()

            states: Snapshot = {}
            for fp in board.get_footprints():
                pos = fp.position
                ref = (fp.reference_field.text.value
                       if getattr(fp, 'reference_field', None) else "UNKNOWN")
                x_mm = pos.x / 1_000_000.0
                y_mm = pos.y / 1_000_000.0
                rot  = getattr(getattr(fp, 'orientation', None), 'degrees', 0.0)
                states[ref] = ComponentState(ref=ref, x=x_mm, y=y_mm, rot=rot)
            return states
        except Exception as e:
            log.debug(f"[LiveState] fetch_live_state: {e}")
            return {}

    # ------------------------------------------------------------------
    # Core sync / delta
    # ------------------------------------------------------------------

    def sync(self) -> List[DesignDelta]:
        """
        Fetch live board state, run delta analysis, fire callbacks.

        Returns:
            List of DesignDeltas since last sync. Empty list if no changes.
        """
        live = self.fetch_live_state()
        if not live:
            return []

        # First call — establish baseline
        if not self.cache:
            self.cache = live
            log.info(f"[LiveState] Baseline captured: {len(live)} components.")
            return []

        deltas = self.analyzer.diff(self.cache, live)
        self.cache = live

        if deltas:
            self.last_deltas = deltas
            for d in deltas:
                log.info(f"[LiveState] {d}")
                if d.delta_type == DeltaType.MANUAL_MOVE:
                    self.manual_edits[d.ref] = d.after
                elif d.delta_type == DeltaType.USER_ADD:
                    self.manual_edits[d.ref] = d.after
                elif d.delta_type == DeltaType.USER_DELETE:
                    self.manual_edits.pop(d.ref, None)
            self._fire(deltas)

        return deltas

    def sync_schematic(self, ipc_client) -> bool:
        """
        Phase 8.1 Hybrid Workflow: check for schematic-level changes.
        Triggers ERC only on net-level edits.
        """
        log.info("[DesignState] Checking for schematic edits...")
        sch = ipc_client.get_schematic()
        if not sch:
            return False

        try:
            has_edits = getattr(sch, 'has_unsaved_changes', lambda: False)()
            if has_edits:
                log.info("[DesignState] Schematic edit detected — triggering ERC.")
                from validation.report import ValidationReport
                report_path = os.path.join(
                    os.path.dirname(__file__), "..", "..", "reports", "auto_erc.json"
                )
                ok = ipc_client.run_erc(report_path)
                status = "PASS ✅" if ok else "FAIL ❌"
                log.info(f"[DesignState] Auto-ERC: {status}")

                # Emit a synthetic NET_EDIT delta for callbacks
                net_delta = DesignDelta(
                    delta_type=DeltaType.NET_EDIT,
                    ref="SCHEMATIC",
                )
                self.last_deltas.append(net_delta)
                self._fire([net_delta])
            return has_edits
        except Exception as e:
            log.debug(f"[DesignState] sync_schematic error: {e}")
            return False

    # ------------------------------------------------------------------
    # Cache management
    # ------------------------------------------------------------------

    def update_cache(self, ref: str, x: float, y: float,
                     rot: float = 0.0, layer: str = "F.Cu") -> None:
        """Update the AI-side cache after an AI-driven component placement."""
        self.cache[ref] = ComponentState(ref=ref, x=x, y=y, rot=rot, layer=layer)

    def get_manual_edits(self) -> List[DesignDelta]:
        """Return all deltas classified as human-originated."""
        return self.last_deltas

    # ------------------------------------------------------------------
    # Background polling
    # ------------------------------------------------------------------

    def start_polling(self, interval_sec: float = 2.0) -> None:
        """
        Start a background thread that calls sync() every `interval_sec`.
        Callbacks are fired on the background thread — keep them fast.
        """
        if self._poll_thread and self._poll_thread.is_alive():
            log.warning("[LiveState] Polling already running.")
            return
        self._stop_event.clear()
        self._poll_thread = threading.Thread(
            target=self._poll_loop,
            args=(interval_sec,),
            daemon=True,
            name="NeuroBoard-StatePoll"
        )
        self._poll_thread.start()
        log.info(f"[LiveState] Background polling started (interval={interval_sec}s).")

    def stop_polling(self) -> None:
        """Stop the background polling thread gracefully."""
        self._stop_event.set()
        if self._poll_thread:
            self._poll_thread.join(timeout=5.0)
        log.info("[LiveState] Background polling stopped.")

    def _poll_loop(self, interval_sec: float) -> None:
        import time
        while not self._stop_event.is_set():
            try:
                self.sync()
            except Exception as e:
                log.debug(f"[LiveState] Poll error: {e}")
            self._stop_event.wait(interval_sec)

    # ------------------------------------------------------------------
    # Conflict detection (unchanged — still useful)
    # ------------------------------------------------------------------

    def has_conflict(self,
                     trace_path: List[Tuple[float, float]],
                     clearance_mm: float = 3.0) -> bool:
        """
        Check if a planned AI route intersects with a recently-moved component.
        """
        if not self.manual_edits or len(trace_path) < 2:
            return False
        line = geom.LineString(trace_path)
        for ref, comp in self.manual_edits.items():
            pt = geom.Point(comp.x, comp.y)
            if line.distance(pt) < clearance_mm:
                log.warning(f"[LiveState] CONFLICT: route crosses manually-moved {ref}!")
                return True
        return False

    # ------------------------------------------------------------------
    # Legacy compat shims (route_trace_live, refresh_ui)
    # ------------------------------------------------------------------

    def route_trace_live(self, *args, **kwargs) -> None:
        """Stub — routing is now delegated to DataCursor / orchestrator."""
        pass

    def refresh_ui(self) -> None:
        """Stub — UI refresh is handled by IPCClient.refresh_ui()."""
        pass
