from __future__ import annotations

from typing import Dict, List

from app.adapters.framework import FrameworkAdapter
from app.domain.models import MediaLink


class FletAdapter(FrameworkAdapter):
    def name(self) -> str:
        return "flet"

    def build_home_screen_model(self, links: List[MediaLink]) -> Dict:
        return {
            "framework": self.name(),
            "view": "home",
            "cards": [{"title": link.title, "subtitle": link.url} for link in links],
        }

    def launch(self) -> str:
        return "Flet adapter placeholder launched. Replace with real Flet app wiring."


def create_adapter() -> FletAdapter:
    return FletAdapter()