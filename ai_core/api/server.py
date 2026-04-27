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

# ── Load environment variables from .env (must run before importing any ai modules)
from dotenv import load_dotenv
load_dotenv(dotenv_path=Path(__file__).resolve().parent.parent.parent / ".env")

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
#  PROJECT MANAGEMENT ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════

from system.project_manager import project_manager
from system.orchestrator import hub

class LoadProjectRequest(BaseModel):
    path: str

@app.get("/api/v1/projects")
def get_projects():
    """List all detected KiCad projects in the workspace."""
    return {"status": "success", "projects": project_manager.list_projects()}

@app.get("/api/v1/projects/active")
def get_active_project():
    """Return the currently loaded project."""
    active = project_manager.get_active_project()
    if active:
        return {"status": "success", "project": active}
    return {"status": "error", "message": "No active project"}

@app.post("/api/v1/projects/load")
def load_project(req: LoadProjectRequest):
    """Load a specific project and rebind KiCad IPC."""
    try:
        project_manager.load_project(req.path)
        # Re-bind IPC to the new active project
        hub.reconnect_kicad()
        return {"status": "success", "project": project_manager.get_active_project()}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/v1/projects/close")
def close_project():
    """Close the current project."""
    project_manager.close_project()
    return {"status": "success"}

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
async def run_agent(intent: str, contexts: str = ""):
    """
    Autonomous goal-driven agent — streams rich events via SSE.
    Events: status | plan | tool_selected | action | completed | error
    """
    from system.orchestrator import AgentSession, hub

    async def event_stream():
        session = AgentSession(session_id="live_ui_session", mcp_hub=hub)
        try:
            # Process with optional context tags from the UI (@board, @mem)
            async for event in session.process_intent(intent, contexts=contexts):
                evt_type = event.get("type")

                if evt_type == "status":
                    yield f"data: {json.dumps({'node': 'status', 'message': event['message'], 'model': event.get('model')})}\n\n"

                elif evt_type == "thought":
                    yield f"data: {json.dumps({'node': 'thought', 'content': event['content'], 'model': event.get('model')})}\n\n"

                elif evt_type == "plan":
                    yield f"data: {json.dumps({'node': 'planning', 'plan': event['plan'], 'message': event['message'], 'model': event.get('model')})}\n\n"

                elif evt_type == "tool_selected":
                    yield f"data: {json.dumps({'node': 'tool_selection', 'tool': event['tool'], 'action': event.get('action',''), 'message': event['message']})}\n\n"

                elif evt_type == "action":
                    yield f"data: {json.dumps({'node': 'execution', 'tool': event['tool'], 'status': event['status'], 'result': event.get('result'), 'message': event.get('message','')})}\n\n"

                elif evt_type == "completed":
                    yield f"data: {json.dumps({'node': 'END', 'status': 'completed', 'message': event['message']})}\n\n"

                elif evt_type == "error":
                    yield f"data: {json.dumps({'node': 'ERROR', 'error': event['message']})}\n\n"

                await asyncio.sleep(0.05)

        except Exception as e:
            log.error(f"Agent stream error: {e}")
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
#  MCP RUNTIME ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════
from mcp_runtime.registry import mcp_registry

@app.get("/api/v1/mcp/servers")
def get_mcp_servers():
    """List all registered MCP servers and their status."""
    return {"status": "success", "servers": mcp_registry.get_servers()}

@app.post("/api/v1/mcp/servers/{server_name}/start")
def start_mcp_server(server_name: str):
    """Start an MCP server."""
    try:
        return mcp_registry.start_server(server_name)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/v1/mcp/servers/{server_name}/stop")
def stop_mcp_server(server_name: str):
    """Stop an MCP server."""
    return mcp_registry.stop_server(server_name)

@app.get("/api/v1/mcp/tools")
def get_mcp_tools(server: str):
    """List tools exposed by a specific running MCP server."""
    return {"status": "success", "server": server, "tools": mcp_registry.get_tools(server)}

class MCPExecuteRequest(BaseModel):
    server: str
    tool: str
    args: dict

@app.post("/api/v1/mcp/execute")
def execute_mcp_tool(req: MCPExecuteRequest):
    """Dynamically execute a tool via MCP registry."""
    try:
        res = mcp_registry.call_tool(req.server, req.tool, req.args)
        return {"status": "success", "result": res}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ═══════════════════════════════════════════════════════════════════════════
#  SETTINGS ENDPOINTS (PHASE 3)
# ═══════════════════════════════════════════════════════════════════════════
from system.settings import settings_manager

@app.get("/api/v1/settings")
def get_settings():
    return settings_manager.get()

@app.post("/api/v1/settings")
def update_settings(new_settings: dict):
    settings_manager.update(new_settings)
    return {"status": "success", "settings": settings_manager.get()}

@app.get("/api/v1/llm/status")
def get_llm_status():
    """Verify Gemini API connection status."""
    import os
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        return {"status": "error", "provider": "Google Gemini", "message": "GOOGLE_API_KEY not configured", "connected": False}
    try:
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(model_name="gemini-3.1-flash-lite-preview")
        resp = model.generate_content("Reply ONLY with the word PONG.")
        connected = "PONG" in (resp.text or "").upper()
        return {"status": "active" if connected else "error", "provider": "Google Gemini Flash-Lite", "model": "gemini-3.1-flash-lite-preview", "connected": connected, "message": "Connection verified" if connected else "Unexpected response"}
    except Exception as e:
        return {"status": "error", "provider": "Google Gemini", "connected": False, "message": str(e)}

# ═══════════════════════════════════════════════════════════════════════════
#  PIPELINE (Placement + Routing + Validation)
# ═══════════════════════════════════════════════════════════════════════════

class GoalRequest(BaseModel):
    goal: str

@app.post("/api/v1/agent/execute")
async def execute_goal(req: GoalRequest):
    """
    Goal-driven execution entry point (replaces fixed pipeline).
    Runs the full autonomous agent graph synchronously and returns results.
    For streaming, use GET /api/v1/agent/run?intent=...
    """
    try:
        from agent.langgraph_loop import build_agent_graph
        agent = build_agent_graph()
        final_state = agent.invoke({
            "goal": req.goal,
            "board_context": {},
            "available_tools": [],
            "scored_tools": [],
            "plan": [],
            "current_step_index": 0,
            "selected_tool": None,
            "execution_results": [],
            "verification_report": {},
            "drc_errors": [],
            "retries": 0,
            "strategy": "shortest_path",
            "precheck_results": {},
            "status": "started",
        })
        return {
            "status": "success",
            "plan": final_state.get("plan", []),
            "execution_results": final_state.get("execution_results", []),
            "verification_report": final_state.get("verification_report", {}),
            "drc_errors": final_state.get("drc_errors", []),
            "retries": final_state.get("retries", 0),
        }
    except Exception as e:
        log.error(f"[API] /agent/execute error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Legacy pipeline endpoint — now delegates to goal-driven agent
@app.post("/api/v1/pipeline/run")
async def run_full_pipeline(req: PipelineRunRequest):
    """Deprecated: delegates to goal-driven agent."""
    return await execute_goal(GoalRequest(goal="Run a full PCB placement, routing and DRC verification pipeline"))

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
