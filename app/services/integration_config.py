from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List

from mas_settings import load_settings


@dataclass(frozen=True)
class FirebaseConfig:
    enabled: bool
    project_id: str = ""
    web_api_key: str = ""
    android_app_id: str = ""
    storage_bucket: str = ""
    google_services_json_path: str = "./android/google-services.json"
    use_auth: bool = True
    use_firestore: bool = True
    use_storage: bool = True
    use_functions: bool = True
    use_analytics: bool = True
    use_crashlytics: bool = True

    def required_env_keys(self) -> List[str]:
        keys = []
        if self.enabled:
            keys.extend(["FIREBASE_PROJECT_ID", "FIREBASE_WEB_API_KEY", "FIREBASE_ANDROID_APP_ID"])
            if self.use_storage:
                keys.append("FIREBASE_STORAGE_BUCKET")
        return keys

    def missing_env_keys(self) -> List[str]:
        current = {
            "FIREBASE_PROJECT_ID": self.project_id,
            "FIREBASE_WEB_API_KEY": self.web_api_key,
            "FIREBASE_ANDROID_APP_ID": self.android_app_id,
            "FIREBASE_STORAGE_BUCKET": self.storage_bucket,
        }
        return [key for key in self.required_env_keys() if not current.get(key, "").strip()]

    def is_configured(self) -> bool:
        return not self.missing_env_keys()


@dataclass(frozen=True)
class BillingConfig:
    enabled: bool
    provider: str = "google_play"
    premium_subscription_id: str = ""
    remove_ads_product_id: str = ""

    def missing_ids(self) -> List[str]:
        missing: List[str] = []
        if self.enabled and not self.premium_subscription_id.strip():
            missing.append("BILLING_PREMIUM_SUBSCRIPTION_ID")
        if self.enabled and not self.remove_ads_product_id.strip():
            missing.append("BILLING_REMOVE_ADS_PRODUCT_ID")
        return missing

    def is_configured(self) -> bool:
        return not self.missing_ids()


@dataclass(frozen=True)
class AdMobConfig:
    enabled: bool
    app_id: str = ""
    banner_ad_unit_id: str = ""
    interstitial_ad_unit_id: str = ""
    rewarded_ad_unit_id: str = ""
    app_open_ad_unit_id: str = ""
    placements: Dict[str, bool] = field(default_factory=dict)

    def missing_ids(self) -> List[str]:
        if not self.enabled:
            return []
        missing = []
        if not self.app_id.strip():
            missing.append("ADMOB_APP_ID")
        placement_to_env = {
            "banner": (self.banner_ad_unit_id, "ADMOB_BANNER_AD_UNIT_ID"),
            "interstitial": (self.interstitial_ad_unit_id, "ADMOB_INTERSTITIAL_AD_UNIT_ID"),
            "rewarded": (self.rewarded_ad_unit_id, "ADMOB_REWARDED_AD_UNIT_ID"),
            "app_open": (self.app_open_ad_unit_id, "ADMOB_APP_OPEN_AD_UNIT_ID"),
        }
        for placement, enabled in self.placements.items():
            if enabled:
                value, env_name = placement_to_env[placement]
                if not value.strip():
                    missing.append(env_name)
        return missing

    def is_configured(self) -> bool:
        return not self.missing_ids()


@dataclass(frozen=True)
class IntegrationStatus:
    firebase: FirebaseConfig
    billing: BillingConfig
    admob: AdMobConfig

    def summary(self) -> Dict[str, Dict[str, object]]:
        return {
            "firebase": {
                "configured": self.firebase.is_configured(),
                "missing": self.firebase.missing_env_keys(),
                "google_services_json_path": self.firebase.google_services_json_path,
            },
            "billing": {
                "configured": self.billing.is_configured(),
                "missing": self.billing.missing_ids(),
            },
            "admob": {
                "configured": self.admob.is_configured(),
                "missing": self.admob.missing_ids(),
            },
        }


def load_integration_status(settings_path: str | None = None) -> IntegrationStatus:
    settings = load_settings(settings_path)
    backend = settings.get("backend", {})
    firebase_data = settings.get("firebase", {})
    billing_data = settings.get("billing", {})
    ads_data = settings.get("ads", {})
    admob_data = settings.get("admob", {})
    android = settings.get("android", {})

    firebase = FirebaseConfig(
        enabled=bool(backend.get("firebase_enabled", False)),
        project_id=str(firebase_data.get("project_id", "")),
        web_api_key=str(firebase_data.get("web_api_key", "")),
        android_app_id=str(firebase_data.get("android_app_id", "")),
        storage_bucket=str(firebase_data.get("storage_bucket", "")),
        google_services_json_path=str(android.get("google_services_json", "./android/google-services.json")),
        use_auth=bool(backend.get("use_auth", True)),
        use_firestore=bool(backend.get("use_firestore", True)),
        use_storage=bool(backend.get("use_storage", True)),
        use_functions=bool(backend.get("use_functions", True)),
        use_analytics=bool(backend.get("use_analytics", True)),
        use_crashlytics=bool(backend.get("use_crashlytics", True)),
    )
    billing = BillingConfig(
        enabled=bool(billing_data.get("enabled", False)),
        provider=str(billing_data.get("provider", "google_play")),
        premium_subscription_id=str(billing_data.get("premium_subscription_id", "")),
        remove_ads_product_id=str(billing_data.get("remove_ads_product_id", "")),
    )
    admob = AdMobConfig(
        enabled=bool(ads_data.get("enabled", False)),
        app_id=str(admob_data.get("app_id", "")),
        banner_ad_unit_id=str(admob_data.get("banner_ad_unit_id", "")),
        interstitial_ad_unit_id=str(admob_data.get("interstitial_ad_unit_id", "")),
        rewarded_ad_unit_id=str(admob_data.get("rewarded_ad_unit_id", "")),
        app_open_ad_unit_id=str(admob_data.get("app_open_ad_unit_id", "")),
        placements={
            "banner": bool(ads_data.get("banner_enabled", False)),
            "interstitial": bool(ads_data.get("interstitial_enabled", False)),
            "rewarded": bool(ads_data.get("rewarded_enabled", False)),
            "app_open": bool(ads_data.get("app_open_enabled", False)),
        },
    )
    return IntegrationStatus(firebase=firebase, billing=billing, admob=admob)
