import os
from typing import Optional, Type, TypeVar, Dict, Any
from pydantic import BaseModel
from .cost_tracker import CostTracker
from .mock_adapter import MockModelAdapter
from .groq_adapter import GroqModelAdapter

T = TypeVar("T", bound=BaseModel)

def _load_env_if_needed():
    if not os.getenv("GROQ_API_KEY"):
        for env_path in (".env", "../.env", "../../.env"):
            if os.path.exists(env_path):
                with open(env_path) as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#') and '=' in line:
                            k, v = line.split('=', 1)
                            os.environ.setdefault(k.strip(), v.strip())
                break

_load_env_if_needed()

class ModelGateway:
    """
    Central provider-agnostic Model Gateway.
    Routes requests to Groq Cloud (openai/gpt-oss-120b, openai/gpt-oss-20b), Google Gemini, or Mock adapter based on config.
    Enforces structured outputs and per-tenant cost tracking.
    """
    def __init__(
        self,
        mock_mode: Optional[bool] = None,
        gemini_api_key: Optional[str] = None,
        groq_api_key: Optional[str] = None,
    ):
        _load_env_if_needed()
        env_mock = os.getenv("MOCK_LLM", "false").lower() in ("true", "1")
        self.mock_mode = mock_mode if mock_mode is not None else env_mock
        self.gemini_api_key = gemini_api_key or os.getenv("GEMINI_API_KEY")
        self.groq_api_key = groq_api_key or os.getenv("GROQ_API_KEY", "")
        self.cost_tracker = CostTracker()
        self.mock_adapter = MockModelAdapter()
        self.groq_adapter = GroqModelAdapter(api_key=self.groq_api_key)


    async def generate_text(
        self,
        prompt: str,
        tenant_id: str = "default",
        system_instruction: Optional[str] = None,
        model: Optional[str] = None,
    ) -> str:
        # Default model selection: reasoning model unless specified
        chosen_model = model or os.getenv("GROQ_REASONING_MODEL", "openai/gpt-oss-120b")

        # Record approximate usage for metering
        self.cost_tracker.record_usage(
            tenant_id=tenant_id,
            prompt_tokens=len(prompt.split()) * 2,
            completion_tokens=50,
            model=chosen_model,
        )

        if not self.mock_mode and self.groq_api_key:
            return await self.groq_adapter.generate_text(
                prompt=prompt,
                system_instruction=system_instruction,
                model=chosen_model,
            )

        return await self.mock_adapter.generate_text(prompt, system_instruction)

    async def generate_structured(
        self,
        prompt: str,
        response_schema: Type[T],
        tenant_id: str = "default",
        system_instruction: Optional[str] = None,
        mock_data: Optional[Dict[str, Any]] = None,
        model: Optional[str] = None,
    ) -> T:
        chosen_model = model or os.getenv("GROQ_REASONING_MODEL", "openai/gpt-oss-120b")

        self.cost_tracker.record_usage(
            tenant_id=tenant_id,
            prompt_tokens=len(prompt.split()) * 2,
            completion_tokens=150,
            model=chosen_model,
        )

        if not self.mock_mode and self.groq_api_key:
            return await self.groq_adapter.generate_structured(
                prompt=prompt,
                response_schema=response_schema,
                system_instruction=system_instruction,
                mock_data=mock_data,
                model=chosen_model,
            )

        return await self.mock_adapter.generate_structured(
            prompt=prompt,
            response_schema=response_schema,
            system_instruction=system_instruction,
            mock_data=mock_data,
        )
