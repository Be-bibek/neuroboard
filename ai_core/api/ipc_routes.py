import sys
import os

# Expose system imports for NeuroBoard Phase 8.2 (Modular IPC Setup)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from system.intent_resolver import IntentResolver
from system.module_registry import MODULES
from system.ipc_kicad import KiCadIPC
from fastapi import APIRouter
from pydantic import BaseModel
from typing import List
import asyncio

router = APIRouter()

# ── WebSocket broadcast registry ───────────────────────────────────────────
# server.py populates this with active WebSocket connections
active_ws_connections: List = []

class DirectModuleRequest(BaseModel):
    module: str


async def _broadcast(event_type: str, message: str):
    """Broadcast a status event to all connected frontend WebSocket clients."""
    if not active_ws_connections:
        return
    payload = {"type": event_type, "payload": {"message": message}}
    dead = []
    for ws in active_ws_connections:
        try:
            await ws.send_json(payload)
        except Exception:
            dead.append(ws)
    for ws in dead:
        active_ws_connections.remove(ws)


@router.post("/api/v1/pcb/add_module")
async def add_module_direct(req: DirectModuleRequest):
    """
    Phase 8.2 API: Receives a raw Intent to add a high-level module (e.g. "NVME_SLOT").
    Resolves dependency prerequisite sequence natively, and executes HTTP-IPC calls to place them.
    Broadcasts real-time EXECUTION_STATUS events to any connected WebSocket clients.
    """
    resolver = IntentResolver()
    execution_list = resolver.resolve([req.module])

    await _broadcast("EXECUTION_STATUS", f"Resolved: {' -> '.join(execution_list)}")

    ipc = KiCadIPC()
    results = []

    # Grid-based placement cursor — keeps components from overlapping
    cursor_x = 20.0
    cursor_y = 20.0

    for mod_name in execution_list:
        await _broadcast("EXECUTION_STATUS", f"Placing {mod_name}...")

        if mod_name not in MODULES:
            results.append({"module": mod_name, "status": "failed", "reason": "Missing in MODULES registry."})
            await _broadcast("EXECUTION_STATUS", f"FAILED {mod_name}: not in registry")
            continue

        mod_data = MODULES[mod_name]
        res = ipc.place_component(
            component_id=mod_data["footprint"],
            ref_des=f"{mod_name}_1",
            x=cursor_x,
            y=cursor_y
        )

        if res:
            results.append({"module": mod_name, "status": "success", "placed_at": [cursor_x, cursor_y]})
            await _broadcast("DELTA_UPDATE", f"COMPONENT_ADD: {mod_name}_1 at ({cursor_x}, {cursor_y})")
            cursor_x += 30.0  # shift cursor right for next component
        else:
            results.append({"module": mod_name, "status": "failed", "reason": "IPC proxy returned no response."})
            await _broadcast("EXECUTION_STATUS", f"FAILED {mod_name}: IPC error")

    await _broadcast("EXECUTION_STATUS", "Module placement sequence complete.")

    return {
        "status": "completed",
        "intent": req.module,
        "resolved_sequence": execution_list,
        "execution_results": results
    }
