"""
Read-only proxy for the public tunnel: exposes ONLY GET/HEAD /api/studio/assets/<workspace>/<file>,
Meta's OAuth callback (GET /api/studio/connections/meta/callback) and the static legal pages /legal/{privacy,terms,data-deletion}.html (Meta requires public URLs).

Instagram and Meta must download media from a public HTTPS URL. Tunnelling the whole app
would also expose every API route, so the tunnel points here instead:

    .venv/bin/python scripts/asset_tunnel_proxy.py          # listens on 127.0.0.1:8090
    .tools/cloudflared tunnel --url http://127.0.0.1:8090   # prints the https URL
    # .env: PUBLIC_ASSET_BASE_URL=<that https URL>
"""
import os
import re

import httpx
import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import Response

UPSTREAM = os.getenv("ASSET_UPSTREAM", "http://127.0.0.1:8000")
WEB_UPSTREAM = os.getenv("WEB_UPSTREAM", "http://127.0.0.1:3000")
LEGAL_PAGES = {"privacy.html", "terms.html", "data-deletion.html"}
PATH_RE = re.compile(r"^[A-Za-z0-9_-]{8,64}/[a-f0-9]{32}\.(png|jpg|mp4)$")

app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)


@app.api_route("/api/studio/assets/{path:path}", methods=["GET", "HEAD"])
async def asset(path: str, request: Request):
    if not PATH_RE.match(path):
        raise HTTPException(status_code=404)
    headers = {k: v for k, v in request.headers.items() if k.lower() == "range"}
    async with httpx.AsyncClient(timeout=60.0) as client:
        res = await client.request(request.method, f"{UPSTREAM}/api/studio/assets/{path}", headers=headers)
    passthrough = {k: v for k, v in res.headers.items()
                   if k.lower() in ("content-type", "content-length", "content-range", "accept-ranges", "cache-control")}
    return Response(content=res.content, status_code=res.status_code, headers=passthrough)


@app.api_route("/legal/{page}", methods=["GET", "HEAD"])
async def legal(page: str, request: Request):
    if page not in LEGAL_PAGES:
        raise HTTPException(status_code=404)
    async with httpx.AsyncClient(timeout=20.0) as client:
        res = await client.request(request.method, f"{WEB_UPSTREAM}/legal/{page}")
    return Response(content=res.content, status_code=res.status_code, media_type="text/html; charset=utf-8")


@app.get("/api/studio/connections/meta/callback")
async def meta_callback(request: Request):
    """Meta's OAuth redirect (Live apps need https). The API validates the one-time state and
    redirects the browser back to the local web app; we pass that redirect through untouched."""
    async with httpx.AsyncClient(timeout=30.0, follow_redirects=False) as client:
        res = await client.get(f"{UPSTREAM}/api/studio/connections/meta/callback", params=request.query_params)
    headers = {"location": res.headers["location"]} if "location" in res.headers else {}
    return Response(content=b"", status_code=res.status_code, headers=headers)


@app.api_route("/{path:path}", methods=["GET", "HEAD", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"])
async def blocked(path: str):
    raise HTTPException(status_code=404)


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=int(os.getenv("ASSET_PROXY_PORT", "8090")))
