"""Pydantic request and response schemas for authentication."""

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


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


class ReviewCriterionCreate(BaseModel):
    announcement_id: str = Field(min_length=1, max_length=100)
    code: str = Field(min_length=1, max_length=50)
    name: str = Field(min_length=1, max_length=200)
    max_score: int = Field(gt=0, le=1000)
    required: bool = True


class ReviewCriterionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    announcement_id: str
    code: str
    name: str
    max_score: int
    required: bool


class ReviewAssignmentCreate(BaseModel):
    application_id: str = Field(min_length=1, max_length=100)
    reviewer_id: str = Field(min_length=1, max_length=100)


class ReviewScoreInput(BaseModel):
    criterion_id: str = Field(min_length=1, max_length=100)
    score: int = Field(ge=0)
    comment: str | None = Field(default=None, max_length=10000)


class ReviewSubmit(BaseModel):
    scores: list[ReviewScoreInput] = Field(min_length=1)


class ReviewAssignmentResponse(BaseModel):
    id: str
    application_id: str
    reviewer_id: str
    recused_at: datetime | None
    recusal_reason: str | None
    total_score: int
    review_count: int


class FollowupCreate(BaseModel):
    application_id: str = Field(min_length=1, max_length=100)
    academic_update: str = Field(min_length=1, max_length=10000)
    ministry_update: str = Field(min_length=1, max_length=10000)
    evidence_note: str | None = Field(default=None, max_length=10000)


class FollowupResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    application_id: str
    applicant_id: str
    status: str
    academic_update: str
    ministry_update: str
    evidence_note: str | None
    submitted_at: datetime
    created_at: datetime
    updated_at: datetime


class FinanceTransactionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    version: int
    transaction_date: datetime
    transaction_type: str
    amount: int
    description: str
    external_reference: str
    counterparty: str | None
    category: str
    source_filename: str | None
    created_at: datetime


class FinanceOverviewResponse(BaseModel):
    total_income: int
    total_expense: int
    balance: int
    transaction_count: int


class SelectionCreate(BaseModel):
    application_id: str = Field(min_length=1, max_length=100)
    status: str = Field(pattern="^(selected|rejected)$")
    amount: int | None = Field(default=None, gt=0)


class SelectionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    application_id: str
    applicant_id: str
    status: str
    amount: int | None
    decided_by: str
    decided_at: datetime


class PaymentCreate(BaseModel):
    amount: int = Field(gt=0)
    payment_method: str = Field(min_length=1, max_length=100)
    external_reference: str = Field(min_length=1, max_length=200)


class PaymentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    selection_id: str
    amount: int
    status: str
    payment_method: str
    external_reference: str
    paid_at: datetime
    finance_transaction_id: str


class DocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    document_type: str
    original_filename: str
    content_type: str
    size_bytes: int
    created_at: datetime

class FinanceTransactionCreate(BaseModel):
    """Names are plain text: recording a payment never requires a scholarship account."""
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    transaction_date: date
    transaction_type: str = Field(pattern="^(income|expense)$")
    amount: int = Field(gt=0, le=1_000_000_000_000, strict=True)
    counterparty: str = Field(min_length=1, max_length=200)
    description: str = Field(min_length=1, max_length=1000)
    category: str = Field(default="general", pattern="^(general|donation|interest|carryover|scholarship|operating|other)$")
    external_reference: str | None = Field(default=None, min_length=1, max_length=200)

    @model_validator(mode="after")
    def validate_direction(self):
        if self.category in {"interest", "donation"} and self.transaction_type != "income":
            raise ValueError("이자와 후원금은 입금으로 등록하세요.")
        if self.category in {"scholarship", "operating"} and self.transaction_type != "expense":
            raise ValueError("장학금과 운영비는 출금으로 등록하세요.")
        return self


class FinanceTransactionUpdate(FinanceTransactionCreate):
    expected_version: int = Field(ge=1, strict=True)
    change_reason: str = Field(min_length=1, max_length=1000)
