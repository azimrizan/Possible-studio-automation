from typing import Dict
from pydantic import BaseModel

class TenantUsage(BaseModel):
    tenant_id: str
    total_prompt_tokens: int = 0
    total_completion_tokens: int = 0
    total_estimated_cost_usd: float = 0.0

class CostTracker:
    """Tracks token consumption and estimated costs per tenant."""
    def __init__(self):
        self._usage: Dict[str, TenantUsage] = {}

    def record_usage(self, tenant_id: str, prompt_tokens: int, completion_tokens: int, model: str = "gemini-1.5-flash"):
        if tenant_id not in self._usage:
            self._usage[tenant_id] = TenantUsage(tenant_id=tenant_id)
        
        usage = self._usage[tenant_id]
        usage.total_prompt_tokens += prompt_tokens
        usage.total_completion_tokens += completion_tokens
        
        # Approximate pricing per 1M tokens (e.g. $0.35/1M input, $1.05/1M output)
        input_rate = 0.00000035
        output_rate = 0.00000105
        cost = (prompt_tokens * input_rate) + (completion_tokens * output_rate)
        usage.total_estimated_cost_usd += cost

    def get_tenant_usage(self, tenant_id: str) -> TenantUsage:
        return self._usage.get(tenant_id, TenantUsage(tenant_id=tenant_id))
