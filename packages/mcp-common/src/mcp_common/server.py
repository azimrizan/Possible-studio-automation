import time
import json
import logging
from typing import Callable, Dict, Any, Optional
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

from .models import (
    ToolDefinition,
    ToolCallRequest,
    ToolCallResponse,
    RiskClass,
)
from .errors import (
    MCPError,
    ToolNotFoundError,
    ApprovalRequiredError,
    TenantContextMissingError,
    InvalidApprovalTokenError,
)
from .security import (
    compute_payload_hash,
    verify_approval_token,
)

logger = logging.getLogger("mcp_server")

class MCPServer:
    """
    Standard Base MCP Server for all first-party servers in the fleet.
    Enforces tenant context, schema validation, defense-in-depth approval tokens,
    and structured error responses.
    """
    def __init__(self, name: str, version: str = "0.1.0", approval_public_key_hex: Optional[str] = None):
        self.name = name
        self.version = version
        self.approval_public_key_hex = approval_public_key_hex
        self.tools: Dict[str, ToolDefinition] = {}
        self.handlers: Dict[str, Callable] = {}
        self.app = FastAPI(title=f"MCP Server: {name}", version=version)
        self._setup_routes()

    def set_approval_public_key(self, public_key_hex: str):
        self.approval_public_key_hex = public_key_hex

    def register_tool(
        self,
        name: str,
        description: str,
        handler: Callable,
        parameters_schema: Optional[Dict[str, Any]] = None,
        risk_class: RiskClass = RiskClass.READ,
        requires_approval: bool = False,
        idempotent: bool = True,
    ):
        tool_def = ToolDefinition(
            name=name,
            description=description,
            parameters_schema=parameters_schema or {},
            risk_class=risk_class,
            requires_approval=requires_approval,
            idempotent=idempotent,
        )
        self.tools[name] = tool_def
        self.handlers[name] = handler

    async def execute_tool(self, req: ToolCallRequest) -> ToolCallResponse:
        start_time = time.time()
        
        # 1. Tenant context validation
        if not req.tenant_context or not req.tenant_context.tenant_id:
            raise TenantContextMissingError()

        # 2. Tool existence
        if req.tool not in self.tools:
            raise ToolNotFoundError(req.tool)

        tool_def = self.tools[req.tool]
        payload_hash = compute_payload_hash(req.arguments)

        # 3. Defense-in-depth approval check
        if tool_def.requires_approval or tool_def.risk_class in [RiskClass.PUBLISH, RiskClass.SPEND]:
            if not req.approval_token:
                raise ApprovalRequiredError(
                    tool_name=req.tool,
                    risk_class=tool_def.risk_class.value,
                    payload_hash=payload_hash,
                )
            
            if not self.approval_public_key_hex:
                raise InvalidApprovalTokenError("Server is missing the verification public key")

            # Parse token if passed as JSON string
            token_dict = req.approval_token
            if isinstance(token_dict, str):
                try:
                    token_dict = json.loads(token_dict)
                except Exception:
                    raise InvalidApprovalTokenError("Failed to parse approval token JSON")

            verify_approval_token(
                token_dict=token_dict,
                expected_payload_hash=payload_hash,
                expected_tenant_id=req.tenant_context.tenant_id,
                expected_tool_name=req.tool,
                public_key_hex=self.approval_public_key_hex,
            )

        # 4. Invoke handler
        handler = self.handlers[req.tool]
        try:
            result = await handler(req.arguments, req.tenant_context)
            execution_time = (time.time() - start_time) * 1000.0
            return ToolCallResponse(
                success=True,
                data=result,
                risk_class=tool_def.risk_class,
                execution_time_ms=execution_time,
            )
        except Exception as e:
            execution_time = (time.time() - start_time) * 1000.0
            logger.exception(f"Tool {req.tool} failed: {e}")
            return ToolCallResponse(
                success=False,
                error=str(e),
                risk_class=tool_def.risk_class,
                execution_time_ms=execution_time,
            )

    def _setup_routes(self):
        @self.app.get("/health")
        async def health():
            return {"status": "ok", "server": self.name, "version": self.version}

        @self.app.get("/tools")
        async def list_tools():
            return {
                "server": self.name,
                "version": self.version,
                "tools": [t.model_dump() for t in self.tools.values()],
            }

        @self.app.post("/call", response_model=ToolCallResponse)
        async def call_tool(req: ToolCallRequest):
            try:
                return await self.execute_tool(req)
            except MCPError as e:
                raise HTTPException(status_code=e.status_code, detail={"code": e.code, "message": e.message})
            except Exception as e:
                raise HTTPException(status_code=500, detail={"code": "INTERNAL_ERROR", "message": str(e)})
