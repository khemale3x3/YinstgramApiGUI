"""Use case: admin service — RBAC profile, feature flags, menus, users, audit, tracking."""
from __future__ import annotations

from typing import Iterable

from app.core.domain.access import MENU_GROUPS, FeatureFlag, MenuItem
from app.core.ports.admin import AdminStorePort


def _roles_allowed(feature: FeatureFlag, role: str) -> bool:
    return role in {r.strip() for r in (feature.roles or "admin,user").split(",")}


def _serialize_feature(feature: FeatureFlag) -> dict:
    return {
        "key": feature.key,
        "label": feature.label,
        "enabled": feature.enabled,
        "group": feature.group,
        "roles": feature.roles or "admin,user",
    }


def _serialize_menu(item: MenuItem) -> dict:
    return {
        "key": item.key,
        "label": item.label,
        "path": item.path,
        "group": item.group,
        "icon": item.icon,
        "order": item.order,
        "feature": item.feature,
    }


class AdminService:
    """Access control + administration use cases.

    Feature flags are the global on/off switches; menus hang off features so a
    disabled feature removes the menu from every client. Features also declare
    which roles may use them — admin-only modules (settings, administration,
    tracking) stay hidden and hard-rejected (403) for other users.
    """

    def __init__(self, admin: AdminStorePort):
        self._admin = admin

    def features(self, role: str | None = None) -> list[dict]:
        rows = self._admin.list_features()
        if role:
            rows = [f for f in rows if _roles_allowed(f, role)]
        return [_serialize_feature(f) for f in rows]

    def get_feature(self, key: str) -> dict | None:
        feature = self._admin.get_feature(key)
        return _serialize_feature(feature) if feature else None

    def set_feature(self, key: str, enabled: bool, actor: str = "") -> dict:
        feature = self._admin.set_feature(key, enabled)
        self._admin.audit(
            actor or "system",
            "feature.change",
            target=key,
            detail=f"{'enabled' if enabled else 'disabled'}",
        )
        return _serialize_feature(feature)

    def menus(self, role: str | None = None) -> dict[str, list[dict]]:
        """Menu tree grouped by section, filtered by enabled features + role."""
        enabled = {f.key: f for f in self._admin.list_features() if f.enabled}
        tree: dict[str, list[dict]] = {group: [] for group in MENU_GROUPS}
        for item in self._admin.list_menus():
            if item.feature:
                feature = enabled.get(item.feature)
                if feature is None:
                    continue
                if role and not _roles_allowed(feature, role):
                    continue
            tree.setdefault(item.group, []).append(_serialize_menu(item))
        return tree

    def profile(self, identity: dict) -> dict:
        """Bootstrap payload for /api/auth/me — drives the dynamic sidebar."""
        email = identity.get("email", "")
        role = identity.get("role", "admin")
        user = self._admin.get_user_by_email(email) if email else None
        return {
            "email": email,
            "name": (user.name if user else ""),
            "username": (user.username if user else ""),
            "role": role,
            "status": (user.status if user else "active"),
            "created_at": (user.created_at if user else ""),
            "last_login": (user.last_login if user else ""),
            "last_activity": self.last_activity(email),
            "users_managed": len(self._admin.list()),
            "permissions": self.features(role=role),
            "instagram_accounts": [],
            "assigned_projects": [],
            "features": self.features(role=role),
            "menus": self.menus(role=role),
        }

    def last_activity(self, email: str) -> str:
        """Most recent created_at across audit, connections and traffic for a user."""
        stamps: list[str] = []
        try:
            for entry in self._admin.list_audit(limit=500):
                if entry.user == email and entry.created_at:
                    stamps.append(entry.created_at)
        except Exception:
            pass
        try:
            for conn in self._admin.list_connections(limit=500):
                if conn.get("user") == email and conn.get("created_at"):
                    stamps.append(conn["created_at"])
        except Exception:
            pass
        try:
            for row in self._admin.list_traffic(limit=500):
                if (row.get("user") == email or row.get("email") == email) and row.get("created_at"):
                    stamps.append(row["created_at"])
        except Exception:
            pass
        return max(stamps) if stamps else ""

    def activity(self, email: str, limit: int = 50) -> list[dict]:
        """Merged activity feed (audit + connections) for a single user."""
        entries: list[dict] = []
        for entry in self._admin.list_audit(limit=limit * 2):
            if entry.user == email:
                entries.append({
                    "kind": "audit",
                    "user": entry.user,
                    "action": entry.action,
                    "target": entry.target,
                    "detail": entry.detail,
                    "created_at": entry.created_at,
                })
        for conn in self._admin.list_connections(limit=limit * 2):
            if conn.get("user") == email:
                entries.append({
                    "kind": "connection",
                    "user": conn.get("user", ""),
                    "action": conn.get("event", "connection"),
                    "target": "",
                    "detail": " · ".join(
                        d for d in (
                            conn.get("device", ""),
                            conn.get("browser", ""),
                            conn.get("os", ""),
                            conn.get("ip", ""),
                            conn.get("location", ""),
                        ) if d
                    ),
                    "created_at": conn.get("created_at", ""),
                })
        entries.sort(key=lambda e: e["created_at"], reverse=True)
        return entries[:limit]

    def feature_enabled(self, key: str) -> bool:
        feature = self._admin.get_feature(key)
        return feature is not None and bool(feature.enabled)

    def feature_allows_role(self, key: str, role: str) -> bool:
        feature = self._admin.get_feature(key)
        return feature is not None and bool(feature.enabled) and _roles_allowed(feature, role)

    # ------------------------------------------------------------------- users
    def list_users(self) -> list[dict]:
        return [
            {
                "id": u.id,
                "email": u.email,
                "name": u.name,
                "username": u.username,
                "role": u.role,
                "status": u.status,
                "created_at": u.created_at,
                "last_login": u.last_login,
            }
            for u in self._admin.list()
        ]

    def update_user(self, user_id: str, role: str | None = None, status: str | None = None,
                    name: str | None = None, username: str | None = None, actor: str = "") -> dict | None:
        """Patch a user's role / status / name / username (admin action)."""
        user = self._admin.update_user(user_id, role=role, status=status, name=name, username=username)
        if user is None:
            return None
        self._admin.audit(
            actor or "system",
            "user.update",
            target=user.email,
            detail=", ".join(
                f"{k}={v}" for k, v in (
                    ("role", role), ("status", status), ("name", name), ("username", username),
                ) if v is not None
            ),
        )
        return {
            "id": user.id,
            "email": user.email,
            "name": user.name,
            "username": user.username,
            "role": user.role,
            "status": user.status,
            "created_at": user.created_at,
            "last_login": user.last_login,
        }

    def audit_logs(self, limit: int = 50) -> list[dict]:
        entries = self._admin.list_audit(limit=limit)
        return [
            {
                "id": entry.id,
                "user": entry.user,
                "action": entry.action,
                "target": entry.target,
                "detail": entry.detail,
                "created_at": entry.created_at,
            }
            for entry in entries
        ]

    # ---------------------------------------------------------------- tracking
    def record_connection(self, user: str, event: str, meta: dict | None = None) -> None:
        meta = meta or {}
        self._admin.record_connection(
            user=user, event=event, ip=meta.get("ip", ""), user_agent=meta.get("user_agent", ""),
            device=meta.get("device", ""), browser=meta.get("browser", ""),
            os=meta.get("os", ""), location=meta.get("location", ""),
        )

    def record_traffic(self, user: str, email: str, meta: dict) -> None:
        self._admin.record_traffic(
            user=user, email=email, method=meta.get("method", ""), path=meta.get("path", ""),
            status=meta.get("status", 0), duration_ms=meta.get("duration_ms", 0),
            ip=meta.get("ip", ""), user_agent=meta.get("user_agent", ""),
            device=meta.get("device", ""), browser=meta.get("browser", ""), os=meta.get("os", ""),
        )

    def traffic(self, limit: int = 200) -> list[dict]:
        return self._admin.list_traffic(limit=limit)

    def connections(self, limit: int = 100) -> list[dict]:
        return self._admin.list_connections(limit=limit)

    def traffic_stats(self) -> dict:
        return self._admin.traffic_stats()