from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException

from app.adapters.primary.api.schemas import AccountListResponse, LoginRequest, VerifyResponse
from app.core.domain.account import Account, AccountError
from app.core.services.account_service import AccountService


def build_router(accounts: AccountService, require_admin=None, dependencies=None) -> APIRouter:
    """Build the accounts router with its dependency injected."""
    router = APIRouter(prefix="/api/accounts", tags=["Accounts"])
    default_deps = ([Depends(require_admin)] if require_admin else []) + list(dependencies or [])

    @router.get("", response_model=AccountListResponse, dependencies=default_deps)
    def list_accounts() -> AccountListResponse:
        return AccountListResponse(accounts=accounts.list_accounts())

    @router.get("/{username}", response_model=Account, dependencies=default_deps)
    def get_account(username: str) -> Account:
        return accounts.get_account(username)

    @router.post("", response_model=Account, status_code=201, dependencies=default_deps)
    def add_account(payload: LoginRequest) -> Account:
        """Add an account. Credentials are used once; the session is persisted."""
        try:
            username = payload.username.strip().lstrip("@")
            return accounts.add_account(username, payload.password)
        except AccountError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @router.post("/{username}/check", response_model=VerifyResponse, dependencies=default_deps)
    def check_account(username: str) -> VerifyResponse:
        """Validate the stored session for an account."""
        result = accounts.check_account(username)
        if result.status == "ready":
            return VerifyResponse(verified=True, message="session valid")
        if result.status == "invalid":
            return VerifyResponse(verified=False, message=result.last_error or "session invalid")
        return VerifyResponse(verified=False, message="no saved session")

    @router.delete("/{username}", response_model=Account, dependencies=default_deps)
    def remove_account(username: str) -> Account:
        if not accounts.remove_account(username):
            raise HTTPException(status_code=404, detail="account not found")
        return Account(username=username, has_session=False, status="no_session")

    return router