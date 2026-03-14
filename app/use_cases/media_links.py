from __future__ import annotations

from typing import List, Optional

from app.domain.models import MediaLink
from app.services.storage import (
    DuplicateMediaLinkError,
    InvalidMediaLinkError,
    LocalMediaRepository,
)


class MediaLinkUseCases:
    def __init__(self, repository: Optional[LocalMediaRepository] = None) -> None:
        self.repository = repository or LocalMediaRepository()

    def list_links(self) -> List[MediaLink]:
        return self.repository.load_all()

    def create_link(
        self,
        *,
        title: str,
        url: str,
        tags: List[str] | None = None,
        is_local: bool = False,
        description: str = "",
    ) -> MediaLink:
        normalized_tags = [tag.strip() for tag in (tags or []) if tag.strip()]

        if not title.strip():
            raise InvalidMediaLinkError("Title is required.")
        if not url.strip():
            raise InvalidMediaLinkError("URL or local path is required.")

        link = MediaLink(
            title=title.strip(),
            url=url.strip(),
            tags=normalized_tags,
            is_local=bool(is_local),
            description=description.strip(),
        )
        return self.repository.add(link)

    def update_link(self, link: MediaLink) -> MediaLink:
        link.title = link.title.strip()
        link.url = link.url.strip()
        link.tags = [tag.strip() for tag in link.tags if tag.strip()]
        link.description = link.description.strip()

        if not link.title:
            raise InvalidMediaLinkError("Title is required.")
        if not link.url:
            raise InvalidMediaLinkError("URL or local path is required.")

        return self.repository.update(link)

    def delete_link(self, link_id: str) -> bool:
        return self.repository.delete(link_id)

    def get_link(self, link_id: str) -> Optional[MediaLink]:
        return self.repository.get(link_id)

    def search_links(self, query: str) -> List[MediaLink]:
        return self.repository.search(query)

    def create_link_safe(
        self,
        *,
        title: str,
        url: str,
        tags: List[str] | None = None,
        is_local: bool = False,
        description: str = "",
    ) -> dict:
        try:
            link = self.create_link(
                title=title,
                url=url,
                tags=tags,
                is_local=is_local,
                description=description,
            )
            return {"ok": True, "link": link, "error": ""}
        except (InvalidMediaLinkError, DuplicateMediaLinkError) as exc:
            return {"ok": False, "link": None, "error": str(exc)}

    def update_link_safe(self, link: MediaLink) -> dict:
        try:
            updated = self.update_link(link)
            return {"ok": True, "link": updated, "error": ""}
        except (InvalidMediaLinkError, DuplicateMediaLinkError) as exc:
            return {"ok": False, "link": None, "error": str(exc)}