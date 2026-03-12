from __future__ import annotations

from pathlib import Path
from typing import Any, Dict
import os

try:
    import yaml
except Exception:
    yaml = None


DEFAULT_SETTINGS: Dict[str, Any] = {
    "project": {
        "name": "LinkSaver",
        "root_dir": ".",
        "artifacts_dir": "./artifacts",
        "logs_dir": "./logs",
        "docs_dir": "./docs",
    },
    "framework": {
        "selected": "kivy",
        "available": ["kivy", "beeware", "flet"],
        "adapter_module": "app_frameworks.kivy_adapter",
    },
    "llm": {
        "provider_mode": "mixed",
        "planner_model": "openai:gpt-5.4",
        "coder_model": "openai:gpt-5.4",
        "reviewer_model": "google:gemini-3-flash-preview",
        "documenter_model": "google:gemini-3-flash-preview",
        "fallback_fast_model": "google:gemini-2.5-flash",
        "fallback_strong_model": "openai:gpt-5.4",
        "cost_mode": "balanced",
        "mock_mode": False,
    },
    "orchestration": {
        "max_iterations": 6,
        "max_repair_attempts": 3,
        "autonomous_mode": True,
        "require_admin_for_release": True,
        "require_admin_for_internet": True,
        "stop_on_failed_guardrail": True,
        "write_iteration_artifacts": True,
        "backlog_file": "./artifacts/backlog.json",
        "iteration_reports_dir": "./artifacts/iterations",
        "auto_run_tests": True,
    },
    "runtime": {
        "dry_run": True,
        "verbose": True,
        "fail_fast": False,
    },
    "android": {
        "gradle_wrapper_path": "./gradlew",
        "avd_name": "Pixel_6_API_34",
        "package_name": "com.example.linksaver",
        "min_sdk": 26,
        "target_sdk": 34,
    },
    "app": {
        "display_name": "LinkSaver",
        "free_tier_ads": True,
        "paid_tier_enabled": True,
        "trial_days": 7,
    },
    "backend": {
        "firebase_enabled": True,
        "use_firestore": True,
        "use_storage": True,
        "use_auth": True,
        "offline_cache_enabled": True,
    },
    "paths": {
        "app_dir": "./app",
        "tests_dir": "./tests",
        "frameworks_dir": "./app_frameworks",
    },
}


def _deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    result = dict(base)
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def load_settings(settings_path: str | None = None) -> Dict[str, Any]:
    path = Path(settings_path or os.environ.get("MAS_SETTINGS_FILE", "settings.yaml"))
    settings = dict(DEFAULT_SETTINGS)

    if path.exists() and yaml is not None:
        loaded = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        if isinstance(loaded, dict):
            settings = _deep_merge(settings, loaded)

    return settings


SETTINGS = load_settings()