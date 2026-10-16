import os
import json
import asyncio
import logging
from typing import Type, TypeVar, Optional, Any, Dict, List, Tuple
import httpx
from pydantic import BaseModel
from .mock_adapter import MockModelAdapter

logger = logging.getLogger("model_gateway.groq")
T = TypeVar("T", bound=BaseModel)


class GroqCallError(Exception):
    """Raised by complete_json when Groq cannot return valid JSON. No silent mock fallback."""

class GroqModelAdapter:
    """
    Adapter for Groq Cloud API.
    Routes tasks to high-performance models:
    - openai/gpt-oss-120b for deep reasoning, creative brief synthesis, video scripts/storyboards.
    - openai/gpt-oss-20b for fast prompt enhancement, checklists, and classification.
    """
    GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("GROQ_API_KEY", "")
        self.reasoning_model = os.getenv("GROQ_REASONING_MODEL", "openai/gpt-oss-120b")
        self.fast_model = os.getenv("GROQ_FAST_MODEL", "openai/gpt-oss-20b")
        self.vision_model = os.getenv("GROQ_VISION_MODEL", "qwen/qwen3.8-27b")
        self.fallback_adapter = MockModelAdapter()

    async def complete_json(
        self,
        system: str,
        user: str,
        model: Optional[str] = None,
        images: Optional[List[str]] = None,
        json_schema: Optional[Dict[str, Any]] = None,
        schema_name: str = "output",
        max_tokens: int = 800,
        temperature: float = 0.7,
        reasoning_effort: Optional[str] = None,
        timeout_s: float = 60.0,
    ) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """
        Token-lean structured call. Returns (parsed_json, usage).
        - images: data URLs (already downscaled by the caller).
        - json_schema: enforced server-side with strict mode, so no repair round-trips.
        - Keep `system` static across calls so Groq prompt caching can apply.
        """
        if not self.api_key:
            raise GroqCallError("GROQ_API_KEY is not configured")

        chosen_model = model or self.reasoning_model
        user_content: Any = user
        if images:
            user_content = [{"type": "text", "text": user}] + [
                {"type": "image_url", "image_url": {"url": url}} for url in images
            ]

        payload: Dict[str, Any] = {
            "model": chosen_model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user_content},
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if json_schema:
            payload["response_format"] = {
                "type": "json_schema",
                "json_schema": {"name": schema_name, "strict": True, "schema": json_schema},
            }
        else:
            payload["response_format"] = {"type": "json_object"}
        if chosen_model.startswith("openai/gpt-oss"):
            # Reasoning tokens are billed even when hidden; effort is chosen per task.
            payload["reasoning_effort"] = reasoning_effort or "low"
            payload["include_reasoning"] = False

        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        last_error = "unknown error"
        for attempt in range(3):
            try:
                async with httpx.AsyncClient(timeout=timeout_s) as client:
                    resp = await client.post(self.GROQ_API_URL, headers=headers, json=payload)
            except httpx.HTTPError as e:
                last_error = f"network error: {e}"
                await asyncio.sleep(1.0 + attempt)
                continue

            if resp.status_code == 200:
                data = resp.json()
                content = data["choices"][0]["message"].get("content") or ""
                usage_raw = data.get("usage") or {}
                usage = {
                    "model": chosen_model,
                    "prompt_tokens": usage_raw.get("prompt_tokens", 0),
                    "completion_tokens": usage_raw.get("completion_tokens", 0),
                    "reasoning_tokens": (usage_raw.get("completion_tokens_details") or {}).get("reasoning_tokens", 0),
                    "cached_tokens": (usage_raw.get("prompt_tokens_details") or {}).get("cached_tokens", 0),
                }
                try:
                    return json.loads(content), usage
                except json.JSONDecodeError:
                    last_error = "model returned invalid JSON"
                    continue

            body = resp.text[:300]
            last_error = f"HTTP {resp.status_code}: {body}"
            if resp.status_code == 429 or resp.status_code >= 500:
                retry_after = min(float(resp.headers.get("retry-after", 1.5 * (attempt + 1))), 8.0)
                await asyncio.sleep(retry_after)
                continue
            if resp.status_code == 400 and "json" in body.lower():
                continue  # JSON validation failure — one more sample usually succeeds
            break

        raise GroqCallError(f"Groq {chosen_model} failed: {last_error}")

    async def generate_text(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        model: Optional[str] = None,
    ) -> str:
        chosen_model = model or self.reasoning_model
        if not self.api_key:
            logger.warning("No GROQ_API_KEY provided; falling back to mock response.")
            return await self.fallback_adapter.generate_text(prompt, system_instruction)

        messages = []
        if system_instruction:
            messages.append({"role": "system", "content": system_instruction})
        messages.append({"role": "user", "content": prompt})

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": chosen_model,
            "messages": messages,
            "temperature": 0.7,
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(self.GROQ_API_URL, headers=headers, json=payload)
                if resp.status_code == 200:
                    data = resp.json()
                    content = data["choices"][0]["message"]["content"]
                    return content.strip()
                else:
                    logger.error(f"Groq API returned status {resp.status_code}: {resp.text}")
                    return await self.fallback_adapter.generate_text(prompt, system_instruction)
        except Exception as e:
            logger.exception(f"Error calling Groq API: {e}. Falling back to mock adapter.")
            return await self.fallback_adapter.generate_text(prompt, system_instruction)

    async def generate_structured(
        self,
        prompt: str,
        response_schema: Type[T],
        system_instruction: Optional[str] = None,
        mock_data: Optional[Dict[str, Any]] = None,
        model: Optional[str] = None,
    ) -> T:
        chosen_model = model or self.reasoning_model
        if not self.api_key:
            return await self.fallback_adapter.generate_structured(
                prompt=prompt,
                response_schema=response_schema,
                system_instruction=system_instruction,
                mock_data=mock_data,
            )

        # Build schema instruction
        schema_json = json.dumps(response_schema.model_json_schema(), indent=2)
        system_prompt = (
            f"{system_instruction or 'You are an expert marketing AI assistant.'}\n"
            f"You MUST return valid JSON adhering strictly to this JSON Schema:\n{schema_json}\n"
            f"Respond ONLY with the JSON object, without markdown formatting or codeblocks."
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt},
        ]

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": chosen_model,
            "messages": messages,
            "response_format": {"type": "json_object"},
            "temperature": 0.5,
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(self.GROQ_API_URL, headers=headers, json=payload)
                if resp.status_code == 200:
                    data = resp.json()
                    content = data["choices"][0]["message"]["content"]
                    parsed = json.loads(content)
                    return response_schema.model_validate(parsed)
                else:
                    logger.error(f"Groq API structured call error {resp.status_code}: {resp.text}")
                    return await self.fallback_adapter.generate_structured(
                        prompt=prompt,
                        response_schema=response_schema,
                        system_instruction=system_instruction,
                        mock_data=mock_data,
                    )
        except Exception as e:
            logger.warning(f"Failed parsing structured output from Groq: {e}. Falling back.")
            return await self.fallback_adapter.generate_structured(
                prompt=prompt,
                response_schema=response_schema,
                system_instruction=system_instruction,
                mock_data=mock_data,
            )
