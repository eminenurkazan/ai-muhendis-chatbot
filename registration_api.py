"""Kullanıcı kaydı API'si; giriş ve JWT sonraki adımdır."""

from typing import Literal
from uuid import UUID

from fastapi import APIRouter, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute
from pydantic import BaseModel, ConfigDict, Field, SecretStr

import app_log
import registration_service as service


class RegistrationRoute(APIRoute):
    def get_route_handler(self):
        handler = super().get_route_handler()

        async def safe_handler(request):
            try:
                return await handler(request)
            except RequestValidationError as exc:
                # Ham parola veya JSON gövdesi yanıt hatasına eklenmemeli.
                details = []
                for error in exc.errors():
                    location = error.get("loc", ())
                    field = location[-1] if location else None
                    error_type = error.get("type", "")
                    if error_type == "json_invalid":
                        message = "İstek gövdesi geçerli JSON olmalı."
                    elif field == "email" and error_type == "missing":
                        message = "E-posta adresi gerekli."
                    elif field == "email" and error_type == "string_too_long":
                        message = "E-posta adresi 320 karakterden kısa olmalı."
                    elif field == "password" and error_type == "missing":
                        message = "Parola gerekli."
                    elif field == "password" and error_type == "string_too_short":
                        message = "Parola en az 8 karakter olmalı."
                    elif field == "password" and error_type == "string_too_long":
                        message = "Parola 1024 karakteri aşamaz."
                    elif error_type == "extra_forbidden":
                        message = "İstek desteklenmeyen bir alan içeriyor."
                    else:
                        message = "İstek bilgilerini kontrol et."
                    if message not in details:
                        details.append(message)
                return JSONResponse(status_code=422, content={"detail": details})

        return safe_handler


router = APIRouter(prefix="/auth", tags=["Kullanıcı"], route_class=RegistrationRoute)


class RegisterRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    email: str = Field(max_length=320)
    password: SecretStr = Field(min_length=8, max_length=1024)


class RegisteredUser(BaseModel):
    id: UUID
    email: str
    role: Literal["user"]
    is_active: bool


@router.post("/register", status_code=201, response_model=RegisteredUser)
def register(request: RegisterRequest):
    try:
        user = service.register_user(request.email, request.password.get_secret_value())
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None
    except service.RegistrationConflict as exc:
        app_log.log_event("warning", "auth.register_conflict")
        raise HTTPException(status_code=409, detail=str(exc)) from None
    except service.RegistrationUnavailable as exc:
        app_log.log_event("error", "auth.register_unavailable")
        raise HTTPException(status_code=503, detail=str(exc)) from None
    app_log.log_event("info", "auth.register_success", user_id=str(user["id"]))
    return user
