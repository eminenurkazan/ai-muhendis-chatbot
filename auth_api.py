"""Giriş ve oturum kontrolü; parola/token hiçbir loga yazılmaz."""

from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, ConfigDict, Field, SecretStr

import app_log
import auth_service as service
from async_utils import run_blocking
from registration_api import RegistrationRoute

router = APIRouter(prefix="/auth", tags=["Kullanıcı"], route_class=RegistrationRoute)
bearer = HTTPBearer(auto_error=False)


class UserInfo(BaseModel):
    id: UUID
    email: str
    role: Literal["user", "admin"]
    is_active: bool


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    email: str = Field(max_length=320)
    password: SecretStr = Field(min_length=1, max_length=1024)


class LoginResponse(BaseModel):
    access_token: str
    token_type: Literal["bearer"]
    expires_in: int
    user: UserInfo


def _unauthorized(message: str) -> HTTPException:
    return HTTPException(status_code=401, detail=message, headers={"WWW-Authenticate": "Bearer"})


async def require_user(credentials: HTTPAuthorizationCredentials | None = Depends(bearer)) -> dict:
    if credentials is None:
        raise _unauthorized("Bu işlem için giriş yapmalısın.")
    try:
        return await run_blocking(service.current_user, credentials.credentials)
    except service.AuthenticationError as exc:
        raise _unauthorized(str(exc)) from None
    except service.AuthenticationUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from None


@router.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest, http_request: Request):
    # E-posta ve parola günlüğe yazılmaz; yalnız istemci adresi ve sonuç kaydedilir.
    client_ip = http_request.client.host if http_request.client else None
    try:
        result = await run_blocking(service.login, request.email, request.password.get_secret_value())
    except service.AuthenticationError as exc:
        app_log.log_event("warning", "auth.login_failed", details={"client_ip": client_ip})
        raise _unauthorized(str(exc)) from None
    except service.AuthenticationUnavailable as exc:
        app_log.log_event("error", "auth.login_unavailable", details={"client_ip": client_ip})
        raise HTTPException(status_code=503, detail=str(exc)) from None
    app_log.log_event("info", "auth.login_success", user_id=str(result["user"]["id"]),
                      details={"client_ip": client_ip})
    return result


@router.get("/me", response_model=UserInfo)
async def me(user: dict = Depends(require_user)):
    return user
