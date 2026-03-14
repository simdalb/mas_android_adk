from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional
import json
import os
import re

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


def _extract_target_files(user_prompt: str) -> list[str]:
    marker = "Target files:\n- "
    if marker not in user_prompt:
        return []
    block = user_prompt.split(marker, 1)[1].split("\n\n", 1)[0]
    return [line.strip().lstrip("-").strip() for line in block.splitlines() if line.strip()]


def _build_mock_patch_plan(system_prompt: str, user_prompt: str) -> str:
    del system_prompt
    targets = _extract_target_files(user_prompt)
    edits: list[dict[str, Any]] = []

    if "docs/AUTONOMOUS_MODE.md" in targets:
        edits.append(
            {
                "path": "docs/AUTONOMOUS_MODE.md",
                "operations": [
                    {
                        "mode": "append",
                        "text": (
                            "\n## Troubleshooting\n"
                            "- If a run pauses, inspect `artifacts/run_state.json` and any pending admin request files.\n"
                            "- If tests fail after an edit, rerun `pytest -q` locally to confirm the saved failure summary.\n"
                            "- If a backlog item keeps failing, review the matching snapshot manifest under `artifacts/snapshots/`.\n"
                        ),
                    }
                ],
            }
        )

    if "app_frameworks/kivy_adapter.py" in targets:
        edits.append(
            {
                "path": "app_frameworks/kivy_adapter.py",
                "operations": [
                    {
                        "mode": "replace_once",
                        "old": 'self.set_status("Link updated.")',
                        "new": 'self.set_status("Link updated successfully.")',
                    },
                    {
                        "mode": "replace_once",
                        "old": 'self.set_status("Link added.")',
                        "new": 'self.set_status("Link added successfully.")',
                    },
                ],
            }
        )

    if "app/use_cases/media_links.py" in targets:
        edits.append(
            {
                "path": "app/use_cases/media_links.py",
                "operations": [
                    {
                        "mode": "replace_once",
                        "old": 'raise InvalidMediaLinkError("Title is required.")',
                        "new": 'raise InvalidMediaLinkError("Title is required before a link can be saved.")',
                    },
                    {
                        "mode": "replace_once",
                        "old": 'raise InvalidMediaLinkError("URL or local path is required.")',
                        "new": 'raise InvalidMediaLinkError("A URL or local media path is required before a link can be saved.")',
                    },
                    {
                        "mode": "replace_once",
                        "old": 'return {"ok": False, "link": None, "error": str(exc)}',
                        "new": 'return {"ok": False, "link": None, "error": f"{exc} Duplicate title + URL combinations are not allowed." if isinstance(exc, DuplicateMediaLinkError) else str(exc)}',
                    },
                ],
            }
        )

    if not edits and targets:
        edits.append(
            {
                "path": targets[0],
                "operations": [{"mode": "append", "text": "\n"}],
            }
        )

    return json.dumps({"summary": "Mock patch plan generated", "edits": edits}, ensure_ascii=False)


class BaseLLM:
    model_name = "base"

    def generate(self, system_prompt: str, user_prompt: str, **kwargs: Any) -> str:
        raise NotImplementedError

    def generate_json(self, system_prompt: str, user_prompt: str, **kwargs: Any) -> Dict[str, Any]:
        text = self.generate(system_prompt=system_prompt, user_prompt=user_prompt, **kwargs)
        try:
            return self._coerce_json(text)
        except Exception as exc:
            raise ValueError(f"Model did not return valid JSON: {exc}") from exc

    @staticmethod
    def _coerce_json(text: str) -> Dict[str, Any]:
        stripped = text.strip()
        if stripped.startswith("{") and stripped.endswith("}"):
            return json.loads(stripped)

        fenced = re.search(r"```(?:json)?\s*(\{.*\})\s*```", stripped, flags=re.DOTALL)
        if fenced:
            return json.loads(fenced.group(1))

        first = stripped.find("{")
        last = stripped.rfind("}")
        if first != -1 and last > first:
            return json.loads(stripped[first:last + 1])
        raise ValueError("No JSON object found")


class MockLLM(BaseLLM):
    model_name = "mock"

    def generate(self, system_prompt: str, user_prompt: str, **kwargs: Any) -> str:
        wants_json = bool(kwargs.get("response_format") == "json" or "ONLY valid JSON" in user_prompt)
        if wants_json:
            return _build_mock_patch_plan(system_prompt, user_prompt)
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
        response_format = kwargs.get("response_format")

        if _should_mock() or not api_key:
            if response_format == "json":
                return _build_mock_patch_plan(system_prompt, user_prompt)
            return (
                "[OPENAI MOCK/FALLBACK RESPONSE]\n"
                f"MODEL: {self.model_name}\n\n"
                f"SYSTEM:\n{system_prompt}\n\n"
                f"USER:\n{user_prompt}"
            )

        try:
            from openai import OpenAI

            client = OpenAI(api_key=api_key, base_url=base_url)
            request: Dict[str, Any] = {
                "model": self.model_name,
                "input": [
                    {"role": "system", "content": [{"type": "input_text", "text": system_prompt}]},
                    {"role": "user", "content": [{"type": "input_text", "text": user_prompt}]},
                ],
            }
            if response_format == "json":
                request["text"] = {"format": {"type": "json_object"}}

            response = client.responses.create(**request)
            output_text = getattr(response, "output_text", None)
            if output_text:
                return output_text
            return str(response)
        except Exception as exc:
            if response_format == "json":
                return _build_mock_patch_plan(system_prompt, user_prompt)
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
        response_format = kwargs.get("response_format")

        if _should_mock() or not api_key:
            if response_format == "json":
                return _build_mock_patch_plan(system_prompt, user_prompt)
            return (
                "[GEMINI MOCK/FALLBACK RESPONSE]\n"
                f"MODEL: {self.model_name}\n\n"
                f"SYSTEM:\n{system_prompt}\n\n"
                f"USER:\n{user_prompt}"
            )

        try:
            from google import genai

            client = genai.Client(api_key=api_key)
            config: Dict[str, Any] = {"system_instruction": system_prompt}
            if response_format == "json":
                config["response_mime_type"] = "application/json"
            response = client.models.generate_content(
                model=self.model_name,
                contents=user_prompt,
                config=config,
            )
            text = getattr(response, "text", None)
            if text:
                return text
            return str(response)
        except Exception as exc:
            if response_format == "json":
                return _build_mock_patch_plan(system_prompt, user_prompt)
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
        self._cache: Dict[str, BaseLLM] = {"mock": MockLLM()}

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
