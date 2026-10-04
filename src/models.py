"""SQLAlchemy models for the initial authentication and program schema."""

from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, String, Table, Column, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.sql import func


class Base(DeclarativeBase):
    pass


user_roles = Table(
    "user_roles",
    Base.metadata,
    Column("user_id", String, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
    Column("role_id", String, ForeignKey("roles.id", ondelete="RESTRICT"), primary_key=True),
    Column("created_at", DateTime, server_default=func.current_timestamp(), nullable=False),
)


class Role(Base):
    __tablename__ = "roles"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    code: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str | None] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.current_timestamp(), nullable=False
    )
    users: Mapped[list["User"]] = relationship(
        secondary=user_roles, back_populates="roles"
    )


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    email: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(
        String, default="active", server_default="active", nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.current_timestamp(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
        nullable=False,
    )
    roles: Mapped[list[Role]] = relationship(
        secondary=user_roles, back_populates="users"
    )
    programs_created: Mapped[list["ScholarshipProgram"]] = relationship(
        back_populates="creator", foreign_keys="ScholarshipProgram.created_by"
    )
    announcements_created: Mapped[list["Announcement"]] = relationship(
        back_populates="creator", foreign_keys="Announcement.created_by"
    )
    applications: Mapped[list["Application"]] = relationship(
        back_populates="applicant", foreign_keys="Application.applicant_id"
    )
    followups: Mapped[list["Followup"]] = relationship(
        back_populates="applicant", foreign_keys="Followup.applicant_id"
    )
    finance_transactions: Mapped[list["FinanceTransaction"]] = relationship(
        back_populates="created_by_user", foreign_keys="FinanceTransaction.created_by"
    )
    selections: Mapped[list["Selection"]] = relationship(
        back_populates="applicant", foreign_keys="Selection.applicant_id"
    )
    application_documents: Mapped[list["ApplicationDocument"]] = relationship(
        back_populates="applicant", foreign_keys="ApplicationDocument.applicant_id"
    )
    followup_documents: Mapped[list["FollowupDocument"]] = relationship(
        back_populates="applicant", foreign_keys="FollowupDocument.applicant_id"
    )
    review_assignments: Mapped[list["ReviewAssignment"]] = relationship(
        back_populates="reviewer", foreign_keys="ReviewAssignment.reviewer_id"
    )
    prayer_requests: Mapped[list["PrayerRequest"]] = relationship(
        back_populates="user", foreign_keys="PrayerRequest.user_id"
    )


class ScholarshipProgram(Base):
    __tablename__ = "scholarship_programs"
    __table_args__ = (
        CheckConstraint(
            "status IN ('draft', 'active', 'closed')",
            name="ck_program_status",
        ),
        CheckConstraint(
            "application_start_at IS NULL OR application_end_at IS NULL "
            "OR application_start_at <= application_end_at",
            name="ck_program_application_dates",
        ),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str | None] = mapped_column(String)
    status: Mapped[str] = mapped_column(
        String, default="draft", server_default="draft", nullable=False
    )
    application_start_at: Mapped[datetime | None] = mapped_column(DateTime)
    application_end_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_by: Mapped[str] = mapped_column(
        String, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.current_timestamp(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
        nullable=False,
    )
    creator: Mapped[User] = relationship(
        back_populates="programs_created", foreign_keys=[created_by]
    )
    announcements: Mapped[list["Announcement"]] = relationship(
        back_populates="program", cascade="all, delete-orphan"
    )


class FundCategory(Base):
    __tablename__ = "fund_categories"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    code: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    category_type: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.current_timestamp(), nullable=False
    )
    announcements: Mapped[list["Announcement"]] = relationship(
        back_populates="fund_category"
    )


class Announcement(Base):
    __tablename__ = "announcements"
    __table_args__ = (
        CheckConstraint(
            "status IN ('draft', 'open', 'closed', 'reviewing', 'finished')",
            name="ck_announcement_status",
        ),
        CheckConstraint(
            "selected_count IS NULL OR selected_count >= 0",
            name="ck_announcement_selected_count",
        ),
        CheckConstraint(
            "application_start_at IS NULL OR application_end_at IS NULL "
            "OR application_start_at <= application_end_at",
            name="ck_announcement_application_dates",
        ),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    program_id: Mapped[str] = mapped_column(
        String, ForeignKey("scholarship_programs.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str] = mapped_column(String, nullable=False)
    target_description: Mapped[str | None] = mapped_column(String)
    selected_count: Mapped[int | None] = mapped_column(Integer)
    payment_description: Mapped[str | None] = mapped_column(String)
    status: Mapped[str] = mapped_column(
        String, default="draft", server_default="draft", nullable=False
    )
    fund_category_id: Mapped[str | None] = mapped_column(
        String, ForeignKey("fund_categories.id", ondelete="SET NULL")
    )
    published_at: Mapped[datetime | None] = mapped_column(DateTime)
    application_start_at: Mapped[datetime | None] = mapped_column(DateTime)
    application_end_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_by: Mapped[str] = mapped_column(
        String, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.current_timestamp(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
        nullable=False,
    )
    program: Mapped[ScholarshipProgram] = relationship(back_populates="announcements")
    fund_category: Mapped[FundCategory | None] = relationship(
        back_populates="announcements"
    )
    creator: Mapped[User] = relationship(
        back_populates="announcements_created", foreign_keys=[created_by]
    )
    applications: Mapped[list["Application"]] = relationship(back_populates="announcement")
    review_criteria: Mapped[list["ReviewCriterion"]] = relationship(
        back_populates="announcement", cascade="all, delete-orphan"
    )


class Application(Base):
    __tablename__ = "applications"
    __table_args__ = (
        UniqueConstraint("applicant_id", "announcement_id", name="uq_application_applicant_announcement"),
        CheckConstraint(
            "status IN ('draft', 'submitted', 'under_review', 'selected', 'rejected', 'withdrawn')",
            name="ck_application_status",
        ),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    applicant_id: Mapped[str] = mapped_column(
        String, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    announcement_id: Mapped[str] = mapped_column(
        String, ForeignKey("announcements.id", ondelete="RESTRICT"), nullable=False
    )
    status: Mapped[str] = mapped_column(
        String, default="submitted", server_default="submitted", nullable=False
    )
    study_plan: Mapped[str] = mapped_column(String, nullable=False)
    financial_need: Mapped[str] = mapped_column(String, nullable=False)
    ministry_plan: Mapped[str | None] = mapped_column(String)
    submitted_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.current_timestamp(), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.current_timestamp(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
        nullable=False,
    )
    applicant: Mapped[User] = relationship(
        back_populates="applications", foreign_keys=[applicant_id]
    )
    announcement: Mapped[Announcement] = relationship(back_populates="applications")
    followups: Mapped[list["Followup"]] = relationship(back_populates="application")
    documents: Mapped[list["ApplicationDocument"]] = relationship(
        back_populates="application", cascade="all, delete-orphan"
    )


class PrayerRequest(Base):
    __tablename__ = "prayer_requests"
    __table_args__ = (CheckConstraint("visibility = 'pastoral'", name="ck_pastoral_visibility"),)

    id: Mapped[str] = mapped_column(String, primary_key=True)
    user_id: Mapped[str] = mapped_column(
        String, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    content: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(
        String, default="active", server_default="active", nullable=False
    )
    visibility: Mapped[str] = mapped_column(
        String, default="pastoral", server_default="pastoral", nullable=False
    )
    retention_until: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.current_timestamp(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
        nullable=False,
    )
    user: Mapped[User] = relationship(back_populates="prayer_requests")
    access_logs: Mapped[list["PrayerRequestAccessLog"]] = relationship(
        back_populates="prayer_request"
    )


class PrayerRequestAccessLog(Base):
    __tablename__ = "prayer_request_access_logs"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    prayer_request_id: Mapped[str] = mapped_column(
        String, ForeignKey("prayer_requests.id", ondelete="RESTRICT"), nullable=False
    )
    user_id: Mapped[str] = mapped_column(
        String, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    purpose: Mapped[str] = mapped_column(String, nullable=False)
    accessed_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.current_timestamp(), nullable=False
    )
    prayer_request: Mapped[PrayerRequest] = relationship(back_populates="access_logs")


class ReviewCriterion(Base):
    __tablename__ = "review_criteria"
    __table_args__ = (
        UniqueConstraint("announcement_id", "code", name="uq_review_criterion_announcement_code"),
        CheckConstraint("max_score > 0", name="ck_review_criterion_max_score"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    announcement_id: Mapped[str] = mapped_column(
        String, ForeignKey("announcements.id", ondelete="CASCADE"), nullable=False
    )
    code: Mapped[str] = mapped_column(String, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    max_score: Mapped[int] = mapped_column(Integer, nullable=False)
    required: Mapped[bool] = mapped_column(default=True, server_default="1", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.current_timestamp(), nullable=False
    )
    announcement: Mapped[Announcement] = relationship(back_populates="review_criteria")
    reviews: Mapped[list["Review"]] = relationship(back_populates="criterion")


class ReviewAssignment(Base):
    __tablename__ = "review_assignments"
    __table_args__ = (
        UniqueConstraint("application_id", "reviewer_id", name="uq_review_assignment_application_reviewer"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    application_id: Mapped[str] = mapped_column(
        String, ForeignKey("applications.id", ondelete="CASCADE"), nullable=False
    )
    reviewer_id: Mapped[str] = mapped_column(
        String, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    recused_at: Mapped[datetime | None] = mapped_column(DateTime)
    recusal_reason: Mapped[str | None] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.current_timestamp(), nullable=False
    )
    application: Mapped[Application] = relationship()
    reviewer: Mapped[User] = relationship(
        back_populates="review_assignments", foreign_keys=[reviewer_id]
    )
    reviews: Mapped[list["Review"]] = relationship(
        back_populates="assignment", cascade="all, delete-orphan"
    )


class Review(Base):
    __tablename__ = "reviews"
    __table_args__ = (
        UniqueConstraint("assignment_id", "criterion_id", name="uq_review_assignment_criterion"),
        CheckConstraint("score >= 0", name="ck_review_score_nonnegative"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    assignment_id: Mapped[str] = mapped_column(
        String, ForeignKey("review_assignments.id", ondelete="CASCADE"), nullable=False
    )
    criterion_id: Mapped[str] = mapped_column(
        String, ForeignKey("review_criteria.id", ondelete="RESTRICT"), nullable=False
    )
    score: Mapped[int] = mapped_column(Integer, nullable=False)
    comment: Mapped[str | None] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.current_timestamp(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
        nullable=False,
    )
    assignment: Mapped[ReviewAssignment] = relationship(back_populates="reviews")
    criterion: Mapped[ReviewCriterion] = relationship(back_populates="reviews")


class Followup(Base):
    __tablename__ = "followups"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    application_id: Mapped[str] = mapped_column(
        String, ForeignKey("applications.id", ondelete="RESTRICT"), nullable=False
    )
    applicant_id: Mapped[str] = mapped_column(
        String, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    status: Mapped[str] = mapped_column(
        String, default="submitted", server_default="submitted", nullable=False
    )
    academic_update: Mapped[str] = mapped_column(String, nullable=False)
    ministry_update: Mapped[str] = mapped_column(String, nullable=False)
    evidence_note: Mapped[str | None] = mapped_column(String)
    submitted_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.current_timestamp(), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.current_timestamp(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
        nullable=False,
    )
    application: Mapped[Application] = relationship(back_populates="followups")
    applicant: Mapped[User] = relationship(
        back_populates="followups", foreign_keys=[applicant_id]
    )
    documents: Mapped[list["FollowupDocument"]] = relationship(
        back_populates="followup", cascade="all, delete-orphan"
    )


class FinanceTransaction(Base):
    __tablename__ = "finance_transactions"
    __table_args__ = (
        UniqueConstraint("external_reference", name="uq_finance_transaction_external_reference"),
        CheckConstraint("transaction_type IN ('income', 'expense')", name="ck_finance_transaction_type"),
        CheckConstraint("amount > 0", name="ck_finance_transaction_amount"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    transaction_date: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    transaction_type: Mapped[str] = mapped_column(String, nullable=False)
    amount: Mapped[int] = mapped_column(Integer, nullable=False)
    description: Mapped[str] = mapped_column(String, nullable=False)
    external_reference: Mapped[str] = mapped_column(String, nullable=False)
    counterparty: Mapped[str | None] = mapped_column(String(200))
    category: Mapped[str] = mapped_column(String(50), nullable=False, default="general", server_default="general")
    source_filename: Mapped[str | None] = mapped_column(String)
    created_by: Mapped[str] = mapped_column(
        String, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.current_timestamp(), nullable=False
    )
    created_by_user: Mapped[User] = relationship(
        back_populates="finance_transactions", foreign_keys=[created_by]
    )


class Selection(Base):
    __tablename__ = "selections"
    __table_args__ = (
        UniqueConstraint("application_id", name="uq_selection_application"),
        CheckConstraint("status IN ('selected', 'rejected')", name="ck_selection_status"),
        CheckConstraint("amount IS NULL OR amount > 0", name="ck_selection_amount"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    application_id: Mapped[str] = mapped_column(
        String, ForeignKey("applications.id", ondelete="RESTRICT"), nullable=False
    )
    applicant_id: Mapped[str] = mapped_column(
        String, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    status: Mapped[str] = mapped_column(String, nullable=False)
    amount: Mapped[int | None] = mapped_column(Integer)
    decided_by: Mapped[str] = mapped_column(
        String, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    decided_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.current_timestamp(), nullable=False
    )
    application: Mapped[Application] = relationship()
    applicant: Mapped[User] = relationship(
        back_populates="selections", foreign_keys=[applicant_id]
    )
    payments: Mapped[list["Payment"]] = relationship(
        back_populates="selection", cascade="all, delete-orphan"
    )


class Payment(Base):
    __tablename__ = "payments"
    __table_args__ = (
        UniqueConstraint("external_reference", name="uq_payment_external_reference"),
        CheckConstraint("amount > 0", name="ck_payment_amount"),
        CheckConstraint("status IN ('planned', 'paid', 'failed')", name="ck_payment_status"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    selection_id: Mapped[str] = mapped_column(
        String, ForeignKey("selections.id", ondelete="RESTRICT"), nullable=False
    )
    amount: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String, default="paid", server_default="paid", nullable=False)
    payment_method: Mapped[str] = mapped_column(String, nullable=False)
    external_reference: Mapped[str] = mapped_column(String, nullable=False)
    paid_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.current_timestamp(), nullable=False
    )
    finance_transaction_id: Mapped[str] = mapped_column(
        String, ForeignKey("finance_transactions.id", ondelete="RESTRICT"), nullable=False
    )
    selection: Mapped[Selection] = relationship(back_populates="payments")


class ApplicationDocument(Base):
    __tablename__ = "application_documents"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    application_id: Mapped[str] = mapped_column(
        String, ForeignKey("applications.id", ondelete="CASCADE"), nullable=False
    )
    applicant_id: Mapped[str] = mapped_column(
        String, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    document_type: Mapped[str] = mapped_column(String, nullable=False)
    original_filename: Mapped[str] = mapped_column(String, nullable=False)
    stored_filename: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    content_type: Mapped[str] = mapped_column(String, nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.current_timestamp(), nullable=False
    )
    application: Mapped[Application] = relationship(back_populates="documents")
    applicant: Mapped[User] = relationship(
        back_populates="application_documents", foreign_keys=[applicant_id]
    )


class FollowupDocument(Base):
    __tablename__ = "followup_documents"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    followup_id: Mapped[str] = mapped_column(
        String, ForeignKey("followups.id", ondelete="CASCADE"), nullable=False
    )
    applicant_id: Mapped[str] = mapped_column(
        String, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    document_type: Mapped[str] = mapped_column(String, nullable=False)
    original_filename: Mapped[str] = mapped_column(String, nullable=False)
    stored_filename: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    content_type: Mapped[str] = mapped_column(String, nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.current_timestamp(), nullable=False
    )
    followup: Mapped[Followup] = relationship(back_populates="documents")
    applicant: Mapped[User] = relationship(
        back_populates="followup_documents", foreign_keys=[applicant_id]
    )