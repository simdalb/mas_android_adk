from __future__ import annotations

from dataclasses import dataclass, field
from typing import List
import uuid


@dataclass
class MediaLink:
    title: str
    url: str
    tags: List[str] = field(default_factory=list)
    is_local: bool = False
    description: str = ""
    link_id: str = field(default_factory=lambda: str(uuid.uuid4()))

    def matches(self, query: str) -> bool:
        q = query.strip().lower()
        if not q:
            return True
        searchable = " ".join([self.title, self.url, self.description, " ".join(self.tags)]).lower()
        return q in searchable


@dataclass
class UserProfile:
    user_id: str
    email: str
    display_name: str = ""
    is_paid: bool = False