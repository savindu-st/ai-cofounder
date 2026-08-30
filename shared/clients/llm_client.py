import os
from typing import Any, Dict

class LLMClient:
    def __init__(self, model: str = "gpt-4o"):
        self.model = model

    def generate_json(self, prompt: str, schema: Any) -> Dict[str, Any]:
        """Mockable LLM JSON completion"""
        return {}
