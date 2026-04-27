import json
import logging
from typing import Any, Dict, List, Optional, TypedDict

from langgraph.graph import StateGraph, END

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from system.settings import settings_manager
from mcp_runtime.registry import mcp_registry
from .llm_factory import LLMFactory

log = logging.getLogger("AutonomousAgent")

# ─────────────────────────────────────────────────────────────────────────────
# LLM Helper
# ─────────────────────────────────────────────────────────────────────────────

def _llm(messages: List[Dict], model: Optional[str] = None) -> str:
    try:
        from litellm import completion
        s = settings_manager.get()
        m = model or s["models"].get("reasoning_model", "claude-3-5-sonnet-20240620")
        return completion(model=m, messages=messages).choices[0].message.content.strip()
    except Exception as e:
        log.warning(f"LLM unavailable ({e}). Using heuristics.")
        return ""

def _fast_llm(messages: List[Dict]) -> str:
    """Use the fast model for lightweight decisions like tool scoring."""
    try:
        from litellm import completion
        s = settings_manager.get()
        m = s["models"].get("fast_model", "gemini/gemini-1.5-flash")
        return completion(model=m, messages=messages).choices[0].message.content.strip()
    except Exception as e:
        log.warning(f"Fast LLM unavailable ({e}).")
        return ""

def _parse_json(text: str) -> Any:
    try:
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0]
        elif "```" in text:
            text = text.split("```")[1].split("```")[0]
        return json.loads(text.strip())
    except Exception:
        return None


# ─────────────────────────────────────────────────────────────────────────────
# State Schema
# ─────────────────────────────────────────────────────────────────────────────

class AgentState(TypedDict):
    goal: str
    board_context: Dict[str, Any]      # live board state fetched via MCP
    available_tools: List[Dict]
    scored_tools: List[Dict]           # tools ranked by the LLM
    plan: List[Dict]
    current_step_index: int
    selected_tool: Optional[Dict]
    execution_results: List[Dict]
    verification_report: Dict[str, Any]
    drc_errors: List[str]
    retries: int
    strategy: str
    precheck_results: Dict[str, Any]
    status: str


# ─────────────────────────────────────────────────────────────────────────────
# BOARD CONTEXT HELPER (Task 3)
# ─────────────────────────────────────────────────────────────────────────────

def _fetch_board_context() -> Dict[str, Any]:
    """Fetch real board state from neuro_layout via MCP."""
    try:
        ctx = mcp_registry.call_tool("neuro_layout", "get_board_info", {})
        return ctx if isinstance(ctx, dict) else {}
    except Exception as e:
        log.warning(f"Board context fetch failed: {e}")
        return {}


# ─────────────────────────────────────────────────────────────────────────────
# NODE 1 — Research: discover tools + fetch board context
# ─────────────────────────────────────────────────────────────────────────────

def research_node(state: AgentState) -> AgentState:
    """Start MCP servers, discover all tools, and fetch live board context."""
    log.info("[research] Starting MCP servers and fetching board context...")

    for srv in ["neuro_layout", "neuro_router", "neuro_schematic"]:
        try:
            mcp_registry.start_server(srv)
        except Exception as e:
            log.warning(f"Could not start {srv}: {e}")

    all_tools = []
    for server in mcp_registry.servers.values():
        if server.status == "running":
            for tool in server.tools:
                all_tools.append({
                    "server": server.name,
                    "name": tool["name"],
                    "description": tool.get("description", ""),
                    "capabilities": tool.get("capabilities", []),
                    "constraints": tool.get("constraints", {}),
                })

    board_ctx = _fetch_board_context()
    log.info(f"[research] {len(all_tools)} tools discovered. Board: {list(board_ctx.keys())}")
    return {**state, "available_tools": all_tools, "board_context": board_ctx, "status": "research_done"}


# ─────────────────────────────────────────────────────────────────────────────
# NODE 1.5 — Strategy Selection (Task 3)
# ─────────────────────────────────────────────────────────────────────────────

def strategy_selection_node(state: AgentState) -> AgentState:
    """Evaluate multiple strategies (shortest path, impedance-optimized, low-noise routing) before planning."""
    goal = state["goal"]
    prompt = f"""You are a PCB Strategy Selector.
USER GOAL: {goal}
Select the BEST strategy for this goal from:
- shortest_path
- impedance_optimized
- low_noise
Respond ONLY with a JSON object: {{"strategy": "..."}}"""
    raw = _fast_llm([{"role": "user", "content": prompt}])
    res = _parse_json(raw) or {"strategy": "shortest_path"}
    log.info(f"[strategy] Selected strategy: {res.get('strategy')}")
    return {**state, "strategy": res.get("strategy", "shortest_path"), "status": "strategy_selected"}


# ─────────────────────────────────────────────────────────────────────────────
# NODE 2 — Tool Scoring (Task 2): LLM ranks tools by relevance
# ─────────────────────────────────────────────────────────────────────────────

def tool_scoring_node(state: AgentState) -> AgentState:
    """
    Use a fast LLM call to score every available tool against the goal.
    Returns tools sorted by score descending — used by planning and selection.
    """
    goal = state["goal"]
    tools = state["available_tools"]
    board_ctx = state["board_context"]

    tool_list = "\n".join(
        f"  [{i}] server={t['server']}, tool={t['name']}: {t['description']}"
        for i, t in enumerate(tools)
    )

    prompt = f"""You are a PCB Design Tool Evaluator.

USER GOAL: {goal}

BOARD CONTEXT (topology, net criticality):
{json.dumps(board_ctx, indent=2)[:600]}

AVAILABLE TOOLS:
{tool_list}

For each tool, assign a relevance score 0.0 to 10.0 based on:
- Relevance to the goal
- Capability match
- Constraint compatibility (impedance, trace width)
- Board topology and net criticality

Respond ONLY with JSON array:
[{{"index": 0, "score": 8.7, "reason": "best for differential routing under impedance constraints"}}, ...]"""

    raw = _fast_llm([{"role": "user", "content": prompt}])
    scores = _parse_json(raw)

    if scores and isinstance(scores, list):
        scored = []
        for entry in scores:
            idx = entry.get("index", -1)
            if 0 <= idx < len(tools):
                scored.append({
                    **tools[idx],
                    "score": float(entry.get("score", 0.0)),
                    "score_reason": entry.get("reason", ""),
                })
        scored.sort(key=lambda x: x.get("score", 0), reverse=True)
        log.info(f"[tool_scoring] Top tool: {scored[0]['name']} (score={scored[0]['score']}) " if scored else "")
    else:
        # Fallback: all tools equal score
        scored = [{**t, "score": 5, "score_reason": "heuristic fallback"} for t in tools]

    return {**state, "scored_tools": scored, "status": "tools_scored"}


# ─────────────────────────────────────────────────────────────────────────────
# NODE 3 — Context-Aware Planning (Task 1): LLM generates deep plan
# ─────────────────────────────────────────────────────────────────────────────

def planning_node(state: AgentState) -> AgentState:
    """
    Generate a deep, dependency-aware multi-step plan using the Gemini-powered LLMFactory.
    """
    goal = state["goal"]
    board_ctx = state["board_context"]
    scored_tools = state["scored_tools"]
    s = settings_manager.get()
    strategy = state.get("strategy", "shortest_path")

    top_tools = [t for t in scored_tools[:10]]

    factory = LLMFactory()
    
    raw = factory.run(
        context=board_ctx,
        tools=top_tools,
        goal=goal,
        strategy=strategy
    )
    
    plan = _parse_json(raw)

    if not plan or not isinstance(plan, list):
        log.warning("[planning] LLM plan failed. Using heuristic.")
        plan = _heuristic_plan(goal, scored_tools, s)

    # Sort by dependency order
    plan.sort(key=lambda x: x.get("step", 0))
    log.info(f"[planning] Plan generated: {len(plan)} steps")
    return {**state, "plan": plan, "current_step_index": 0, "status": "plan_ready"}


def _heuristic_plan(goal: str, scored_tools: List[Dict], settings: Dict) -> List[Dict]:
    g = goal.lower()
    plan = [{
        "step": 1, "action": "Capture board state",
        "server": "neuro_layout", "tool": "get_board_info",
        "args": {}, "depends_on": [], "rationale": "Always start with board context"
    }]
    w = settings["pcb"].get("default_trace_width", 0.25)
    imp = settings["pcb"].get("impedance_target", "90ohm")

    if any(k in g for k in ["diff", "usb", "pcie", "lvds"]):
        plan += [
            {"step": 2, "action": "Route D+ trace", "server": "neuro_router", "tool": "route_trace",
             "args": {"net": "/USB_DP", "width": w, "layer": "F.Cu"}, "depends_on": [1],
             "rationale": f"Differential pair at {imp}"},
            {"step": 3, "action": "Route D- trace", "server": "neuro_router", "tool": "route_trace",
             "args": {"net": "/USB_DM", "width": w, "layer": "F.Cu"}, "depends_on": [2],
             "rationale": "Match-length to D+ for diff pair"},
        ]
    elif any(k in g for k in ["power", "pwr", "gnd", "ground"]):
        plan.append({"step": 2, "action": "Route power net", "server": "neuro_router", "tool": "route_trace",
                     "args": {"net": "/VCC", "width": settings["pcb"].get("power_trace_min_width", 0.5), "layer": "F.Cu"},
                     "depends_on": [1], "rationale": "Power trace needs extra width"})
    else:
        plan.append({"step": 2, "action": "Auto-route all nets", "server": "neuro_router",
                     "tool": "apply_routing_strategy",
                     "args": {"strategy": "auto", "trace_width": w}, "depends_on": [1],
                     "rationale": "General routing"})

    plan.append({"step": len(plan) + 1, "action": "Run DRC", "server": "neuro_layout", "tool": "run_drc",
                 "args": {}, "depends_on": [len(plan)], "rationale": "Verify routing integrity"})
    return plan


# ─────────────────────────────────────────────────────────────────────────────
# NODE 4 — Tool Selection (Task 2): LLM picks best tool per step with scoring
# ─────────────────────────────────────────────────────────────────────────────

def tool_selection_node(state: AgentState) -> AgentState:
    """Select and validate the best-scored tool for the current plan step."""
    plan = state["plan"]
    idx = state["current_step_index"]

    if idx >= len(plan):
        return {**state, "selected_tool": None, "status": "plan_exhausted"}

    step = plan[idx]
    scored = state["scored_tools"]

    # Check if plan-specified tool is in our scored list
    plan_server = step.get("server", "")
    plan_tool = step.get("tool", "")
    match = next((t for t in scored if t["server"] == plan_server and t["name"] == plan_tool), None)

    if match and match["score"] >= 5:
        selected = {**step, "score": match["score"], "score_reason": match.get("score_reason", "")}
        log.info(f"[tool_selection] Step {idx+1}: '{plan_tool}' score={match['score']}/10 — {match.get('score_reason','')}")
    else:
        # Ask LLM to pick from top-scored alternatives
        top5 = "\n".join(
            f"  [{t['score']}/10] server={t['server']}, tool={t['name']}: {t['description']}"
            for t in scored[:5]
        )
        raw = _fast_llm([{"role": "user", "content": f"""Task: {step.get('action')}
Top 5 Tools:
{top5}
Pick BEST tool. JSON only: {{"server":"...","tool":"...","args":{{}}}}"""}])
        alt = _parse_json(raw)
        if alt:
            selected = {**step, **alt, "score": "override"}
            log.info(f"[tool_selection] Step {idx+1}: LLM override → {alt.get('tool')}")
        else:
            selected = step

    return {**state, "selected_tool": selected, "status": "tool_selected"}


# ─────────────────────────────────────────────────────────────────────────────
# NODE 4.5 — Pre-Execution Simulation (Task 1)
# ─────────────────────────────────────────────────────────────────────────────

def precheck_node(state: AgentState) -> AgentState:
    """
    Before execution, simulate routing outcome.
    Estimate spacing violations, impedance mismatch, congestion.
    If risk detected, adjust plan or args BEFORE execution.
    """
    selected = state.get("selected_tool")
    if not selected:
        return {**state, "precheck_results": {}, "status": "skipped_precheck"}
    
    tool_name = selected.get("tool", "")
    args = selected.get("args", {})
    
    prompt = f"""Simulate routing outcome for this step.
TOOL: {tool_name}
ARGS: {json.dumps(args)}
BOARD CONTEXT: {json.dumps(state.get("board_context", {}))[:400]}

Estimate risks:
- spacing violations
- impedance mismatch
- congestion

Respond with JSON: {{"risk_level": "high|medium|low", "issues": ["..."], "suggested_args": {{...}}}}"""
    raw = _fast_llm([{"role": "user", "content": prompt}])
    res = _parse_json(raw) or {"risk_level": "low", "issues": [], "suggested_args": args}
    
    # Adjust args if high risk
    if res.get("risk_level") in ["high", "medium"] and res.get("suggested_args"):
        selected["args"].update(res["suggested_args"])
        log.warning(f"[precheck] Risk detected: {res.get('issues')}. Adjusted args.")
        
    return {**state, "selected_tool": selected, "precheck_results": res, "status": "precheck_done"}


# ─────────────────────────────────────────────────────────────────────────────
# NODE 5 — Context-Aware Execution & Parameter Optimization (Task 3, 4)
# ─────────────────────────────────────────────────────────────────────────────

def execution_node(state: AgentState) -> AgentState:
    """
    Before each step, refresh board context and dynamically adjust tool arguments.
    """
    selected = state.get("selected_tool")
    if not selected:
        return {**state, "status": "skipped_no_tool"}

    settings = settings_manager.get()
    review = settings["agent"].get("review_policy", "auto")
    strategy = state.get("strategy", "shortest_path")

    # Refresh board context before execution
    live_ctx = _fetch_board_context()
    
    # Parameter Optimization (Task 4)
    # Dynamically patch args from live context and strategy
    args = dict(selected.get("args", {}))
    if "trace_width" not in args or strategy == "impedance_optimized":
        args["trace_width"] = settings["pcb"].get("impedance_trace_width", settings["pcb"].get("default_trace_width", 0.25))
    if strategy == "low_noise":
        args["spacing"] = settings["pcb"].get("low_noise_spacing", 0.5)
        
    if "layer" not in args and live_ctx.get("active_layer"):
        args["layer"] = live_ctx.get("active_layer", "F.Cu")

    if review == "dry_run":
        result = {"dry_run": True, "tool": selected["tool"], "patched_args": args}
    else:
        try:
            log.info(f"[execution] {selected['server']}::{selected['tool']} args={args}")
            result = mcp_registry.call_tool(selected["server"], selected["tool"], args)
        except Exception as e:
            log.error(f"[execution] Failed: {e}")
            result = {"error": str(e)}

    entry = {
        "step_index": state["current_step_index"],
        "step": selected.get("step"),
        "action": selected.get("action"),
        "server": selected["server"],
        "tool": selected.get("tool"),
        "args": args,
        "result": result,
        "rationale": selected.get("rationale", ""),
    }

    return {
        **state,
        "board_context": live_ctx,
        "execution_results": state.get("execution_results", []) + [entry],
        "current_step_index": state["current_step_index"] + 1,
        "status": "step_done",
    }


# ─────────────────────────────────────────────────────────────────────────────
# NODE 5.5 — Partial Execution Loop (Task 5)
# ─────────────────────────────────────────────────────────────────────────────

def step_validation_node(state: AgentState) -> AgentState:
    """After each step, validate and adjust next step."""
    results = state.get("execution_results", [])
    if not results:
        return state
        
    last_result = results[-1].get("result", {})
    if "error" in str(last_result):
        log.warning("[step_validation] Error in last step execution. May need adjustment.")
        
    # We can perform mid-step validation here and modify future plan if needed
    return {**state, "status": "step_validated"}


# ─────────────────────────────────────────────────────────────────────────────
# NODE 6 — Advanced Verification (Task 4): DRC + impedance + power + completeness
# ─────────────────────────────────────────────────────────────────────────────

def verification_node(state: AgentState) -> AgentState:
    """
    Comprehensive board analysis:
      1. KiCad DRC (spacing / clearance violations)
      2. Impedance check (controlled impedance nets)
      3. Power integrity (net widths on power rails)
      4. Routing completeness (all nets routed?)
    """
    settings = settings_manager.get()
    report = {"drc": [], "impedance": [], "power": [], "completeness": [], "passed": True}

    if not settings["agent"].get("strict_mode", True):
        log.info("[verification] strict_mode=False — skipping.")
        return {**state, "drc_errors": [], "verification_report": report, "status": "verified_skip"}

    # 1. DRC
    try:
        drc = mcp_registry.call_tool("neuro_layout", "run_drc", {})
        violations = drc.get("violations", []) if isinstance(drc, dict) else []
        report["drc"] = violations
    except Exception as e:
        violations = [f"DRC unavailable: {e}"]
        report["drc"] = violations

    # 2. Impedance check — look for diff pair nets in results
    board_ctx = state.get("board_context", {})
    target_imp = settings["pcb"].get("impedance_target", "90ohm")
    imp_nets = [n for n in board_ctx.get("nets", []) if any(k in str(n).upper() for k in ["DP", "DM", "TX", "RX"])]
    if imp_nets:
        # Could call a real S-param tool here; for now flag if any diff pair was executed
        routed = [r["tool"] for r in state.get("execution_results", [])]
        if "route_trace" in routed:
            report["impedance"] = [f"Verify {target_imp} controlled impedance on: {imp_nets}"]
        else:
            report["impedance"] = [f"WARNING: diff pair nets {imp_nets} may not be routed"]

    # 3. Power integrity — check power trace widths in execution args
    min_pwr = settings["pcb"].get("power_trace_min_width", 0.5)
    for r in state.get("execution_results", []):
        if "VCC" in str(r.get("args", {})) or "GND" in str(r.get("args", {})):
            w = r.get("args", {}).get("trace_width", 0)
            if w and float(w) < float(min_pwr):
                report["power"].append(f"Power trace too narrow: {w}mm < {min_pwr}mm required")
                report["passed"] = False

    # 4. Routing completeness
    total_nets = len(board_ctx.get("nets", []))
    routed_steps = sum(1 for r in state.get("execution_results", []) if r["tool"] in ["route_trace", "apply_routing_strategy"])
    if total_nets > 0 and routed_steps == 0:
        report["completeness"].append("No routing steps were executed — board may be unrouted")

    all_errors = report["drc"] + report["power"] + report["completeness"]
    if all_errors:
        report["passed"] = False

    log.info(f"[verification] DRC={len(report['drc'])} imp={len(report['impedance'])} pwr={len(report['power'])} complete={len(report['completeness'])}")
    return {**state, "drc_errors": all_errors, "verification_report": report, "status": "verified"}


# ─────────────────────────────────────────────────────────────────────────────
# NODE 7 — Targeted Self-Correction (Task 5): Fix-not-replan
# ─────────────────────────────────────────────────────────────────────────────

def self_correction_node(state: AgentState) -> AgentState:
    """
    Analyze each error category and generate a TARGETED corrective plan,
    not a full replan — focus only on what failed.
    """
    settings = settings_manager.get()
    retries = state.get("retries", 0)
    max_r = settings["agent"].get("max_iterations", 5)

    if retries >= max_r:
        log.warning(f"[correction] Max retries ({max_r}) reached.")
        return {**state, "status": "failed"}

    report = state.get("verification_report", {})
    errors = state.get("drc_errors", [])
    tools = state.get("scored_tools", [])
    board_ctx = state.get("board_context", {})

    # Build targeted error summary
    error_groups = {
        "DRC spacing": [e for e in report.get("drc", []) if e],
        "Impedance": report.get("impedance", []),
        "Power trace": report.get("power", []),
        "Completeness": report.get("completeness", []),
    }
    non_empty = {k: v for k, v in error_groups.items() if v}

    tool_list = "\n".join(f"  server={t['server']}, tool={t['name']}: {t['description']}" for t in tools[:8])

    prompt = f"""You are a PCB Debug Agent performing TARGETED error correction.

DO NOT replan everything. Fix ONLY the detected problems.

DETECTED FAILURES:
{json.dumps(non_empty, indent=2)}

BOARD CONTEXT:
{json.dumps(board_ctx, indent=2)[:600]}

AVAILABLE TOOLS:
{tool_list}

Generate a MINIMAL corrective plan (only steps needed to fix failures).
JSON array: [{{"step":1,"action":"...","server":"...","tool":"...","args":{{}},"depends_on":[],"rationale":"why this fixes the specific error"}}]"""

    raw = _llm([{"role": "user", "content": prompt}])
    fix_plan = _parse_json(raw)

    if not fix_plan:
        # Targeted heuristic fallback
        fix_plan = []
        if report.get("drc"):
            fix_plan.append({"step": 1, "action": "Respace violating traces", "server": "neuro_router",
                              "tool": "apply_routing_strategy", "args": {"strategy": "respace", "clearance": 0.3},
                              "depends_on": [], "rationale": "Fix DRC spacing violation"})
        if report.get("power"):
            fix_plan.append({"step": len(fix_plan)+1, "action": "Widen power traces", "server": "neuro_router",
                              "tool": "route_trace",
                              "args": {"net": "VCC", "width": settings["pcb"].get("power_trace_min_width", 0.5)},
                              "depends_on": [], "rationale": "Fix power trace width violation"})

    log.info(f"[correction] Retry {retries+1}/{max_r} — targeted fix plan: {len(fix_plan)} step(s)")
    return {
        **state,
        "plan": fix_plan,
        "current_step_index": 0,
        "retries": retries + 1,
        "drc_errors": [],
        "verification_report": {},
        "status": "targeted_fix_ready",
    }


# ─────────────────────────────────────────────────────────────────────────────
# EDGES
# ─────────────────────────────────────────────────────────────────────────────

def after_tool_selection(state: AgentState) -> str:
    return "verification" if state.get("status") == "plan_exhausted" else "precheck"

def after_step_validation(state: AgentState) -> str:
    return "tool_selection" if state["current_step_index"] < len(state.get("plan", [])) else "verification"

def after_verification(state: AgentState) -> str:
    return "self_correction" if state.get("drc_errors") else "end"

def after_correction(state: AgentState) -> str:
    return "end" if state.get("status") == "failed" else "tool_selection"


# ─────────────────────────────────────────────────────────────────────────────
# GRAPH BUILDER
# ─────────────────────────────────────────────────────────────────────────────

def build_agent_graph():
    wf = StateGraph(AgentState)

    wf.add_node("research",        research_node)
    wf.add_node("strategy_selection", strategy_selection_node)
    wf.add_node("tool_scoring",    tool_scoring_node)
    wf.add_node("planning",        planning_node)
    wf.add_node("tool_selection",  tool_selection_node)
    wf.add_node("precheck",        precheck_node)
    wf.add_node("execution",       execution_node)
    wf.add_node("step_validation", step_validation_node)
    wf.add_node("verification",    verification_node)
    wf.add_node("self_correction", self_correction_node)

    wf.set_entry_point("research")
    wf.add_edge("research",     "strategy_selection")
    wf.add_edge("strategy_selection", "tool_scoring")
    wf.add_edge("tool_scoring", "planning")
    wf.add_edge("planning",     "tool_selection")

    wf.add_conditional_edges("tool_selection", after_tool_selection, {
        "precheck":    "precheck",
        "verification": "verification",
    })
    
    wf.add_edge("precheck", "execution")
    wf.add_edge("execution", "step_validation")
    
    wf.add_conditional_edges("step_validation", after_step_validation, {
        "tool_selection": "tool_selection",
        "verification":   "verification",
    })
    
    wf.add_conditional_edges("verification", after_verification, {
        "self_correction": "self_correction",
        "end": END,
    })
    wf.add_conditional_edges("self_correction", after_correction, {
        "tool_selection": "tool_selection",
        "end": END,
    })

    return wf.compile()
