from __future__ import annotations
import hashlib
import hmac
import os

from app.core.domain.access import User
from app.core.ports.admin import AdminStorePort
from app.core.ports.auth import TokenPort


class AuthError(Exception):
    """Raised for expected, reportable auth failures."""


def hash_password(password: str, salt: str | None = None) -> str:
    """PBKDF2-SHA256 password hash. Format: pbkdf2$iterations$salt$digest."""
    salt = salt or os.urandom(16).hex()
    iterations = 120_000
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), bytes.fromhex(salt), iterations
    ).hex()
    return f"pbkdf2${iterations}${salt}${digest}"


def verify_password(password: str, stored: str) -> bool:
    try:
        scheme, iterations, salt, digest = stored.split("$", 3)
        if scheme != "pbkdf2":
            return False
        candidate = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), bytes.fromhex(salt), int(iterations)
        ).hex()
        return hmac.compare_digest(candidate, digest)
    except (ValueError, TypeError):
        return False


class AuthService:
    """Use case: login and token verification against a users store.

    The configured environment admin (ADMIN_EMAIL / ADMIN_PASSWORD /
    ADMIN_PASSWORD_HASH) is provisioned as a user row on first login, so the
    rest of the system (feature flags, audit log, future roles) works the same
    for every identity. Extra users can be added by the admin later. Passwords
    are never transmitted back to the client.
    """

    def __init__(self, tokens: TokenPort, admin: AdminStorePort, email: str, password_verifier):
        self._tokens = tokens
        self._admin = admin
        self._email = (email or "").strip().lower()
        self._verify = password_verifier

    def login(self, email: str, password: str) -> dict:
        if not email or not password:
            raise AuthError("email and password are required")
        email = email.strip().lower()

        user = self._admin.get_user_by_email(email)
        is_env_admin = email == self._email

        if user is None:
            if is_env_admin and self._verify(password):
                # first-time admin — provision the user row from env credentials
                user = User(
                    id="",
                    email=email,
                    name="Administrator",
                    role="admin",
                    status="active",
                    password_hash=hash_password(password),
                )
                self._admin.upsert_user(user)
                self._audit(email, "login", "provisioned admin from .env")
                self._admin.record_login(email)
                token = self._tokens.create_token(email, role="admin", uid=user.id)
                return {"token": token, "email": email, "role": "admin"}
            raise AuthError("invalid credentials")

        if user.status != "active":
            raise AuthError("account disabled")

        if self._verify_password(user, password):
            self._audit(email, "login", "signed in")
            self._admin.record_login(email)
            token = self._tokens.create_token(email, role=user.role, uid=user.id)
            return {"token": token, "email": email, "role": user.role}

        raise AuthError("invalid credentials")

    def signup(self, email: str, name: str, password: str) -> dict:
        """Register a new non-admin user (role 'user') and return tokens.

        Passwords are stored as PBKDF2 hashes only — never plaintext — and
        every signup is audited. Only the environment admin (ADMIN_EMAIL) is
        ever provisioned as `admin`; self-signup always creates a `user`.
        """
        if not email or not password:
            raise AuthError("email and password are required")
        email = email.strip().lower()
        if len(password) < 8:
            raise AuthError("password must be at least 8 characters")
        if self._admin.get_user_by_email(email) is not None:
            raise AuthError("an account with this email already exists")

        user = User(
            id="",
            email=email,
            name=(name or "").strip(),
            role="user",
            status="active",
            password_hash=hash_password(password),
        )
        self._admin.upsert_user(user)
        self._admin.record_login(email)
        self._audit(email, "user.signup", "new account registered")
        token = self._tokens.create_token(email, role="user", uid=user.id)
        return {"token": token, "email": email, "role": "user"}

    def _verify_password(self, user: User, password: str) -> bool:
        if user.password_hash and verify_password(password, user.password_hash):
            return True
        if user.email == self._email and self._verify(password):
            # env password changed — adopt the new one into the store
            self._admin.upsert_user(
                User(
                    id=user.id,
                    email=user.email,
                    name=user.name or "Administrator",
                    username=user.username,
                    role=user.role,
                    status=user.status,
                    password_hash=hash_password(password),
                    created_at=user.created_at,
                    last_login=user.last_login,
                )
            )
            return True
        return False

    def update_profile(self, email: str, name: str | None = None, username: str | None = None) -> dict:
        """Update the current user's profile. Returns the updated user dict."""
        email = (email or "").strip().lower()
        user = self._admin.get_user_by_email(email)
        if user is None:
            raise AuthError("account not found")
        updates = {
            "role": user.role,
            "status": user.status,
            "name": (name if name is not None else user.name).strip(),
            "username": (username if username is not None else user.username).strip().lstrip("@"),
        }
        self._admin.upsert_user(
            User(
                id=user.id,
                email=user.email,
                name=updates["name"],
                username=updates["username"],
                role=updates["role"],
                status=user.status,
                password_hash=user.password_hash,
                created_at=user.created_at,
                last_login=user.last_login,
            )
        )
        try:
            self._admin.audit(email, "profile.update", target="auth", detail="profile details updated")
        except Exception:
            pass
        return {"email": user.email, "name": updates["name"], "username": updates["username"]}

    def change_password(self, email: str, current_password: str, new_password: str) -> None:
        """Verify the current password and replace it with a new one."""
        if not new_password or len(new_password) < 8:
            raise AuthError("new password must be at least 8 characters")
        if current_password == new_password:
            raise AuthError("new password must be different from the current password")
        email = (email or "").strip().lower()
        user = self._admin.get_user_by_email(email)
        if user is None:
            raise AuthError("account not found")
        if not self._verify_password(user, current_password):
            raise AuthError("current password is incorrect")
        self._admin.upsert_user(
            User(
                id=user.id,
                email=user.email,
                name=user.name,
                username=user.username,
                role=user.role,
                status=user.status,
                password_hash=hash_password(new_password),
                created_at=user.created_at,
                last_login=user.last_login,
            )
        )
        try:
            self._admin.audit(email, "password.change", target="auth", detail="password updated")
        except Exception:
            pass

    def _audit(self, user: str, action: str, detail: str = "") -> None:
        try:
            self._admin.audit(user, action, target="auth", detail=detail)
        except Exception:
            pass  # audit must never block login

    def verify(self, token: str) -> dict | None:
        claims = self._tokens.verify_token(token)
        if not claims:
            return None
        email = (claims.get("sub") or "").strip().lower()
        user = self._admin.get_user_by_email(email)
        if user is None or user.status != "active":
            return None
        if user.email != self._email and not user.password_hash:
            return None
        return {"email": email, "role": claims.get("role", user.role), "uid": claims.get("uid", user.id)}