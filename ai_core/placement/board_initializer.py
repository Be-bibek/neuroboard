"""
ai_core/placement/board_initializer.py
========================================
Phase 8: Physical Board Initialization Agent

Responsibilities:
  - Draws board outlines on 'Edge.Cuts' layer.
  - Places "Anchored" components (Mounting Holes, GPIO Header) at deterministic coordinates.
  - Enforces hybrid sizing (100x100mm default for custom profiles).
  - Synchronizes placement metadata for downstream smart-placement.
"""

from __future__ import annotations

import logging
from typing import Dict, Any, List, Optional
from pathlib import Path

log = logging.getLogger("SystemLogger")

try:
    from kipy.board_types import BoardLayer, DrawSegment, Vector2
    KIPY_OK = True
except ImportError:
    KIPY_OK = False


class BoardInitializer:
    """
    Initializes a physical KiCad board from a validated design manifest.
    """

    def __init__(self, ipc_client):
        self.ipc = ipc_client

    def initialize(self, manifest: Dict[str, Any]) -> bool:
        """
        Full initialization sequence.
        """
        if not self.ipc.board:
            if not self.ipc.connect():
                log.warning("[BoardInit] IPC unavailable — skipping physical initialization.")
                return False

        constraints = manifest.get("constraints", {})
        profile_id  = constraints.get("profile", "custom")

        log.info(f"[BoardInit] Initializing board for profile: {profile_id}")

        commit = self.ipc.begin_commit()
        try:
            # 1. Draw Outline
            self._draw_outline(constraints)

            # 2. Place Anchored Components
            self._place_anchors(manifest)

            # 3. Synchronize Metadata
            self._sync_metadata(manifest)

            self.ipc.push_commit(commit, f"NeuroBoard Init: {profile_id}")
            log.info("[BoardInit] ✅ Initialization complete.")
            return True
        except Exception as e:
            log.error(f"[BoardInit] Fatal error: {e}")
            self.ipc._safe_cancel_commit()
            return False

    def _draw_outline(self, constraints: Dict[str, Any]):
        """
        Clears existing outlines and draws new boundaries on Edge.Cuts.
        Supports fixed (HAT+) and hybrid (custom 100x100) sizing.
        """
        if not KIPY_OK: return

        width  = constraints.get("board_width_mm") or 100.0
        height = constraints.get("board_height_mm") or 100.0

        log.info(f"[BoardInit] Drawing outline: {width}x{height} mm")

        # Clear existing Edge.Cuts
        # Note: kipy doesn't have a direct "delete all on layer" yet, 
        # so we iterate through drawings.
        try:
            drawings = list(self.ipc.board.get_drawings())
            for d in drawings:
                if d.layer == BoardLayer.BL_Edge_Cuts:
                    # TODO: Delete drawing if kipy supports it
                    pass
        except Exception:
            pass

        # Square outline
        pts = [
            (0, 0), (width, 0), (width, height), (0, height), (0, 0)
        ]
        segments = []
        for i in range(len(pts) - 1):
            seg = DrawSegment()
            seg.layer = BoardLayer.BL_Edge_Cuts
            seg.start = Vector2.from_xy_mm(*pts[i])
            seg.end   = Vector2.from_xy_mm(*pts[i+1])
            segments.append(seg)
        
        self.ipc.create_items(segments)

    def _place_anchors(self, manifest: Dict[str, Any]):
        """
        Place components defined with fixed positions in the profile.
        """
        if not KIPY_OK: return

        # Map current board footprints by reference
        fp_map = {fp.reference_field.text.value: fp 
                  for fp in self.ipc.board.get_footprints() 
                  if fp.reference_field}

        constraints = manifest.get("constraints", {})
        
        # 1. Mounting Holes
        hole_positions = constraints.get("mounting_holes", [])
        # Find MH footprints (often named H1, H2 or MH1...)
        hole_refs = sorted([r for r in fp_map if any(k in r.upper() for k in ["H", "MH", "HOLE"])])
        
        for i, pos in enumerate(hole_positions):
            if i < len(hole_refs):
                fp = fp_map[hole_refs[i]]
                fp.position = Vector2.from_xy_mm(pos["x"], pos["y"])
                log.info(f"[BoardInit] Anchor: {hole_refs[i]} → ({pos['x']}, {pos['y']})")

        # 2. GPIO Header (specific to HAT profiles)
        gpio_spec = constraints.get("gpio_header")
        if gpio_spec:
            # Find J1 or similar
            gpio_refs = [r for r in fp_map if any(k in r.upper() for k in ["J1", "GPIO"])]
            if gpio_refs:
                fp = fp_map[gpio_refs[0]]
                x, y = gpio_spec["pin1_x"], gpio_spec["pin1_y"]
                rot  = gpio_spec.get("orientation_deg", 0.0)
                fp.position = Vector2.from_xy_mm(x, y)
                fp.orientation.degrees = rot
                log.info(f"[BoardInit] Anchor: {gpio_refs[0]} → ({x}, {y})@{rot}°")

    def _sync_metadata(self, manifest: Dict[str, Any]):
        """
        Attaches placement hints and SI constraints to individual footprints.
        These are stored as Properties or Fields in KiCad for Phase 9 logic.
        """
        # TODO: Implement metadata attachment once kipy Field API is stable.
        # For now, we rely on the orchestrator keeping this meta in memory.
        pass
