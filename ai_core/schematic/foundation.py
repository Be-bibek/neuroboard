"""
ai_core/schematic/foundation.py
================================
Phase 7: Hardware DSL Foundation

NeuroModule — the base class for all generative hardware modules.

Design Philosophy:
  - "Schematic-First": Every module is electrically self-contained.
  - "Recipe & Ingredients": Python defines the logic; YAML configures the parts.
  - "Reproductive": Modules compose infinitely without changing core logic.

Orchestration flow:
    User Intent
        ↓ IntentParser
    Structured Spec (JSON)
        ↓ IngredientLoader
    NeuroModule instances
        ↓ DynamicSchematicGenerator
    SKiDL Netlist (.net)
        ↓ ERC validation gate
    KiCad PCB sync (IPC)
        ↓ GenerativePlacer
    Routed Board → Validation Loop
"""

from __future__ import annotations

import logging
import os
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

log = logging.getLogger("SystemLogger")

# ---------------------------------------------------------------------------
# SKiDL environment bootstrap (idempotent — safe to import multiple times)
# ---------------------------------------------------------------------------
os.environ.setdefault("KICAD_SYMBOL_DIR",  r"C:\Program Files\KiCad\10.0\share\kicad\symbols")
os.environ.setdefault("KICAD8_SYMBOL_DIR", r"C:\Program Files\KiCad\10.0\share\kicad\symbols")
os.environ.setdefault("SKIDL_NOUI", "1")

try:
    from skidl import Net, Part, KICAD8, lib_search_paths  # type: ignore
    lib_search_paths[KICAD8].append(r"C:\Program Files\KiCad\10.0\share\kicad\symbols")
    
    # Add local NeuroBoard lib path
    LOCAL_LIB = os.path.join(os.getcwd(), "lib")
    if os.path.exists(LOCAL_LIB) and LOCAL_LIB not in lib_search_paths[KICAD8]:
        lib_search_paths[KICAD8].append(LOCAL_LIB)
        
    SKIDL_OK = True
    log.info(f"[foundation] SKiDL search paths: {lib_search_paths[KICAD8]}")
except ImportError:
    SKIDL_OK = False
    log.warning("[foundation] SKiDL not installed — modules will operate in MOCK mode.")

# ---------------------------------------------------------------------------
# Global Power Domain registry
# ---------------------------------------------------------------------------

class PowerDomain:
    """
    Singleton registry of global power nets shared across all NeuroModules.
    Guarantees that "GND" in Module A is the same net as "GND" in Module B.
    """
    _nets: Dict[str, Any] = {}

    @classmethod
    def get(cls, name: str) -> Any:
        """Return (or lazily create) a global power net by name."""
        if not SKIDL_OK:
            return name          # mock: return plain string in test mode
        if name not in cls._nets:
            cls._nets[name] = Net(name)
            log.debug(f"[PowerDomain] Created global net '{name}'")
        return cls._nets[name]

    @classmethod
    def reset(cls) -> None:
        """Clear all cached nets (call before each synthesis run)."""
        cls._nets.clear()
        log.debug("[PowerDomain] Global nets cleared.")

    # Standard domains used by every HAT-class board
    GND  = property(lambda self: self.get("GND"))
    V5   = property(lambda self: self.get("+5V"))
    V3V3 = property(lambda self: self.get("+3V3"))
    V1V8 = property(lambda self: self.get("+1V8"))


# ---------------------------------------------------------------------------
# ElectricalConstraints — structured electrical spec for an Interface
# ---------------------------------------------------------------------------

from dataclasses import dataclass, field as dc_field

@dataclass
class ElectricalConstraints:
    """
    Electrical contract for an Interface bus.
    Validated at synthesis time to catch gross mis-connections.
    """
    # Signal integrity
    max_freq_hz:          Optional[float] = None   # e.g. 400_000 for I2C Fast-Mode
    max_trace_length_mm:  Optional[float] = None   # e.g. 300 mm
    impedance_ohm:        Optional[float] = None   # e.g. 50 or 90
    differential:         bool  = False

    # Power
    max_current_ma:       Optional[float] = None
    voltage_level_v:      Optional[float] = None   # e.g. 3.3 or 1.8

    # Pull-ups / Pull-downs
    pullup_kohm:          Optional[float] = None
    pulldown_kohm:        Optional[float] = None

    # EMC
    max_slew_rate_v_ns:   Optional[float] = None

    def describe(self) -> str:
        parts = []
        if self.max_freq_hz:
            parts.append(f"f_max={self.max_freq_hz/1e3:.0f}kHz")
        if self.impedance_ohm:
            parts.append(f"Z={self.impedance_ohm}Ω")
        if self.differential:
            parts.append("diff-pair")
        if self.pullup_kohm:
            parts.append(f"pull-up={self.pullup_kohm}kΩ")
        return ", ".join(parts) or "unconstrained"


# ---------------------------------------------------------------------------
# Interface — Group of nets for modular connectivity
# ---------------------------------------------------------------------------

class Interface:
    """
    Atopile-inspired signal grouping with optional electrical constraints.
    Enables high-level connectivity: `self.mcu.i2c += self.sensor.i2c`
    """
    def __init__(self, name: str, signals: List[str], module_name: str = "",
                 constraints: Optional[ElectricalConstraints] = None):
        self.name = name
        self.signals = signals
        self.constraints: Optional[ElectricalConstraints] = constraints
        bus_prefix = f"{module_name}_" if module_name else ""
        self.nets: Dict[str, Any] = {}

        for sig in signals:
            net_name = f"{bus_prefix}{name}_{sig}"
            if SKIDL_OK:
                self.nets[sig] = Net(net_name)
            else:
                self.nets[sig] = net_name

    def __getitem__(self, key: str) -> Any:
        return self.nets.get(key)

    def __iadd__(self, other: Any) -> "Interface":
        """Overload += to connect two interfaces together."""
        if not isinstance(other, Interface):
            log.warning(f"[Interface] Cannot connect {self.name} to non-Interface type.")
            return self
        # Constraint compatibility check
        self._check_compatibility(other)
        for sig in self.signals:
            if sig in other.nets:
                if SKIDL_OK:
                    self.nets[sig] += other.nets[sig]
                else:
                    log.debug(f"[Mock] Connected {self.name}.{sig} → {other.name}.{sig}")
        return self

    def validate_constraints(self) -> List[str]:
        """
        Self-validate that the interface's electrical constraints are internally
        consistent. Returns a list of violation strings (empty = OK).
        """
        violations: List[str] = []
        c = self.constraints
        if c is None:
            return violations
        if c.differential and len(self.signals) < 2:
            violations.append(f"{self.name}: differential interface needs ≥2 signals.")
        if c.max_freq_hz and c.max_freq_hz > 1e9:
            violations.append(f"{self.name}: max_freq_hz > 1 GHz is unusually high.")
        if c.pullup_kohm and c.pulldown_kohm:
            violations.append(f"{self.name}: cannot have both pullup and pulldown.")
        return violations

    def _check_compatibility(self, other: "Interface") -> None:
        """Cross-check constraints between two interfaces being connected."""
        sc, oc = self.constraints, other.constraints
        if sc and oc:
            if sc.voltage_level_v and oc.voltage_level_v:
                if abs(sc.voltage_level_v - oc.voltage_level_v) > 0.1:
                    log.warning(
                        f"[Interface] ⚠️  Voltage mismatch: {self.name} "
                        f"({sc.voltage_level_v}V) ↔ {other.name} ({oc.voltage_level_v}V). "
                        f"Level-shifting required!"
                    )
            if sc.differential != oc.differential:
                log.warning(
                    f"[Interface] ⚠️  Topology mismatch: {self.name} is "
                    f"{'diff' if sc.differential else 'single-ended'} but "
                    f"{other.name} is {'diff' if oc.differential else 'single-ended'}."
                )


# ---------------------------------------------------------------------------
# NeuroModule — Abstract Base Class
# ---------------------------------------------------------------------------

class NeuroModule(ABC):
    """
    Base class for all reproductive hardware modules.

    Subclasses define the electrical "Recipe" (SKiDL wiring logic).
    The "Ingredients" (part values, count, footprints) are injected via `config`.

    Attributes:
        name          Unique module name, e.g. "SD_PRIMARY"
        config        Dict of user/YAML-driven parameters
        parts         All SKiDL Part instances created by this module
        nets          Module-local nets (power nets come from PowerDomain)
        submodules    Dict of child NeuroModule instances
        interfaces    Dict of Interface instances exposed for connectivity
        metadata      Placement, thermal, and SI hints for downstream engines
    """

    def __init__(self, name: str, config: Optional[Dict[str, Any]] = None):
        self.name    = name
        self.config  = config or {}
        self.parts:  List[Any]        = []
        self.nets:   Dict[str, Any]   = {}
        self.submodules: Dict[str, Any] = {}
        self.interfaces: Dict[str, Interface] = {}
        
        self.metadata: Dict[str, Any] = {
            "placement_hint": "auto",   # "edge" | "center" | "auto"
            "thermal_class":  "low",    # "low" | "medium" | "high"
            "interface":      "none",   # "PCIe" | "SDIO" | "USB" | ...
            "net_names":      [],       # all nets exposed by this module
        }
        log.debug(f"[NeuroModule] Initialising '{self.name}' ({self.__class__.__name__})")
        
        # Build logic: 
        # 1. Subclasses instantiate interfaces in __init__ (optional)
        # 2. Subclasses implement build() for internal wiring
        self.build()

    # ------------------------------------------------------------------
    # Abstract Interface — subclasses must implement
    # ------------------------------------------------------------------

    @abstractmethod
    def build(self) -> None:
        """
        Define the internal wiring logic for this module using SKiDL.
        All Part and Net creation must happen inside this method.
        """

    # ------------------------------------------------------------------
    # Helper utilities — available to all subclasses
    # ------------------------------------------------------------------

    def _part(self, lib: str, symbol: str, footprint: str,
              value: str = "", ref_prefix: str = "U", lcsc: str = None) -> Any:
        """
        Create a SKiDL Part. If lcsc is provided, attempts to fetch it first.
        """
        if lcsc:
            from system.lcsc_fetcher import LcscFetcher
            try:
                fetcher = LcscFetcher()
                log.info(f"[NeuroModule] Pre-fetching LCSC part: {lcsc}")
                res = fetcher.fetch_component(lcsc)
                if res["status"] == "success":
                    # Verify the kicad_sym file was actually downloaded
                    import shutil
                    resolved_lib = shutil.which(f"{lcsc}.kicad_sym")
                    # Try the lib/ directory directly
                    lib_dir = os.path.join(os.getcwd(), "lib", f"{lcsc}.kicad_sym")
                    if os.path.exists(lib_dir):
                        lib    = lcsc
                        symbol = lcsc
                        log.info(f"[NeuroModule] LCSC part {lcsc} resolved → {lib_dir}")
                    else:
                        log.warning(
                            f"[NeuroModule] LCSC fetch reported success for {lcsc} "
                            f"but .kicad_sym not found in lib/. "
                            f"Falling back to standard: {lib}:{symbol}"
                        )
            except Exception as e:
                log.warning(f"[NeuroModule] LCSC fetch failed for {lcsc}: {e}. "
                            f"Using: {lib}:{symbol}.")

        if not SKIDL_OK:
            log.debug(f"[NeuroModule:{self.name}] MOCK Part({lib}, {symbol})")
            return _MockPart(symbol, ref_prefix)

        try:
            p = Part(lib, symbol, footprint=footprint, dest=TEMPLATE)
            p = p(value=value) if value else p()
            self.parts.append(p)
            return p
        except Exception as e:
            log.error(f"[NeuroModule] SKiDL Part instantiation failed: {e}")
            raise e

    def _net(self, name: str) -> Any:
        """Create or return a module-local net, registered in metadata."""
        qualified = f"{self.name}_{name}" if not name.startswith("+") else name
        if qualified not in self.nets:
            self.nets[qualified] = Net(qualified) if SKIDL_OK else qualified
            self.metadata["net_names"].append(qualified)
        return self.nets[qualified]

    def _power(self, rail: str) -> Any:
        """Get a global power net from the PowerDomain registry."""
        return PowerDomain.get(rail)

    def _add_decoupling(self, power_rail: str, count: int = 1,
                         value: str = "100nF",
                         footprint: str = "Capacitor_SMD:C_0402_1005Metric") -> None:
        """
        Insert decoupling capacitors between a power rail and GND.
        Follows best-practice: one cap per power pin, placed close to the IC.
        """
        for _ in range(count):
            if SKIDL_OK:
                cap = Part("Device", "C", footprint=footprint, value=value)
                pwr_net = PowerDomain.get(power_rail)
                gnd_net = PowerDomain.get("GND")
                pwr_net += cap["1"]
                gnd_net += cap["2"]
                self.parts.append(cap)
            log.debug(f"[NeuroModule:{self.name}] Added {value} decoupling on {power_rail}")

    def _set_metadata(self, **kwargs: Any) -> None:
        """Convenience method to update placement/SI metadata."""
        self.metadata.update(kwargs)

    def summary(self) -> Dict[str, Any]:
        """Return a summary dict for logging and UI telemetry."""
        return {
            "module":    self.name,
            "class":     self.__class__.__name__,
            "parts":     len(self.parts),
            "nets":      list(self.nets.keys()),
            "metadata":  self.metadata,
        }


# ---------------------------------------------------------------------------
# Mock helper for test/offline mode
# ---------------------------------------------------------------------------

class _MockPart:
    """Stands in for a SKiDL Part when the library is not installed."""
    def __init__(self, symbol: str, ref_prefix: str):
        self.symbol     = symbol
        self.ref_prefix = ref_prefix

    def __getitem__(self, key: str):   # part["pin_name"]
        return f"_mock_pin_{key}"

    def __iadd__(self, other):         # net += part["pin"]
        return self

    def __repr__(self):
        return f"MockPart({self.symbol})"


# ---------------------------------------------------------------------------
# TEMPLATE sentinel (used internally by _part helper)
# ---------------------------------------------------------------------------
try:
    if SKIDL_OK:
        from skidl import Part, Net, TEMPLATE, lib_search_paths, KICAD8
        # Add local NeuroBoard lib path
        LOCAL_LIB = os.path.join(os.getcwd(), "lib")
        if LOCAL_LIB not in lib_search_paths[KICAD8]:
            lib_search_paths[KICAD8].append(LOCAL_LIB)
        log.info(f"[foundation] SKiDL search paths: {lib_search_paths[KICAD8]}")
    else:
        Part = Net = None
except ImportError:
    TEMPLATE = None
