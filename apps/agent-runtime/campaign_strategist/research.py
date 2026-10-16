"""
Web research tool. Tavily (TAVILY_API_KEY) or Brave Search (BRAVE_SEARCH_API_KEY), both have free tiers.
Snippets are trimmed before they reach the LLM: research is the biggest token cost of the agent.
Search results are untrusted text; they are only ever passed as quoted data, never as instructions.
"""
import logging
import os
import re
from typing import Dict, List

import httpx

logger = logging.getLogger("campaign_strategist.research")

SNIPPET_CHARS = 260


def search_provider() -> str:
    if os.getenv("TAVILY_API_KEY", "").strip():
        return "tavily"
    if os.getenv("BRAVE_SEARCH_API_KEY", "").strip():
        return "brave"
    return ""


def _clean(text: str) -> str:
    text = re.sub(r"\s+", " ", text or "").strip()
    return text[:SNIPPET_CHARS]


async def web_search(query: str, max_results: int = 3) -> List[Dict[str, str]]:
    provider = search_provider()
    if not provider:
        return []
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            if provider == "tavily":
                res = await client.post(
                    "https://api.tavily.com/search",
                    headers={"Authorization": f"Bearer {os.environ['TAVILY_API_KEY']}"},
                    json={"query": query, "max_results": max_results, "search_depth": "basic"},
                )
                rows = res.json().get("results", []) if res.status_code == 200 else []
                return [{"title": _clean(r.get("title", ""))[:100], "url": r.get("url", ""), "snippet": _clean(r.get("content", ""))} for r in rows]
            res = await client.get(
                "https://api.search.brave.com/res/v1/web/search",
                headers={"X-Subscription-Token": os.environ["BRAVE_SEARCH_API_KEY"], "Accept": "application/json"},
                params={"q": query, "count": max_results},
            )
            rows = (res.json().get("web") or {}).get("results", []) if res.status_code == 200 else []
            return [{"title": _clean(r.get("title", ""))[:100], "url": r.get("url", ""), "snippet": _clean(r.get("description", ""))} for r in rows]
    except Exception as e:
        logger.warning(f"[research] search failed for '{query}': {e}")
        return []
