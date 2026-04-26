import json
from typing import Dict, Any, List, TypedDict, Annotated
import operator

try:
    from langgraph.graph import StateGraph, END
except ImportError:
    # Fallback/stub if langgraph is not installed, but keeping the structure intact
    StateGraph = None

# Define State Structure
class AgentState(TypedDict):
    intent: str
    board_target: str # e.g., "Raspberry Pi 5 PCIe", "Arduino"
    components_needed: List[str]
    routing_plan: List[Dict[str, Any]]
    execution_results: List[Dict[str, Any]]
    drc_errors: List[str]
    retries: int
    status: str

# ------------------------------------------------------------------
# PROMPT 2: LANGGRAPH AUTONOMOUS PCB AGENT
# ------------------------------------------------------------------

def parse_intent_node(state: AgentState) -> AgentState:
    """Parses user intent to identify target board and requirements."""
    intent = state.get("intent", "").lower()
    
    board_target = "Generic"
    if "raspberry pi" in intent or "rpi" in intent:
        board_target = "Raspberry Pi 5 PCIe"
    elif "arduino" in intent:
        board_target = "Arduino"
        
    return {
        **state,
        "board_target": board_target,
        "status": "intent_parsed"
    }

def research_node(state: AgentState) -> AgentState:
    """Extracts datasheets and pinouts (mocking MCP call)."""
    # In production, this calls the MCP `extract_pinout` and `fetch_component_specs`
    return {
        **state,
        "status": "research_complete"
    }

def planning_node(state: AgentState) -> AgentState:
    """Generates a semantic routing strategy."""
    board_target = state.get("board_target")
    plan = []
    
    if board_target == "Raspberry Pi 5 PCIe":
        plan = [
            {"type": "power", "net": "+5V", "width": "1mm"},
            {"type": "diff_pair", "net_pair": ["TX_P", "TX_N"], "impedance": "90ohm", "clearance": "0.2mm"},
            {"type": "diff_pair", "net_pair": ["RX_P", "RX_N"], "impedance": "90ohm", "clearance": "0.2mm"}
        ]
    else:
        plan = [
            {"type": "standard", "net": "default", "width": "0.25mm"}
        ]
        
    return {
        **state,
        "routing_plan": plan,
        "status": "planning_complete"
    }

def execution_node(state: AgentState) -> AgentState:
    """Calls MCP tools to execute the routing plan."""
    # In production, this uses MCP `create_tracks` or `apply_routing_strategy`
    plan = state.get("routing_plan", [])
    results = [{"action": "executed", "plan_item": item} for item in plan]
    
    return {
        **state,
        "execution_results": results,
        "status": "execution_complete"
    }

def verification_node(state: AgentState) -> AgentState:
    """Runs DRC checks and verifies impedance constraints."""
    # Mock DRC check. Introduce artificial error on first pass for self-correction demo.
    retries = state.get("retries", 0)
    errors = []
    if retries == 0 and state.get("board_target") == "Raspberry Pi 5 PCIe":
        errors = ["DRC Violation: TX_P / TX_N impedance mismatch (calculated 85ohm, target 90ohm)"]
        
    return {
        **state,
        "drc_errors": errors,
        "status": "verification_complete"
    }

def self_correction_node(state: AgentState) -> AgentState:
    """Adjusts routing plan based on verification errors."""
    errors = state.get("drc_errors", [])
    plan = state.get("routing_plan", [])
    
    # Adjust plan to fix impedance
    for item in plan:
        if item.get("type") == "diff_pair":
            item["trace_gap"] = "0.15mm" # Example correction
            
    return {
        **state,
        "routing_plan": plan,
        "retries": state.get("retries", 0) + 1,
        "status": "self_corrected"
    }

# Workflow Graph Definition
def build_agent_graph():
    if not StateGraph:
        print("LangGraph not installed. Returning mocked graph structure.")
        return None
        
    workflow = StateGraph(AgentState)
    
    workflow.add_node("parse_intent", parse_intent_node)
    workflow.add_node("research", research_node)
    workflow.add_node("planning", planning_node)
    workflow.add_node("execution", execution_node)
    workflow.add_node("verification", verification_node)
    workflow.add_node("self_correction", self_correction_node)
    
    # Define routing logic
    def should_correct(state: AgentState):
        if len(state.get("drc_errors", [])) > 0 and state.get("retries", 0) < 3:
            return "self_correction"
        return "end"
        
    workflow.set_entry_point("parse_intent")
    workflow.add_edge("parse_intent", "research")
    workflow.add_edge("research", "planning")
    workflow.add_edge("planning", "execution")
    workflow.add_edge("execution", "verification")
    
    workflow.add_conditional_edges(
        "verification",
        should_correct,
        {
            "self_correction": "self_correction",
            "end": END
        }
    )
    workflow.add_edge("self_correction", "execution") # Re-execute after correction
    
    return workflow.compile()

if __name__ == "__main__":
    app = build_agent_graph()
    if app:
        print("LangGraph Agent compiled successfully.")
        initial_state = {
            "intent": "Design a Raspberry Pi 5 PCIe HAT",
            "retries": 0,
            "drc_errors": []
        }
        # To run: result = app.invoke(initial_state)
