import json
from typing import Type, TypeVar, Optional, Any, Dict
from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)

class MockModelAdapter:
    """Mock adapter that simulates LLM text completions and structured outputs."""
    def __init__(self):
        self.call_history = []

    async def generate_text(self, prompt: str, system_instruction: Optional[str] = None) -> str:
        self.call_history.append({"prompt": prompt, "system_instruction": system_instruction})
        return f"[Mock LLM Response] Successfully processed prompt: {prompt[:80]}"

    async def generate_structured(
        self,
        prompt: str,
        response_schema: Type[T],
        system_instruction: Optional[str] = None,
        mock_data: Optional[Dict[str, Any]] = None,
    ) -> T:
        self.call_history.append({
            "prompt": prompt,
            "response_schema": response_schema.__name__,
            "system_instruction": system_instruction
        })
        
        if mock_data:
            return response_schema.model_validate(mock_data)

        # If no explicit mock_data provided, construct a minimal valid instance from schema defaults
        # or empty fields
        fields = {}
        for name, field in response_schema.model_fields.items():
            if field.default is not None and field.default != ...:
                fields[name] = field.default
            elif field.annotation is str:
                fields[name] = f"Mock {name}"
            elif field.annotation is int:
                fields[name] = 1
            elif field.annotation is float:
                fields[name] = 1.0
            elif field.annotation is bool:
                fields[name] = True
            elif getattr(field.annotation, "__origin__", None) is list:
                fields[name] = []
            elif getattr(field.annotation, "__origin__", None) is dict:
                fields[name] = {}
            else:
                fields[name] = None
                
        return response_schema.model_validate(fields)
