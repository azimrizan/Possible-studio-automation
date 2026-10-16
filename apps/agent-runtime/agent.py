import asyncio
import json
import logging
from typing import Dict, Any, Optional
from mcp_common import TenantContext, ToolCallRequest, redact_secrets
from model_gateway import ModelGateway

logger = logging.getLogger("agent_runtime")

class HelloAgent:
    """
    Phase 0 Demonstration Agent.
    Interacts with ModelGateway and calls MCP tools via MCP Gateway.
    """
    def __init__(self, model_gateway: ModelGateway, mcp_gateway_client: Any):
        self.model_gateway = model_gateway
        self.mcp_gateway = mcp_gateway_client
        self.traces = []

    def _log_trace(self, step: str, payload: Any):
        trace = {"step": step, "payload": payload}
        self.traces.append(trace)
        logger.info(f"[TRACE] {step}: {redact_secrets(str(payload))}")

    async def run_echo_flow(self, user_prompt: str, tenant_context: TenantContext) -> Dict[str, Any]:
        self._log_trace("AGENT_INPUT", {"prompt": user_prompt, "tenant": tenant_context.tenant_id})

        # Step 1: Model Gateway plan
        llm_reasoning = await self.model_gateway.generate_text(
            prompt=f"User asked: '{user_prompt}'. Plan: Call hello_echo tool.",
            tenant_id=tenant_context.tenant_id,
        )
        self._log_trace("MODEL_REASONING", {"reasoning": llm_reasoning})

        # Step 2: MCP Gateway tool call (Safe read tool)
        tool_req = ToolCallRequest(
            tool="hello_echo",
            arguments={"message": f"Agent responded to: {user_prompt}"},
            tenant_context=tenant_context,
        )
        self._log_trace("MCP_TOOL_DISPATCH", {"tool": tool_req.tool, "args": tool_req.arguments})
        
        tool_res = await self.mcp_gateway.dispatch(tool_req)
        self._log_trace("MCP_TOOL_RESULT", {"success": tool_res.success, "data": tool_res.data})

        return {
            "status": "COMPLETED",
            "llm_reasoning": llm_reasoning,
            "tool_response": tool_res.data,
            "traces": self.traces,
        }

    async def run_protected_flow(
        self,
        action: str,
        tenant_context: TenantContext,
        approval_token: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        self._log_trace("AGENT_PROTECTED_ACTION_START", {"action": action, "has_token": approval_token is not None})

        # Attempt to call high-risk tool
        tool_req = ToolCallRequest(
            tool="hello_protected_action",
            arguments={"action": action},
            tenant_context=tenant_context,
            approval_token=json.dumps(approval_token) if approval_token else None,
        )

        tool_res = await self.mcp_gateway.dispatch(tool_req)
        self._log_trace("MCP_TOOL_RESULT", {
            "success": tool_res.success,
            "data": tool_res.data,
            "error": tool_res.error,
        })

        return {
            "success": tool_res.success,
            "data": tool_res.data,
            "error": tool_res.error,
            "traces": self.traces,
        }
