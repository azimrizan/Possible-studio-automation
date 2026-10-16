"""
Instagram + Meta Ads connection (one Facebook Login for Business flow).

- Tokens are exchanged server-side, upgraded to long-lived (~60 days), encrypted with the
  vault and stored per workspace. They are never returned to the browser.
- MOCK mode (MOCK_META_GRAPH=true or no META_APP_ID) connects a clearly-labelled demo
  account so the whole flow can be exercised without a Meta app.
- `graph_for(workspace)` is the credential provider used by mcp-instagram / mcp-meta-ads.
"""
import logging
import os
import secrets
import time
from typing import Any, Dict, Optional
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, Header, HTTPException, Query
from fastapi.responses import RedirectResponse
from pydantic import BaseModel

from mcp_common.meta_graph import MetaGraph, MetaGraphError, MockMetaGraph, graph_version, meta_mock_enabled, meta_mode
from mcp_common.vault import decrypt_secret, encrypt_secret
from poster_studio import StoreError, StudioStore

logger = logging.getLogger("uvicorn.error")
router = APIRouter(prefix="/studio/connections", tags=["Meta Connect"])

store = StudioStore()

META_SCOPES = [
    "instagram_basic",
    "instagram_content_publish",
    "pages_show_list",
    "pages_read_engagement",
    "business_management",
    "ads_management",
    "ads_read",
]
STATE_TTL_S = 600


def web_app_url() -> str:
    return os.getenv("WEB_APP_URL") or os.getenv("NEXT_PUBLIC_APP_URL") or "http://localhost:3000"


def redirect_uri() -> str:
    # Live Meta apps require an https redirect on a domain listed in App Domains, so the callback can
    # come in through the public tunnel (META_REDIRECT_BASE_URL) while the user returns to the web app.
    base = (os.getenv("META_REDIRECT_BASE_URL") or web_app_url()).rstrip("/")
    return f"{base}/api/studio/connections/meta/callback"


def _ws(workspace: Optional[str]) -> str:
    if not workspace:
        raise HTTPException(status_code=400, detail="X-Studio-Workspace header required")
    return workspace


def public_connection(conn: Dict[str, Any]) -> Dict[str, Any]:
    meta = conn.get("meta") or {}
    if meta.get("mock") and not meta_mock_enabled():
        meta = {}  # a demo connection is never shown as connected outside demo mode
    return {
        "meta": {
            "connected": bool(meta.get("token_enc")),
            "mock": bool(meta.get("mock")),
            "user_name": meta.get("user_name", ""),
            "pages": meta.get("pages", []),
            "ad_accounts": meta.get("ad_accounts", []),
            "selection": meta.get("selection") or {},
            "expires_at": meta.get("expires_at"),
            "needs_reauth": bool(meta.get("needs_reauth")) or (
                bool(meta.get("expires_at")) and meta["expires_at"] < time.time()
            ),
            "mode": meta_mode(),
            "kind": meta.get("kind", "user_login"),
            "redirect_uri": redirect_uri(),
        }
    }


async def graph_for(workspace: str):
    """Credential provider: returns a Graph client for the workspace's connected Meta account."""
    meta = (store.load_private(workspace, "connections").get("meta") or {})
    if meta.get("mock") and not meta_mock_enabled():
        meta = {}
    if not meta.get("token_enc"):
        if meta_mock_enabled():
            return MockMetaGraph()
        raise MetaGraphError("Instagram / Meta is not connected for this workspace", needs_reauth=True)
    if meta.get("mock"):
        return MockMetaGraph()
    token = decrypt_secret(meta["token_enc"], associated_data=workspace)
    return MetaGraph(token)


def mark_needs_reauth(workspace: str) -> None:
    conn = store.load_private(workspace, "connections")
    if conn.get("meta"):
        conn["meta"]["needs_reauth"] = True
        store.save_private(workspace, "connections", conn)


async def _load_accounts(graph) -> Dict[str, Any]:
    me = await graph.request("GET", "me", {"fields": "id,name"})
    pages = await graph.request("GET", "me/accounts", {"fields": "id,name,instagram_business_account{id,username}", "limit": 50})
    accts = await graph.request("GET", "me/adaccounts", {"fields": "id,name,currency,account_status,timezone_name", "limit": 50})
    return {
        "user_name": me.get("name", ""),
        "pages": [
            {
                "id": p["id"], "name": p.get("name", ""),
                "ig_user_id": (p.get("instagram_business_account") or {}).get("id", ""),
                "ig_username": (p.get("instagram_business_account") or {}).get("username", ""),
            }
            for p in pages.get("data", [])
        ],
        "ad_accounts": [
            {"id": a["id"], "name": a.get("name", ""), "currency": a.get("currency", "USD"),
             "timezone": a.get("timezone_name", "UTC"), "active": a.get("account_status") == 1}
            for a in accts.get("data", [])
        ],
    }


def _auto_selection(accounts: Dict[str, Any]) -> Dict[str, Any]:
    pages = [p for p in accounts["pages"] if p["ig_user_id"]]
    ads = [a for a in accounts["ad_accounts"] if a["active"]]
    sel: Dict[str, Any] = {}
    if len(pages) == 1:
        p = pages[0]
        sel.update(page_id=p["id"], page_name=p["name"], ig_user_id=p["ig_user_id"], ig_username=p["ig_username"])
    if len(ads) == 1:
        a = ads[0]
        sel.update(ad_account_id=a["id"], ad_account_name=a["name"], currency=a["currency"], timezone=a["timezone"])
    return sel


async def _save_connection(workspace: str, token: str, expires_at: Optional[int], mock: bool, kind: str = "user_login") -> None:
    graph = MockMetaGraph() if mock else MetaGraph(token)
    accounts = await _load_accounts(graph)
    conn = store.load_private(workspace, "connections")
    conn["meta"] = {
        "token_enc": encrypt_secret(token, associated_data=workspace),
        "expires_at": expires_at,
        "mock": mock,
        "kind": kind,
        "connected_at": int(time.time()),
        **accounts,
        "selection": _auto_selection(accounts),
    }
    store.save_private(workspace, "connections", conn)


# ---- routes -----------------------------------------------------------------

@router.get("")
async def get_connections(x_studio_workspace: Optional[str] = Header(None)):
    try:
        return public_connection(store.load_private(_ws(x_studio_workspace), "connections"))
    except StoreError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/meta/start")
async def meta_start(workspace: str = Query(...)):
    """Browser navigates here (no custom headers possible), so the workspace comes as a query param."""
    try:
        store.load_private(workspace, "connections")  # validates the id
    except StoreError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if meta_mode() == "not_configured":
        return RedirectResponse(f"{web_app_url()}/?meta_error=meta_app_not_configured")
    state = secrets.token_urlsafe(24)
    store.cache_set("oauth_" + state.replace("-", "_"), {"workspace": workspace, "exp": time.time() + STATE_TTL_S})

    if meta_mock_enabled():
        return RedirectResponse(f"{redirect_uri()}?{urlencode({'code': 'mock', 'state': state})}")

    params = {
        "client_id": os.environ["META_APP_ID"],
        "redirect_uri": redirect_uri(),
        "state": state,
        "response_type": "code",
    }
    config_id = os.getenv("META_LOGIN_CONFIG_ID", "").strip()
    if config_id:
        params["config_id"] = config_id  # Facebook Login for Business configuration
    else:
        params["scope"] = ",".join(META_SCOPES)
    return RedirectResponse(f"https://www.facebook.com/{graph_version()}/dialog/oauth?{urlencode(params)}")


@router.get("/meta/callback")
async def meta_callback(code: str = "", state: str = "", error: str = "", error_description: str = ""):
    back = web_app_url()
    key = "oauth_" + state.replace("-", "_")
    record = store.cache_get(key) if state else None
    if not record or record.get("used") or record.get("exp", 0) < time.time():
        return RedirectResponse(f"{back}/?meta_error=invalid_or_expired_state")
    store.cache_set(key, {**record, "used": True})
    workspace = record["workspace"]

    if error or not code:
        return RedirectResponse(f"{back}/?{urlencode({'meta_error': error_description or error or 'cancelled'})}")

    try:
        if meta_mock_enabled():
            await _save_connection(workspace, "mock-token", None, mock=True)
        else:
            base = f"https://graph.facebook.com/{graph_version()}/oauth/access_token"
            async with httpx.AsyncClient(timeout=20.0) as client:
                short = await client.get(base, params={
                    "client_id": os.environ["META_APP_ID"], "client_secret": os.environ["META_APP_SECRET"],
                    "redirect_uri": redirect_uri(), "code": code,
                })
                short.raise_for_status()
                long_res = await client.get(base, params={
                    "grant_type": "fb_exchange_token", "client_id": os.environ["META_APP_ID"],
                    "client_secret": os.environ["META_APP_SECRET"], "fb_exchange_token": short.json()["access_token"],
                })
                long_res.raise_for_status()
            data = long_res.json()
            expires_in = data.get("expires_in")
            await _save_connection(workspace, data["access_token"], int(time.time() + expires_in) if expires_in else None, mock=False)
    except Exception as e:
        logger.error(f"[MetaConnect] OAuth exchange failed: {type(e).__name__}")
        return RedirectResponse(f"{back}/?meta_error=connection_failed")
    return RedirectResponse(f"{back}/?meta_connected=1")


REQUIRED_SCOPES = {
    "ads_management", "business_management", "pages_show_list", "pages_read_engagement",
    "instagram_basic", "instagram_content_publish",
}


class SystemTokenBody(BaseModel):
    token: str


@router.post("/meta/system-token")
async def meta_system_token(body: SystemTokenBody, x_studio_workspace: Optional[str] = Header(None)):
    """Connect with a Business System User token (not tied to a person's login security checks).
    The token is verified with Meta, then stored encrypted exactly like an OAuth login token."""
    ws = _ws(x_studio_workspace)
    if meta_mode() != "live":
        raise HTTPException(status_code=400, detail="Set META_APP_ID and META_APP_SECRET first")
    token = body.token.strip()
    if not token or len(token) > 1000 or any(c.isspace() for c in token):
        raise HTTPException(status_code=400, detail="Paste the full token, with no spaces")

    app_token = f"{os.environ['META_APP_ID']}|{os.environ['META_APP_SECRET']}"
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            res = await client.get(f"https://graph.facebook.com/{graph_version()}/debug_token",
                                   params={"input_token": token, "access_token": app_token})
        info = res.json().get("data") or {}
    except Exception:
        raise HTTPException(status_code=502, detail="Could not reach Meta to verify the token")
    if not info.get("is_valid"):
        raise HTTPException(status_code=400, detail="Meta says this token is not valid (expired or revoked)")
    if str(info.get("app_id")) != os.environ["META_APP_ID"]:
        raise HTTPException(status_code=400, detail="This token was generated for a different app; choose Possible Studio when generating it")
    missing = sorted(REQUIRED_SCOPES - set(info.get("scopes") or []))
    if missing:
        raise HTTPException(status_code=400, detail="Token is missing permissions: " + ", ".join(missing))

    expires = info.get("expires_at") or None  # 0 = never expires
    try:
        await _save_connection(ws, token, int(expires) if expires else None, mock=False, kind="system_user")
    except MetaGraphError as e:
        raise HTTPException(status_code=400, detail=f"Token verified, but loading accounts failed: {e}")
    conn = store.load_private(ws, "connections")
    if not conn["meta"].get("pages") or not conn["meta"].get("ad_accounts"):
        raise HTTPException(
            status_code=400,
            detail="Token works, but no Page or ad account is assigned to this System User. Assign them in Business settings and try again.",
        )
    return public_connection(conn)


class SelectionBody(BaseModel):
    page_id: str
    ad_account_id: Optional[str] = None


@router.put("/meta/selection")
async def meta_selection(body: SelectionBody, x_studio_workspace: Optional[str] = Header(None)):
    ws = _ws(x_studio_workspace)
    conn = store.load_private(ws, "connections")
    meta = conn.get("meta")
    if not meta:
        raise HTTPException(status_code=400, detail="Connect Instagram & Meta first")
    page = next((p for p in meta.get("pages", []) if p["id"] == body.page_id), None)
    if not page or not page.get("ig_user_id"):
        raise HTTPException(status_code=400, detail="Choose a Facebook Page that has an Instagram professional account linked")
    sel = {"page_id": page["id"], "page_name": page["name"], "ig_user_id": page["ig_user_id"], "ig_username": page["ig_username"]}
    if body.ad_account_id:
        acct = next((a for a in meta.get("ad_accounts", []) if a["id"] == body.ad_account_id), None)
        if not acct:
            raise HTTPException(status_code=400, detail="Unknown ad account")
        sel.update(ad_account_id=acct["id"], ad_account_name=acct["name"], currency=acct["currency"], timezone=acct["timezone"])
    meta["selection"] = sel
    store.save_private(ws, "connections", conn)
    return public_connection(conn)


@router.delete("/meta")
async def meta_disconnect(x_studio_workspace: Optional[str] = Header(None)):
    ws = _ws(x_studio_workspace)
    conn = store.load_private(ws, "connections")
    conn.pop("meta", None)
    store.save_private(ws, "connections", conn)
    return public_connection(conn)
