"""
ai_core/agent/llm_factory.py
==============================
PILLAR 5 — Hardware Coder System Prompt

The "personality transplant" that makes Gemini think like a Senior ECE Engineer.
Injects live board facts from Agent Memory (Pillar 4) into every planning call.
"""

import os
import json
from pathlib import Path
from typing import Dict, Any, List

from dotenv import load_dotenv
load_dotenv(dotenv_path=Path(__file__).resolve().parent.parent.parent / ".env")

import google.generativeai as genai


HARDWARE_CODER_PROMPT = """You are a Senior Hardware Engineering Agent (Antigravity-level).
Output ONLY raw engineering reasoning followed by a structured JSON plan.
NO conversational filler. STRICT KiCad 10 API usage.

## CRITICAL RULES:
1. COMMITS: Mutations MUST be in board.begin_commit() / board.push_commit(commit, "desc") / board.save().
2. POSITIONS: Use Vector2.from_xy(mm(x), mm(y)). NEVER use Vector2(x, y).
3. UNITS: Use mm(v) helper (converts to NM).
4. SCRATCHPAD: Use execute_engineering_script for ALL geometry (moves, routing, offsets).
5. HELPERS: get_footprint(ref), get_net(name), mm(v), NM=1,000,000.
6. VIAS: via.drill_diameter (NOT via.drill).

## OUTPUT FORMAT:
### THOUGHT
<Short engineering rationale: calculations, layer choices, risk assessment>

```json
[
  {
    "step": 1,
    "action": "Description",
    "server": "neuro_scratchpad",
    "tool": "execute_engineering_script",
    "args": {"script_code": "...", "description": "..."},
    "depends_on": [],
    "rationale": "..."
  }
]
```"""


class LLMFactory:
    def __init__(self):
        api_key = os.getenv("GOOGLE_API_KEY")
        if api_key:
            genai.configure(api_key=api_key)
        else:
            raise ValueError("GOOGLE_API_KEY not found in environment variables.")

        # Primary reasoning model — Hardware Coder personality
        self.model = genai.GenerativeModel(
            model_name="models/gemini-3-flash-preview",
            system_instruction=HARDWARE_CODER_PROMPT,
        )

    def run(
        self,
        context: Dict[str, Any],
        tools: List[Dict],
        goal: str,
        strategy: str,
        memory_context: str = "",
    ) -> str:
        """
        Generate a deep, multi-step engineering plan using the Hardware Coder personality.
        Injects live board state, memory context, and available tools.
        """
        # Inject memory context from Pillar 4 if provided
        memory_block = f"\n{memory_context}\n" if memory_context else ""

        # Summarise tools including the scratchpad
        tool_list = json.dumps([
            {"server": t.get("server"), "tool": t.get("name"), "description": t.get("description", "")}
            for t in tools
        ], indent=2)[:1500]

        prompt = f"""\
## ENGINEERING GOAL
{goal}

## STRATEGY
{strategy}
{memory_block}
## LIVE BOARD STATE
{json.dumps(context, indent=2)[:800]}

## AVAILABLE MCP TOOLS
{tool_list}

## INSTRUCTIONS
First output a THOUGHT block explaining your engineering reasoning.
Then output a JSON plan array.

Each step must have:
- "step": integer
- "action": human-readable description
- "server": MCP server name (use "neuro_scratchpad" for execute_engineering_script)
- "tool": exact tool name
- "args": dict — for execute_engineering_script, include "script_code" and "description"
- "depends_on": list of step numbers
- "rationale": why this specific tool/approach

For complex geometry (move, route, measure), ALWAYS use execute_engineering_script.
For simple reads, use get_board_info or get_nets_list.

Respond with ONLY a JSON code block.
"""
        try:
            response = self.model.generate_content(prompt)
            return response.text
        except Exception as e:
            print(f"Error calling Gemini: {e}")
            return ""
