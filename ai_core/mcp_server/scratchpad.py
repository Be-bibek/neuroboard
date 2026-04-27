"""
ai_core/mcp_server/scratchpad.py
==================================
PILLAR 1 — The Scratchpad Engine

Exposes execute_engineering_script as an MCP tool.
The LLM writes raw Python → we execute it → we return stdout/stderr.
The Reflection Loop (Pillar 3) reads the result and retries on failure.
"""

import subprocess
import tempfile
import textwrap
import logging
import sys
from pathlib import Path
from typing import Dict, Any

from mcp.server.fastmcp import FastMCP

log = logging.getLogger("Scratchpad")

# The Python interpreter that has kipy installed
KIPY_PYTHON = sys.executable

# Allowed imports — safety whitelist
SAFE_IMPORTS = {
    "kipy", "kipy.board_types", "kipy.geometry", "kipy.util.units",
    "math", "json", "os.path", "pathlib", "re", "sys",
    "typing", "collections", "itertools",
}

mcp = FastMCP("NeuroBoard-Scratchpad")

SCRIPT_HEADER = textwrap.dedent("""\
import sys
sys.path.insert(0, r'C:\\Users\\Bibek\\Documents\\KiCad\\10.0\\3rdparty\\Python311\\site-packages')
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

""")


@mcp.tool()
def execute_engineering_script(script_code: str, description: str = "") -> Dict[str, Any]:
    """
    Execute a dynamically generated Python script against the live KiCad board.

    The script has full access to:
    - board (KiCad board object)
    - get_footprint(ref) helper
    - get_net(name) helper
    - all kipy bindings (Track, Via, Zone, Vector2, etc.)
    - math, json, re

    Every board mutation MUST use board.begin_commit() / board.push_commit().
    Returns stdout, stderr, exit_code, and status string.
    """
    if description:
        log.info(f"[Scratchpad] Running: {description}")

    full_script = SCRIPT_HEADER + "\n# ── USER SCRIPT ──────────────────────────────\n" + script_code

    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".py",
            prefix="neuro_fix_",
            dir=Path(__file__).resolve().parent.parent / "scratch",
            delete=False,
            encoding="utf-8",
        ) as f:
            f.write(full_script)
            script_path = f.name

        result = subprocess.run(
            [KIPY_PYTHON, script_path],
            capture_output=True,
            text=True,
            timeout=30,
            encoding="utf-8",
            errors="replace",
        )

        status = "success" if result.returncode == 0 else "failed"
        log.info(f"[Scratchpad] {status.upper()} (exit {result.returncode})")

        if result.returncode != 0:
            log.warning(f"[Scratchpad] stderr: {result.stderr[:300]}")

        return {
            "status":    status,
            "stdout":    result.stdout.strip(),
            "stderr":    result.stderr.strip(),
            "exit_code": result.returncode,
            "script_path": script_path,
        }

    except subprocess.TimeoutExpired:
        return {"status": "failed", "stderr": "Script timed out (30s limit)", "stdout": "", "exit_code": -1}
    except Exception as e:
        return {"status": "failed", "stderr": str(e), "stdout": "", "exit_code": -1}


@mcp.tool()
def read_board_state() -> Dict[str, Any]:
    """
    Lightweight board state reader — returns footprints with positions,
    net count, and layer count. Safe read-only call.
    """
    try:
        script = textwrap.dedent("""\
        fps = []
        for fp in board.get_footprints():
            try:
                ref = fp.reference_field.text.value
                fps.append({"ref": ref, "x": fp.position.x / NM, "y": fp.position.y / NM, "rot": fp.orientation.degrees})
            except Exception:
                pass
        nets = [n.name for n in board.get_nets() if n.name]
        import json
        print(json.dumps({"footprints": fps, "nets": nets, "layer_count": board.get_copper_layer_count()}))
        """)
        result = execute_engineering_script(script, "Read board state")
        if result["status"] == "success":
            import json
            return json.loads(result["stdout"])
        return {"error": result["stderr"]}
    except Exception as e:
        return {"error": str(e)}


if __name__ == "__main__":
    mcp.run()
