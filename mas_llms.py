from __future__ import annotations

from typing import Any, Dict


class BaseLLM:
    model_name = "base"

    def generate(self, system_prompt: str, user_prompt: str, **kwargs: Any) -> str:
        raise NotImplementedError


class MockLLM(BaseLLM):
    model_name = "mock"

    def generate(self, system_prompt: str, user_prompt: str, **kwargs: Any) -> str:
        return f"[MOCK RESPONSE]\nSYSTEM:\n{system_prompt}\n\nUSER:\n{user_prompt}"


class GoogleADKLLMAdapter(BaseLLM):
    """
    Placeholder adapter.

    Later, replace the body of generate() with real Google ADK calls.
    This keeps the orchestration layer stable.
    """

    def __init__(self, model_name: str) -> None:
        self.model_name = model_name

    def generate(self, system_prompt: str, user_prompt: str, **kwargs: Any) -> str:
        return (
            f"[GOOGLE ADK PLACEHOLDER]\n"
            f"MODEL: {self.model_name}\n\n"
            f"SYSTEM:\n{system_prompt}\n\n"
            f"USER:\n{user_prompt}"
        )


LLM_REGISTRY: Dict[str, BaseLLM] = {
    "mock": MockLLM(),
    "gemini-2.0-flash": GoogleADKLLMAdapter("gemini-2.0-flash"),
    "gemini-2.5-pro": GoogleADKLLMAdapter("gemini-2.5-pro"),
}