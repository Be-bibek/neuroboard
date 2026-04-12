"""
ai_core/system/execution_mode.py
==================================
Phase 8.1: Execution Mode Enum & Environment Probe

Defines the three execution modes for NeuroBoard:
  - IPC        → KiCad 10 is running with api.sock; all edits are live.
  - HEADLESS   → KiCad CLI available but no interactive UI.
  - SIMULATION → No KiCad; all IPC calls are mocked and logged.
"""

from __future__ import annotations

import os
import logging
from enum import Enum, auto
from pathlib import Path
from typing import Optional

log = logging.getLogger("SystemLogger")


# ---------------------------------------------------------------------------
# ExecutionMode Enum
# ---------------------------------------------------------------------------

class ExecutionMode(Enum):
    """Defines the operational mode for all IPC-dependent subsystems."""
    IPC        = "ipc"        # Live KiCad IPC socket available
    HEADLESS   = "headless"   # kicad-cli available, no GUI
    SIMULATION = "simulation" # No KiCad; full mock mode

    def is_live(self) -> bool:
        """Returns True if actual KiCad interaction is possible."""
        return self in (ExecutionMode.IPC, ExecutionMode.HEADLESS)

    def __str__(self) -> str:
        return self.value.upper()


# ---------------------------------------------------------------------------
# EnvironmentProbe — auto-detect best mode
# ---------------------------------------------------------------------------

class EnvironmentProbe:
    """
    Inspects the runtime environment and recommends the best ExecutionMode.

    Order of preference:
        1. IPC        — if api.sock is present and kipy is importable.
        2. HEADLESS   — if kicad-cli is on PATH.
        3. SIMULATION — fallback.
    """

    DEFAULT_SOCKET_PATH = r"C:\Users\Bibek\AppData\Local\Temp\kicad\api.sock"

    @classmethod
    def detect(cls,
               socket_path: Optional[str] = None,
               kicad_cli_path: Optional[str] = None) -> ExecutionMode:
        """
        Auto-detect and return the best ExecutionMode.
        """
        sock = Path(socket_path or cls.DEFAULT_SOCKET_PATH)

        # 1. IPC mode: socket must exist AND kipy must be importable
        if sock.exists():
            try:
                import kipy  # type: ignore  # noqa: F401
                log.info(f"[EnvProbe] IPC socket found at {sock}. Mode: IPC")
                return ExecutionMode.IPC
            except ImportError:
                log.warning("[EnvProbe] api.sock exists but kipy is not installed. Downgrading to HEADLESS.")

        # 2. HEADLESS mode: kicad-cli on PATH
        cli = cls._find_kicad_cli(kicad_cli_path)
        if cli:
            log.info(f"[EnvProbe] kicad-cli found at '{cli}'. Mode: HEADLESS")
            return ExecutionMode.HEADLESS

        # 3. SIMULATION fallback
        log.warning("[EnvProbe] No KiCad found. Mode: SIMULATION (mock only)")
        return ExecutionMode.SIMULATION

    @staticmethod
    def _find_kicad_cli(hint: Optional[str] = None) -> Optional[str]:
        """Check common locations for kicad-cli."""
        import shutil
        candidates = [
            hint,
            r"C:\Program Files\KiCad\10.0\bin\kicad-cli.exe",
            r"C:\Program Files\KiCad\9.0\bin\kicad-cli.exe",
            "kicad-cli",
        ]
        for c in candidates:
            if c and shutil.which(c):
                return c
        return None

    @classmethod
    def describe(cls, mode: ExecutionMode) -> str:
        """Human-readable description for logging."""
        descriptions = {
            ExecutionMode.IPC:        "Live KiCad 10 IPC (api.sock connected)",
            ExecutionMode.HEADLESS:   "KiCad CLI available (kicad-cli on PATH)",
            ExecutionMode.SIMULATION: "Simulation / Mock mode (no KiCad)",
        }
        return descriptions[mode]
