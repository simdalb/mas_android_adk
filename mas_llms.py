from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional
import os

try:
    from mas_settings import load_settings
except Exception:
    load_settings = None


def _settings_mock_mode() -> bool:
    if load_settings is None:
        return False
    try:
        settings = load_settings()
        return bool(settings.get("llm", {}).get("mock_mode", False))
    except Exception:
        return False


def _env_truthy(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in {"1", "true", "yes", "on"}


def _should_mock() -> bool:
    if _env_truthy("MAS_LLM_MOCK_MODE"):
        return True
    return _settings_mock_mode()


class BaseLLM:
    model_name = "base"

    def generate(self, system_prompt: str, user_prompt: str, **kwargs: Any) -> str:
        raise NotImplementedError


class MockLLM(BaseLLM):
    model_name = "mock"

    def generate(self, system_prompt: str, user_prompt: str, **kwargs: Any) -> str:
        return (
            "[MOCK RESPONSE]\n"
            f"MODEL: {self.model_name}\n\n"
            f"SYSTEM:\n{system_prompt}\n\n"
            f"USER:\n{user_prompt}"
        )


@dataclass
class OpenAIResponsesLLM(BaseLLM):
    model_name: str

    def generate(self, system_prompt: str, user_prompt: str, **kwargs: Any) -> str:
        api_key = os.environ.get("OPENAI_API_KEY", "").strip()
        base_url = os.environ.get("OPENAI_BASE_URL", "").strip() or None

        if _should_mock() or not api_key:
            return (
                "[OPENAI MOCK/FALLBACK RESPONSE]\n"
                f"MODEL: {self.model_name}\n\n"
                f"SYSTEM:\n{system_prompt}\n\n"
                f"USER:\n{user_prompt}"
            )

        try:
            from openai import OpenAI

            client = OpenAI(api_key=api_key, base_url=base_url)
            response = client.responses.create(
                model=self.model_name,
                input=[
                    {"role": "system", "content": [{"type": "input_text", "text": system_prompt}]},
                    {"role": "user", "content": [{"type": "input_text", "text": user_prompt}]},
                ],
            )
            output_text = getattr(response, "output_text", None)
            if output_text:
                return output_text
            return str(response)
        except Exception as exc:
            return (
                "[OPENAI ERROR FALLBACK]\n"
                f"MODEL: {self.model_name}\n"
                f"ERROR: {exc}\n\n"
                f"SYSTEM:\n{system_prompt}\n\n"
                f"USER:\n{user_prompt}"
            )


@dataclass
class GoogleGeminiLLM(BaseLLM):
    model_name: str

    def generate(self, system_prompt: str, user_prompt: str, **kwargs: Any) -> str:
        api_key = (
            os.environ.get("GEMINI_API_KEY", "").strip()
            or os.environ.get("GOOGLE_API_KEY", "").strip()
        )

        if _should_mock() or not api_key:
            return (
                "[GEMINI MOCK/FALLBACK RESPONSE]\n"
                f"MODEL: {self.model_name}\n\n"
                f"SYSTEM:\n{system_prompt}\n\n"
                f"USER:\n{user_prompt}"
            )

        try:
            from google import genai

            client = genai.Client(api_key=api_key)
            response = client.models.generate_content(
                model=self.model_name,
                contents=user_prompt,
                config={"system_instruction": system_prompt},
            )
            text = getattr(response, "text", None)
            if text:
                return text
            return str(response)
        except Exception as exc:
            return (
                "[GEMINI ERROR FALLBACK]\n"
                f"MODEL: {self.model_name}\n"
                f"ERROR: {exc}\n\n"
                f"SYSTEM:\n{system_prompt}\n\n"
                f"USER:\n{user_prompt}"
            )


class DynamicLLMRegistry(dict):
    def __init__(self) -> None:
        super().__init__()
        self._cache: Dict[str, BaseLLM] = {
            "mock": MockLLM(),
        }

    def _normalize(self, spec: str) -> str:
        return (spec or "mock").strip()

    def _build(self, spec: str) -> Optional[BaseLLM]:
        spec = self._normalize(spec)
        if spec in self._cache:
            return self._cache[spec]

        if ":" in spec:
            provider, model_name = spec.split(":", 1)
        else:
            provider, model_name = "openai", spec

        provider = provider.strip().lower()
        model_name = model_name.strip()

        if provider == "mock":
            llm = MockLLM()
            llm.model_name = "mock"
            return llm

        if provider in {"openai", "gpt"}:
            return OpenAIResponsesLLM(model_name=model_name)

        if provider in {"google", "gemini"}:
            return GoogleGeminiLLM(model_name=model_name)

        return None

    def get(self, key: str, default: Any = None) -> Any:
        spec = self._normalize(key)
        if spec in self._cache:
            return self._cache[spec]

        built = self._build(spec)
        if built is None:
            return default

        self._cache[spec] = built
        return built


LLM_REGISTRY = DynamicLLMRegistry()