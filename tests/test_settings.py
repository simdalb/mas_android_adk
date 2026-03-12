from app.config import load_app_config


def test_app_config_loads():
    config = load_app_config()
    assert config.display_name
    assert config.package_name.startswith("com.")
    assert config.framework in {"kivy", "beeware", "flet"}