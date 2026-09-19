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