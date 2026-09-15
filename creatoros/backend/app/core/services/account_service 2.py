from __future__ import annotations
from datetime import datetime, timezone
from typing import Callable

from app.core.domain.account import Account, AccountError
from app.core.ports.instagram import InstagramPort
from app.core.ports.session_store import SessionStorePort

_STATUS_READY = "ready"
_STATUS_NO_SESSION = "no_session"
_STATUS_INVALID = "invalid"

InstagramFactory = Callable[[dict | None], InstagramPort]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class AccountService:
    """Use case: manage Instagram accounts and their persisted sessions.

    Passwords are used once during login and never stored. Only the session
    state is persisted, through the `SessionStorePort` adapter.
    """

    def __init__(self, sessions: SessionStorePort, instagram_factory: InstagramFactory):
        self._sessions = sessions
        self._factory = instagram_factory

    def list_accounts(self) -> list[str]:
        return self._sessions.list_accounts()

    def get_account(self, username: str) -> Account:
        has_session = self._sessions.has(username)
        return Account(
            username=username,
            has_session=has_session,
            status=_STATUS_READY if has_session else _STATUS_NO_SESSION,
        )

    def add_account(self, username: str, password: str) -> Account:
        client = self._factory(None)
        try:
            ok = client.login(username, password)
        except Exception as exc:
            raise AccountError(f"login failed: {exc}") from exc
        if not ok:
            raise AccountError("login failed: Instagram did not accept the credentials")
        session = client.dump_session()
        self._sessions.save(username, session)
        return Account(
            username=username,
            has_session=True,
            status=_STATUS_READY,
            last_checked=_now(),
        )

    def check_account(self, username: str) -> Account:
        session = self._sessions.load(username)
        if session is None:
            return Account(
                username=username,
                has_session=False,
                status=_STATUS_NO_SESSION,
                last_checked=_now(),
            )
        client = self._factory(session)
        try:
            valid = client.verify_session()
        except Exception as exc:
            return Account(
                username=username,
                has_session=True,
                status=_STATUS_INVALID,
                last_checked=_now(),
                last_error=str(exc),
            )
        return Account(
            username=username,
            has_session=True,
            status=_STATUS_READY if valid else _STATUS_INVALID,
            last_checked=_now(),
            last_error=None if valid else "session rejected by Instagram",
        )

    def remove_account(self, username: str) -> bool:
        return self._sessions.remove(username)