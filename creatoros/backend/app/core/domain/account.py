from __future__ import annotations
from dataclasses import dataclass


class AccountError(Exception):
    """Raised by account use cases for expected, reportable failures."""


@dataclass(frozen=True)
class Account:
    """Instagram account entity with persisted-session state."""

    username: str
    has_session: bool
    status: str  # one of: ready, no_session, invalid
    last_checked: str | None = None
    last_error: str | None = None