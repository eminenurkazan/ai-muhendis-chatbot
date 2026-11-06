"""Giriş ve oturum kontrolü; parola/token hiçbir loga yazılmaz."""

from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, ConfigDict, Field, SecretStr

import auth_service as service
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


def require_user(credentials: HTTPAuthorizationCredentials | None = Depends(bearer)) -> dict:
    if credentials is None:
        raise _unauthorized("Bu işlem için giriş yapmalısın.")
    try:
        return service.current_user(credentials.credentials)
    except service.AuthenticationError as exc:
        raise _unauthorized(str(exc)) from None
    except service.AuthenticationUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from None


@router.post("/login", response_model=LoginResponse)
def login(request: LoginRequest):
    try:
        return service.login(request.email, request.password.get_secret_value())
    except service.AuthenticationError as exc:
        raise _unauthorized(str(exc)) from None
    except service.AuthenticationUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from None


@router.get("/me", response_model=UserInfo)
def me(user: dict = Depends(require_user)):
    return user
