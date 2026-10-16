import os
import json
import logging
from typing import Dict, Any, Optional, List
from mcp_common import (
    MCPServer,
    RiskClass,
    CostClass,
    TenantContext,
    BaseMockAdapter,
)

logger = logging.getLogger("mcp_knowledge")

# Default brand tokens fallback for mock/standalone mode
DEFAULT_BRAND_TOKENS = {
    "brand_name": "Possible Studio",
    "logo_url": "https://assets.possiblestudio.ai/logo.png",
    "color_palette": {
        "primary": "#6366f1",
        "secondary": "#4f46e5",
        "accent": "#ec4899",
        "surface": "#0f172a",
        "background": "#080c14",
        "text": {
            "primary": "#f8fafc",
            "secondary": "#94a3b8",
        },
    },
    "typography": {
        "headline": {
            "font_family": "Inter, sans-serif",
            "weights": ["700", "800"],
        },
        "body": {
            "font_family": "Inter, sans-serif",
            "weights": ["400", "500"],
        },
    },
    "tone_of_voice": {
        "keywords": ["Innovative", "Direct", "Authoritative", "Empowering"],
        "do": [
            "Emphasize customer ROI and time saved",
            "Use clear, energetic verbs",
            "Focus on health, productivity, and lifestyle advantages",
        ],
        "dont": [
            "Never use vague buzzwords without substance",
            "Avoid aggressive or pushy sales copy",
        ],
        "samples": [
            "Say goodbye to manual campaign setup. Let your AI Marketing Employee handle research, creative, and ads launch in minutes.",
            "Smarter Every Move. AI-powered tracking with 7-day battery life.",
        ],
    },
    "layout_guidelines": {
        "aspect_ratios": ["1:1", "4:5", "9:16"],
        "safe_zones": {
            "top_percent": 15,
            "bottom_percent": 20,
            "sides_percent": 8,
        },
        "logo_placement": "top_left",
    },
    "product_catalog": [
        {
            "name": "AI Smartwatch Pro",
            "description": "Next-gen fitness and productivity smartwatch with on-device AI health insights",
            "price": 10000,
            "currency": "INR",
            "key_features": ["7-Day Battery Life", "Real-Time AI Fitness Coach", "AMOLED Display", "Water Resistant 50m"],
            "target_audience": "Tech enthusiasts, working professionals, fitness lovers aged 22-35",
        }
    ],
}

DEFAULT_KB_CHUNKS = [
    {
        "content": "Product: AI Smartwatch Pro. Features: 7-Day Battery Life, Real-time AI Health Coaching, AMOLED Display. Price: ₹10,000.",
        "category": "product_spec",
        "score": 0.94,
    },
    {
        "content": "Brand Voice Guidelines: Tone is inspiring, clear, and confident. Slogans: 'Smarter Every Move', 'More Than a Watch'.",
        "category": "voice_sample",
        "score": 0.88,
    },
    {
        "content": "Ad Policy Compliance: Never claim medical diagnostic capability. Always state battery life based on typical usage conditions.",
        "category": "policy",
        "score": 0.82,
    },
]

class KnowledgeMockAdapter(BaseMockAdapter):
    def __init__(self):
        super().__init__(is_mock_enabled=True)
        self.tenant_tokens: Dict[str, Dict[str, Any]] = {}
        self.tenant_kb: Dict[str, List[Dict[str, Any]]] = {}

    def set_tenant_tokens(self, tenant_id: str, tokens: Dict[str, Any]):
        self.tenant_tokens[tenant_id] = tokens

    def get_tenant_tokens(self, tenant_id: str) -> Dict[str, Any]:
        return self.tenant_tokens.get(tenant_id, DEFAULT_BRAND_TOKENS)

    def search(self, tenant_id: str, query: str, category: Optional[str] = None, top_k: int = 3) -> List[Dict[str, Any]]:
        chunks = self.tenant_kb.get(tenant_id, DEFAULT_KB_CHUNKS)
        results = []
        q_words = query.lower().split()
        
        for item in chunks:
            if category and item.get("category") != category:
                continue
            
            # Simple keyword matching score
            text = item.get("content", "").lower()
            matches = sum(1 for w in q_words if w in text)
            score = 0.5 + (0.5 * (matches / max(len(q_words), 1)))
            
            results.append({
                "content": item.get("content"),
                "category": item.get("category"),
                "relevance_score": round(score, 2),
            })

        results.sort(key=lambda x: x["relevance_score"], reverse=True)
        return results[:top_k]

mock_adapter = KnowledgeMockAdapter()

# Initialize MCP Server
server = MCPServer(
    name="mcp-knowledge",
    version="0.1.0",
)

async def handle_get_brand_tokens(args: Dict[str, Any], ctx: TenantContext) -> Dict[str, Any]:
    """Retrieves machine-readable design tokens for the active tenant."""
    tokens = mock_adapter.get_tenant_tokens(ctx.tenant_id)
    return {
        "tenant_id": ctx.tenant_id,
        "design_tokens": tokens,
    }

async def handle_search_kb(args: Dict[str, Any], ctx: TenantContext) -> Dict[str, Any]:
    """Performs semantic and keyword search across tenant brand knowledge."""
    query = args.get("query", "")
    category = args.get("category")
    top_k = args.get("top_k", 3)

    results = mock_adapter.search(
        tenant_id=ctx.tenant_id,
        query=query,
        category=category,
        top_k=top_k,
    )
    return {
        "tenant_id": ctx.tenant_id,
        "query": query,
        "matches": results,
    }

# Register tools with strict metadata
server.register_tool(
    name="get_brand_tokens",
    description="Returns the tenant's compiled design system tokens (colors, typography, tone of voice, logos, product catalog) in JSON.",
    handler=handle_get_brand_tokens,
    parameters_schema={
        "type": "object",
        "properties": {},
        "required": [],
    },
    risk_class=RiskClass.READ,
    requires_approval=False,
    idempotent=True,
)

server.register_tool(
    name="search_kb",
    description="Performs knowledge base retrieval (RAG) for brand guidelines, product specs, and policies.",
    handler=handle_search_kb,
    parameters_schema={
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Search term or concept to find in brand knowledge"},
            "category": {"type": "string", "enum": ["product_spec", "voice_sample", "policy", "faq"]},
            "top_k": {"type": "integer", "default": 3},
        },
        "required": ["query"],
    },
    risk_class=RiskClass.READ,
    requires_approval=False,
    idempotent=True,
)

app = server.app

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8107"))
    uvicorn.run(app, host="0.0.0.0", port=port)
