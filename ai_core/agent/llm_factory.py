import os
import json
from pathlib import Path
from typing import Dict, Any, List

from dotenv import load_dotenv
load_dotenv(dotenv_path=Path(__file__).resolve().parent.parent.parent / ".env")

import google.generativeai as genai

class LLMFactory:
    def __init__(self):
        # Initialize Google GenAI
        api_key = os.getenv("GOOGLE_API_KEY")
        if api_key:
            genai.configure(api_key=api_key)
        else:
            raise ValueError("GOOGLE_API_KEY not found in environment variables.")

        # Configure the model
        # Using gemini-1.5-flash as the primary reasoning engine per the instructions
        self.model = genai.GenerativeModel(
            model_name="gemini-1.5-flash",
            system_instruction="You are an Expert ECE Hardware Engineer. Your goal is to generate precise, valid JSON plans for KiCad 10 using the available MCP tools."
        )

    def run(self, context: Dict[str, Any], tools: List[Dict], goal: str, strategy: str) -> str:
        """
        Accepts the PCB context (footprints, nets, design rules), tools, user goal,
        and overarching strategy, then calls the Gemini API to generate a JSON plan.
        """
        prompt = f"""
USER GOAL: {goal}
OVERARCHING STRATEGY: {strategy}

LIVE BOARD STATE:
{json.dumps(context, indent=2)[:800]}

AVAILABLE TOOLS (ranked by relevance):
{json.dumps(tools, indent=2)[:1000]}

Generate a DEEP, multi-step structured plan as a JSON array.
Each step MUST have:
  - "step": integer (1-based)
  - "action": what this step does
  - "server": which MCP server
  - "tool": exact tool name from the list
  - "args": dict of arguments (use real values from board context where possible)
  - "depends_on": list of step numbers this depends on (empty if first)
  - "rationale": why this tool was chosen for this step

Respond ONLY with a JSON code block.

Example:
```json
[
  {{"step": 1, "action": "Capture current board state", "server": "neuro_layout", "tool": "get_board_info", "args": {{}}, "depends_on": [], "rationale": "Need board context before routing"}},
  {{"step": 2, "action": "Route USB D+ differential trace", "server": "neuro_router", "tool": "route_trace", "args": {{"net": "/USB_DP", "width": 0.2, "layer": "F.Cu"}}, "depends_on": [1], "rationale": "USB requires controlled impedance 90ohm differential pair"}}
]
```"""
        try:
            response = self.model.generate_content(prompt)
            return response.text
        except Exception as e:
            print(f"Error calling Gemini: {e}")
            return ""
