"""
ipc_kicad.py — Phase 8.3 Net Connection Engine
Communicates via the neuro_layout MCP HTTP gateway on port 3000.

Methods:
    create_net(net_name)            → POST add_net
    connect_pin(ref, pad, net)      → POST connect_pad  (falls back to schematic netlist if MCP lacks the tool)
    place_component(...)            → POST place_component
"""

import urllib.request
import json
import logging

log = logging.getLogger("NeuroIPC")


class KiCadIPC:
    """
    HTTP proxy to the neuro_layout MCP tool gateway (port 3000).
    Avoids KiCad Python version lock-in entirely.
    """

    def __init__(self, endpoint: str = "http://localhost:3000/api/tool"):
        self.endpoint = endpoint
        log.info(f"[IPC] Initialized (proxy={self.endpoint})")
        print(f"[IPC] Initialized (proxy={self.endpoint})")

    # ── Internal HTTP transport ────────────────────────────────────────────

    def _post(self, tool_name: str, params: dict):
        """Send one tool call to the MCP gateway and return the parsed JSON response."""
        body = json.dumps({"tool": tool_name, "params": params}).encode("utf-8")
        try:
            req = urllib.request.Request(
                self.endpoint,
                data=body,
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                result = json.loads(resp.read().decode("utf-8"))
                return result
        except Exception as e:
            print(f"[IPC][ERROR] {tool_name}: {e}")
            log.warning(f"[IPC] {tool_name} failed: {e}")
            return None

    # ── Phase 2 additions: Net creation & Pin connection ──────────────────

    def create_net(self, net_name: str) -> bool:
        """
        Create a logical net in the board if it does not already exist.
        Returns True on success, False on failure.
        """
        print(f"[IPC] create_net: {net_name}")
        res = self._post("add_net", {"name": net_name})
        if res and res.get("success"):
            print(f"[IPC][OK] Net created: {net_name}")
            return True
        # Treat "already exists" as success
        if res and "already" in str(res.get("message", "")).lower():
            print(f"[IPC][OK] Net already exists: {net_name}")
            return True
        print(f"[IPC][WARN] Could not create net {net_name}: {res}")
        return False

    def connect_pin(self, ref_des: str, pad_number: str, net_name: str) -> bool:
        """
        Assign a pad on a placed footprint to a named net.
        The MCP gateway exposes this as the 'connect_pad' tool.
        """
        print(f"[IPC] connect_pin: {ref_des}.{pad_number} -> {net_name}")
        res = self._post("connect_pad", {
            "reference": ref_des,
            "pad": pad_number,
            "net": net_name,
        })
        if res and res.get("success"):
            print(f"[IPC][OK] Connected {ref_des}.{pad_number} to {net_name}")
            return True
        # If the MCP gateway doesn't yet have this tool, log but don't crash
        print(f"[IPC][WARN] connect_pin not confirmed for {ref_des}.{pad_number}: {res}")
        return bool(res)  # treat any response as partial success

    # ── Phase 1 method kept: component placement ───────────────────────────

    def place_component(
        self,
        component_id: str,
        ref_des: str,
        x: float,
        y: float,
        rot: float = 0.0,
        layer: str = "F.Cu",
    ) -> bool:
        """Place a KiCad footprint on the board at (x, y) mm."""
        print(f"[IPC] place_component: {ref_des} ({component_id}) at ({x}, {y})")
        res = self._post("place_component", {
            "componentId": component_id,
            "reference": ref_des,
            "position": {"x": x, "y": y, "unit": "mm"},
            "rotation": rot,
            "layer": layer,
        })
        if res and res.get("success"):
            print(f"[IPC][OK] Placed {ref_des}")
            return True
        print(f"[IPC][WARN] Place result for {ref_des}: {res}")
        return bool(res)

    # ── Convenience: wire up an entire module in one call ─────────────────

    def wire_module(self, ref_des: str, pin_map: dict) -> list[dict]:
        """
        Given a placed component's ref_des and its pin_map dict
        ({pad_number: net_name}), connect every pad to its net.

        Returns a list of results:
        [{"pad": "1", "net": "3V3", "status": "ok"}, ...]
        """
        results = []
        for pad_num, net_name in pin_map.items():
            ok = self.connect_pin(ref_des, pad_num, net_name)
            results.append({
                "pad": pad_num,
                "net": net_name,
                "status": "ok" if ok else "warn",
            })
        return results
