from __future__ import annotations

from pathlib import Path
from typing import List, Optional
import json

from app.domain.models import MediaLink


class DuplicateMediaLinkError(ValueError):
    pass


class InvalidMediaLinkError(ValueError):
    pass


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
        items: List[MediaLink] = []
        for item in self._safe_load_raw():
            try:
                items.append(MediaLink(**item))
            except Exception:
                continue
        return items

    def save_all(self, links: List[MediaLink]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = [link.__dict__ for link in links]
        self.path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def _normalize_title(self, value: str) -> str:
        return value.strip().casefold()

    def _normalize_url(self, value: str) -> str:
        return value.strip()

    def _validate(self, link: MediaLink) -> None:
        if not link.title.strip():
            raise InvalidMediaLinkError("Title is required.")
        if not link.url.strip():
            raise InvalidMediaLinkError("URL or local path is required.")

    def _is_duplicate(self, link: MediaLink, items: List[MediaLink]) -> bool:
        title = self._normalize_title(link.title)
        url = self._normalize_url(link.url)
        for item in items:
            if item.link_id == link.link_id:
                continue
            if self._normalize_title(item.title) == title and self._normalize_url(item.url) == url:
                return True
        return False

    def add(self, link: MediaLink) -> MediaLink:
        self._validate(link)
        links = self.load_all()
        if self._is_duplicate(link, links):
            raise DuplicateMediaLinkError("A link with the same title and URL already exists.")
        links.append(link)
        self.save_all(links)
        return link

    def get(self, link_id: str) -> Optional[MediaLink]:
        for item in self.load_all():
            if item.link_id == link_id:
                return item
        return None

    def update(self, updated_link: MediaLink) -> MediaLink:
        self._validate(updated_link)
        links = self.load_all()
        if self._is_duplicate(updated_link, links):
            raise DuplicateMediaLinkError("A link with the same title and URL already exists.")

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