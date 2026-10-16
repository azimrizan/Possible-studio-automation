# MASTER BUILD PROMPT: "AI Marketing Employee" (AI-powered social media + ads + lead-conversion platform)

## 0. HOW YOU (ANTIGRAVITY) MUST WORK
You are acting as a principal engineer and architect with 15+ years of experience shipping production GenAI SaaS.

Rules of engagement:
1. **Plan first.** Before writing code, produce a Planning Artifact: architecture diagram, repo structure, data model, API contracts, MCP tool catalog, risk register. Wait for my approval.
2. **Build phase by phase** (Section 6). Never start phase N+1 until phase N's acceptance criteria pass and I approve. At the end of each phase, give me: what was built, how to run it, test results, known gaps.
3. **Mock-first for external APIs.** Every external integration (Meta, Instagram, WhatsApp, Gemini, etc.) sits behind an interface with a real adapter and a mock adapter. The whole product must run end-to-end locally with mocks.
4. **Tests are part of "done".** Unit tests for logic, contract tests for adapters and MCP tools, one E2E test per phase.
5. **No secrets in code.** Use env vars and a secrets abstraction. Provide `.env.example`.
6. **We build all MCP servers ourselves.** Do not depend on third-party or community MCP servers for core platform functions (Instagram, Meta Ads, WhatsApp, media rendering, etc.). Wrap the official vendor APIs directly.
7. **Ask me when something is genuinely ambiguous**; otherwise state your assumption and proceed.

## 1. PRODUCT VISION
A multi-tenant SaaS where a small business types one prompt (e.g. "make a digital poster for my air fryer") and an AI team handles the rest:

prompt → enhanced brief → on-brand creative (poster / reel / both) → human approval → publish to Instagram → market research + Meta Ads strategy → ad launch (via our Meta Ads MCP) → continuous monitoring and optimization suggestions → auto-replies and lead conversion on Instagram DMs and WhatsApp.

The product is **agentic but human-governed**: AI proposes and executes, humans approve anything public-facing or money-spending.

## 2. TECH STACK (use unless you justify a change)
- **Frontend:** Next.js (App Router) + TypeScript, Tailwind, shadcn/ui, TanStack Query, SSE/WebSocket for live agent progress.
- **Backend API:** Python 3.12 + FastAPI, Pydantic v2, SQLAlchemy 2 + Alembic.
- **Agent orchestration:** LangGraph (stateful graphs, checkpointing, `interrupt()` for human-in-the-loop). Each agent is a node or subgraph with typed input/output schemas.
- **Durable workflows / long jobs:** Temporal (preferred) or Celery + Redis. Video generation, publishing and ad sync must be retryable, idempotent and resumable.
- **DB:** PostgreSQL + pgvector (brand knowledge, conversation memory). Redis for cache, rate limiting, pub/sub.
- **Storage:** S3-compatible (MinIO locally) for assets; signed URLs only.
- **Rendering:** Playwright/Satori for poster compositing (HTML/CSS templates driven by design tokens); FFmpeg (+ optionally Remotion) for reel assembly: captions, music, transitions, 9:16 export.
- **LLM layer:** a provider-agnostic `ModelGateway` (Gemini default; pluggable for Claude / OpenAI). Model names live in config, never hard-coded. Include structured-output enforcement, retries, timeouts, token/cost metering per tenant.
- **Image/video models:** behind `ImageProvider` and `VideoProvider` interfaces (Gemini image generation and Veo-class video as default adapters, plus a mock).
- **MCP:** our own **MCP Server Fleet** plus **MCP Gateway** (Section 4). Use the official MCP SDK (Python or TypeScript) and the current MCP spec; check the latest spec version and transport recommendations (Streamable HTTP for remote servers) before designing.
- **Observability:** OpenTelemetry + Langfuse (or equivalent) for traces of every agent step, prompt, tool call, cost and latency. Sentry for errors.
- **Infra:** Docker Compose for local; Terraform + containers (AWS ECS/Fargate or GKE) for cloud. GitHub Actions CI.

## 3. ARCHITECTURE
Services (monorepo, clean boundaries):
- `web` – Next.js app
- `api` – FastAPI (auth, tenants, campaigns, assets, approvals, billing hooks)
- `agent-runtime` – LangGraph graphs + workers
- `mcp-gateway` – connector registry, OAuth token vault, tool proxy, policy enforcement
- `mcp-servers/` – our own MCP servers, one package each (Section 4)
- `render-service` – poster compositing and video assembly
- `webhook-service` – inbound Meta (Instagram/WhatsApp) webhooks: signature verification, dedupe, enqueue
- `scheduler` – publish schedules, ad sync, report jobs

Cross-cutting principles:
- **Every tenant-owned row has `tenant_id`; enforce with Postgres Row-Level Security.**
- **Event-sourced campaign timeline:** every agent action, approval and external call is an immutable event (audit log + UI timeline).
- **Idempotency keys** on all publish/ad/message actions.
- **Typed contracts between agents** (Pydantic schemas). Agents never pass free-form text to each other when structured data is possible.
- **Policy engine** (code, not prompts) decides what can run without approval.

## 4. MCP SERVER FLEET AND MCP GATEWAY (WE BUILD ALL OF IT)

### 4.1 Our MCP servers (first-party, built in-house)
Build each as a standalone, independently deployable MCP server with its own tool schemas, tests and mock mode:

| Server | Wraps | Example tools |
|---|---|---|
| `mcp-instagram` | Instagram Graph API (content publishing, comments, insights, DMs) | `create_media_container`, `check_container_status`, `publish_media`, `schedule_post`, `get_post_insights`, `list_comments`, `reply_comment`, `send_dm` |
| `mcp-meta-ads` | Meta Marketing API | `create_campaign`, `create_adset`, `create_ad`, `upload_creative`, `set_status`, `update_budget`, `get_insights`, `estimate_reach`, `list_ad_accounts` |
| `mcp-whatsapp` | WhatsApp Cloud API | `send_template_message`, `send_session_message`, `list_templates`, `mark_read`, `get_media` |
| `mcp-media` | our render-service | `render_poster`, `render_reel`, `get_render_status` |
| `mcp-gemini` (and later others) | Google Gemini API using the **tenant's own key/account** | `image.generate`, `video.generate`, `text.generate` |
| `mcp-crm` | our lightweight CRM | `create_lead`, `update_lead_stage`, `add_note`, `search_leads` |
| `mcp-knowledge` | tenant knowledge base (RAG) | `search_kb`, `get_brand_tokens` |
| `mcp-research` | web search/fetch, Meta Ad Library where permitted | `web_search`, `fetch_page`, `ad_library_search` |

Rules for every MCP server:
- **Shared MCP SDK package** (`packages/mcp-common`): auth middleware, tenant context, structured logging, error taxonomy (retryable vs terminal vs needs-human), idempotency handling, pagination, rate-limit and backoff helpers, secret redaction, OpenTelemetry tracing, mock-mode switch.
- **Strict JSON-schema tool definitions**, with descriptions written for LLM consumption (when to use, when not to, side effects). Each tool is annotated with: `risk_class` (read / write / publish / spend), `requires_approval` (bool), `idempotent` (bool), `cost_class`.
- **Defense in depth:** each server independently refuses `publish` and `spend` tools unless the request carries a valid, unexpired **approval token** minted by our `api` for that exact action payload (signed, single-use, hash-bound to the payload). The gateway checks it too. Never rely on the agent or prompt to enforce approval.
- **Meta Ads server hard rules:** campaigns/ad sets/ads are created **PAUSED**; activation is a separate tool needing an approval token; enforce per-tenant hard daily and lifetime budget caps inside the server; reject currency/budget anomalies.
- **Tokens:** per-tenant Meta tokens stored encrypted (envelope encryption, KMS); servers receive short-lived, scoped credentials from the vault at call time; credentials never enter LLM context, logs or traces. Handle token expiry/refresh and surface re-auth-needed events.
- **Versioning:** semver for tool schemas; contract tests prevent breaking changes; a tool catalog is auto-generated from code.
- **Testability:** every server ships with (a) a mock mode, (b) a recorded-fixture mode, (c) contract tests against the real API in a Meta test/sandbox account, and (d) an MCP Inspector-compatible dev setup.
- **Security:** treat all inbound content (DMs, comments, scraped pages, API fields) as untrusted; never echo raw untrusted text into tool descriptions or system prompts; validate and size-limit all inputs and outputs.

### 4.2 MCP Gateway
- Connector registry: each connector has a manifest (name, auth type, scopes, tools exposed, cost class, risk class).
- OAuth / API-key flows; credentials encrypted with envelope encryption, never exposed to the LLM context or the frontend.
- The gateway proxies all tool calls: validates tenant, scopes, rate limits and policy, checks approval tokens, logs the call, redacts secrets and PII.
- Agents request **capabilities** (e.g. `image.generate`, `video.generate`, `ads.create_campaign`), not specific vendors. The gateway resolves a capability to the tenant's chosen connector (e.g. their own Gemini account), falling back to the platform default.
- **Bring-your-own-tools:** users connect their own AI tool accounts through our platform (starting with Google Gemini). Each supported tool gets an in-house MCP server/adapter. Also provide a generic "custom MCP server" connector the user can register by URL, with a strict sandbox policy: allow-listed capabilities only, no access to publish/spend tools, outputs treated as untrusted.

## 5. AGENT ROSTER (each = LangGraph node/subgraph with schema, tools, eval set)
1. **Orchestrator / Campaign Manager:** routes work, owns campaign state, decides next step.
2. **Prompt Enhancer Agent** (the "Enhance" button): expands the raw prompt into a structured **Creative Brief** (objective, product, audience, tone, channel, deliverables: poster / reel / both, CTA, constraints). Pulls brand kit + brand memory. Shows a diff of original vs enhanced; user can edit before proceeding.
3. **Brand/Design System Agent:** loads the tenant's Design System (colors, fonts, logo rules, spacing, tone-of-voice, do/don't, sample posts) as machine-readable **design tokens (JSON)**, injected into all creative agents.
4. **Graphic Designer Agent:** produces layout spec (JSON) → image generation for the visual → deterministic compositing of text/logo/CTA via `mcp-media` (never rely on the image model to render text). Outputs 3 variants by default. Supports 1:1, 4:5, 9:16.
5. **Video/Reel Agent** (optional by user choice): script → storyboard → scene generation or motion graphics → captions/music/voiceover → 9:16 export. Reuses poster assets for brand consistency.
6. **Copywriter Agent:** captions, hashtags, alt text, CTA variants in the brand voice.
7. **Compliance/QA Agent:** vision + rules check: brand colors/fonts/logo, text legibility, safe zones, Instagram specs, prohibited claims, trademark/IP red flags, Meta ad policy risks. Returns pass/warn/fail with reasons. Fail blocks approval.
8. **Publisher Agent:** schedules and publishes via `mcp-instagram`; verifies the post is live; stores permalink.
9. **Market Research Agent:** audience, competitor and trend research via `mcp-research`; outputs structured insights with sources and confidence.
10. **Ads Strategist Agent:** objective, budget split, audience/targeting, placements, creative-to-ad-set mapping, duration, predicted ranges (labelled as estimates).
11. **Ads Ops Agent:** builds campaign → ad set → ad via `mcp-meta-ads`. **Always PAUSED**, activated only after explicit approval.
12. **Performance Analyst Agent:** pulls insights on a schedule (spend, reach, impressions, CTR, CPC, CPA/CPL, per-creative and per-audience), detects anomalies, writes plain-language insights and **recommended actions** (increase budget, pause creative, test new audience, new creative suggestion). Each recommendation is an approvable action card.
13. **Inbox Agent (Instagram DM, comments, WhatsApp):** intent classification, brand-voiced replies, FAQ/RAG answers via `mcp-knowledge`, lead qualification (name/phone/need), booking or checkout link, CRM write via `mcp-crm`, human handoff on low confidence, anger, payment, complaint, or sensitive topics.

## 6. PHASES (deliver sequentially; each ends with a demo + acceptance tests)

### Phase 0: Foundations and Planning
Monorepo, Docker Compose, CI, lint/format, env management, base FastAPI + Next.js shell, Postgres with RLS, auth (email + OAuth), tenants/workspaces/roles (Owner, Editor, Approver, Viewer), observability skeleton, `ModelGateway`, mock adapters, and the **`mcp-common` SDK skeleton plus one "hello" MCP server** wired through the gateway.
**Accept:** `docker compose up` runs everything; a user can sign up, create a workspace; a traced "hello agent" call goes agent → gateway → hello MCP server and appears in Langfuse.

### Phase 1: Dashboard, Brand Kit and Design System
Dashboard matching the UX in my attached flow (sidebar: Marketing, Sales, Proposal, Execution, Management; prompt bar with attach files, product details, advanced options). Brand Kit onboarding: upload logo, colors, fonts, tone, sample posts, product catalog → compiled into design tokens + embeddings. Build `mcp-knowledge`.
**Accept:** brand kit saved, versioned, retrievable as tokens JSON via MCP; the prompt bar persists draft campaigns.

### Phase 2: Prompt Enhancer and Campaign Brief
"Enhance" button → Prompt Enhancer Agent → editable structured Brief; deliverable selector (Poster / Reel / Both) and channel options. Streaming progress UI (the "Understanding & Planning" checklist from my flow).
**Accept:** the same raw prompt yields schema-valid briefs; user edits are respected; an eval set of 20 prompts scores above the agreed threshold.

### Phase 3: Creative Generation (Poster)
Build `mcp-media` (poster rendering) and `mcp-gemini` (image generation, platform key for now). Graphic Designer Agent with design tokens; layout-spec → image gen → deterministic compositing; 3 variants; caption/hashtag generation; asset storage and versioning.
**Accept:** posters never contain model-rendered text errors (text is composited); logo/colors match the design system; the variant gallery works.

### Phase 4: Reel / Video Generation
Video Agent: script → storyboard → clips/motion graphics → captions + music → FFmpeg/Remotion export 9:16, ≤ 90s via `mcp-media` and `mcp-gemini` video. Async, resumable jobs with progress. A user can pick Poster only, Reel only, or both from one brief.
**Accept:** a reel is produced end-to-end from one brief with brand-consistent captions; the job survives a worker restart.

### Phase 5: Human-in-the-Loop Review and Approval
LangGraph `interrupt()` at the approval gate. Review screen (as in my flow, step 5): preview, brand-compliance checklist, campaign details, **Approve / Request Changes**. "Request Changes" takes free-text feedback → converted to structured edit instructions → targeted regeneration (not full restart), keeping version history and diff. Comments per asset. Only Approvers can approve. **Approval service mints signed, single-use, payload-bound approval tokens** consumed by the MCP servers.
**Accept:** the graph pauses indefinitely and resumes correctly after approval or feedback; there is no path to publish without a valid approval token.

### Phase 6: MCP Gateway Hardening and Bring-Your-Own-Tools
Connector registry, OAuth/key vault, capability routing, policy engine, usage metering. Ship the BYO connector for the user's own Google Gemini account (routing through `mcp-gemini` with the tenant's credentials), plus the sandboxed "custom MCP server by URL" connector. Complete the shared contract-test suite that every MCP server must pass (schema validity, risk annotations, approval enforcement, redaction, idempotency).
**Accept:** a user connects their own Gemini account and generations route through it; credentials never appear in logs, traces or LLM context; a custom MCP server cannot call publish/spend tools.

### Phase 7: Instagram Publishing (`mcp-instagram`)
Build `mcp-instagram` over the Instagram Graph API. Handle the account prerequisites (professional account linked to a Facebook Page, required permissions, app review and test-mode flow), the container-create → status-poll → publish sequence for image, carousel and reel, media specs, rate limits, scheduling, retries and idempotency. Post-publish verification and permalink.
**Accept:** end-to-end approve → publish works in a Meta test setup; failures surface a clear, actionable error; no duplicate posts on retry; the server rejects publish without a valid approval token.

### Phase 8: Research and Meta Ads (`mcp-research`, `mcp-meta-ads`)
Build both servers. Market Research Agent → Ads Strategist → Ads Ops. Strategy UI (as in my flow step 3). Campaign → ad set → ad structure; creatives from approved assets; **created PAUSED**; hard daily and lifetime budget caps enforced inside `mcp-meta-ads`; explicit "Launch" approval showing budget, audience, dates, and estimated reach labelled as estimates.
**Accept:** the ad structure is created in a Meta sandbox/test ad account; no spend is possible without approval and caps; a full audit trail exists.

### Phase 9: Monitoring and Optimization
Scheduled insights sync via `mcp-meta-ads`; metrics warehouse tables; dashboards (spend, reach, CTR, CPC, CPA, per-creative/audience); Performance Analyst Agent writes insights and **one-click approvable recommendations** (apply budget change, pause creative, add audience, generate new creative, which loops back to Phase 3). Alerts for anomalies and budget pacing.
**Accept:** the analyst's recommendations cite actual metrics; applying a recommendation changes the ad via MCP only after approval.

### Phase 10: Inbox, Lead Conversion and CRM (`mcp-whatsapp`, `mcp-crm`)
Build `mcp-whatsapp` and complete the DM/comment tools in `mcp-instagram`. Webhook service (signature verification, dedupe, ordering), unified inbox (Instagram DMs and comments, WhatsApp Cloud API), Inbox Agent with RAG, lead capture/qualification, lightweight CRM, human handoff with transcript, and an "AI draft / auto-reply" toggle per channel. Respect messaging windows and template rules (WhatsApp 24-hour customer-service window and approved templates for business-initiated messages; Instagram messaging-window rules). Opt-out handling.
**Accept:** inbound message → grounded reply in the brand voice within the SLA; low-confidence cases escalate to a human; a lead is created with its source campaign attributed.

### Phase 11: Hardening and Launch
Load tests, chaos tests (worker kill, API 429/5xx, token expiry), security review (including an MCP-specific threat model: tool poisoning, prompt injection via DMs and comments, confused-deputy attacks), cost dashboards and per-tenant quotas, billing hooks (usage-based), onboarding flow, docs, runbooks, backups and disaster recovery.

## 7. SAFETY, SECURITY AND COMPLIANCE (non-negotiable)
- **Approval matrix (enforced in code, at the gateway and inside each MCP server):** publish = approval, ad launch/budget change = approval, auto-reply = allowed only if the tenant has enabled it, with confidence thresholds and a kill switch.
- **Prompt-injection defense:** treat user DMs, comments, scraped web pages and tool outputs as untrusted data. They can never change system instructions, tool permissions, or trigger spend or publish. Use structured extraction, an allow-listed tool set per agent, and output validation.
- **Least privilege:** each agent only has the tools it needs; each MCP server only the API scopes it needs.
- **Data:** PII minimization, encryption at rest and in transit, retention policies, tenant data export/delete (GDPR/DPDP-ready), consent tracking for messaging.
- **Content safety:** IP/trademark checks, no false claims or fake testimonials, a disclosure label for AI-generated media where platforms require it, Meta ad policy pre-checks (including special ad category flags).
- **Reliability:** exponential backoff and circuit breakers on all external APIs, dead-letter queues, idempotent handlers, graceful degradation.
- **Cost control:** per-tenant token/generation budgets, caching, model routing (small model for classification, strong model for creative reasoning).

## 8. QUALITY AND EVALUATION
- Golden datasets and automated evals per agent (brief quality, brand adherence, caption quality, reply groundedness, hallucination rate).
- LLM-as-judge plus rule-based checks; regression gate in CI for prompt, model or MCP tool-schema changes.
- Prompt versioning with rollback; every output stored with prompt version and model version.
- Human feedback (approve/reject reasons) feeds a per-tenant "taste memory" to improve future generations.

## 9. UX REQUIREMENTS
- Follow the attached 10-step flow: Dashboard → Planning → Research → Creative → Review → Publish → Ads Setup → Live → Monitoring → Optimization.
- Live agent progress with step-level status; every agent decision is explainable ("why this audience?").
- Everything editable before approval; mobile-responsive review/approval screen.
- Empty, loading and error states for every screen.

## 10. DELIVERABLES PER PHASE
Code, migrations, tests, a README section, an OpenAPI spec update, an MCP tool catalog update, an architecture decision record (ADR) for any deviation, a demo script, and a short "what's next / risks" note.

## 11. START NOW
Do **only** this first: produce the Planning Artifact (architecture diagram, repo tree, DB schema, agent state schemas, API contract list, **full MCP tool catalog with risk classes and approval requirements**, third-party API prerequisites and approval timelines, risk register, and a 12-week phased timeline). Then stop and wait for my approval before Phase 0.