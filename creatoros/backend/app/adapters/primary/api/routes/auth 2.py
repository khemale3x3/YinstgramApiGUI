from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException, Request

from app.adapters.primary.api.clientinfo import meta_from_request
from app.adapters.primary.api.deps import build_require_admin
from app.adapters.primary.api.schemas import (
    AdminLoginRequest,
    ChangePasswordRequest,
    MeResponse,
    ProfileUpdateRequest,
    SignupRequest,
    TokenResponse,
)
from app.core.services.admin_service import AdminService
from app.core.services.auth_service import AuthError, AuthService


def build_router(auth_service: AuthService, admin_service: AdminService | None = None) -> APIRouter:
    router = APIRouter(prefix="/api/auth", tags=["Auth"])
    require_admin = build_require_admin(auth_service)

    @router.post("/login", response_model=TokenResponse)
    def login(payload: AdminLoginRequest, request: Request) -> TokenResponse:
        try:
            result = auth_service.login(payload.email, payload.password)
        except AuthError as exc:
            raise HTTPException(status_code=401, detail=str(exc)) from exc
        if admin_service is not None:
            admin_service.record_connection(
                result["email"], event="login", meta=meta_from_request(request)
            )
        return TokenResponse(**result)

    @router.post("/signup", response_model=TokenResponse)
    def signup(payload: SignupRequest, request: Request) -> TokenResponse:
        try:
            result = auth_service.signup(payload.email, payload.name, payload.password)
        except AuthError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        if admin_service is not None:
            admin_service.record_connection(
                result["email"], event="signup", meta=meta_from_request(request)
            )
        return TokenResponse(**result)

    @router.get("/me", response_model=MeResponse)
    def me(identity: dict = Depends(require_admin)) -> MeResponse:
        profile = admin_service.profile(identity) if admin_service else {
            "email": identity["email"], "role": identity["role"]
        }
        return MeResponse(**profile)

    @router.put("/profile", response_model=ProfileUpdateRequest)
    def update_profile(payload: ProfileUpdateRequest, identity: dict = Depends(require_admin)):
        try:
            result = auth_service.update_profile(
                email=identity["email"], name=payload.name, username=payload.username
            )
        except AuthError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return result

    @router.post("/change-password")
    def change_password(payload: ChangePasswordRequest, identity: dict = Depends(require_admin)):
        try:
            auth_service.change_password(
                email=identity["email"],
                current_password=payload.current_password,
                new_password=payload.new_password,
            )
        except AuthError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return {"changed": True}

    @router.get("/activity")
    def activity(limit: int = 50, identity: dict = Depends(require_admin)):
        if admin_service is None:
            return {"entries": []}
        return {"entries": admin_service.activity(email=identity["email"], limit=limit)}

    return router