from typing import Dict, Any, Optional

class BaseMockAdapter:
    """Base class for mock adapters powering local offline testing."""
    def __init__(self, is_mock_enabled: bool = True):
        self.is_mock_enabled = is_mock_enabled
        self.call_history: list[Dict[str, Any]] = []

    def record_call(self, method: str, kwargs: Dict[str, Any], result: Any) -> None:
        self.call_history.append({
            "method": method,
            "kwargs": kwargs,
            "result": result
        })

    def reset(self) -> None:
        self.call_history.clear()
