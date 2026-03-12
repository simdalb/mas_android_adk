from __future__ import annotations

from pathlib import Path
from typing import List
import json

from app.domain.models import MediaLink


class LocalMediaRepository:
    def __init__(self, path: str = "artifacts/media_links.json") -> None:
        self.path = Path(path)

    def load_all(self) -> List[MediaLink]:
        if not self.path.exists():
            return []
        raw = json.loads(self.path.read_text(encoding="utf-8"))
        return [MediaLink(**item) for item in raw]

    def save_all(self, links: List[MediaLink]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = [link.__dict__ for link in links]
        self.path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def add(self, link: MediaLink) -> MediaLink:
        links = self.load_all()
        links.append(link)
        self.save_all(links)
        return link

    def search(self, query: str) -> List[MediaLink]:
        return [item for item in self.load_all() if item.matches(query)]