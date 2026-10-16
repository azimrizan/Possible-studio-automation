"""
Minimal Meta Graph API client shared by mcp-instagram and mcp-meta-ads.

`MetaGraph` talks to graph.facebook.com; `MockMetaGraph` answers the same calls with
plausible, clearly-labelled fixtures so the whole publish/ads flow runs offline
(MOCK_META_GRAPH=true or no META_APP_ID).
"""
import asyncio
import hashlib
import logging
import os
import re
from typing import Any, Dict, List, Optional, Tuple

import httpx

logger = logging.getLogger("meta_graph")

DEFAULT_VERSION = "v24.0"


class MetaGraphError(Exception):
    def __init__(self, message: str, code: int = 0, retryable: bool = False, needs_reauth: bool = False):
        super().__init__(message)
        self.code = code
        self.retryable = retryable
        self.needs_reauth = needs_reauth


def graph_version() -> str:
    return os.getenv("META_GRAPH_VERSION", DEFAULT_VERSION)


def meta_mock_enabled() -> bool:
    """Demo mode is opt-in only: a missing Meta app must never silently turn into fake posting."""
    return os.getenv("MOCK_META_GRAPH", "false").lower() == "true"


def meta_configured() -> bool:
    return bool(os.getenv("META_APP_ID", "").strip() and os.getenv("META_APP_SECRET", "").strip())


def meta_mode() -> str:
    return "mock" if meta_mock_enabled() else ("live" if meta_configured() else "not_configured")


class MetaGraph:
    mock = False

    def __init__(self, access_token: str, version: Optional[str] = None, timeout_s: float = 60.0):
        self.access_token = access_token
        self.base = f"https://graph.facebook.com/{version or graph_version()}"
        self.timeout_s = timeout_s

    async def request(
        self,
        method: str,
        path: str,
        params: Optional[Dict[str, Any]] = None,
        files: Optional[Dict[str, Tuple[str, bytes, str]]] = None,
    ) -> Dict[str, Any]:
        params = {k: v for k, v in (params or {}).items() if v is not None}
        url = f"{self.base}/{path.lstrip('/')}"
        headers = {"Authorization": f"Bearer {self.access_token}"}
        for attempt in range(3):
            try:
                async with httpx.AsyncClient(timeout=self.timeout_s) as client:
                    if method == "GET":
                        res = await client.get(url, params=params, headers=headers)
                    else:
                        res = await client.request(method, url, data=params, files=files, headers=headers)
            except httpx.HTTPError as e:
                if attempt == 2:
                    raise MetaGraphError(f"Network error calling Meta: {e}", retryable=True)
                await asyncio.sleep(1.5 * (attempt + 1))
                continue

            data = res.json() if res.content else {}
            if res.status_code == 200 and "error" not in data:
                return data
            err = data.get("error", {}) if isinstance(data, dict) else {}
            code = int(err.get("code", res.status_code) or 0)
            message = err.get("error_user_msg") or err.get("message") or res.text[:300]
            # 190 = expired/invalid token; 4/17/32/613 = rate limits; 1/2 = transient.
            needs_reauth = code == 190
            retryable = code in (1, 2, 4, 17, 32, 613) or res.status_code >= 500
            if retryable and attempt < 2:
                await asyncio.sleep(2.0 * (attempt + 1))
                continue
            raise MetaGraphError(f"Meta API error {code}: {message}", code, retryable, needs_reauth)
        raise MetaGraphError("Meta API request failed")


def _mock_id(*parts: str) -> str:
    return str(int(hashlib.sha256("|".join(parts).encode()).hexdigest()[:12], 16))


class MockMetaGraph:
    """Offline stand-in. Every object it returns is tagged so the UI can say 'mock'."""

    mock = True

    def __init__(self, access_token: str = "mock", version: Optional[str] = None):
        self.access_token = access_token
        self.calls: List[Tuple[str, str, Dict[str, Any]]] = []
        self.statuses: Dict[str, str] = {}

    async def request(self, method: str, path: str, params: Optional[Dict[str, Any]] = None, files=None) -> Dict[str, Any]:
        params = dict(params or {})
        self.calls.append((method, path, params))
        p = path.strip("/")

        if method == "GET" and p == "me":
            return {"id": "100000000000001", "name": "Demo User (mock)"}
        if method == "GET" and p == "me/accounts":
            return {"data": [{
                "id": "200000000000001", "name": "Demo Brand Page (mock)",
                "instagram_business_account": {"id": "17841400000000001", "username": "demo_brand_mock"},
            }]}
        if method == "GET" and p == "me/adaccounts":
            return {"data": [{
                "id": "act_300000000000001", "name": "Sandbox Ad Account (mock)", "currency": "INR",
                "account_status": 1, "timezone_name": "Asia/Kolkata",
            }]}
        if method == "GET" and p == "search":
            q = str(params.get("q", "")).strip() or "general"
            if params.get("type") == "adgeolocation":
                return {"data": [{"key": _mock_id("geo", q), "name": q.title(), "type": "city",
                                  "country_code": params.get("country_code", "IN"), "region": "Mock Region"}]}
            base = 400000 + (int(_mock_id(q)) % 9) * 350000
            return {"data": [
                {"id": _mock_id("int", q), "name": q.title(), "audience_size_lower_bound": base,
                 "audience_size_upper_bound": int(base * 1.18), "path": ["Interests", q.title()]},
                {"id": _mock_id("int", q, "2"), "name": f"{q.title()} enthusiasts",
                 "audience_size_lower_bound": base // 3, "audience_size_upper_bound": int(base / 3 * 1.18),
                 "path": ["Interests", q.title()]},
            ]}
        if method == "GET" and p.endswith("/delivery_estimate"):
            return {"data": [{"estimate_mau_lower_bound": 1800000, "estimate_mau_upper_bound": 2100000,
                              "estimate_dau": 650000, "estimate_ready": True}]}
        if method == "GET" and re.match(r"^cont_\w+$", p):
            return {"id": p, "status_code": "FINISHED"}
        if method == "GET" and re.match(r"^media_\w+$", p):
            return {"id": p, "permalink": f"https://www.instagram.com/p/MOCK{p[-8:].upper()}/"}

        if method == "POST" and p.endswith("/media"):
            return {"id": "cont_" + _mock_id(p, str(params.get("image_url") or params.get("video_url") or params.get("children")))}
        if method == "POST" and p.endswith("/media_publish"):
            return {"id": "media_" + _mock_id(str(params.get("creation_id")))}
        if method == "POST" and p.endswith("/adimages"):
            name = list(files.values())[0][0] if files else "image.jpg"
            return {"images": {name: {"hash": "mockhash" + _mock_id(name)[:8]}}}
        for kind in ("campaigns", "adsets", "adcreatives", "ads"):
            if method == "POST" and p.endswith(f"/{kind}"):
                new_id = f"{kind[:-1]}_{_mock_id(kind, str(params.get('name')))}"
                self.statuses[new_id] = str(params.get("status", "PAUSED"))
                return {"id": new_id}
        if method == "DELETE":
            self.statuses.pop(p, None)
            return {"success": True}
        if method == "POST" and "status" in params:
            self.statuses[p] = params["status"]
            return {"success": True}
        raise MetaGraphError(f"Mock Meta Graph has no fixture for {method} {path}")
