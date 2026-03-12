import importlib

from app.domain.models import MediaLink
from mas_settings import load_settings


def test_selected_adapter_loads():
    settings = load_settings()
    module = importlib.import_module(settings["framework"]["adapter_module"])
    adapter = module.create_adapter()
    assert adapter.name() == settings["framework"]["selected"]


def test_adapter_builds_home_model():
    settings = load_settings()
    module = importlib.import_module(settings["framework"]["adapter_module"])
    adapter = module.create_adapter()
    model = adapter.build_home_screen_model(
        [
            MediaLink(title="One", url="https://example.com/1"),
            MediaLink(title="Two", url="https://example.com/2"),
        ]
    )
    assert isinstance(model, dict)
    assert model