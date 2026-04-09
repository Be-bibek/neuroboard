"""
NeuroBoard AI Compiler — Strategy Layer
========================================
Translates high-level *intents* into concrete, batched MCP tool-call plans.
Instead of the AI issuing 40 individual placement calls it asks the compiler
to expand an intent such as "square_leds" into a placement matrix, then
issues a single batch plan that the bridge executes sequentially.

Architecture
------------
Intent  ──►  StrategyCompiler.compile()  ──►  PlacementPlan
                                                    │
                                                    ▼
                                           [ {tool, params}, … ]   (MCP calls)

Usage
-----
    from ai_core.compiler import StrategyCompiler, Intent

    compiler = StrategyCompiler()
    plan = compiler.compile(
        Intent(
            name="square_leds",
            params={
                "reference_prefix": "D",
                "footprint": "LED_THT:LED_D5.0mm",
                "count": 4,
                "center_x_mm": 100.0,
                "center_y_mm": 100.0,
                "spacing_mm": 10.0,
                "start_reference": 1,
            },
        )
    )
    for call in plan.tool_calls:
        print(call)
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from typing import Any


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------


@dataclass
class Intent:
    """A high-level design intent submitted to the compiler."""

    name: str
    params: dict[str, Any] = field(default_factory=dict)


@dataclass
class ToolCall:
    """A single resolved MCP tool invocation."""

    tool: str
    params: dict[str, Any]

    def __repr__(self) -> str:
        return f"ToolCall(tool={self.tool!r}, params={self.params})"


@dataclass
class PlacementPlan:
    """The compiled output — an ordered list of MCP tool calls."""

    intent: Intent
    tool_calls: list[ToolCall] = field(default_factory=list)

    def summary(self) -> str:
        lines = [f"PlacementPlan for intent '{self.intent.name}':"]
        for i, call in enumerate(self.tool_calls, 1):
            lines.append(f"  {i:3d}. {call.tool}({call.params})")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Strategy implementations
# ---------------------------------------------------------------------------


class _StrategyBase:
    """Abstract base for all placement strategies."""

    intent_name: str = ""

    def compile(self, params: dict[str, Any]) -> list[ToolCall]:  # noqa: D102
        raise NotImplementedError


class _SquareGridStrategy(_StrategyBase):
    """
    Arrange N components in the closest square grid pattern.

    Required params
    ---------------
    reference_prefix : str   e.g. "D"
    footprint        : str   e.g. "LED_THT:LED_D5.0mm"
    count            : int   total number of components (e.g. 4)
    center_x_mm      : float X centre of the grid on the PCB
    center_y_mm      : float Y centre of the grid on the PCB
    spacing_mm       : float pitch between component centres

    Optional params
    ---------------
    start_reference  : int   first reference number (default 1)
    rotation_deg     : float rotation applied to every component (default 0.0)
    net_name         : str   if set, a single add_net call is prepended
    """

    intent_name = "square_leds"

    def compile(self, params: dict[str, Any]) -> list[ToolCall]:
        prefix = params["reference_prefix"]
        footprint = params["footprint"]
        count = int(params["count"])
        cx = float(params["center_x_mm"])
        cy = float(params["center_y_mm"])
        spacing = float(params["spacing_mm"])
        start_ref = int(params.get("start_reference", 1))
        rotation = float(params.get("rotation_deg", 0.0))
        net_name: str | None = params.get("net_name")

        # Determine grid dimensions (prefer square, bias wider)
        cols = math.ceil(math.sqrt(count))
        rows = math.ceil(count / cols)

        # Grid origin so the grid is centred on (cx, cy)
        origin_x = cx - (cols - 1) * spacing / 2.0
        origin_y = cy - (rows - 1) * spacing / 2.0

        calls: list[ToolCall] = []

        # Optionally ensure the net exists first
        if net_name:
            calls.append(ToolCall(tool="add_net", params={"net_name": net_name}))

        ref_number = start_ref
        placed = 0
        for row in range(rows):
            for col in range(cols):
                if placed >= count:
                    break
                x = origin_x + col * spacing
                y = origin_y + row * spacing
                reference = f"{prefix}{ref_number}"

                calls.append(
                    ToolCall(
                        tool="place_component",
                        params={
                            "reference": reference,
                            "footprint": footprint,
                            "x": round(x, 4),
                            "y": round(y, 4),
                            "rotation": rotation,
                        },
                    )
                )
                ref_number += 1
                placed += 1

        return calls


class _CircleStrategy(_StrategyBase):
    """
    Arrange N components evenly around a circle.

    Required params
    ---------------
    reference_prefix, footprint, count, center_x_mm, center_y_mm,
    radius_mm        : float  radius of the circle

    Optional params
    ---------------
    start_reference, start_angle_deg (default 0), face_outward (default True)
    """

    intent_name = "circle_leds"

    def compile(self, params: dict[str, Any]) -> list[ToolCall]:
        prefix = params["reference_prefix"]
        footprint = params["footprint"]
        count = int(params["count"])
        cx = float(params["center_x_mm"])
        cy = float(params["center_y_mm"])
        radius = float(params["radius_mm"])
        start_ref = int(params.get("start_reference", 1))
        start_angle = float(params.get("start_angle_deg", 0.0))
        face_outward = bool(params.get("face_outward", True))

        calls: list[ToolCall] = []
        angle_step = 360.0 / count

        for i in range(count):
            angle_deg = start_angle + i * angle_step
            angle_rad = math.radians(angle_deg)
            x = cx + radius * math.cos(angle_rad)
            y = cy + radius * math.sin(angle_rad)
            rotation = angle_deg if face_outward else (angle_deg + 180.0)

            calls.append(
                ToolCall(
                    tool="place_component",
                    params={
                        "reference": f"{prefix}{start_ref + i}",
                        "footprint": footprint,
                        "x": round(x, 4),
                        "y": round(y, 4),
                        "rotation": round(rotation, 2),
                    },
                )
            )

        return calls


class _LinearRowStrategy(_StrategyBase):
    """
    Arrange N components in a single horizontal or vertical line.

    Required params
    ---------------
    reference_prefix, footprint, count, start_x_mm, start_y_mm, spacing_mm

    Optional params
    ---------------
    axis             : "x" | "y"   (default "x")
    start_reference, rotation_deg
    """

    intent_name = "linear_row"

    def compile(self, params: dict[str, Any]) -> list[ToolCall]:
        prefix = params["reference_prefix"]
        footprint = params["footprint"]
        count = int(params["count"])
        sx = float(params["start_x_mm"])
        sy = float(params["start_y_mm"])
        spacing = float(params["spacing_mm"])
        axis = params.get("axis", "x")
        start_ref = int(params.get("start_reference", 1))
        rotation = float(params.get("rotation_deg", 0.0))

        calls: list[ToolCall] = []
        for i in range(count):
            x = sx + (i * spacing if axis == "x" else 0.0)
            y = sy + (i * spacing if axis == "y" else 0.0)
            calls.append(
                ToolCall(
                    tool="place_component",
                    params={
                        "reference": f"{prefix}{start_ref + i}",
                        "footprint": footprint,
                        "x": round(x, 4),
                        "y": round(y, 4),
                        "rotation": rotation,
                    },
                )
            )
        return calls


class _PCIeRouteStrategy(_StrategyBase):
    """
    Generate a differential-pair routing intent for PCIe / high-speed lanes.

    Physics constraints are hardcoded for the **JLCPCB JLC04161H-3313**
    4-layer 1.6 mm FR4 stackup targeting 100 Ω differential impedance:

        Trace Width  = 0.15 mm  →  150 000 IU
        Trace Space  = 0.15 mm  →  150 000 IU

    Unit Rule
    ---------
    KiCad Internal Units (IU) use nanometre resolution:
        1 mm = 1 000 000 IU

    Required params
    ---------------
    source_ref : str   Reference designator of the source (e.g. "U1")
    target_ref : str   Reference designator of the target (e.g. "J1")

    Optional params
    ---------------
    width_mm           : float  Override trace width  (default 0.15)
    spacing_mm         : float  Override trace gap     (default 0.15)
    target_impedance   : float  Target Z-diff in Ω     (default 100)
    layer              : str    Routing layer          (default "F.Cu")
    """

    intent_name = "route_pcie_lane"

    # JLCPCB JLC04161H-3313 stackup constants
    _DEFAULT_WIDTH_MM: float = 0.15
    _DEFAULT_SPACING_MM: float = 0.15
    _DEFAULT_IMPEDANCE: float = 100.0
    _MM_TO_IU: int = 1_000_000  # 1 mm = 1 000 000 Internal Units (nm)

    def compile(self, params: dict[str, Any]) -> list[ToolCall]:
        source_ref: str = params["source_ref"]
        target_ref: str = params["target_ref"]

        width_mm = float(params.get("width_mm", self._DEFAULT_WIDTH_MM))
        spacing_mm = float(params.get("spacing_mm", self._DEFAULT_SPACING_MM))
        impedance = float(params.get("target_impedance", self._DEFAULT_IMPEDANCE))
        layer = params.get("layer", "F.Cu")

        # Convert mm → KiCad Internal Units (nanometres)
        width_iu = int(width_mm * self._MM_TO_IU)
        spacing_iu = int(spacing_mm * self._MM_TO_IU)

        # Build the structured routing intent
        route_intent = {
            "action": "route_diff_pair",
            "source": source_ref,
            "dest": target_ref,
            "width_iu": width_iu,
            "spacing_iu": spacing_iu,
            "target_impedance": impedance,
            "layer": layer,
            "stackup": "JLC04161H-3313",
            "stackup_notes": (
                "4-layer 1.6mm FR4, 100Ω diff impedance. "
                f"Trace W={width_mm}mm, S={spacing_mm}mm."
            ),
        }

        # Emit a single tool-call that carries the full intent as JSON
        return [
            ToolCall(
                tool="route_differential_pair",
                params=route_intent,
            )
        ]


# ---------------------------------------------------------------------------
# StrategyCompiler — public API
# ---------------------------------------------------------------------------


class StrategyCompiler:
    """
    Central compiler that dispatches intents to their strategy implementation.

    Register additional strategies via :py:meth:`register`.
    """

    def __init__(self) -> None:
        self._strategies: dict[str, _StrategyBase] = {}
        # Register built-in strategies
        for strategy_cls in (
            _SquareGridStrategy,
            _CircleStrategy,
            _LinearRowStrategy,
            _PCIeRouteStrategy,
        ):
            instance = strategy_cls()
            self._strategies[instance.intent_name] = instance

    def register(self, strategy: _StrategyBase) -> None:
        """Register a custom strategy at runtime."""
        self._strategies[strategy.intent_name] = strategy

    def compile(self, intent: Intent) -> PlacementPlan:
        """
        Compile an intent into an ordered PlacementPlan.

        Parameters
        ----------
        intent : Intent
            The high-level design intent.

        Returns
        -------
        PlacementPlan
            An ordered list of MCP tool calls ready for execution.

        Raises
        ------
        ValueError
            If no strategy is registered for the given intent name.
        """
        strategy = self._strategies.get(intent.name)
        if strategy is None:
            available = ", ".join(sorted(self._strategies))
            raise ValueError(
                f"Unknown intent '{intent.name}'. "
                f"Available strategies: {available}"
            )

        tool_calls = strategy.compile(intent.params)
        return PlacementPlan(intent=intent, tool_calls=tool_calls)

    def available_intents(self) -> list[str]:
        """Return the list of registered intent names."""
        return sorted(self._strategies)


# ---------------------------------------------------------------------------
# Quick smoke-test (run: python -m ai_core.compiler)
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    compiler = StrategyCompiler()

    # --- Example 1: 4 LEDs in a square ---
    plan = compiler.compile(
        Intent(
            name="square_leds",
            params={
                "reference_prefix": "D",
                "footprint": "LED_THT:LED_D5.0mm",
                "count": 4,
                "center_x_mm": 100.0,
                "center_y_mm": 100.0,
                "spacing_mm": 10.0,
            },
        )
    )
    print(plan.summary())
    print()

    # --- Example 2: 8 LEDs in a circle ---
    plan2 = compiler.compile(
        Intent(
            name="circle_leds",
            params={
                "reference_prefix": "D",
                "footprint": "LED_THT:LED_D5.0mm",
                "count": 8,
                "center_x_mm": 150.0,
                "center_y_mm": 100.0,
                "radius_mm": 20.0,
            },
        )
    )
    print(plan2.summary())
    print()

    # --- Example 3: 5 components in a row ---
    plan3 = compiler.compile(
        Intent(
            name="linear_row",
            params={
                "reference_prefix": "R",
                "footprint": "Resistor_SMD:R_0805_2012Metric",
                "count": 5,
                "start_x_mm": 50.0,
                "start_y_mm": 75.0,
                "spacing_mm": 5.0,
            },
        )
    )
    print(plan3.summary())
    print()

    # --- Example 4: PCIe differential pair route ---
    plan4 = compiler.compile(
        Intent(
            name="route_pcie_lane",
            params={
                "source_ref": "U1",
                "target_ref": "J1",
            },
        )
    )
    print(plan4.summary())
    # Also print the raw JSON intent for verification
    print(f"  Raw intent JSON: {json.dumps(plan4.tool_calls[0].params, indent=2)}")
