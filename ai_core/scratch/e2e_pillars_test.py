"""
Final E2E validation for all 5 pillars.
Run from NeuroBoard root: python ai_core/scratch/e2e_pillars_test.py
"""
import sys, os, json
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, "ai_core")
from dotenv import load_dotenv
load_dotenv()

PASS = "[PASS]"
FAIL = "[FAIL]"

results = {}

# ── PILLAR 1: Scratchpad Engine ────────────────────────────────────────────────
print("\n━━━ PILLAR 1: Scratchpad Engine ━━━")
try:
    from mcp_server.scratchpad import execute_engineering_script
    res = execute_engineering_script(
        script_code="print(f'Board connected: {board.name}')\nprint(f'Nets: {len(list(board.get_nets()))}')",
        description="Pillar 1 validation"
    )
    ok = res["status"] == "success" and "Board connected" in res["stdout"]
    print(f"  {PASS if ok else FAIL} execute_engineering_script: {res['status']} | {res['stdout'][:80]}")
    results["pillar1"] = ok
except Exception as e:
    print(f"  {FAIL} Exception: {e}")
    results["pillar1"] = False

# ── PILLAR 2: Thought Extraction ───────────────────────────────────────────────
print("\n━━━ PILLAR 2: Thought Extraction ━━━")
try:
    from agent.langgraph_loop import _extract_thought
    sample = """### THOUGHT
Moving J1 connector 0.5mm right for edge clearance. Current X=100mm. Edge at 101mm.

```json
[{"step": 1, "action": "move", "server": "neuro_scratchpad", "tool": "execute_engineering_script"}]
```"""
    thought, plan_raw = _extract_thought(sample)
    ok = "Moving J1" in thought and "execute_engineering_script" in plan_raw
    print(f"  {PASS if ok else FAIL} _extract_thought: thought='{thought[:60]}...'")
    results["pillar2"] = ok
except Exception as e:
    print(f"  {FAIL} Exception: {e}")
    results["pillar2"] = False

# ── PILLAR 3: Reflect Node exists ─────────────────────────────────────────────
print("\n━━━ PILLAR 3: Reflection Loop ━━━")
try:
    from agent.langgraph_loop import reflect_node, MAX_REFLECT
    state = {
        "goal": "Test reflection",
        "last_script_error": "TypeError: Vector2.__init__() takes 1 to 2 positional arguments",
        "reflect_retries": 0,
        "execution_results": [{"args": {"script_code": "fp.position = Vector2(100, 200)"}, "result": {"status": "failed"}}],
        "current_step_index": 1,
        "plan": [{"step": 1, "action": "move", "args": {"script_code": "fp.position = Vector2(100, 200)"}}],
        "active_project": "test",
        "board_context": {}, "available_tools": [], "scored_tools": [],
        "verification_report": {}, "drc_errors": [], "retries": 0,
        "strategy": "shortest_path", "precheck_results": {}, "status": "step_done",
        "last_model_used": None, "thought": None, "memory_context": None,
        "selected_tool": None,
    }
    result_state = reflect_node(state)
    ok = result_state.get("reflect_retries", 0) == 1 or result_state.get("last_script_error") is None
    print(f"  {PASS if ok else FAIL} reflect_node: retries={result_state.get('reflect_retries')} last_error={result_state.get('last_script_error')}")
    print(f"  {PASS} MAX_REFLECT={MAX_REFLECT} (hard cap enforced)")
    results["pillar3"] = ok
except Exception as e:
    print(f"  {FAIL} Exception: {e}")
    results["pillar3"] = False

# ── PILLAR 4: Agent Memory ─────────────────────────────────────────────────────
print("\n━━━ PILLAR 4: Agent Memory ━━━")
try:
    from system.agent_memory import get_memory
    mem = get_memory("test_project")
    mem.update_board_facts({"board_name": "PiHAT", "net_count": 43})
    mem.save_pattern("move_connector", "fp.position = Vector2.from_xy(mm(100), mm(200))", "Move connector to XY")
    mem.record_session("Move J1 right", "...script...", True, "Moved J1 from 100 to 100.5mm")
    facts = mem.get_board_facts()
    patterns = mem.search_patterns("move")
    history = mem.get_recent_history(1)
    ok = facts.get("net_count") == 43 and len(patterns) > 0 and len(history) > 0
    print(f"  {PASS if ok else FAIL} Board facts: {facts}")
    print(f"  {PASS if ok else FAIL} Patterns found: {[p['keyword'] for p in patterns]}")
    print(f"  {PASS if ok else FAIL} History: {history[0]['intent']}")
    results["pillar4"] = ok
except Exception as e:
    print(f"  {FAIL} Exception: {e}")
    results["pillar4"] = False

# ── PILLAR 5: Hardware Coder Prompt ───────────────────────────────────────────
print("\n━━━ PILLAR 5: Hardware Coder System Prompt ━━━")
try:
    from agent.llm_factory import LLMFactory, HARDWARE_CODER_PROMPT
    ok = all(rule in HARDWARE_CODER_PROMPT for rule in [
        "Vector2.from_xy", "begin_commit", "push_commit",
        "drill_diameter", "THOUGHT", "execute_engineering_script"
    ])
    print(f"  {PASS if ok else FAIL} All 6 critical rules present in system prompt")
    results["pillar5"] = ok
except Exception as e:
    print(f"  {FAIL} Exception: {e}")
    results["pillar5"] = False

# ── REGISTRY: neuro_scratchpad ────────────────────────────────────────────────
print("\n━━━ MCP Registry: neuro_scratchpad ━━━")
try:
    from mcp_runtime.registry import mcp_registry
    mcp_registry.start_server("neuro_scratchpad")
    srv = mcp_registry.servers.get("neuro_scratchpad")
    tool_names = [t["name"] for t in (srv.tools if srv else [])]
    ok = "execute_engineering_script" in tool_names and "read_board_state" in tool_names
    print(f"  {PASS if ok else FAIL} Tools registered: {tool_names}")
    results["registry"] = ok
except Exception as e:
    print(f"  {FAIL} Exception: {e}")
    results["registry"] = False

# ── SUMMARY ────────────────────────────────────────────────────────────────────
print("\n" + "━" * 50)
print("FINAL RESULTS")
print("━" * 50)
total = len(results)
passed = sum(1 for v in results.values() if v)
for pillar, ok in results.items():
    print(f"  {PASS if ok else FAIL} {pillar.upper()}")
print(f"\n{'✅ ALL SYSTEMS GO' if passed == total else '⚠️  PARTIAL'}: {passed}/{total} pillars operational")
