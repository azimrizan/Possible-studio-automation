# Campaigns: creatives → Meta strategist → Instagram → Meta ads

Two ways in, one flow out:

```
Home ─ [Create with AI Studio] ─► Poster Studio ─┐
     └ [I have my creatives]  ─► upload (posters, optional MP4) ─┤
                                                                  ▼
             Campaign Strategist agent (Groq)  ── meta-loading robot
                                                                  ▼
             Campaign Settings (every field editable, "why" under each decision)
                                                                  ▼
             Review & approve ─► post to Instagram (mcp-instagram)
                              ─► build Meta campaign PAUSED (mcp-meta-ads) ── meta-loading robot
                              ─► insta-done robot + "Launch ads" (shows daily, days, max total)
                              ─► launch (SPEND approval) ── all-done robot
```

Code: `apps/agent-runtime/campaign_strategist/`, `apps/api/app/api/studio_campaigns.py`,
`apps/api/app/api/meta_connect.py`, `mcp-servers/mcp-instagram/`, `mcp-servers/mcp-meta-ads/`,
`packages/mcp-common/src/mcp_common/{meta_graph,vault}.py`, UI in `apps/web/src/components/campaign/`.

## Strategist agent (3 Groq calls, ~4-6k tokens)

| Step | Model | Notes |
|---|---|---|
| Creative insight | `qwen3.8-27b` vision, 512px | Cached by image hash; skipped for Poster Studio creatives (already known) |
| Research plan | `gpt-oss-20b`, low effort | Picks ≤4 web queries, ≤6 Meta interest keywords, ≤4 cities |
| Research | code, parallel | Tavily/Brave snippets (trimmed to 260 chars) + Meta targeting search (real interest IDs, city keys) |
| Strategy | `gpt-oss-120b`, medium effort, strict JSON | Meta-specialist rules in the system prompt |
| Rules | code | Pixel/website prerequisites, special ad categories, budget floor/cap, schedule, drops any interest/city Meta didn't return |
| Estimate | Meta `delivery_estimate` | Audience range from Meta, labelled as an estimate |

KPIs are decision rules ("CTR below 0.8% after 3 days: refresh the hook"), never invented forecasts.

## Governance (in code, not prompts)

- Nothing is posted or built before **Approve**; nothing spends before **Launch**.
- Every MCP call carries an Ed25519 approval token minted for that exact payload; `ads.activate` is a separate SPEND token.
- `mcp-meta-ads` always creates campaign, ad set and ads `PAUSED` and enforces `META_MAX_DAILY_BUDGET`.
- Publishing is idempotent per campaign: retrying after a failure never double-posts.
- Meta tokens are long-lived, AES-GCM encrypted per workspace (`APP_MASTER_KEY`), never sent to the browser or an LLM.

## Ads delivery

- **With a website link:** link ads from each image creative (image uploaded to the ad account), CTA per ad.
- **Without a website:** the ad promotes the Instagram post that was just published (`source_instagram_media_id`), objective Engagement/Awareness.
- Sales/Leads optimisation requires a Pixel ID; without one the rules switch to Traffic (website) or Engagement.

## Running it

Demo mode (default: no `META_APP_ID`, or `MOCK_META_GRAPH=true`) connects a labelled sample account. The whole
flow works and nothing is posted or spent.

For real posting and ads:
1. Create a Meta app (Business type), add **Facebook Login for Business**, **Instagram** and **Marketing API**.
2. Add `http://localhost:3000/api/studio/connections/meta/callback` as a valid OAuth redirect URI.
3. Set `META_APP_ID`, `META_APP_SECRET`, `MOCK_META_GRAPH=false` in `.env`.
4. Your Instagram must be a Business/Creator account linked to a Facebook Page; add yourself as an app admin/tester
   (development mode needs no App Review for your own accounts).
5. Expose the app publicly so Instagram can fetch media: `cloudflared tunnel --url http://localhost:3000`
   and set `PUBLIC_ASSET_BASE_URL` to that https URL.
6. For ads without spending, use a Meta **sandbox ad account**.
7. Optional: `TAVILY_API_KEY` (free tier) enables web research.

Before onboarding customers: Meta App Review + Business Verification, and Marketing API Standard Access.

## Known limits

- Workspace = per-browser id until platform login exists (then move to JWT tenant context + Postgres/MinIO).
- Progress is polled (1.5 s) and background steps run in the API process; move to the durable worker when it exists.
- Videos in link ads are not uploaded to the ad account yet; videos are promoted via the Instagram post.
- Advantage+ audience targeting fields follow Meta's current documented shape; real API errors are surfaced verbatim.
