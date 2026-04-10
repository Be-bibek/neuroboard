import os
import json
import logging
import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from ai_core.system.ipc_client import IPCClient
from ai_core.system.orchestrator import CompilerOrchestrator

log = logging.getLogger("SystemLogger")
app = FastAPI(title="NeuroBoard API", version="3.0", description="Backend for Tauri Frontend")

ipc = IPCClient()
orchestrator = CompilerOrchestrator()

class RoutingRequest(BaseModel):
    src_ref: str
    dst_ref: str
    pin_mapping: dict

@app.get("/api/v1/board/state")
def get_live_board_state():
    """ Retrieves live KiCad IPC state for Tauri visualization. """
    try:
        if not ipc.board:
            ipc.connect()
        return {"status": "success", "state": ipc.get_board_state()}
    except Exception as e:
        log.error(f"Failed to get board state: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/route")
def execute_routing(req: RoutingRequest):
    """ Executes validation pipeline. """
    try:
        # Assuming run_full_pipeline generates the validation report and commits via IPC
        report = orchestrator.run_full_pipeline(req.src_ref, req.dst_ref, req.pin_mapping)
        return {"status": "success", "report": report}
    except Exception as e:
        log.error(f"Routing failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/reports/latest")
def get_latest_report():
    """ Serves the newest neuroboard_validation.json report. """
    report_path = "reports/neuroboard_validation.json"
    if not os.path.exists(report_path):
        raise HTTPException(status_code=404, detail="No report found.")
    
    with open(report_path, "r") as f:
        return json.load(f)

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
