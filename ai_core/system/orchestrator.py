import os
import asyncio
import logging
from typing import Dict, Any, List

# Ensure we use the exact KiCad 10 IPC socket specified
IPC_SOCKET_PATH = "ipc:///C:/Users/Bibek/AppData/Local/Temp/kicad/api.sock"
os.environ["KICAD_API_SOCKET"] = IPC_SOCKET_PATH

try:
    from kipy import KiCad
except ImportError:
    KiCad = None
    logging.warning("kipy not available.")

# ═══════════════════════════════════════════════════════════════════════════
# ROO CODE: MCP Hub Architecture
# ═══════════════════════════════════════════════════════════════════════════
class McpHub:
    """
    Roo Code style MCP Service Layer.
    Manages connections to standard MCP providers and our KiCad IPC layer.
    """
    def __init__(self):
        self.kicad_client = None
        self.servers = {}
        
    def connect_kicad(self):
        """Establish direct gRPC/IPC bridge to KiCad 10"""
        logging.info(f"[McpHub] Connecting to KiCad 10 via {IPC_SOCKET_PATH}")
        if KiCad:
            try:
                # Kipy uses env var or default path
                self.kicad_client = KiCad()
                logging.info("[McpHub] KiCad IPC Connected.")
            except Exception as e:
                logging.error(f"[McpHub] Connection Failed: {e}")
        else:
            logging.warning("[McpHub] KiCad client simulated.")

    def reconnect_kicad(self):
        """Force a reconnection to the active project context."""
        logging.info("[McpHub] Re-binding KiCad context for new project...")
        self.kicad_client = None
        self.connect_kicad()
        # Also signal the local mcp server if necessary
        # We can re-import and trigger a re-init
        import sys
        from pathlib import Path
        sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
        try:
            import mcp_server.server as backend_server
            backend_server.bridge.reconnect()
        except Exception as e:
            logging.error(f"[McpHub] Failed to re-bind local MCP bridge: {e}")
            
    def call_tool(self, server: str, tool: str, args: Dict[str, Any]) -> Any:
        logging.info(f"[McpHub] Executing {server}::{tool} with {args}")
        # In the full fusion, this dispatches to mcp_runtime/registry.py
        import sys
        from pathlib import Path
        sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
        from mcp_runtime.registry import mcp_registry
        
        try:
            return mcp_registry.call_tool(server, tool, args)
        except Exception as e:
            return {"error": str(e)}

# ═══════════════════════════════════════════════════════════════════════════
# OPENHANDS: App Server & Agent Session
# ═══════════════════════════════════════════════════════════════════════════
class AgentSession:
    """
    OpenHands style session manager.
    Maintains state loop, streams actions to UI, and routes through McpHub.
    """
    def __init__(self, session_id: str, mcp_hub: McpHub):
        self.session_id = session_id
        self.hub = mcp_hub
        self.history = []
        
    async def process_intent(self, user_intent: str, contexts: str = ""):
        """
        Autonomous goal-driven loop.
        Streams rich events: plan reveal → per-step tool selection → execution → verification.
        """
        # Append context tags if provided
        if contexts:
            tags = [f"@{c.strip()}" for c in contexts.split(",") if c.strip()]
            user_intent = f"{user_intent} {' '.join(tags)}"
            logging.info(f"[orchestrator] Injected contexts: {tags}")

        self.history.append({"role": "user", "content": user_intent})
        yield {"type": "status", "message": "🔍 Discovering MCP tools..."}

        import sys
        from pathlib import Path
        sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
        from agent.langgraph_loop import build_agent_graph
        from system.project_manager import project_manager

        active_proj = project_manager.get_active_project()
        active_path = active_proj["path"] if active_proj else None

        if not active_path:
            yield {"type": "error", "message": "No active project selected. Please select a project first."}
            return

        agent = build_agent_graph()
        initial_state = {
            "goal": user_intent,
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
            "active_project": active_path,
        }

        try:
            for event in agent.stream(initial_state):
                for node_name, state_update in event.items():
                    model_name = state_update.get("last_model_used")
                    if node_name == "research":
                        tc = len(state_update.get("available_tools", []))
                        yield {"type": "status", "message": f"🛠️ {tc} MCP tools discovered across 3 servers", "model": model_name}

                    elif node_name == "strategy_selection":
                        strat = state_update.get("strategy", "unknown")
                        yield {"type": "status", "message": f"🧠 Strategy selected: {strat}", "model": model_name}

                    elif node_name == "tool_scoring":
                        top = (state_update.get("scored_tools") or [{}])[0]
                        yield {"type": "status", "message": f"🏆 Top tool: {top.get('name','?')} (score {top.get('score','?')}/10)", "model": model_name}

                    elif node_name == "planning":
                        plan = state_update.get("plan", [])
                        thought = state_update.get("thought", "")

                        # PILLAR 2: Stream the THOUGHT block first
                        if thought:
                            yield {
                                "type": "thought",
                                "content": thought,
                                "message": "Engineering reasoning complete.",
                                "model": model_name,
                            }
                            await asyncio.sleep(0.1)

                        yield {"type": "plan", "plan": plan, "message": f"Plan generated: {len(plan)} steps", "model": model_name}

                    elif node_name == "tool_selection":
                        tool = state_update.get("selected_tool") or {}
                        yield {
                            "type": "tool_selected",
                            "tool": f"{tool.get('server','?')}::{tool.get('tool','?')}",
                            "action": tool.get("action", ""),
                            "score": tool.get("score", "?"),
                            "message": f"🎯 Step {tool.get('step','?')}: {tool.get('tool','?')} (score {tool.get('score','?')})",
                            "model": model_name
                        }

                    elif node_name == "precheck":
                        res = state_update.get("precheck_results", {})
                        risk = res.get("risk_level", "low")
                        if risk in ["high", "medium"]:
                            yield {"type": "status", "message": f"⚠️ Precheck risk ({risk}): {', '.join(res.get('issues', []))} — adjusting args", "model": model_name}
                        else:
                            yield {"type": "status", "message": f"✅ Precheck passed (risk: {risk})", "model": model_name}

                    elif node_name == "execution":
                        results = state_update.get("execution_results", [])
                        last = results[-1] if results else {}
                        result = last.get("result", {})
                        has_err = isinstance(result, dict) and result.get("status") == "failed"
                        tool_name = f"{last.get('server','')}::{last.get('tool','')}"

                        # PILLAR 2: If this was a scratchpad call, stream the script
                        if last.get("tool") == "execute_engineering_script":
                            script_code = last.get("args", {}).get("script_code", "")
                            if script_code:
                                yield {
                                    "type": "script",
                                    "script_code": script_code,
                                    "stdout": result.get("stdout", "") if isinstance(result, dict) else "",
                                    "stderr": result.get("stderr", "") if isinstance(result, dict) else "",
                                    "status": "failed" if has_err else "success",
                                    "message": f"Script {'failed' if has_err else 'executed'}: {last.get('action', '')}",
                                    "model": model_name,
                                }
                                await asyncio.sleep(0.05)
                                continue

                        yield {
                            "type": "action",
                            "status": "error" if has_err else "success",
                            "tool": tool_name,
                            "result": result,
                            "message": f"⚡ {last.get('action', last.get('tool',''))}",
                            "model": model_name,
                        }

                    elif node_name == "reflect":
                        # PILLAR 2+3: Stream the reflection event
                        reflect_n = state_update.get("reflect_retries", 1)
                        plan = state_update.get("plan", [])
                        # The last plan step contains the corrected script
                        corrected_step = plan[state_update.get("current_step_index", 0)] if plan else {}
                        corrected_script = corrected_step.get("args", {}).get("script_code", "")
                        yield {
                            "type": "reflect",
                            "attempt": reflect_n,
                            "corrected_script": corrected_script,
                            "message": f"Self-correcting script (attempt {reflect_n}/3)...",
                            "model": model_name,
                        }

                    elif node_name == "step_validation":
                        yield {"type": "status", "message": "✅ Step validated", "model": model_name}

                    elif node_name == "verification":
                        rpt = state_update.get("verification_report", {})
                        errs = state_update.get("drc_errors", [])
                        if errs:
                            summary = f"DRC={len(rpt.get('drc',[]))} Impedance={len(rpt.get('impedance',[]))} Power={len(rpt.get('power',[]))} Complete={len(rpt.get('completeness',[]))}"
                            yield {"type": "status", "message": f"⚠️ {len(errs)} issue(s) — {summary}", "model": model_name}
                        else:
                            yield {"type": "status", "message": "✅ All checks passed: DRC, Impedance, Power Integrity, Routing Completeness", "model": model_name}

                    elif node_name == "self_correction":
                        retries = state_update.get("retries", 0)
                        new_plan = state_update.get("plan", [])
                        yield {"type": "status", "message": f"🔄 Targeted fix (attempt {retries}): {len(new_plan)} corrective step(s)", "model": model_name}

                    await asyncio.sleep(0.05)

            yield {"type": "completed", "message": "✅ Goal achieved. Agent workflow complete."}

        except Exception as e:
            logging.error(f"Agent Execution Failed: {e}")
            yield {"type": "error", "message": f"Agent loop failed: {e}"}


class OrchestratorBridge:
    """
    Backward compatibility bridge for legacy endpoints.
    """
    def __init__(self, mcp_hub: McpHub):
        self.hub = mcp_hub

    def inject_decoupling(self, target_ref: str):
        # Dispatch to neuro_layout MCP server (conceptual tool)
        return self.hub.call_tool("neuro_layout", "inject_decoupling", {"target_ref": target_ref})

    def save_board(self):
        # Dispatch to neuro_layout save_project tool
        return self.hub.call_tool("neuro_layout", "save_project", {})

# Global instances
hub = McpHub()
hub.connect_kicad()
orchestrator = OrchestratorBridge(hub)
