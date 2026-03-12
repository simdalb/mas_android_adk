from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict

from mas_settings import load_settings


@dataclass(frozen=True)
class AppConfig:
    display_name: str
    package_name: str
    framework: str
    firebase_enabled: bool
    ads_enabled: bool
    paid_tier_enabled: bool
    trial_days: int


def load_app_config(settings_path: str | None = None) -> AppConfig:
    settings: Dict[str, Any] = load_settings(settings_path)
    return AppConfig(
        display_name=settings["app"]["display_name"],
        package_name=settings["android"]["package_name"],
        framework=settings["framework"]["selected"],
        firebase_enabled=bool(settings["backend"]["firebase_enabled"]),
        ads_enabled=bool(settings["app"]["free_tier_ads"]),
        paid_tier_enabled=bool(settings["app"]["paid_tier_enabled"]),
        trial_days=int(settings["app"]["trial_days"]),
    )