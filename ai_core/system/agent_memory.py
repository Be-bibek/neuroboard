"""
ai_core/system/agent_memory.py
================================
Pillar 4 — Agent Memory ("Engineer's Notebook")

Persists board facts, successful scripts, and API patterns per-project.
Uses a simple JSON store — no vector DB needed at this stage.
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

log = logging.getLogger("AgentMemory")

GLOBAL_MEMORY_DIR = Path(__file__).resolve().parent.parent.parent / "ai_core" / "memory"
GLOBAL_MEMORY_DIR.mkdir(parents=True, exist_ok=True)


class AgentMemory:
    """
    Per-project memory store. Tracks:
    - board_facts: component positions, net topology, known DRC violations
    - session_history: last 10 completed intents + scripts that worked
    - api_patterns: successful kipy patterns (indexed by keyword)
    """

    def __init__(self, project_name: str = "global"):
        self.project_name = project_name
        self.memory_dir = GLOBAL_MEMORY_DIR / project_name
        self.memory_dir.mkdir(parents=True, exist_ok=True)

        self._facts_path    = self.memory_dir / "board_facts.json"
        self._history_path  = self.memory_dir / "session_history.json"
        self._patterns_path = self.memory_dir / "api_patterns.json"

        self._facts:    Dict[str, Any]  = self._load(self._facts_path, {})
        self._history:  List[Dict]      = self._load(self._history_path, [])
        self._patterns: List[Dict]      = self._load(self._patterns_path, [])

    # ── Helpers ──────────────────────────────────────────────────────────────

    def _load(self, path: Path, default: Any) -> Any:
        try:
            if path.exists():
                return json.loads(path.read_text(encoding="utf-8"))
        except Exception as e:
            log.warning(f"[Memory] Could not load {path.name}: {e}")
        return default

    def _save(self, path: Path, data: Any) -> None:
        try:
            path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        except Exception as e:
            log.error(f"[Memory] Could not save {path.name}: {e}")

    # ── Board Facts ───────────────────────────────────────────────────────────

    def update_board_facts(self, facts: Dict[str, Any]) -> None:
        """Merge new board state into the persistent facts store."""
        self._facts.update(facts)
        self._save(self._facts_path, self._facts)
        log.info(f"[Memory] Board facts updated ({len(self._facts)} keys).")

    def get_board_facts(self) -> Dict[str, Any]:
        return self._facts

    # ── Session History ───────────────────────────────────────────────────────

    def record_session(self, intent: str, script: Optional[str], success: bool, result: str) -> None:
        """Log a completed session (intent + script that worked) to history."""
        entry = {
            "intent":  intent,
            "script":  script,
            "success": success,
            "result":  result[:500],  # cap to avoid huge files
        }
        self._history.insert(0, entry)
        self._history = self._history[:10]  # keep last 10
        self._save(self._history_path, self._history)
        log.info(f"[Memory] Session recorded: success={success}")

    def get_recent_history(self, n: int = 5) -> List[Dict]:
        return self._history[:n]

    # ── API Patterns ──────────────────────────────────────────────────────────

    def save_pattern(self, keyword: str, script: str, description: str) -> None:
        """Save a successful kipy script pattern for future retrieval."""
        # Deduplicate by keyword
        existing = next((p for p in self._patterns if p["keyword"] == keyword), None)
        if existing:
            existing["script"] = script
            existing["description"] = description
        else:
            self._patterns.append({
                "keyword": keyword,
                "script": script,
                "description": description,
            })
        self._save(self._patterns_path, self._patterns)
        log.info(f"[Memory] Pattern saved: '{keyword}'")

    def search_patterns(self, query: str, top_k: int = 3) -> List[Dict]:
        """Keyword search in saved patterns."""
        q = query.lower()
        hits = [p for p in self._patterns if q in p.get("keyword", "").lower()
                or q in p.get("description", "").lower()]
        return hits[:top_k]

    # ── Context Builder ───────────────────────────────────────────────────────

    def build_context_block(self, intent: str) -> str:
        """
        Build a rich context string to inject into the LLM system prompt.
        Includes relevant past patterns and board facts.
        """
        patterns = self.search_patterns(intent)
        history  = self.get_recent_history(3)
        facts    = self._facts

        lines = ["## Engineer's Notebook (from memory)"]

        if facts:
            lines.append(f"\n### Board Facts\n{json.dumps(facts, indent=2)[:600]}")

        if patterns:
            lines.append("\n### Relevant Past Patterns (use these as reference):")
            for p in patterns:
                lines.append(f"- [{p['keyword']}]: {p['description']}")
                lines.append(f"  ```python\n{p['script'][:300]}\n  ```")

        if history:
            lines.append("\n### Recent Session History:")
            for h in history:
                status = "✅" if h["success"] else "❌"
                lines.append(f"- {status} '{h['intent']}' → {h['result'][:100]}")

        return "\n".join(lines)


# ── Global factory ────────────────────────────────────────────────────────────

_memory_cache: Dict[str, AgentMemory] = {}

def get_memory(project_name: str = "global") -> AgentMemory:
    """Returns a cached AgentMemory instance for the given project."""
    if project_name not in _memory_cache:
        _memory_cache[project_name] = AgentMemory(project_name)
    return _memory_cache[project_name]
