from __future__ import annotations
import jwt
from jwt import InvalidTokenError

from app.core.ports.auth import TokenPort


class JwtTokenAdapter(TokenPort):
    """Driven adapter: signs and verifies HS256 JWT bearer tokens."""

    def __init__(self, secret: str, expires_minutes: int = 720, algorithm: str = "HS256"):
        self._secret = secret
        self._expires_minutes = expires_minutes
        self._algorithm = algorithm

    def create_token(self, subject: str, **claims) -> str:
        import datetime

        payload = {
            "sub": subject,
            "iat": datetime.datetime.now(datetime.timezone.utc),
            "exp": datetime.datetime.now(datetime.timezone.utc)
            + datetime.timedelta(minutes=self._expires_minutes),
        }
        payload.update(claims)
        return jwt.encode(payload, self._secret, algorithm=self._algorithm)

    def verify_token(self, token: str) -> dict | None:
        try:
            payload = jwt.decode(token, self._secret, algorithms=[self._algorithm])
        except InvalidTokenError:
            return None
        return payload