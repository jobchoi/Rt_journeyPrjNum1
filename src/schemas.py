"""Pydantic request and response schemas for authentication."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class RegisterRequest(BaseModel):
    email: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=8, max_length=72)
    name: str = Field(min_length=1, max_length=100)
    role_code: str = Field(default="applicant", min_length=1, max_length=50)

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        normalized = value.strip().lower()
        if "@" not in normalized or normalized.startswith("@"):
            raise ValueError("유효한 이메일을 입력하세요.")
        return normalized

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        return value.strip()


class LoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=1, max_length=72)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return value.strip().lower()


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    email: str
    name: str
    status: str
    roles: list[str]


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    roles: list[str] = Field(default_factory=list)


class ApplicationCreate(BaseModel):
    announcement_id: str = Field(min_length=1, max_length=100)
    study_plan: str = Field(min_length=1, max_length=10000)
    financial_need: str = Field(min_length=1, max_length=10000)
    ministry_plan: str | None = Field(default=None, max_length=10000)


class ApplicationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    applicant_id: str
    announcement_id: str
    status: str
    study_plan: str
    financial_need: str
    ministry_plan: str | None
    submitted_at: datetime
    created_at: datetime
    updated_at: datetime