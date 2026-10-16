# Poster Studio

Turns a product photo + a one-line direction (+ an optional brand kit) into three
designer-grade posters. Groq does the art direction; Gemini renders the final image
with the real product photo and logo as reference images.

## Flow

```
product photo(s) ─┐
user direction ───┼─► [1] Product analyst   Groq vision (qwen3.8-27b), 512px, cached by image hash
brand kit (opt.) ─┘   [2] Creative Director  gpt-oss-120b, reasoning=medium, strict JSON schema
                                             → 3 compact concepts (idea, scene, vocab enums, copy)
                      [3] Prompt Composer    code only — expands enums via poster_studio/vocab.py
                      [4] Gemini image model product photo(s) + logo + prompt → poster
                      [5] QA                 Groq vision, 512px: headline spelling + logo integrity
                                             → one targeted re-render → logo lock (Pillow) if needed
```

Code: `apps/agent-runtime/poster_studio/`, API: `apps/api/app/api/studio.py`,
Gemini client: `mcp-servers/mcp-gemini/gemini_image.py`.

## API (`/api/studio`, header `X-Studio-Workspace`)

| Method | Path | Purpose |
|---|---|---|
| GET / PUT / DELETE | `/brand-kit` | Read, update (all fields optional), clear |
| POST / DELETE | `/brand-kit/logo` | Upload (analysed once) / remove logo |
| POST | `/uploads` | Product photo → `asset_id` |
| GET | `/assets/{workspace}/{file}` | Serve uploads and posters |
| POST | `/posters/generate` | 3 posters; `use_brand_kit:false` ignores the kit |
| POST | `/posters/regenerate` | One poster; text edits use no LLM, `change` uses one small call |

Gemini credentials: the user's key / Google OAuth token from the request, else
`GEMINI_API_KEY`. With neither, `MOCK_GEMINI=true` returns labelled placeholders;
otherwise the API returns 400.

## Token budget (measured, Oct 2026)

| Step | Input | Output | When |
|---|---|---|---|
| Product analysis | ~1.4k | ~150 | first time a photo is seen |
| Logo analysis | ~0.8k | ~40 | once, at upload |
| Creative Director | ~1.2–1.3k | ~1.7–2.6k (incl. ~1–2k hidden reasoning) | every generation |
| QA (per poster) | ~1.3k | ~25 | per render (disable: `POSTER_QA_ENABLED=false`) |
| Revise (edit with a change note) | ~0.6k | ~300 | per edit |

Choices that keep tokens low without losing quality:
- The Director outputs ~150 tokens per concept; the 400-word Gemini prompt is assembled in code.
- `reasoning_effort=medium` was kept after an A/B: `low` halved tokens but produced flatter ideas
  and dropped a stated "20% off" offer. Override with `POSTER_DIRECTOR_REASONING_EFFORT`.
- Strict `json_schema` output means no repair round-trips.
- Static system prompts first, so Groq prompt caching can apply where the model supports it.
- "Generate more" sends only previous big-idea lines as `AVOID`.

## Known limits

- Workspaces are per-browser ids until the web app has platform login; move to the JWT tenant
  context (`deps.get_tenant_context`) and MinIO storage when it does.
- Product fidelity is enforced by prompt, not checked by QA (would need a second image per check).
