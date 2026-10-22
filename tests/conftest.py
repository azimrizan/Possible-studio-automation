import pytest
import pytest_asyncio
import sys
import os

# Tests never call live LLMs (the API loads .env, which may contain real keys).
os.environ["MOCK_LLM"] = "true"
# Meta flags are pinned too, so a developer's .env (e.g. MOCK_META_ADS=true) cannot change test behaviour.
os.environ["MOCK_META_ADS"] = "false"
os.environ.setdefault("MOCK_META_GRAPH", "true")
# The video editor calls Claude / ElevenLabs when these are set; blank them so .env keys are never used in tests.
os.environ["ANTHROPIC_API_KEY"] = ""
os.environ["ELEVENLABS_API_KEY"] = ""

# Add root paths to sys.path
sys.path.insert(0, os.path.abspath("."))
sys.path.insert(0, os.path.abspath("packages/mcp-common/src"))
sys.path.insert(0, os.path.abspath("packages/model-gateway/src"))
sys.path.insert(0, os.path.abspath("apps/api"))
sys.path.insert(0, os.path.abspath("apps/mcp-gateway"))
sys.path.insert(0, os.path.abspath("apps/agent-runtime"))
sys.path.insert(0, os.path.abspath("mcp-servers/mcp-hello"))
sys.path.insert(0, os.path.abspath("mcp-servers/mcp-knowledge"))
sys.path.insert(0, os.path.abspath("mcp-servers/mcp-gemini"))
sys.path.insert(0, os.path.abspath("mcp-servers/mcp-media"))
sys.path.insert(0, os.path.abspath("mcp-servers/mcp-instagram"))
sys.path.insert(0, os.path.abspath("mcp-servers/mcp-meta-ads"))

from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from apps.api.app.main import app as fastapi_app
from apps.api.app.db.session import Base, get_db
from apps.api.app.core.security import APPROVAL_PUBLIC_KEY_HEX, APPROVAL_PRIVATE_KEY_HEX

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

@pytest_asyncio.fixture
async def test_db():
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async_session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_session() as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()

@pytest_asyncio.fixture
async def client(test_db):
    async def override_get_db():
        yield test_db

    fastapi_app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=fastapi_app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    fastapi_app.dependency_overrides.clear()
