"""
ai_core/system/env_validator.py
================================
Phase 8.1 Enhancement 2: Dependency & Environment Validator

Performs a structured pre-flight check on startup and emits a
JSON-serializable EnvironmentReport. All downstream modules call
`EnvironmentValidator.run()` exactly once per process.
"""

from __future__ import annotations

import json
import logging
import os
import shutil
import sys
import importlib
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

log = logging.getLogger("SystemLogger")


# ---------------------------------------------------------------------------
# Data Types
# ---------------------------------------------------------------------------

@dataclass
class CheckResult:
    name: str
    status: str       # "PASS" | "WARN" | "FAIL"
    version: Optional[str] = None
    detail:  str = ""

    @property
    def icon(self) -> str:
        return {"PASS": "✅", "WARN": "⚠️", "FAIL": "❌"}.get(self.status, "?")

    def __str__(self) -> str:
        v = f" v{self.version}" if self.version else ""
        msg = f" — {self.detail}" if self.detail else ""
        return f"{self.icon} {self.name}{v}{msg}"


@dataclass
class EnvironmentReport:
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    python_version: str = field(default_factory=lambda: sys.version.split()[0])
    overall: str = "PASS"       # "PASS" | "WARN" | "FAIL"
    checks: List[CheckResult] = field(default_factory=list)

    def add(self, result: CheckResult) -> None:
        self.checks.append(result)
        if result.status == "FAIL" and self.overall != "FAIL":
            self.overall = "FAIL"
        elif result.status == "WARN" and self.overall == "PASS":
            self.overall = "WARN"

    def to_dict(self) -> dict:
        return {
            "timestamp":      self.timestamp,
            "python_version": self.python_version,
            "overall":        self.overall,
            "checks":         [asdict(c) for c in self.checks],
        }

    def log_summary(self) -> None:
        log.info("=" * 60)
        log.info(f"   NeuroBoard Environment Report  [{self.overall}]")
        log.info("=" * 60)
        for c in self.checks:
            log.info(f"   {c}")
        log.info("-" * 60)

    def save(self, path: str) -> None:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2)
        log.info(f"[EnvValidator] Report saved → {path}")


# ---------------------------------------------------------------------------
# Validator Engine
# ---------------------------------------------------------------------------

class EnvironmentValidator:
    """
    Run `EnvironmentValidator.run()` at startup to get a full pre-flight report.
    The `strict` flag causes the process to abort on any FAIL.
    """

    # Python packages: (import_name, pip_name, required)
    PYTHON_DEPS: List[tuple] = [
        ("kipy",              "kipy",             False),   # WARN if missing
        ("pynng",             "pynng",            False),
        ("psutil",            "psutil",           True),    # FAIL if missing
        ("skidl",             "skidl",            False),
        ("yaml",              "pyyaml",           True),
        ("fastapi",           "fastapi",          False),
        ("shapely",           "shapely",          True),
        ("langgraph",         "langgraph",        False),
    ]

    # Environment variables
    ENV_VARS: List[tuple] = [
        ("KICAD8_SYMBOL_DIR", True),    # WARN
        ("KICAD6_SYMBOL_DIR", False),
        ("KICAD7_SYMBOL_DIR", False),
    ]

    # Executables
    EXECUTABLES: List[tuple] = [
        ("kicad-cli", False),           # WARN if missing
        ("kicad-cli.exe", False),
    ]

    @classmethod
    def run(cls,
            report_path: Optional[str] = None,
            strict: bool = False) -> EnvironmentReport:
        """
        Execute all environment checks and return an EnvironmentReport.

        Args:
            report_path: Optional path to save the JSON report.
            strict:      If True, sys.exit(1) on any FAIL result.
        """
        report = EnvironmentReport()

        # 1. Python package checks
        cls._check_python_deps(report)

        # 2. KiCad CLI check
        cls._check_kicad_cli(report)

        # 3. Environment variables
        cls._check_env_vars(report)

        # 4. KiCad IPC socket
        cls._check_ipc_socket(report)

        # 5. JLC2KiCadLib
        cls._check_jlc2kicadlib(report)

        # 6. KiCad symbol libraries
        cls._check_symbol_dirs(report)

        # Finalise
        report.log_summary()
        if report_path:
            report.save(report_path)

        if strict and report.overall == "FAIL":
            log.critical("[EnvValidator] STRICT mode: aborting due to FAIL results.")
            sys.exit(1)

        return report

    # ------------------------------------------------------------------
    # Individual checks
    # ------------------------------------------------------------------

    @staticmethod
    def _check_python_deps(report: EnvironmentReport) -> None:
        for import_name, pip_name, required in EnvironmentValidator.PYTHON_DEPS:
            try:
                mod = importlib.import_module(import_name)
                version = getattr(mod, "__version__", None)
                report.add(CheckResult(
                    name=pip_name,
                    status="PASS",
                    version=version
                ))
            except ImportError:
                report.add(CheckResult(
                    name=pip_name,
                    status="FAIL" if required else "WARN",
                    detail=f"Install with: pip install {pip_name}"
                ))

    @staticmethod
    def _check_kicad_cli(report: EnvironmentReport) -> None:
        candidates = [
            r"C:\Program Files\KiCad\10.0\bin\kicad-cli.exe",
            r"C:\Program Files\KiCad\9.0\bin\kicad-cli.exe",
            "kicad-cli",
        ]
        for c in candidates:
            found = shutil.which(c)
            if found:
                report.add(CheckResult("kicad-cli", "PASS", detail=found))
                return
        report.add(CheckResult(
            "kicad-cli",
            "WARN",
            detail="Not found on PATH. HEADLESS and ERC modes unavailable."
        ))

    @staticmethod
    def _check_env_vars(report: EnvironmentReport) -> None:
        for varname, required in EnvironmentValidator.ENV_VARS:
            val = os.environ.get(varname)
            if val and Path(val).exists():
                report.add(CheckResult(varname, "PASS", detail=val))
            elif val:
                report.add(CheckResult(varname, "WARN", detail=f"Set but path not found: {val}"))
            else:
                status = "WARN" if required else "PASS"
                report.add(CheckResult(varname, status, detail="Not set"))

    @staticmethod
    def _check_ipc_socket(report: EnvironmentReport) -> None:
        sock = Path(r"C:\Users\Bibek\AppData\Local\Temp\kicad\api.sock")
        if sock.exists():
            report.add(CheckResult("KiCad IPC Socket", "PASS", detail=str(sock)))
        else:
            report.add(CheckResult(
                "KiCad IPC Socket",
                "WARN",
                detail="api.sock not found. Open KiCad 10 with a project to enable IPC mode."
            ))

    @staticmethod
    def _check_jlc2kicadlib(report: EnvironmentReport) -> None:
        found = shutil.which("jlc2kicadlib") or shutil.which("JLC2KiCadLib")
        if found:
            report.add(CheckResult("JLC2KiCadLib", "PASS", detail=found))
            return
        # Try pip import
        try:
            importlib.import_module("JLC2KiCadLib")
            report.add(CheckResult("JLC2KiCadLib", "PASS", detail="importable"))
        except ImportError:
            report.add(CheckResult(
                "JLC2KiCadLib",
                "WARN",
                detail="Install with: pip install JLC2KiCadLib"
            ))

    @staticmethod
    def _check_symbol_dirs(report: EnvironmentReport) -> None:
        default_dir = Path(r"C:\Program Files\KiCad\10.0\share\kicad\symbols")
        if default_dir.exists():
            report.add(CheckResult("KiCad Symbol Dir", "PASS", detail=str(default_dir)))
        else:
            report.add(CheckResult(
                "KiCad Symbol Dir",
                "WARN",
                detail=f"Default dir not found: {default_dir}"
            ))
