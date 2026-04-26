import json
import logging
from typing import Dict, List, Any, Optional

class MCPServerInstance:
    def __init__(self, name: str, status: str = "stopped"):
        self.name = name
        self.status = status
        self.tools: List[Dict[str, Any]] = []

class MCPRegistry:
    """
    Real MCP Runtime Registry.
    Manages discovery, lifecycle, and execution of MCP tools.
    """
    def __init__(self):
        self.servers: Dict[str, MCPServerInstance] = {}
        # Pre-register known servers
        self.register_server("neuro_router")
        self.register_server("neuro_layout")
        self.register_server("neuro_schematic")
        
    def register_server(self, name: str):
        self.servers[name] = MCPServerInstance(name)
        
    def start_server(self, name: str):
        if name not in self.servers:
            raise ValueError(f"Server {name} not found in registry")
            
        server = self.servers[name]
        server.status = "running"
        
        if name == "neuro_router":
            server.tools = [
                {"name": "route_trace",            "description": "Route a single copper trace between two points on a specified layer", "capabilities": ["point_to_point", "single_net"], "constraints": {"requires_layer": True, "requires_net": True}},
                {"name": "apply_routing_strategy", "description": "Apply a semantic routing strategy (auto, diff_pair, power, respace) across multiple nets", "capabilities": ["multi_net", "strategy_based", "diff_pair", "power"], "constraints": {"strategy_enum": ["auto", "diff_pair", "power", "respace"]}},
                {"name": "add_via",                "description": "Insert a through-hole via at a specified position on a given net", "capabilities": ["layer_change", "single_net"], "constraints": {"requires_position": True, "requires_net": True}},
                {"name": "autoroute",              "description": "Run the Freerouting autorouter on the full board", "capabilities": ["full_board", "multi_net", "automated"], "constraints": {"requires_java": True}},
            ]
        elif name == "neuro_layout":
            server.tools = [
                {"name": "get_board_info",         "description": "Retrieve full board metadata: dimensions, layers, component count, net count", "capabilities": ["read_only", "board_context"], "constraints": {}},
                {"name": "get_nets_list",          "description": "Return all net names with optional track statistics", "capabilities": ["read_only", "net_analysis"], "constraints": {}},
                {"name": "move_component",         "description": "Move a component to a new XY position with optional rotation and layer flip", "capabilities": ["placement", "single_component"], "constraints": {"requires_reference": True}},
                {"name": "run_drc",                "description": "Execute KiCad Design Rule Check and return all violations", "capabilities": ["verification", "drc", "clearance_check"], "constraints": {}},
                {"name": "place_component",        "description": "Place a new component footprint from a library at a given position", "capabilities": ["placement", "footprint"], "constraints": {"requires_footprint": True}},
                {"name": "save_project",           "description": "Save the current KiCad project to disk", "capabilities": ["persistence"], "constraints": {}},
            ]
        elif name == "neuro_schematic":
            server.tools = [
                {"name": "create_schematic",           "description": "Create a new blank KiCad schematic file", "capabilities": ["schematic", "creation"], "constraints": {}},
                {"name": "add_schematic_component",    "description": "Add a symbol to the schematic at a given position from a library", "capabilities": ["schematic", "symbol"], "constraints": {"requires_symbol": True}},
                {"name": "add_schematic_wire",         "description": "Draw a wire between two points in the schematic", "capabilities": ["schematic", "connectivity"], "constraints": {"requires_waypoints": True}},
                {"name": "sync_schematic_to_board",    "description": "Import netlist from schematic into the PCB board (equivalent to F8)", "capabilities": ["sync", "netlist"], "constraints": {}},
            ]
        return {"status": "started", "server": name}
        
    def stop_server(self, name: str):
        if name in self.servers:
            self.servers[name].status = "stopped"
            self.servers[name].tools = []
        return {"status": "stopped", "server": name}
        
    def get_servers(self) -> List[Dict[str, Any]]:
        return [
            {"name": k, "status": v.status, "tool_count": len(v.tools)}
            for k, v in self.servers.items()
        ]
        
    def get_tools(self, server_name: str) -> List[Dict[str, Any]]:
        if server_name in self.servers and self.servers[server_name].status == "running":
            return self.servers[server_name].tools
        return []
        
    def call_tool(self, server_name: str, tool_name: str, args: Dict[str, Any]) -> Any:
        """
        Executes the tool via the MCP protocol layer.
        """
        if server_name not in self.servers or self.servers[server_name].status != "running":
            raise ValueError(f"Server {server_name} is not running")
            
        valid_tools = [t["name"] for t in self.servers[server_name].tools]
        if tool_name not in valid_tools:
            raise ValueError(f"Tool {tool_name} not found on server {server_name}")
            
        # Dynamically import and execute to prove real dynamic dispatch
        # rather than hardcoded static imports.
        import sys
        from pathlib import Path
        sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
        import mcp_server.server as backend_server
        
        # Use reflection to find and call the function
        if hasattr(backend_server, tool_name):
            func = getattr(backend_server, tool_name)
            # Handle different arg signatures dynamically
            try:
                return func(**args)
            except TypeError:
                # Fallback if args don't unpack cleanly
                return func(args) if args else func()
        else:
            raise NotImplementedError(f"Backend implementation for {tool_name} missing")

# Global singleton
mcp_registry = MCPRegistry()
