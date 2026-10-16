import httpx
import logging
from typing import Dict, Any, Optional
from mcp_common import (
    ToolCallRequest,
    ToolCallResponse,
    ToolDefinition,
    ToolNotFoundError,
    MCPError,
    redact_secrets,
)

logger = logging.getLogger("mcp_gateway")

class MCPGatewayRouter:
    """
    Registry and proxy router for first-party and external MCP servers.
    """
    def __init__(self):
        # Maps server_name -> base_url
        self.server_registry: Dict[str, str] = {}
        # Cached tool routing: tool_name -> server_name
        self.tool_routes: Dict[str, str] = {}
        # In-process servers (for fast local execution / unit tests)
        self.in_process_servers: Dict[str, Any] = {}

    def register_server(self, name: str, base_url: str):
        self.server_registry[name] = base_url.rstrip("/")

    def register_in_process_server(self, name: str, mcp_server_instance: Any):
        self.in_process_servers[name] = mcp_server_instance
        for tool_name in mcp_server_instance.tools.keys():
            self.tool_routes[tool_name] = name

    async def refresh_catalog(self) -> Dict[str, Any]:
        """Queries all registered MCP servers and builds aggregated catalog."""
        catalog = {}
        # 1. In-process servers
        for s_name, server in self.in_process_servers.items():
            for t_name, t_def in server.tools.items():
                self.tool_routes[t_name] = s_name
                catalog[t_name] = t_def.model_dump()

        # 2. HTTP servers
        async with httpx.AsyncClient(timeout=5.0) as client:
            for s_name, base_url in self.server_registry.items():
                try:
                    resp = await client.get(f"{base_url}/tools")
                    if resp.status_code == 200:
                        data = resp.json()
                        for tool in data.get("tools", []):
                            t_name = tool["name"]
                            self.tool_routes[t_name] = s_name
                            catalog[t_name] = tool
                except Exception as e:
                    logger.warning(f"Could not reach MCP server '{s_name}' at {base_url}: {e}")

        return catalog

    async def dispatch(self, req: ToolCallRequest) -> ToolCallResponse:
        """Dispatches a tool call to the designated MCP server."""
        # Find which server owns this tool
        server_name = self.tool_routes.get(req.tool)
        
        # If not cached, attempt a refresh
        if not server_name:
            await self.refresh_catalog()
            server_name = self.tool_routes.get(req.tool)

        if not server_name:
            raise ToolNotFoundError(req.tool)

        # In-process dispatch
        if server_name in self.in_process_servers:
            server = self.in_process_servers[server_name]
            try:
                return await server.execute_tool(req)
            except MCPError as e:
                return ToolCallResponse(
                    success=False,
                    error=f"[{e.code}] {e.message}",
                )

        # HTTP dispatch
        base_url = self.server_registry.get(server_name)
        if not base_url:
            raise ToolNotFoundError(req.tool)

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{base_url}/call",
                json=req.model_dump(),
            )
            if resp.status_code != 200:
                err_detail = resp.json().get("detail", {})
                return ToolCallResponse(
                    success=False,
                    error=redact_secrets(str(err_detail.get("message", "Tool execution error"))),
                )
            return ToolCallResponse.model_validate(resp.json())
