from __future__ import annotations
from app.core.domain.creator import Creator
from app.core.domain.post import CreatorPost
from app.core.ports.instagram import InstagramPort


class InstagramService:
    """Use case: read-only creator intelligence operations."""

    def __init__(self, instagram: InstagramPort):
        self._instagram = instagram

    def get_creator(self, username: str) -> Creator:
        return self._instagram.get_profile(username)

    def get_creator_posts(self, username: str, amount: int = 10) -> list[CreatorPost]:
        return self._instagram.get_posts(username, amount)

    def search_creators(self, query: str, count: int = 20) -> list[dict]:
        return self._instagram.search_users(query, count)