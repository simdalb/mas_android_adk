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
        "plan_artifacts_dir": "./artifacts/plans",
        "run_state_file": "./artifacts/run_state.json",
        "auto_run_tests": True,
        "auto_build_android": False,
        "auto_smoke_test_android": False,
        "app_spec_file": "./artifacts/app_spec.json",
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
        "app_name": "LinkSaver",
        "min_sdk": 26,
        "target_sdk": 34,
        "build_artifacts_dir": "./artifacts/android",
        "google_services_json": "./android/google-services.json",
        "release_keystore_properties": "./android/keystore.properties",
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
        "use_functions": True,
        "use_analytics": True,
        "use_crashlytics": True,
        "offline_cache_enabled": True,
    },
    "billing": {
        "enabled": True,
        "provider": "google_play",
        "premium_subscription_id": "premium_monthly",
        "remove_ads_product_id": "remove_ads",
    },
    "ads": {
        "enabled": True,
        "provider": "admob",
        "banner_enabled": True,
        "interstitial_enabled": False,
        "rewarded_enabled": False,
        "app_open_enabled": False,
    },
    "paths": {
        "app_dir": "./app",
        "tests_dir": "./tests",
        "frameworks_dir": "./app_frameworks",
    },
}


ENV_TO_SETTINGS = {
    "GOOGLE_PLAY_PACKAGE_NAME": ("android", "package_name"),
    "ANDROID_APP_NAME": ("android", "app_name"),
    "APP_DISPLAY_NAME": ("app", "display_name"),
    "APP_TRIAL_DAYS": ("app", "trial_days"),
    "FIREBASE_PROJECT_ID": ("firebase", "project_id"),
    "FIREBASE_WEB_API_KEY": ("firebase", "web_api_key"),
    "FIREBASE_ANDROID_APP_ID": ("firebase", "android_app_id"),
    "FIREBASE_STORAGE_BUCKET": ("firebase", "storage_bucket"),
    "FIREBASE_USE_AUTH": ("backend", "use_auth"),
    "FIREBASE_USE_FIRESTORE": ("backend", "use_firestore"),
    "FIREBASE_USE_STORAGE": ("backend", "use_storage"),
    "FIREBASE_USE_FUNCTIONS": ("backend", "use_functions"),
    "FIREBASE_USE_ANALYTICS": ("backend", "use_analytics"),
    "FIREBASE_USE_CRASHLYTICS": ("backend", "use_crashlytics"),
    "ADMOB_APP_ID": ("admob", "app_id"),
    "ADMOB_BANNER_AD_UNIT_ID": ("admob", "banner_ad_unit_id"),
    "ADMOB_INTERSTITIAL_AD_UNIT_ID": ("admob", "interstitial_ad_unit_id"),
    "ADMOB_REWARDED_AD_UNIT_ID": ("admob", "rewarded_ad_unit_id"),
    "ADMOB_APP_OPEN_AD_UNIT_ID": ("admob", "app_open_ad_unit_id"),
    "BILLING_PREMIUM_SUBSCRIPTION_ID": ("billing", "premium_subscription_id"),
    "BILLING_REMOVE_ADS_PRODUCT_ID": ("billing", "remove_ads_product_id"),
}

BOOLEAN_KEYS = {
    "FIREBASE_USE_AUTH",
    "FIREBASE_USE_FIRESTORE",
    "FIREBASE_USE_STORAGE",
    "FIREBASE_USE_FUNCTIONS",
    "FIREBASE_USE_ANALYTICS",
    "FIREBASE_USE_CRASHLYTICS",
}
INTEGER_KEYS = {"APP_TRIAL_DAYS"}


def _deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    result = dict(base)
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def _coerce_env_value(key: str, value: str) -> Any:
    if key in BOOLEAN_KEYS:
        return value.strip().lower() in {"1", "true", "yes", "on"}
    if key in INTEGER_KEYS:
        try:
            return int(value.strip())
        except Exception:
            return value
    return value


def _set_nested(mapping: Dict[str, Any], path: tuple[str, str], value: Any) -> None:
    section, key = path
    section_mapping = mapping.setdefault(section, {})
    if isinstance(section_mapping, dict):
        section_mapping[key] = value


def load_env_file(env_path: str | None = None) -> Dict[str, str]:
    path = Path(env_path or os.environ.get("MAS_ENV_FILE", ".env"))
    if not path.exists():
        return {}

    values: Dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        values[key] = value
    return values


def load_settings(settings_path: str | None = None) -> Dict[str, Any]:
    path = Path(settings_path or os.environ.get("MAS_SETTINGS_FILE", "settings.yaml"))
    settings = dict(DEFAULT_SETTINGS)

    if path.exists() and yaml is not None:
        loaded = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        if isinstance(loaded, dict):
            settings = _deep_merge(settings, loaded)

    env_values = load_env_file()
    merged_env = {**env_values, **os.environ}
    for env_key, setting_path in ENV_TO_SETTINGS.items():
        raw = merged_env.get(env_key)
        if raw is None or raw == "":
            continue
        _set_nested(settings, setting_path, _coerce_env_value(env_key, raw))

    android = settings.setdefault("android", {})
    android["app_name"] = str(android.get("app_name") or settings.get("app", {}).get("display_name") or "LinkSaver")
    return settings


SETTINGS = load_settings()
