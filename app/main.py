from __future__ import annotations

import importlib
import os
from typing import Any, List

from app.config import load_app_config
from app.domain.models import MediaLink
from app.services.storage import LocalMediaRepository


def load_framework_adapter() -> Any:
    from mas_settings import load_settings

    settings = load_settings()
    module_name = settings["framework"]["adapter_module"]
    module = importlib.import_module(module_name)
    return module.create_adapter()


def build_demo_links() -> List[MediaLink]:
    repo = LocalMediaRepository()
    links = repo.load_all()
    if links:
        return links

    return [
        MediaLink(
            title="Sample remote video",
            url="https://example.com/video/123",
            tags=["sample", "remote"],
            description="Example starter content",
        ),
        MediaLink(
            title="Sample local file",
            url="/storage/emulated/0/Movies/demo.mp4",
            tags=["sample", "local"],
            is_local=True,
            description="Example local media path",
        ),
    ]


def main() -> int:
    config = load_app_config()
    adapter = load_framework_adapter()
    links = build_demo_links()

    print(f"Launching {config.display_name} with framework adapter: {adapter.name()}")

    run_ui = os.environ.get("RUN_KIVY_UI", "").lower() in {"1", "true", "yes"}
    if run_ui and hasattr(adapter, "run_ui"):
        adapter.run_ui(links)
        return 0

    print(adapter.launch())
    print(adapter.build_home_screen_model(links))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())