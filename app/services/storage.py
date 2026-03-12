from __future__ import annotations

from pathlib import Path
from typing import List, Optional
import json

from app.domain.models import MediaLink


class LocalMediaRepository:
    def __init__(self, path: str = "artifacts/media_links.json") -> None:
        self.path = Path(path)

    def _safe_load_raw(self) -> List[dict]:
        if not self.path.exists():
            return []
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
            if isinstance(raw, list):
                return [item for item in raw if isinstance(item, dict)]
            return []
        except Exception:
            return []

    def load_all(self) -> List[MediaLink]:
        return [MediaLink(**item) for item in self._safe_load_raw()]

    def save_all(self, links: List[MediaLink]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = [link.__dict__ for link in links]
        self.path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def add(self, link: MediaLink) -> MediaLink:
        links = self.load_all()
        links.append(link)
        self.save_all(links)
        return link

    def get(self, link_id: str) -> Optional[MediaLink]:
        for item in self.load_all():
            if item.link_id == link_id:
                return item
        return None

    def update(self, updated_link: MediaLink) -> MediaLink:
        links = self.load_all()
        replaced = False
        for idx, item in enumerate(links):
            if item.link_id == updated_link.link_id:
                links[idx] = updated_link
                replaced = True
                break
        if not replaced:
            links.append(updated_link)
        self.save_all(links)
        return updated_link

    def delete(self, link_id: str) -> bool:
        links = self.load_all()
        new_links = [item for item in links if item.link_id != link_id]
        changed = len(new_links) != len(links)
        if changed:
            self.save_all(new_links)
        return changed

    def search(self, query: str) -> List[MediaLink]:
        q = query.strip()
        if not q:
            return self.load_all()
        return [item for item in self.load_all() if item.matches(q)]