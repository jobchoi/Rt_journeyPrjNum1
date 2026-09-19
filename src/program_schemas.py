"""Pydantic schemas for scholarship programs and announcements."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


ProgramStatus = Literal["draft", "active", "closed"]
AnnouncementStatus = Literal["draft", "open", "closed", "reviewing", "finished"]


class ProgramCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=5000)
    status: ProgramStatus = "draft"
    application_start_at: datetime | None = None
    application_end_at: datetime | None = None

    @model_validator(mode="after")
    def validate_application_dates(self):
        if (
            self.application_start_at is not None
            and self.application_end_at is not None
            and self.application_start_at > self.application_end_at
        ):
            raise ValueError("신청 시작일은 종료일보다 늦을 수 없습니다.")
        return self


class ProgramUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=5000)
    status: ProgramStatus | None = None
    application_start_at: datetime | None = None
    application_end_at: datetime | None = None

    @model_validator(mode="after")
    def validate_application_dates(self):
        if (
            self.application_start_at is not None
            and self.application_end_at is not None
            and self.application_start_at > self.application_end_at
        ):
            raise ValueError("신청 시작일은 종료일보다 늦을 수 없습니다.")
        return self


class ProgramResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    description: str | None
    status: str
    application_start_at: datetime | None
    application_end_at: datetime | None
    created_by: str
    created_at: datetime
    updated_at: datetime


class AnnouncementCreate(BaseModel):
    program_id: str = Field(min_length=1, max_length=100)
    title: str = Field(min_length=1, max_length=200)
    target_description: str | None = Field(default=None, max_length=5000)
    selected_count: int | None = Field(default=None, ge=0)
    payment_description: str | None = Field(default=None, max_length=5000)
    status: AnnouncementStatus = "draft"
    fund_category_id: str | None = Field(default=None, max_length=100)
    published_at: datetime | None = None
    application_start_at: datetime | None = None
    application_end_at: datetime | None = None

    @model_validator(mode="after")
    def validate_application_dates(self):
        if (
            self.application_start_at is not None
            and self.application_end_at is not None
            and self.application_start_at > self.application_end_at
        ):
            raise ValueError("모집 시작일은 종료일보다 늦을 수 없습니다.")
        return self


class AnnouncementUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    target_description: str | None = Field(default=None, max_length=5000)
    selected_count: int | None = Field(default=None, ge=0)
    payment_description: str | None = Field(default=None, max_length=5000)
    status: AnnouncementStatus | None = None
    fund_category_id: str | None = Field(default=None, max_length=100)
    published_at: datetime | None = None
    application_start_at: datetime | None = None
    application_end_at: datetime | None = None

    @model_validator(mode="after")
    def validate_application_dates(self):
        if (
            self.application_start_at is not None
            and self.application_end_at is not None
            and self.application_start_at > self.application_end_at
        ):
            raise ValueError("모집 시작일은 종료일보다 늦을 수 없습니다.")
        return self


class AnnouncementResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    program_id: str
    title: str
    target_description: str | None
    selected_count: int | None
    payment_description: str | None
    status: str
    fund_category_id: str | None
    published_at: datetime | None
    application_start_at: datetime | None
    application_end_at: datetime | None
    created_by: str
    created_at: datetime
    updated_at: datetime