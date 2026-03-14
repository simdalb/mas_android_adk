import os
import tempfile
from pathlib import Path

from app.config import load_app_config
from app.services.integration_config import load_integration_status
from mas_settings import load_env_file, load_settings


def test_load_env_file_parses_simple_key_values():
    with tempfile.TemporaryDirectory() as tmp:
        env_path = Path(tmp) / ".env"
        env_path.write_text("APP_DISPLAY_NAME=SpecSaver\nFIREBASE_USE_AUTH=true\n", encoding="utf-8")
        values = load_env_file(str(env_path))
        assert values["APP_DISPLAY_NAME"] == "SpecSaver"
        assert values["FIREBASE_USE_AUTH"] == "true"


def test_load_settings_applies_env_file_overrides():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "settings.yaml").write_text("app:\n  display_name: BaseName\nandroid:\n  package_name: com.example.base\n", encoding="utf-8")
        (root / ".env").write_text("APP_DISPLAY_NAME=EnvName\nGOOGLE_PLAY_PACKAGE_NAME=com.example.env\n", encoding="utf-8")
        old_env = os.environ.get("MAS_ENV_FILE")
        try:
            os.environ["MAS_ENV_FILE"] = str(root / ".env")
            settings = load_settings(str(root / "settings.yaml"))
        finally:
            if old_env is None:
                os.environ.pop("MAS_ENV_FILE", None)
            else:
                os.environ["MAS_ENV_FILE"] = old_env
        assert settings["app"]["display_name"] == "EnvName"
        assert settings["android"]["package_name"] == "com.example.env"


def test_integration_status_reports_missing_values_by_default():
    status = load_integration_status()
    summary = status.summary()
    assert "firebase" in summary
    assert summary["firebase"]["configured"] in {True, False}
    assert "missing" in summary["billing"]


def test_app_config_exposes_integration_status():
    config = load_app_config()
    assert config.integration_status.summary()["firebase"]["google_services_json_path"].endswith("google-services.json")
