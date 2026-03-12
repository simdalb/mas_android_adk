from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Dict, List

from app.domain.models import MediaLink


class FrameworkAdapter(ABC):
    @abstractmethod
    def name(self) -> str:
        raise NotImplementedError

    @abstractmethod
    def build_home_screen_model(self, links: List[MediaLink]) -> Dict:
        raise NotImplementedError

    @abstractmethod
    def launch(self) -> str:
        raise NotImplementedError