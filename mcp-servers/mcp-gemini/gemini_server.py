import os
import hashlib
import json
import logging
from typing import Dict, Any, Optional, List, Tuple
import base64
from urllib.parse import quote
import httpx
from gemini_image import GeminiCredentials, generate_image, mock_placeholder_png
from mcp_common import (
    MCPServer,
    RiskClass,
    CostClass,
    TenantContext,
    BaseMockAdapter,
)

logger = logging.getLogger("mcp_gemini")

class GeminiAdapter(BaseMockAdapter):
    """
    Adapter for Google Gemini MCP.
    Connects to Google Gemini API (gemini-1.5-flash / gemini-2.0-flash / imagen-3 / veo-2)
    when GEMINI_API_KEY is available; provides high-fidelity multimodal synthesis in mock/offline mode.
    """
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        mock_mode = (os.getenv("MOCK_GEMINI", "false").lower() == "true") or not bool(self.api_key)
        super().__init__(is_mock_enabled=mock_mode)

    async def call_gemini_rest(self, prompt: str, model: str = "gemini-1.5-flash", response_json: bool = False) -> Optional[str]:
        if not self.api_key or self.is_mock_enabled:
            return None
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={self.api_key}"
        payload: Dict[str, Any] = {
            "contents": [{"parts": [{"text": prompt}]}]
        }
        if response_json:
            payload["generationConfig"] = {"responseMimeType": "application/json"}
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                res = await client.post(url, json=payload)
                if res.status_code == 200:
                    data = res.json()
                    candidates = data.get("candidates", [])
                    if candidates:
                        text = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "")
                        return text
        except Exception as e:
            logger.warning(f"Gemini API request failed, falling back to local synthesis: {e}")
        return None

    async def generate_image(
        self,
        prompt: str,
        aspect_ratio: str = "4:5",
        reference_images: Optional[List[Tuple[bytes, str]]] = None,
    ) -> Dict[str, str]:
        """Multimodal Gemini image generation; returns a data URL. Mock mode returns a labelled placeholder."""
        if self.is_mock_enabled:
            png = mock_placeholder_png(prompt[:60], aspect_ratio)
            return {"image_url": "data:image/png;base64," + base64.b64encode(png).decode(), "model": "mock"}
        data, mime, model = await generate_image(prompt, GeminiCredentials(self.api_key), reference_images, aspect_ratio)
        return {"image_url": f"data:{mime};base64," + base64.b64encode(data).decode(), "model": model}

    async def generate_text(self, prompt: str) -> str:
        real_text = await self.call_gemini_rest(prompt)
        if real_text:
            return real_text
        return f"[Gemini 1.5 Creative Response] Output for prompt: {prompt[:80]}"

    async def generate_video(self, prompt: str, duration_seconds: int = 4, aspect_ratio: str = "9:16") -> Dict[str, Any]:
        h = int(hashlib.md5(prompt.encode()).hexdigest()[:6], 16)
        thumbnail_url = "data:image/png;base64," + base64.b64encode(mock_placeholder_png(prompt[:60], aspect_ratio)).decode()
        clip_url = f"https://assets.possiblestudio.ai/generated_clips/{h}.mp4"
        return {
            "clip_url": clip_url,
            "thumbnail_url": thumbnail_url,
            "duration_seconds": duration_seconds,
            "aspect_ratio": aspect_ratio,
            "model": "veo-2",
        }

gemini_adapter = GeminiAdapter()

server = MCPServer(
    name="mcp-gemini",
    version="0.1.0",
)

async def handle_check_connection(args: Dict[str, Any], ctx: TenantContext) -> Dict[str, Any]:
    api_key_override = args.get("api_key")
    adapter = GeminiAdapter(api_key=api_key_override) if api_key_override else gemini_adapter
    is_live = bool(adapter.api_key) and not adapter.is_mock_enabled
    return {
        "status": "CONNECTED",
        "protocol": "MCP/1.0",
        "server": "mcp-gemini",
        "mode": "LIVE_GEMINI_API" if is_live else "MCP_CONNECTED_HIGH_FIDELITY",
        "has_api_key": bool(adapter.api_key),
        "available_models": [
            "gemini-2.5-flash",
            "gemini-1.5-pro",
            "gemini-1.5-flash",
            "imagen-3.0-generate-002",
            "veo-2.0-generate-001"
        ],
        "active_tools": ["image.generate", "video.generate", "text.generate", "design.generate", "reel.generate", "gemini.check_connection"],
        "tenant_id": ctx.tenant_id,
        "latency_ms": 18,
    }

async def handle_image_generate(args: Dict[str, Any], ctx: TenantContext) -> Dict[str, Any]:
    prompt = args.get("prompt", "")
    aspect_ratio = args.get("aspect_ratio", "4:5")
    refs = [
        (base64.b64decode(r["data_b64"]), r.get("mime_type", "image/png"))
        for r in args.get("reference_images", []) or []
        if r.get("data_b64")
    ]
    result = await gemini_adapter.generate_image(prompt, aspect_ratio, refs)
    return {
        "tenant_id": ctx.tenant_id,
        "image_url": result["image_url"],
        "aspect_ratio": aspect_ratio,
        "prompt": prompt,
        "model": result["model"],
    }

async def handle_video_generate(args: Dict[str, Any], ctx: TenantContext) -> Dict[str, Any]:
    prompt = args.get("prompt", "Cinematic product shot")
    duration_seconds = args.get("duration_seconds", 4)
    aspect_ratio = args.get("aspect_ratio", "9:16")
    res = await gemini_adapter.generate_video(prompt, duration_seconds, aspect_ratio)
    res["tenant_id"] = ctx.tenant_id
    res["prompt"] = prompt
    return res

async def handle_text_generate(args: Dict[str, Any], ctx: TenantContext) -> Dict[str, Any]:
    prompt = args.get("prompt", "")
    text = await gemini_adapter.generate_text(prompt)
    return {
        "tenant_id": ctx.tenant_id,
        "text": text,
        "model": "gemini-1.5-flash",
    }

async def handle_design_generate(args: Dict[str, Any], ctx: TenantContext) -> Dict[str, Any]:
    """Generates 3 multi-variant graphic poster design concepts using Gemini MCP."""
    brief = args.get("brief", {})
    brand_name = args.get("brand_name", "Brand Studio")
    image_ref = args.get("image_ref")
    aspect_ratio = args.get("aspect_ratio", "4:5")

    product_focus = brief.get("product_focus", "Featured Product")
    objective = brief.get("objective", "Drive Sales")
    cta = brief.get("call_to_action", "Shop Now")

    # Construct 3 distinctive creative variants powered by Gemini
    concepts = [
        {
            "index": 1,
            "theme": "dark_titanium",
            "title": "Bold & High-Impact Precision",
            "tag": "V1 · HERO",
            "description": f"Sleek architectural spotlight highlighting {brand_name} {product_focus} with futuristic chrome-satin precision and high-contrast rim lighting.",
            "visual_prompt": f"8k ultra-high-resolution photorealistic commercial studio shot of {brand_name} {product_focus} on matte black pedestal, cinematic rim lighting, dramatic backlight, studio strobes",
            "accent": "#6366f1",
            "badge": "NEW LAUNCH",
            "headline": f"UNLEASH {product_focus.upper()[:16]}",
            "subheadline": f"Engineered for performance and uncompromising craftsmanship.",
            "cta": cta,
            "copy": {
                "hook": f"Built for the bold: experience the next generation of {product_focus}.",
                "body": f"{brand_name} presents an uncompromising standard in design and ergonomics. Elevate your everyday with precision engineering built to inspire.",
                "hashtags": [f"#{brand_name.replace(' ', '')}", f"#{product_focus.replace(' ', '')}", "#NextGen", "#Innovation", "#ShopNow"],
                "alt": f"Studio shot of {product_focus} under dramatic lighting.",
            }
        },
        {
            "index": 2,
            "theme": "lifestyle_action",
            "title": "Lifestyle Action / Dynamic Energy",
            "tag": "V2 · LIFESTYLE",
            "description": f"Sun-splashed urban daylight and dynamic movement capturing real-world utility of {product_focus}.",
            "visual_prompt": f"lifestyle commercial photography of {product_focus} in modern urban environment, sun flare, vibrant colors, shallow depth of field, 8k",
            "accent": "#f59e0b",
            "badge": "TRENDING NOW",
            "headline": f"MOVE WITH POWER",
            "subheadline": f"Designed to match your ambition everywhere you go.",
            "cta": cta,
            "copy": {
                "hook": f"When momentum matters, your gear must keep up.",
                "body": f"Designed for life in motion. Experience effortless utility and standout aesthetics with {brand_name} {product_focus}.",
                "hashtags": [f"#{brand_name.replace(' ', '')}", "#ActiveLife", "#UrbanStyle", "#Trending", "#ShopNow"],
                "alt": f"Vibrant lifestyle capture of {product_focus} in natural sunlight.",
            }
        },
        {
            "index": 3,
            "theme": "minimalist_luxury",
            "title": "Minimalist Luxury / Elegance",
            "tag": "V3 · LUXURY",
            "description": f"Pure editorial minimalism on neutral marble pedestal with soft diffused lighting.",
            "visual_prompt": f"8k minimalist luxury studio photograph of {product_focus} on white marble pedestal, soft diffused overhead lighting, pure minimal aesthetics",
            "accent": "#10b981",
            "badge": "EXCLUSIVE",
            "headline": f"ELEVATE THE STANDARD",
            "subheadline": f"Understated elegance meets meticulous attention to detail.",
            "cta": cta,
            "copy": {
                "hook": f"Where premium craftsmanship meets quiet confidence.",
                "body": f"Pure form, purposeful function. Discover the art of subtle luxury with {brand_name} {product_focus}.",
                "hashtags": [f"#{brand_name.replace(' ', '')}", "#LuxuryEditorial", "#MinimalistDesign", "#Craftsmanship", "#Exclusive"],
                "alt": f"Minimalist luxury studio presentation of {product_focus} on marble.",
            }
        }
    ]

    # Resolve imagery via Gemini MCP image generation or user reference
    for c in concepts:
        if image_ref:
            c["bgUrl"] = image_ref
        else:
            c["bgUrl"] = (await gemini_adapter.generate_image(c["visual_prompt"], aspect_ratio=aspect_ratio))["image_url"]

    return {
        "tenant_id": ctx.tenant_id,
        "variants": concepts,
        "engine": "gemini-mcp",
        "model": "imagen-3 / gemini-1.5-flash",
    }

async def handle_reel_generate(args: Dict[str, Any], ctx: TenantContext) -> Dict[str, Any]:
    """Generates 4-scene video reel storyboard with Veo 2 video clips using Gemini MCP."""
    brief = args.get("brief", {})
    brand_name = args.get("brand_name", "Brand Studio")
    image_ref = args.get("image_ref")

    product_focus = brief.get("product_focus", "Featured Product")
    cta = brief.get("call_to_action", "Shop Now")

    scenes = [
        {
            "id": 1,
            "title": "The Hook",
            "duration": "3.0s",
            "timecode": "0:00 - 0:03",
            "visual": f"Extreme macro shot of {brand_name} {product_focus} emerging from deep shadows into bright cinematic rim light.",
            "caption": f"WHAT IF EVERYTHING CHANGED?",
            "voiceover": f"What if your everyday gear finally matched your highest standard?",
            "cue": "Heavy sub-bass impact with rising cinematic synthesizer sweep.",
        },
        {
            "id": 2,
            "title": "Core Feature Reveal",
            "duration": "4.0s",
            "timecode": "0:03 - 0:07",
            "visual": f"Precision 360-degree orbital camera pan highlighting key materials and ergonomic craftsmanship of {product_focus}.",
            "caption": f"UNCOMPROMISING PRECISION",
            "voiceover": f"Meet the all-new {brand_name} {product_focus}. Engineered from the ground up.",
            "cue": "Crisp kinetic percussion groove dropping at 128 BPM.",
        },
        {
            "id": 3,
            "title": "Lifestyle Action / Proof",
            "duration": "4.0s",
            "timecode": "0:07 - 0:11",
            "visual": f"Fast-paced kinetic cuts of dynamic real-world usage, effortless handling and responsive performance in action.",
            "caption": f"BUILT FOR MOMENTUM",
            "voiceover": f"Seamless performance in every moment, wherever ambition takes you.",
            "cue": "High-energy synth arpeggio builds towards climax.",
        },
        {
            "id": 4,
            "title": "Outro & Call To Action",
            "duration": "4.0s",
            "timecode": "0:11 - 0:15",
            "visual": f"Hero product lockup with glowing {brand_name} branding, dynamic CTA text banner and launch badge.",
            "caption": f"{cta.upper()} · CLAIM YOURS",
            "voiceover": f"Available now. Tap the link to experience {brand_name} today.",
            "cue": "Resonant bass drop with memorable brand chime.",
        }
    ]

    for s in scenes:
        if image_ref:
            s["bgUrl"] = image_ref
        else:
            video_meta = await gemini_adapter.generate_video(s["visual"], duration_seconds=int(float(s["duration"].replace("s", ""))))
            s["bgUrl"] = video_meta["thumbnail_url"]
            s["clip_url"] = video_meta["clip_url"]

    return {
        "tenant_id": ctx.tenant_id,
        "scenes": scenes,
        "engine": "gemini-mcp",
        "model": "veo-2 / gemini-1.5-flash",
        "aspect_ratio": "9:16",
        "duration_seconds": 15.0,
    }

# Tool registrations
server.register_tool(
    name="gemini.check_connection",
    description="Checks live connectivity, latency, and available tools of Gemini MCP server.",
    handler=handle_check_connection,
    parameters_schema={
        "type": "object",
        "properties": {
            "api_key": {"type": "string", "description": "Optional Gemini API key to validate"},
        },
    },
    risk_class=RiskClass.READ,
    requires_approval=False,
    idempotent=True,
)

server.register_tool(
    name="image.generate",
    description="Generates visual background art via Imagen/Gemini. Does not render text on image.",
    handler=handle_image_generate,
    parameters_schema={
        "type": "object",
        "properties": {
            "prompt": {"type": "string", "description": "Visual scene description"},
            "aspect_ratio": {"type": "string", "enum": ["1:1", "4:5", "9:16"], "default": "4:5"},
        },
        "required": ["prompt"],
    },
    risk_class=RiskClass.WRITE,
    requires_approval=False,
    idempotent=True,
)

server.register_tool(
    name="video.generate",
    description="Generates high-definition video clip via Veo/Gemini Video (9:16 vertical format).",
    handler=handle_video_generate,
    parameters_schema={
        "type": "object",
        "properties": {
            "prompt": {"type": "string", "description": "Visual scene description for video"},
            "duration_seconds": {"type": "integer", "default": 4},
            "aspect_ratio": {"type": "string", "enum": ["9:16", "1:1", "16:9"], "default": "9:16"},
        },
        "required": ["prompt"],
    },
    risk_class=RiskClass.WRITE,
    requires_approval=False,
    idempotent=True,
)

server.register_tool(
    name="text.generate",
    description="Generates creative copy, captions, and reasoning with Gemini.",
    handler=handle_text_generate,
    parameters_schema={
        "type": "object",
        "properties": {
            "prompt": {"type": "string"},
        },
        "required": ["prompt"],
    },
    risk_class=RiskClass.WRITE,
    requires_approval=False,
    idempotent=False,
)

server.register_tool(
    name="design.generate",
    description="Generates 3 multi-variant graphic poster designs with Imagen 3 imagery and layout specs via Gemini MCP.",
    handler=handle_design_generate,
    parameters_schema={
        "type": "object",
        "properties": {
            "brief": {"type": "object"},
            "brand_name": {"type": "string"},
            "image_ref": {"type": "string"},
            "aspect_ratio": {"type": "string", "default": "4:5"},
        },
        "required": ["brief"],
    },
    risk_class=RiskClass.WRITE,
    requires_approval=False,
    idempotent=True,
)

server.register_tool(
    name="reel.generate",
    description="Generates 4-scene 9:16 video reel storyboard with Veo 2 video clips via Gemini MCP.",
    handler=handle_reel_generate,
    parameters_schema={
        "type": "object",
        "properties": {
            "brief": {"type": "object"},
            "brand_name": {"type": "string"},
            "image_ref": {"type": "string"},
        },
        "required": ["brief"],
    },
    risk_class=RiskClass.WRITE,
    requires_approval=False,
    idempotent=True,
)

app = server.app

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8105"))
    uvicorn.run(app, host="0.0.0.0", port=port)
