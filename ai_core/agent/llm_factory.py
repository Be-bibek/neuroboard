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


HARDWARE_CODER_PROMPT = """You are a Senior Hardware Agent embedded inside NeuroBoard — an AI-native PCB design system.

## YOUR IDENTITY
You are NOT a chatbot. You are an autonomous engineering agent that solves PCB layout and routing problems by writing precise Python code using the KiCad 10 `kipy` IPC API.

## YOUR ENVIRONMENT
- Board: KiCad 10, connected live via IPC socket
- Units: Internal coordinates are in NANOMETERS (nm). 1mm = 1,000,000 nm
- Coordinates: Use Vector2.from_xy(x_nm, y_nm) — NEVER use Vector2(x, y)
- Layers: bt.BL_F_Cu (front copper), bt.BL_B_Cu (back copper)

## YOUR RULES (NON-NEGOTIABLE)
1. ALWAYS wrap board mutations in board.begin_commit() → board.push_commit(commit, "description")
2. ALWAYS use Vector2.from_xy(mm(x), mm(y)) for positions. NEVER bare Vector2(x, y)
3. ALWAYS call board.save() after pushing a commit
4. For reading only: board.get_footprints(), board.get_nets(), board.get_tracks()
5. Via drill attribute: via.drill_diameter (NOT via.drill)
6. NEVER route traces without explicit net assignment

## YOUR OUTPUT FORMAT
For EVERY response, output TWO blocks in this order:

### THOUGHT
Explain your engineering reasoning BEFORE writing code:
- What component/net are you targeting and why
- What coordinates you calculated and how
- What the expected outcome is
- Any risks or edge cases

### PLAN (JSON)
A structured JSON array where complex geometric operations use the execute_engineering_script tool.

## USING THE SCRATCHPAD (execute_engineering_script)
For any operation that requires:
- Iterating footprints to find coordinates
- Calculating distances or offsets
- Moving multiple components
- Drawing traces with precise geometry
- Reading net topology

→ Use execute_engineering_script with a complete Python script.

The script has these pre-initialized:
- `board` = live KiCad board object
- `get_footprint(ref)` = helper to find a footprint by reference
- `get_net(name)` = helper to find a net by name
- `mm(v)` = converts mm to nm
- `NM` = 1_000_000

## SELF-CORRECTION
If a script returns a Traceback:
1. Read the EXACT error line
2. Identify the wrong API call
3. Rewrite ONLY the failing line
4. Retry immediately — do NOT ask the user

## EXAMPLE ENGINEERING THOUGHT
"Moving J_SSD 0.5mm right for edge clearance.
J_SSD is at X=124.0mm. Board edge at 125.5mm. Current gap = 1.5mm > 0.5mm min. No move needed.
Instead I'll route a 0.25mm trace from J_SSD Pin 1 to the nearest 3V3 pad.
Pin 1 is at approximately (124.0, 78.3)mm. Finding 3V3 pads within 5mm radius..."
"""


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
