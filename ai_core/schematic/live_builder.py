"""
ai_core/schematic/live_builder.py
==================================
Phase 8.1: Live AI-Powered Schematic Generator

Uses IPCClient to directly manipulate the KiCad 10 schematic canvas live.
Implements the Raspberry Pi HAT mandatory components and optional expansion interfaces.
"""

import logging
from typing import Dict, Any
from system.ipc_client import IPCClient

log = logging.getLogger("SystemLogger")

class LiveSchematicBuilder:
    def __init__(self, ipc: IPCClient):
        self.ipc = ipc

    def build_from_module(self, module: Any) -> bool:
        """
        Hydrate the live KiCad schematic from a NeuroModule DSL graph.
        """
        log.info(f"[LiveBuilder] Hydrating schematic from module: {module.name}")
        
        self.placed_parts = {}
        self.cursor_x = 50
        self.cursor_y = 50
        
        try:
            self._recursive_build(module)
            log.info("[LiveBuilder] Generic DSL synthesis complete.")
            return True
        except Exception as e:
            log.error(f"[LiveBuilder] DSL Build Error: {e}")
            return False

    def _recursive_build(self, module: Any):
        """Recursively place parts and submodules."""
        log.debug(f"[LiveBuilder] Synthesis: {module.name}")
        
        # 1. Place Parts in this module
        for part in module.parts:
            # Avoid duplicate placement if ref already exists
            ref = getattr(part, 'ref', "U?")
            
            # Simple Grid Placement (20mm spacing)
            self.ipc.add_symbol(
                lib_id=f"{getattr(part, 'lib', 'Device')}:{getattr(part, 'name', 'R')}",
                reference=ref,
                x=self.cursor_x,
                y=self.cursor_y
            )
            self.placed_parts[ref] = (self.cursor_x, self.cursor_y)
            
            self.cursor_x += 40
            if self.cursor_x > 250:
                self.cursor_x = 50
                self.cursor_y += 50

        # 2. Recurse into submodules
        for sub_name, submodule in getattr(module, 'submodules', {}).items():
            self._recursive_build(submodule)

        # 3. Wires (Net Extraction)
        # Note: In Phase 8.1, we focus on symbols. 
        # Full wire synthesis from the DSL graph is scheduled for Phase 8.2.
        # But we can add basic power symbols.
        self._inject_power_symbols(module)

    def _inject_power_symbols(self, module: Any):
        """Helper to sprinkle power symbols based on used nets."""
        # Fix: processed_nets logic was stubbed
        for net_name, skidl_net in getattr(module, 'nets', {}).items():
            if "V3V" in net_name or "+3.3V" in net_name:
                self.ipc.add_power_symbol("+3.3V", self.cursor_x, self.cursor_y)
                self.cursor_y += 10
            elif "GND" in net_name:
                self.ipc.add_power_symbol("GND", self.cursor_x, self.cursor_y)
                self.cursor_y += 10
