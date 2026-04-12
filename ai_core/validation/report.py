"""
ai_core/validation/report.py
==============================
Phase 8.1 Enhancement 5: Standardized ERC/DRC/HAT Validation Report

Provides a single, unified ValidationReport type used by ALL validators
(ERC, DRC, HAT Compliance, DFM, SI) so the orchestrator can aggregate
them into a consistent MasterReport.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

log = logging.getLogger("SystemLogger")


# ---------------------------------------------------------------------------
# Individual Violation Record
# ---------------------------------------------------------------------------

@dataclass
class Violation:
    code: str                        # e.g. "ERC_UNCONNECTED_PIN"
    severity: str                    # "error" | "warning" | "info"
    message: str
    location: Optional[str] = None  # e.g. "R3 Pin 2" or "(x=12.5, y=34.2)"
    rule: Optional[str] = None      # e.g. "KiCad-HAT-R2"
    auto_fixable: bool = False

    @property
    def is_error(self) -> bool:
        return self.severity == "error"

    def to_dict(self) -> dict:
        return asdict(self)


# ---------------------------------------------------------------------------
# Unified ValidationReport
# ---------------------------------------------------------------------------

@dataclass
class ValidationReport:
    """
    Single canonical report type for ALL NeuroBoard validation stages.

    Usage:
        report = ValidationReport(tool="ERC", board_path="pi_hat.kicad_sch")
        report.add_violation(Violation("UNCONNECTED", "error", "Pin D1-1 unconnected"))
        report.finalize()
        report.to_json("reports/erc.json")
    """
    tool: str                            # "ERC" | "DRC" | "HAT_COMPLIANCE" | "DFM" | "SI" | "PDN"
    board_path: str = ""
    passed: bool = False
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    violations: List[Violation] = field(default_factory=list)
    warnings:   List[Violation] = field(default_factory=list)
    metadata:   Dict[str, Any] = field(default_factory=dict)
    duration_sec: float = 0.0

    # ------------------------------------------------------------------
    # Mutation helpers
    # ------------------------------------------------------------------

    def add_violation(self, code: str, severity: str, message: str,
                      location: Optional[str] = None,
                      rule: Optional[str] = None,
                      auto_fixable: bool = False) -> None:
        v = Violation(code=code, severity=severity, message=message,
                      location=location, rule=rule, auto_fixable=auto_fixable)
        if severity == "warning":
            self.warnings.append(v)
        else:
            self.violations.append(v)

    def finalize(self) -> "ValidationReport":
        """
        Determine overall pass/fail status.
        Passed = zero errors (warnings are acceptable).
        """
        self.passed = all(not v.is_error for v in self.violations)
        return self

    # ------------------------------------------------------------------
    # Serialisation
    # ------------------------------------------------------------------

    def to_dict(self) -> dict:
        return {
            "tool":         self.tool,
            "board_path":   self.board_path,
            "passed":       self.passed,
            "timestamp":    self.timestamp,
            "duration_sec": self.duration_sec,
            "summary": {
                "errors":   sum(1 for v in self.violations if v.is_error),
                "warnings": len(self.warnings) + sum(1 for v in self.violations if not v.is_error),
            },
            "violations": [v.to_dict() for v in self.violations],
            "warnings":   [v.to_dict() for v in self.warnings],
            "metadata":   self.metadata,
        }

    def to_json(self, path: str) -> None:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2)
        log.info(f"[{self.tool}] Report saved → {path}")

    def to_html(self, path: str) -> None:
        """Minimal HTML report for browser preview."""
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        status_color = "#27ae60" if self.passed else "#e74c3c"
        rows = ""
        for v in (self.violations + self.warnings):
            color = "#e74c3c" if v.is_error else "#f39c12"
            rows += (
                f"<tr style='color:{color}'>"
                f"<td>{v.severity.upper()}</td>"
                f"<td>{v.code}</td>"
                f"<td>{v.message}</td>"
                f"<td>{v.location or ''}</td>"
                f"</tr>"
            )
        html = f"""<!DOCTYPE html>
<html><head><meta charset='utf-8'><title>{self.tool} Report</title>
<style>body{{font-family:monospace;background:#1a1a2e;color:#eee}}
table{{width:100%;border-collapse:collapse}}th,td{{padding:6px;border:1px solid #444}}
th{{background:#16213e}}</style></head>
<body>
<h2 style='color:{status_color}'>{self.tool} — {'PASS ✅' if self.passed else 'FAIL ❌'}</h2>
<p>Board: {self.board_path} | {self.timestamp}</p>
<table><tr><th>Severity</th><th>Code</th><th>Message</th><th>Location</th></tr>
{rows if rows else "<tr><td colspan='4'>No violations.</td></tr>"}
</table></body></html>"""
        with open(path, "w", encoding="utf-8") as f:
            f.write(html)
        log.info(f"[{self.tool}] HTML Report saved → {path}")

    def __repr__(self) -> str:
        e = sum(1 for v in self.violations if v.is_error)
        w = len(self.warnings)
        return f"ValidationReport(tool={self.tool}, passed={self.passed}, errors={e}, warnings={w})"


# ---------------------------------------------------------------------------
# MasterReport — aggregate of multiple ValidationReports
# ---------------------------------------------------------------------------

@dataclass
class MasterReport:
    """Aggregates all stage reports into a single top-level document."""
    project: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    overall: bool = True
    stages: Dict[str, ValidationReport] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def add_stage(self, report: ValidationReport) -> None:
        self.stages[report.tool] = report
        if not report.passed:
            self.overall = False

    def to_dict(self) -> dict:
        return {
            "project":   self.project,
            "timestamp": self.timestamp,
            "overall":   self.overall,
            "stages":    {k: v.to_dict() for k, v in self.stages.items()},
            "metadata":  self.metadata,
        }

    def to_json(self, path: str) -> None:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2)
        log.info(f"[MasterReport] Saved → {path}")
