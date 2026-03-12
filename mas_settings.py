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
        "name": "LinkNest",
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
        "planner_model": "gemini-2.0-flash",
        "coder_model": "gemini-2.0-flash",
        "reviewer_model": "gemini-2.0-flash",
        "documenter_model": "gemini-2.0-flash",
        "cost_mode": "balanced",
        "provider": "google_adk",
    },
    "orchestration": {
        "max_iterations": 3,
        "max_repair_attempts": 2,
        "autonomous_mode": True,
        "require_admin_for_release": True,
        "require_admin_for_internet": True,
    },
    "runtime": {
        "dry_run": True,
        "verbose": True,
        "fail_fast": False,
    },
    "android": {
        "gradle_wrapper_path": "./gradlew",
        "avd_name": "Pixel_6_API_34",
        "package_name": "com.example.linknest",
    },
    "monetization": {
        "ads_enabled": True,
        "paid_tier_enabled": True,
        "trial_days": 7,
    },
    "backend": {
        "firebase_enabled": True,
        "use_firestore": True,
        "use_storage": True,
        "use_auth": True,
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