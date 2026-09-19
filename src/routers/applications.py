"""Scholarship application endpoints for applicants."""

from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..database import get_db
from ..dependencies import require_roles
from ..models import Announcement, Application, User
from ..schemas import ApplicationCreate, ApplicationResponse


router = APIRouter(prefix="/api/applications", tags=["applications"])
Applicant = Annotated[User, Depends(require_roles("applicant"))]


@router.post("", response_model=ApplicationResponse, status_code=status.HTTP_201_CREATED)
def submit_application(
    request: ApplicationCreate,
    current_user: Applicant,
    db: Annotated[Session, Depends(get_db)],
) -> Application:
    announcement = db.get(Announcement, request.announcement_id)
    if announcement is None:
        raise HTTPException(status_code=404, detail="장학 공고를 찾을 수 없습니다.")
    if announcement.status != "open":
        raise HTTPException(status_code=400, detail="현재 신청할 수 없는 공고입니다.")

    application = Application(
        id=uuid4().hex,
        applicant_id=current_user.id,
        **request.model_dump(),
    )
    db.add(application)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="해당 공고에는 이미 신청서를 제출했습니다.",
        ) from None
    db.refresh(application)
    return application


@router.get("/me", response_model=list[ApplicationResponse])
def list_my_applications(
    current_user: Applicant,
    db: Annotated[Session, Depends(get_db)],
) -> list[Application]:
    return list(
        db.scalars(
            select(Application)
            .where(Application.applicant_id == current_user.id)
            .order_by(Application.created_at.desc())
        )
    )