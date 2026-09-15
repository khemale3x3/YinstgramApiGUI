from __future__ import annotations
from abc import ABC, abstractmethod


class TokenPort(ABC):
    """Secondary port for issuing and verifying bearer tokens."""

    @abstractmethod
    def create_token(self, subject: str, **claims) -> str:
        """Issue a signed token for the given subject."""

    @abstractmethod
    def verify_token(self, token: str) -> dict | None:
        """Validate a token and return its claims, or None if invalid."""