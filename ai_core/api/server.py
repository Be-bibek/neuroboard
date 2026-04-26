"""
ai_core/api/server.py
======================
NeuroBoard FastAPI Backend — Phase 5 (Copilot Intelligence)

Endpoints
---------
POST /api/v1/copilot/prompt         → parse NLP + suggest components (Stage 1+2)
POST /api/v1/copilot/confirm        → confirm BOM + generate netlist (Stage 3+4+5)
POST /api/v1/pipeline/run           → run full Phase 2 placement + routing + validation
GET  /api/v1/validation/report      → latest JSON validation report
GET  /api/v1/board/state            → live KiCad IPC state (REST snapshot)
WS   /api/v1/live_stream            → real-time KiCad board state (WebSocket)
"""

import os
import sys
import json
import logging
import asyncio
import uvicorn
from pathlib import Path

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Any, Dict, List, Optional

# ── Resolve imports regardless of CWD ─────────────────────────────────────
_AI_CORE = Path(__file__).resolve().parent.parent
if str(_AI_CORE) not in sys.path:
    sys.path.insert(0, str(_AI_CORE))

log = logging.getLogger("SystemLogger")
if not log.handlers:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s │ %(message)s")

# ── App ────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="NeuroBoard Copilot API",
    version="5.0",
    description="AI-native PCB design backend for the Tauri Copilot frontend",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from api.ipc_routes import router as ipc_router, active_ws_connections
app.include_router(ipc_router)

# ── Lazy-load heavy modules (avoids import errors if deps missing) ─────────
_pipeline      = None
_orchestrator  = None
_ipc           = None


def _get_pipeline():
    global _pipeline
    if _pipeline is None:
        from copilot.pipeline import CopilotPipeline
        _pipeline = CopilotPipeline()
    return _pipeline


def _get_orchestrator():
    global _orchestrator
    if _orchestrator is None:
        from system.orchestrator import CompilerOrchestrator
        _orchestrator = CompilerOrchestrator()
    return _orchestrator


def _get_ipc():
    global _ipc
    if _ipc is None:
        from system.ipc_client import IPCClient
        _ipc = IPCClient()
    return _ipc


# ── Pydantic models ────────────────────────────────────────────────────────

class CopilotPromptRequest(BaseModel):
    intent: str

class CopilotConfirmRequest(BaseModel):
    """
    Sent by the frontend when the user approves the component list.
    Includes the internal spec + manifest returned from /copilot/prompt.
    """
    spec: Dict[str, Any]
    manifest: Dict[str, Any]
    netlist_path: Optional[str] = None

class PipelineRunRequest(BaseModel):
    force_sim: bool = False

class LcscFetchRequest(BaseModel):
    lcsc_number: str

class SchematicBuildRequest(BaseModel):
    module_class: str = "PiHatModule"
    manifest_path: Optional[str] = None

class AddModuleRequest(BaseModel):
    module_class: str
    name: str
    config: Optional[Dict[str, Any]] = None

# ═══════════════════════════════════════════════════════════════════════════
#  COPILOT ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════

@app.post("/api/v1/copilot/prompt")
async def copilot_prompt(req: CopilotPromptRequest):
    """
    Stage 1+2: Parse user intent → return structured spec + component suggestions.
    Fast (~50ms). No schematic generation yet — just shows what will be built.
    """
    try:
        result = _get_pipeline().parse_and_suggest(req.intent)
        return result
    except Exception as e:
        log.error(f"[API] /copilot/prompt error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

from fastapi.responses import StreamingResponse
import time

@app.get("/api/v1/agent/run")
async def run_agent(intent: str):
    """
    Runs the LangGraph autonomous agent loop and streams events via Server-Sent Events (SSE).
    """
    from agent.langgraph_loop import build_agent_graph
    
    agent = build_agent_graph()
    if not agent:
        raise HTTPException(status_code=500, detail="LangGraph not available")
        
    async def event_stream():
        initial_state = {"intent": intent, "retries": 0, "drc_errors": []}
        try:
            # invoke() is synchronous. For a real stream, we'd use stream() 
            # But since it might block the thread, we will yield steps manually or use stream if available
            for event in agent.stream(initial_state):
                for node_name, state_update in event.items():
                    data = json.dumps({"node": node_name, "state": state_update})
                    yield f"data: {data}\n\n"
                    await asyncio.sleep(0.5) # Slight delay for UI effect
            yield f"data: {json.dumps({'node': 'END', 'status': 'completed'})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'node': 'ERROR', 'error': str(e)})}\n\n"
            
    return StreamingResponse(event_stream(), media_type="text/event-stream")


@app.post("/api/v1/copilot/confirm")
async def copilot_confirm(req: CopilotConfirmRequest, background_tasks: BackgroundTasks):
    """
    Stage 3+4+5: User confirmed the BOM.
    Fetch libraries → generate SKiDL netlist → validate connectivity.
    Runs synchronously (may take a few seconds for SKiDL).
    """
    try:
        result = _get_pipeline().confirm_and_generate(
            spec=req.spec,
            manifest=req.manifest,
            netlist_path=req.netlist_path or "pi_hat.net",
        )
        return result
    except Exception as e:
        log.error(f"[API] /copilot/confirm error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ═══════════════════════════════════════════════════════════════════════════
#  PIPELINE (Placement + Routing + Validation)
# ═══════════════════════════════════════════════════════════════════════════

@app.post("/api/v1/pipeline/run")
async def run_full_pipeline(req: PipelineRunRequest):
    """
    Phase 2 full pipeline: Placement → Routing → SI/PDN/DRC Validation.
    Requires a netlist to be present (run /copilot/confirm first).
    """
    try:
        report = _get_orchestrator().run_full_pipeline()
        return {"status": "success", "report": report}
    except Exception as e:
        log.error(f"[API] /pipeline/run error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/schematic/build")
async def build_schematic(req: SchematicBuildRequest):
    """
    Phase 8.1 API: Trigger the live schematic builder pipeline via IPC.
    """
    try:
        report = _get_orchestrator().build_live_schematic(
            module_class=req.module_class,
            manifest_path=req.manifest_path
        )
        return {"status": "success", "report": report}
    except Exception as e:
        log.error(f"[API] /schematic/build error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/schematic/add_module")
async def add_module(req: AddModuleRequest):
    """
    Phase 8.1 API: Dynamically inject a specific NeuroModule into the live project.
    """
    try:
        report = _get_orchestrator().build_live_schematic(module_class=req.module_class)
        return {"status": "success", "report": report}
    except Exception as e:
        log.error(f"[API] /schematic/add_module error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/library/fetch_lcsc")
async def fetch_lcsc_part(req: LcscFetchRequest):
    """
    Phase 8.1 API: Fetch footprint and symbol dynamically from LCSC using JLC2KiCadLib.
    """
    try:
        from system.lcsc_fetcher import LcscFetcher
        fetcher = LcscFetcher()
        res = fetcher.fetch_component(req.lcsc_number)
        if res["status"] != "success":
            raise Exception(res.get("error", "Unknown error fetching part"))
        return res
    except Exception as e:
        log.error(f"[API] /library/fetch_lcsc error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ═══════════════════════════════════════════════════════════════════════════
#  BOARD STATE & VALIDATION REPORT
# ═══════════════════════════════════════════════════════════════════════════

@app.get("/api/v1/board/state")
def get_board_state():
    """REST snapshot of current KiCad IPC board state."""
    try:
        ipc = _get_ipc()
        if not ipc.board:
            ipc.connect()
        return {"status": "success", "state": ipc.get_board_state()}
    except Exception as e:
        log.warning(f"[API] Board state unavailable (KiCad may be closed): {e}")
        return {"status": "ipc_offline", "state": {}}


@app.get("/api/v1/validation/report")
def get_validation_report():
    """Returns the latest neuroboard_validation.json report."""
    paths = [
        Path("reports/neuroboard_validation.json"),
        Path("reports/pi_hat_validation_report.json"),
        Path(__file__).parent.parent.parent / "reports" / "neuroboard_validation.json",
    ]
    for p in paths:
        if p.exists():
            try:
                return json.loads(p.read_text())
            except Exception:
                pass
    raise HTTPException(status_code=404, detail="No validation report found. Run the pipeline first.")


# ═══════════════════════════════════════════════════════════════════════════
#  WEBSOCKET — Live Digital Twin
# ═══════════════════════════════════════════════════════════════════════════

@app.websocket("/ws/sync")
async def ws_sync(websocket: WebSocket):
    """
    Phase 8.2 Sync WebSocket expected by the frontend syncEngine.ts.
    Streams EXECUTION_STATUS and DELTA_UPDATE events in real-time.
    """
    await websocket.accept()
    active_ws_connections.append(websocket)
    log.info(f"[WS/sync] Frontend connected. Total: {len(active_ws_connections)}")
    try:
        while True:
            # Push a heartbeat board state every 2s so the UI stays alive
            try:
                ipc = _get_ipc()
                if not ipc.board:
                    ipc.connect()
                state = ipc.get_board_state()
                comp_count = len(state.get("components", []))
                net_count = len(state.get("nets", []))
            except Exception:
                comp_count, net_count = 0, 0

            await websocket.send_json({
                "type": "PCB_STATE_UPDATE",
                "payload": {"component_count": comp_count, "net_count": net_count}
            })
            await asyncio.sleep(2.0)
    except WebSocketDisconnect:
        log.info("[WS/sync] Frontend disconnected")
    except Exception as e:
        log.error(f"[WS/sync] Error: {e}")
    finally:
        if websocket in active_ws_connections:
            active_ws_connections.remove(websocket)


@app.websocket("/api/v1/live_stream")
async def live_stream(websocket: WebSocket):
    """
    Streams live KiCad IPC board state at 1 Hz.
    Falls back to empty state if KiCad is offline.
    """
    await websocket.accept()
    log.info("[WS] Digital Twin viewer connected")
    try:
        ipc = _get_ipc()
        while True:
            try:
                if not ipc.board:
                    ipc.connect()
                state = ipc.get_board_state()
            except Exception:
                state = {}
            await websocket.send_json({"type": "board_update", "state": state})
            await asyncio.sleep(1.0)
    except WebSocketDisconnect:
        log.info("[WS] Digital Twin viewer disconnected")
    except Exception as e:
        log.error(f"[WS] Unexpected error: {e}")


# ═══════════════════════════════════════════════════════════════════════════
#  Healthcheck
# ═══════════════════════════════════════════════════════════════════════════

@app.get("/api/v1/health")
def health():
    return {"status": "ok", "version": "5.0", "service": "NeuroBoard Copilot API"}


# ── Entry ──────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info")
