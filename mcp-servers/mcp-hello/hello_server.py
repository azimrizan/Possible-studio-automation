import os
import time
from typing import Dict, Any
from mcp_common import MCPServer, RiskClass, CostClass, TenantContext

approval_pub_key = os.getenv("APPROVAL_PUBLIC_KEY_HEX", None)
server = MCPServer(
    name="mcp-hello",
    version="0.1.0",
    approval_public_key_hex=approval_pub_key,
)

async def handle_hello_echo(args: Dict[str, Any], ctx: TenantContext) -> Dict[str, Any]:
    message = args.get("message", "Hello from MCP!")
    return {
        "echo": message,
        "tenant_id": ctx.tenant_id,
        "caller_role": ctx.workspace_role,
        "timestamp": time.time(),
    }

async def handle_hello_protected(args: Dict[str, Any], ctx: TenantContext) -> Dict[str, Any]:
    action = args.get("action", "test_publish")
    return {
        "status": "APPROVED_AND_EXECUTED",
        "action": action,
        "tenant_id": ctx.tenant_id,
        "executed_by": ctx.user_id,
        "timestamp": time.time(),
    }

server.register_tool(
    name="hello_echo",
    description="Echoes back a message with tenant context. Safe, read-only.",
    handler=handle_hello_echo,
    parameters_schema={
        "type": "object",
        "properties": {"message": {"type": "string"}},
        "required": [],
    },
    risk_class=RiskClass.READ,
    requires_approval=False,
    idempotent=True,
)

server.register_tool(
    name="hello_protected_action",
    description="A high-risk publishing action that strictly requires a valid cryptographic approval token.",
    handler=handle_hello_protected,
    parameters_schema={
        "type": "object",
        "properties": {"action": {"type": "string"}},
        "required": ["action"],
    },
    risk_class=RiskClass.PUBLISH,
    requires_approval=True,
    idempotent=False,
)

app = server.app

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8101"))
    uvicorn.run(app, host="0.0.0.0", port=port)
