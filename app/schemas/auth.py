# Pydantic schemas define the API contracts used by routes, services, and frontend callers.
from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import EmailStr, Field

from app.schemas.common import APIModel


class LoginRequest(APIModel):
    # Request contract for login; FastAPI validates incoming JSON against these fields before service code runs.
    email: EmailStr
    password: str = Field(min_length=8)


class ActivationRequest(APIModel):
    # Request contract for activation; FastAPI validates incoming JSON against these fields before service code
    # runs.
    token: str
    password: str = Field(min_length=8)


class ForgotPasswordRequest(APIModel):
    # Request contract for forgot password; FastAPI validates incoming JSON against these fields before service
    # code runs.
    email: EmailStr


class ResetPasswordRequest(APIModel):
    # Request contract for reset password; FastAPI validates incoming JSON against these fields before service
    # code runs.
    token: str
    password: str = Field(min_length=8)


class RefreshTokenRequest(APIModel):
    # Request contract for refresh token; FastAPI validates incoming JSON against these fields before service
    # code runs.
    refresh_token: str = Field(min_length=1)


class ChangePasswordRequest(APIModel):
    # Request contract for change password; FastAPI validates incoming JSON against these fields before service
    # code runs.
    current_password: str = Field(min_length=8)
    new_password: str = Field(min_length=8)


class ProfileUpdateRequest(APIModel):
    # Request contract for profile update; FastAPI validates incoming JSON against these fields before service
    # code runs.
    full_name: str | None = None
    email: EmailStr | None = None
    phone_number: str | None = None
    notifications_enabled: bool | None = None
    email_notifications_enabled: bool | None = None
    in_app_notifications_enabled: bool | None = None


class TokenPairResponse(APIModel):
    # Response contract for token pair; routes serialize service or ORM results into this frontend-facing shape.
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TwoFactorChallengeResponse(APIModel):
    # Response contract for two factor challenge; routes serialize service or ORM results into this frontend-
    # facing shape.
    requires_two_factor: bool = True
    two_factor_ticket: str
    delivery: str = "authenticator"
    email: EmailStr


AuthLoginResponse = TokenPairResponse | TwoFactorChallengeResponse


class PasswordResetResponse(APIModel):
    # Response contract for password reset; routes serialize service or ORM results into this frontend-facing
    # shape.
    message: str
    reset_token: str | None = None


class TwoFactorVerifyRequest(APIModel):
    # Request contract for two factor verify; FastAPI validates incoming JSON against these fields before
    # service code runs.
    ticket: str
    code: str = Field(min_length=6, max_length=6)


class TwoFactorCodeRequest(APIModel):
    # Request contract for two factor code; FastAPI validates incoming JSON against these fields before service
    # code runs.
    code: str = Field(min_length=6, max_length=6)


class TwoFactorSetupResponse(APIModel):
    # Response contract for two factor setup; routes serialize service or ORM results into this frontend-facing
    # shape.
    enabled: bool
    pending_setup: bool
    secret: str | None = None
    otpauth_url: str | None = None
    qr_code_url: str | None = None


class CurrentUserResponse(APIModel):
    # Response contract for current user; routes serialize service or ORM results into this frontend-facing
    # shape.
    user_id: UUID
    tenant_id: UUID | None = None
    email: EmailStr
    full_name: str
    role_codes: list[str]
    assigned_brand_space_ids: list[UUID]
    extra: dict[str, Any] = Field(default_factory=dict)
