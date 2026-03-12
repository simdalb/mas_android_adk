from __future__ import annotations

from typing import Optional

from app.domain.models import UserProfile


class AuthService:
    """
    Placeholder auth boundary.

    Replace or extend with Firebase auth integration later.
    """

    def __init__(self) -> None:
        self._current_user: Optional[UserProfile] = None

    def sign_in_demo(self, email: str, display_name: str = "") -> UserProfile:
        profile = UserProfile(
            user_id=email.lower(),
            email=email,
            display_name=display_name or email.split("@")[0],
            is_paid=False,
        )
        self._current_user = profile
        return profile

    def current_user(self) -> Optional[UserProfile]:
        return self._current_user

    def sign_out(self) -> None:
        self._current_user = None