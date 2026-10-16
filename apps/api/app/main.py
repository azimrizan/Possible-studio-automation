import os
import sys
from pathlib import Path

# Automatically inject monorepo paths into sys.path
root_dir = Path(__file__).resolve().parents[3]
monorepo_paths = [
    str(root_dir / "packages" / "mcp-common" / "src"),
    str(root_dir / "packages" / "model-gateway" / "src"),
    str(root_dir / "apps" / "mcp-gateway"),
    str(root_dir / "apps" / "agent-runtime"),
    str(root_dir / "mcp-servers" / "mcp-hello"),
    str(root_dir / "mcp-servers" / "mcp-knowledge"),
    str(root_dir / "mcp-servers" / "mcp-gemini"),
    str(root_dir / "mcp-servers" / "mcp-media"),
    str(root_dir / "mcp-servers" / "mcp-instagram"),
    str(root_dir / "mcp-servers" / "mcp-meta-ads"),
]
for p in monorepo_paths:
    if p not in sys.path:
        sys.path.insert(0, p)

# Load repo-level .env into os.environ (adapters read os.getenv); real env vars win.
from dotenv import load_dotenv
load_dotenv(root_dir / ".env", override=False)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from .core.config import settings
from .core.security import APPROVAL_PUBLIC_KEY_HEX
from .db.session import engine, Base
from .api.v1.router import api_router
from .api.mcp_gemini import router as mcp_gemini_router
from .api.studio import router as studio_router
from .api.meta_connect import router as meta_connect_router
from .api.studio_campaigns import router as studio_campaigns_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize database tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield

app = FastAPI(
    title="Possible Studio Automation API",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api")
app.include_router(mcp_gemini_router, prefix="/api")
app.include_router(studio_router, prefix="/api")
app.include_router(meta_connect_router, prefix="/api")
app.include_router(studio_campaigns_router, prefix="/api")

@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "service": "api",
        "environment": settings.ENVIRONMENT,
        "approval_public_key": APPROVAL_PUBLIC_KEY_HEX,
    }
