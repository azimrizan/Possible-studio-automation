from enum import Enum
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field

class RiskClass(str, Enum):
    READ = "READ"
    WRITE = "WRITE"
    PUBLISH = "PUBLISH"
    SPEND = "SPEND"

class CostClass(str, Enum):
    FREE = "FREE"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"

class TenantContext(BaseModel):
    tenant_id: str
    workspace_role: str = "VIEWER"
    user_id: Optional[str] = None
    correlation_id: Optional[str] = None

class ToolDefinition(BaseModel):
    name: str
    description: str
    parameters_schema: Dict[str, Any] = Field(default_factory=dict)
    risk_class: RiskClass = RiskClass.READ
    requires_approval: bool = False
    idempotent: bool = True
    cost_class: CostClass = CostClass.FREE

class ApprovalTokenPayload(BaseModel):
    token_jti: str
    tenant_id: str
    tool_name: str
    payload_hash: str
    expires_at: int
    signature: str

class ToolCallRequest(BaseModel):
    tool: str
    arguments: Dict[str, Any] = Field(default_factory=dict)
    tenant_context: TenantContext
    approval_token: Optional[str] = None  # Serialized signed token or JWT
    idempotency_key: Optional[str] = None

class ToolCallResponse(BaseModel):
    success: bool
    data: Optional[Any] = None
    error: Optional[str] = None
    risk_class: RiskClass = RiskClass.READ
    execution_time_ms: float = 0.0
