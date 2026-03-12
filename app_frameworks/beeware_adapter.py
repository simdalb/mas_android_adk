from __future__ import annotations

from typing import Dict, List

from app.adapters.framework import FrameworkAdapter
from app.domain.models import MediaLink


class BeeWareAdapter(FrameworkAdapter):
    def name(self) -> str:
        return "beeware"

    def build_home_screen_model(self, links: List[MediaLink]) -> Dict:
        return {
            "framework": self.name(),
            "screen": "home",
            "title": "LinkSaver",
            "rows": [link.title for link in links],
        }

    def launch(self) -> str:
        return "BeeWare adapter placeholder launched. Replace with real Toga/BeeWare app wiring."


def create_adapter() -> BeeWareAdapter:
    return BeeWareAdapter()