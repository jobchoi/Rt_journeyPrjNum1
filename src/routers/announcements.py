"""Scholarship announcement CRUD endpoints."""

from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..dependencies import get_current_user, require_roles
from ..models import Announcement, FundCategory, ScholarshipProgram, User
from ..program_schemas import (
    AnnouncementCreate,
    AnnouncementResponse,
    AnnouncementUpdate,
)


router = APIRouter(prefix="/api/announcements", tags=["announcements"])
Manager = Annotated[User, Depends(require_roles("administrator", "program_manager"))]
AuthenticatedUser = Annotated[User, Depends(get_current_user)]


def ensure_references(
    request: AnnouncementCreate | AnnouncementUpdate,
    db: Session,
) -> None:
    program_id = getattr(request, "program_id", None)
    if program_id is not None and db.get(ScholarshipProgram, program_id) is None:
        raise HTTPException(status_code=400, detail="존재하지 않는 장학 사업입니다.")
    if (
        request.fund_category_id is not None
        and db.get(FundCategory, request.fund_category_id) is None
    ):
        raise HTTPException(status_code=400, detail="존재하지 않는 후원 카테고리입니다.")


@router.get("", response_model=list[AnnouncementResponse])
def list_announcements(
    _: AuthenticatedUser,
    db: Annotated[Session, Depends(get_db)],
) -> list[Announcement]:
    return list(db.scalars(select(Announcement).order_by(Announcement.created_at.desc())))


@router.post("", response_model=AnnouncementResponse, status_code=status.HTTP_201_CREATED)
def create_announcement(
    request: AnnouncementCreate,
    current_user: Manager,
    db: Annotated[Session, Depends(get_db)],
) -> Announcement:
    ensure_references(request, db)
    announcement = Announcement(
        id=uuid4().hex,
        created_by=current_user.id,
        **request.model_dump(),
    )
    db.add(announcement)
    db.commit()
    db.refresh(announcement)
    return announcement


@router.get("/{announcement_id}", response_model=AnnouncementResponse)
def get_announcement(
    announcement_id: str,
    _: AuthenticatedUser,
    db: Annotated[Session, Depends(get_db)],
) -> Announcement:
    announcement = db.get(Announcement, announcement_id)
    if announcement is None:
        raise HTTPException(status_code=404, detail="장학 공고를 찾을 수 없습니다.")
    return announcement


@router.patch("/{announcement_id}", response_model=AnnouncementResponse)
def update_announcement(
    announcement_id: str,
    request: AnnouncementUpdate,
    _: Manager,
    db: Annotated[Session, Depends(get_db)],
) -> Announcement:
    announcement = db.get(Announcement, announcement_id)
    if announcement is None:
        raise HTTPException(status_code=404, detail="장학 공고를 찾을 수 없습니다.")
    ensure_references(request, db)
    for field, value in request.model_dump(exclude_unset=True).items():
        setattr(announcement, field, value)
    db.commit()
    db.refresh(announcement)
    return announcement


@router.delete("/{announcement_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_announcement(
    announcement_id: str,
    _: Manager,
    db: Annotated[Session, Depends(get_db)],
) -> None:
    announcement = db.get(Announcement, announcement_id)
    if announcement is None:
        raise HTTPException(status_code=404, detail="장학 공고를 찾을 수 없습니다.")
    db.delete(announcement)
    db.commit()