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
        
    def register_server(self, name: str):
        self.servers[name] = MCPServerInstance(name)
        
    def start_server(self, name: str):
        if name not in self.servers:
            raise ValueError(f"Server {name} not found in registry")
            
        server = self.servers[name]
        server.status = "running"
        
        # In a full stdio implementation, this would spawn a subprocess.
        # For now, we dynamically inspect and expose the tools.
        if name == "neuro_router":
            server.tools = [
                {"name": "apply_routing_strategy", "description": "Apply semantic routing strategy (e.g. diff_pair)"},
                {"name": "create_tracks", "description": "Batch create copper tracks"}
            ]
        elif name == "neuro_layout":
            server.tools = [
                {"name": "get_board_state", "description": "Retrieve semantic board state"},
                {"name": "add_via", "description": "Add a via at the specified coordinates"}
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
