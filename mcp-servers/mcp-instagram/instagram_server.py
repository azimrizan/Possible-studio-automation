"""
mcp-instagram: publishes images, carousels and reels via the Instagram Graph API
(container -> poll -> publish -> permalink).

Credentials are never tool arguments: the hosting process sets `graph_provider`,
which resolves a Graph client for the calling tenant from the encrypted vault.
`instagram.publish` is a PUBLISH tool, so MCPServer rejects it without a valid,
payload-bound approval token.
"""
import asyncio
import logging
from typing import Any, Awaitable, Callable, Dict, List, Optional

from mcp_common import MCPServer, RiskClass, TenantContext
from mcp_common.meta_graph import MetaGraphError

logger = logging.getLogger("mcp_instagram")

GraphProvider = Callable[[TenantContext], Awaitable[Any]]
graph_provider: Optional[GraphProvider] = None

MAX_CAROUSEL_ITEMS = 10
POLL_INTERVAL_S = 3.0
POLL_TIMEOUT_S = 300.0  # reels can take minutes to process

server = MCPServer(name="mcp-instagram", version="0.1.0")
_published: Dict[str, Dict[str, Any]] = {}  # idempotency_key -> result (process-local; API also persists)


async def _graph(ctx: TenantContext):
    if not graph_provider:
        raise RuntimeError("mcp-instagram has no credential provider configured")
    return await graph_provider(ctx)


async def _wait_until_ready(graph, container_id: str) -> None:
    waited = 0.0
    while True:
        status = (await graph.request("GET", container_id, {"fields": "status_code,status"})).get("status_code")
        if status in ("FINISHED", "PUBLISHED"):
            return
        if status in ("ERROR", "EXPIRED"):
            raise MetaGraphError(f"Instagram could not process media container {container_id} ({status})")
        if waited >= POLL_TIMEOUT_S:
            raise MetaGraphError(f"Instagram media processing timed out after {POLL_TIMEOUT_S:.0f}s", retryable=True)
        await asyncio.sleep(POLL_INTERVAL_S if not getattr(graph, "mock", False) else 0)
        waited += POLL_INTERVAL_S


async def publish(graph, ig_user_id: str, items: List[Dict[str, str]], caption: str) -> Dict[str, Any]:
    """items: [{"url": public https url, "kind": "image"|"video"}] — 1 item = single post/reel, 2-10 = carousel."""
    if not items:
        raise ValueError("Nothing to publish")
    if len(items) > MAX_CAROUSEL_ITEMS:
        raise ValueError(f"Instagram carousels allow at most {MAX_CAROUSEL_ITEMS} items")

    if len(items) == 1:
        item = items[0]
        params: Dict[str, Any] = {"caption": caption}
        if item["kind"] == "video":
            params.update(media_type="REELS", video_url=item["url"], share_to_feed="true")
        else:
            params["image_url"] = item["url"]
        container = (await graph.request("POST", f"{ig_user_id}/media", params))["id"]
        await _wait_until_ready(graph, container)
    else:
        children = []
        for item in items:
            params = {"is_carousel_item": "true"}
            if item["kind"] == "video":
                params.update(media_type="VIDEO", video_url=item["url"])
            else:
                params["image_url"] = item["url"]
            child = (await graph.request("POST", f"{ig_user_id}/media", params))["id"]
            children.append(child)
        for child in children:
            await _wait_until_ready(graph, child)
        container = (await graph.request(
            "POST", f"{ig_user_id}/media", {"media_type": "CAROUSEL", "children": ",".join(children), "caption": caption}
        ))["id"]
        await _wait_until_ready(graph, container)

    media_id = (await graph.request("POST", f"{ig_user_id}/media_publish", {"creation_id": container}))["id"]
    permalink = (await graph.request("GET", media_id, {"fields": "permalink"})).get("permalink", "")
    return {"media_id": media_id, "permalink": permalink, "mock": bool(getattr(graph, "mock", False))}


async def handle_publish(args: Dict[str, Any], ctx: TenantContext) -> Dict[str, Any]:
    key = args.get("idempotency_key") or ""
    if key and key in _published:
        return {**_published[key], "deduplicated": True}
    graph = await _graph(ctx)
    result = await publish(graph, args["ig_user_id"], args["items"], args.get("caption", "")[:2200])
    if key:
        _published[key] = result
    logger.info(f"[mcp-instagram] published {result['media_id']} for tenant {ctx.tenant_id}")
    return result


server.register_tool(
    name="instagram.publish",
    description=(
        "Publish an approved image, carousel (2-10 items) or reel to the tenant's connected Instagram "
        "professional account. Side effect: the post goes live publicly. Requires an approval token."
    ),
    handler=handle_publish,
    parameters_schema={
        "type": "object",
        "properties": {
            "ig_user_id": {"type": "string"},
            "items": {"type": "array", "items": {"type": "object"}},
            "caption": {"type": "string"},
            "idempotency_key": {"type": "string"},
        },
        "required": ["ig_user_id", "items"],
    },
    risk_class=RiskClass.PUBLISH,
    requires_approval=True,
    idempotent=True,
)

app = server.app
