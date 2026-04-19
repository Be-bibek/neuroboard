"""
api/ipc_routes.py — Phase 8.3: Net Connection Engine
Execution order per module:
  1. Collect all required_nets across the resolved sequence
  2. Create every unique net once
  3. Place each footprint
  4. Wire every pin in the footprint's pin_map to its net
"""

import sys
import os
import asyncio

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from system.intent_resolver import IntentResolver
from system.module_registry import MODULES
from system.ipc_kicad import KiCadIPC
from fastapi import APIRouter
from pydantic import BaseModel
from typing import List

router = APIRouter()

# Shared list of active WebSocket connections — populated by server.py's ws_sync endpoint
active_ws_connections: List = []


# ── Internal broadcaster ───────────────────────────────────────────────────

async def _broadcast(event_type: str, message: str, extra: dict | None = None):
    """
    Send a typed event to every connected frontend WebSocket client.
    event_type: EXECUTION_STATUS | DELTA_UPDATE | NET_CREATED | NET_CONNECTED
    """
    if not active_ws_connections:
        return
    payload = {"type": event_type, "payload": {"message": message, **(extra or {})}}
    dead = []
    for ws in active_ws_connections:
        try:
            await ws.send_json(payload)
        except Exception:
            dead.append(ws)
    for ws in dead:
        active_ws_connections.remove(ws)


# ── Request model ──────────────────────────────────────────────────────────

class DirectModuleRequest(BaseModel):
    module: str


# ── Main endpoint ──────────────────────────────────────────────────────────

@router.post("/api/v1/pcb/add_module")
async def add_module_direct(req: DirectModuleRequest):
    """
    Phase 8.3 — Full circuit generation for a module intent.
    
    Steps:
      1. Resolve dependency tree
      2. Collect + deduplicate all required nets
      3. Create every net via IPC
      4. Place every footprint via IPC
      5. Wire every pin via IPC (connect_pin for each entry in pin_map)
      6. Emit WS events at each step
    """
    ipc = KiCadIPC()

    # ── Step 1: Resolve dependency tree ───────────────────────────────────
    resolver = IntentResolver()
    execution_list = resolver.resolve([req.module])
    await _broadcast("EXECUTION_STATUS",
                     f"Resolved: {' -> '.join(execution_list)}",
                     {"sequence": execution_list})

    # ── Step 2: Collect all required nets (deduplicated, ordered) ─────────
    all_nets: list[str] = []
    seen_nets: set[str] = set()
    for mod_name in execution_list:
        mod = MODULES.get(mod_name, {})
        for net in mod.get("required_nets", []):
            if net not in seen_nets:
                all_nets.append(net)
                seen_nets.add(net)

    # ── Step 3: Create every net ──────────────────────────────────────────
    net_results = []
    for net_name in all_nets:
        await _broadcast("EXECUTION_STATUS", f"Creating net: {net_name}")
        ok = ipc.create_net(net_name)
        status = "created" if ok else "warn"
        net_results.append({"net": net_name, "status": status})
        await _broadcast(
            "NET_CREATED",
            f"Net {net_name} {status}",
            {"net": net_name, "status": status},
        )

    # ── Step 4 & 5: Place components then wire pins ───────────────────────
    placement_results = []
    cursor_x = 20.0
    cursor_y = 20.0
    x_step   = 30.0   # mm between components horizontally

    for mod_name in execution_list:
        mod = MODULES.get(mod_name)
        if not mod:
            placement_results.append({
                "module": mod_name, "status": "failed",
                "reason": "Not found in MODULES registry",
                "net_connections": []
            })
            await _broadcast("EXECUTION_STATUS", f"SKIP {mod_name}: not in registry")
            continue

        ref_des = f"{mod_name}_1"
        footprint = mod["footprint"]

        # -- Place --
        await _broadcast("EXECUTION_STATUS", f"Placing {mod_name} ({ref_des})...")
        placed = ipc.place_component(
            component_id=footprint,
            ref_des=ref_des,
            x=cursor_x,
            y=cursor_y,
        )

        if placed:
            await _broadcast(
                "DELTA_UPDATE",
                f"COMPONENT_ADD: {ref_des} at ({cursor_x}, {cursor_y})",
                {"ref": ref_des, "x": cursor_x, "y": cursor_y},
            )
        else:
            await _broadcast("EXECUTION_STATUS", f"WARN: could not confirm placement of {ref_des}")

        # -- Wire pins --
        pin_map = mod.get("pin_map", {})
        wire_results = []

        if pin_map:
            await _broadcast("EXECUTION_STATUS",
                             f"Wiring {len(pin_map)} pins for {ref_des}...")
            raw_results = ipc.wire_module(ref_des, pin_map)
            for r in raw_results:
                wire_results.append(r)
                await _broadcast(
                    "NET_CONNECTED",
                    f"{ref_des}.{r['pad']} -> {r['net']} ({r['status']})",
                    {"ref": ref_des, "pad": r["pad"], "net": r["net"], "status": r["status"]},
                )
        else:
            await _broadcast("EXECUTION_STATUS",
                             f"No pin_map for {mod_name} — skipping pin wiring")

        placement_results.append({
            "module": mod_name,
            "status": "success" if placed else "warn",
            "placed_at": [cursor_x, cursor_y],
            "net_connections": wire_results,
        })
        cursor_x += x_step

    await _broadcast("EXECUTION_STATUS", "Circuit generation complete.")

    return {
        "status": "completed",
        "intent": req.module,
        "resolved_sequence": execution_list,
        "nets_created": net_results,
        "execution_results": placement_results,
    }
