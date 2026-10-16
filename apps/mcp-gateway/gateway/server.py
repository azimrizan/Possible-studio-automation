import os
from fastapi import FastAPI, HTTPException
from mcp_common import ToolCallRequest, ToolCallResponse
from .router import MCPGatewayRouter

app = FastAPI(title="MCP Gateway", version="0.1.0")
router = MCPGatewayRouter()

# Register default servers from environment
mcp_hello_url = os.getenv("MCP_HELLO_URL", "http://localhost:8101")
router.register_server("mcp-hello", mcp_hello_url)

mcp_knowledge_url = os.getenv("MCP_KNOWLEDGE_URL", "http://localhost:8107")
router.register_server("mcp-knowledge", mcp_knowledge_url)

mcp_gemini_url = os.getenv("MCP_GEMINI_URL", "http://localhost:8105")
router.register_server("mcp-gemini", mcp_gemini_url)

mcp_media_url = os.getenv("MCP_MEDIA_URL", "http://localhost:8104")
router.register_server("mcp-media", mcp_media_url)

@app.get("/health")
async def health():
    return {"status": "ok", "service": "mcp-gateway"}

@app.get("/catalog")
async def get_catalog():
    catalog = await router.refresh_catalog()
    return {"catalog": catalog}

@app.post("/proxy/call", response_model=ToolCallResponse)
async def proxy_call(req: ToolCallRequest):
    try:
        return await router.dispatch(req)
    except Exception as e:
        raise HTTPException(status_code=500, detail={"code": "GATEWAY_ERROR", "message": str(e)})

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8100"))
    uvicorn.run(app, host="0.0.0.0", port=port)
