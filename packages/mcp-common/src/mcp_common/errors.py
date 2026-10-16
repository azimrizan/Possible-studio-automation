class MCPError(Exception):
    """Base error class for all MCP operations."""
    def __init__(self, message: str, code: str = "MCP_ERROR", status_code: int = 500):
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code

class ToolNotFoundError(MCPError):
    def __init__(self, tool_name: str):
        super().__init__(f"Tool '{tool_name}' not found on this MCP server.", "TOOL_NOT_FOUND", 404)

class ApprovalRequiredError(MCPError):
    def __init__(self, tool_name: str, risk_class: str, payload_hash: str):
        super().__init__(
            f"Tool '{tool_name}' is annotated as '{risk_class}' and requires a valid, signed approval token. "
            f"Action payload hash: {payload_hash}",
            "APPROVAL_REQUIRED",
            403
        )
        self.payload_hash = payload_hash

class InvalidApprovalTokenError(MCPError):
    def __init__(self, reason: str):
        super().__init__(f"Approval token verification failed: {reason}", "INVALID_APPROVAL_TOKEN", 401)

class TenantContextMissingError(MCPError):
    def __init__(self):
        super().__init__("Tenant context is required for all MCP tool executions.", "TENANT_CONTEXT_MISSING", 400)

class BudgetCapExceededError(MCPError):
    def __init__(self, reason: str):
        super().__init__(f"Budget cap violation: {reason}", "BUDGET_CAP_EXCEEDED", 403)
