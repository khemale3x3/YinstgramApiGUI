from __future__ import annotations
from typing import Callable

from fastapi import Depends, Header, HTTPException

from app.core.services.admin_service import AdminService
from app.core.services.auth_service import AuthService


def build_require_admin(auth: AuthService) -> Callable:
    """FastAPI dependency returning the verified admin identity."""

    def require_admin(authorization: str | None = Header(default=None)) -> dict:
        if not authorization or not authorization.lower().startswith("bearer "):
            raise HTTPException(status_code=401, detail="not authenticated")
        token = authorization.split(" ", 1)[1].strip()
        identity = auth.verify(token)
        if not identity:
            raise HTTPException(status_code=401, detail="invalid or expired token")
        return identity

    return require_admin


def build_require_feature(require_admin: Callable, admin_service: AdminService) -> Callable:
    """Factory of dependencies that gate a route behind a feature flag + role.

    Usage:  `Depends(require_feature("creators"))` alongside `require_admin`.
    A disabled feature returns 403 *before* the route runs — hiding the menu
    in the frontend is never the real security boundary. Features that declare
    admin-only roles reject non-admin identities as well.
    """

    def require_feature(key: str) -> Callable:
        def dependency(identity: dict = Depends(require_admin)) -> dict:
            role = identity.get("role", "")
            feature = admin_service.get_feature(key) if admin_service is not None else None
            if feature is None or not feature.get("enabled"):
                raise HTTPException(status_code=403, detail=f"feature disabled: {key}")
            allowed = {r.strip() for r in str(feature.get("roles") or "admin,user").split(",")}
            if not allowed or role not in allowed:
                raise HTTPException(status_code=403, detail="insufficient permissions")
            return identity

        return dependency

    return require_feature