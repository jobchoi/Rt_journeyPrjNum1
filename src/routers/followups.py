"""Applicant follow-up reporting endpoints."""

from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..dependencies import require_roles
from ..models import Application, Followup, User
from ..schemas import FollowupCreate, FollowupResponse


router = APIRouter(prefix="/api/followups", tags=["followups"])
Applicant = Annotated[User, Depends(require_roles("applicant"))]


@router.post("", response_model=FollowupResponse, status_code=status.HTTP_201_CREATED)
def create_followup(
    request: FollowupCreate,
    current_user: Applicant,
    db: Annotated[Session, Depends(get_db)],
) -> Followup:
    application = db.scalar(
        select(Application).where(
            Application.id == request.application_id,
            Application.applicant_id == current_user.id,
        )
    )
    if application is None:
        raise HTTPException(status_code=404, detail="본인의 신청서를 찾을 수 없습니다.")
    if application.status != "selected":
        raise HTTPException(status_code=400, detail="선발된 신청서만 사후보고를 제출할 수 있습니다.")
    followup = Followup(
        id=uuid4().hex,
        applicant_id=current_user.id,
        **request.model_dump(),
    )
    db.add(followup)
    db.commit()
    db.refresh(followup)
    return followup


@router.get("/me", response_model=list[FollowupResponse])
def list_my_followups(
    current_user: Applicant,
    db: Annotated[Session, Depends(get_db)],
) -> list[Followup]:
    return list(
        db.scalars(
            select(Followup)
            .where(Followup.applicant_id == current_user.id)
            .order_by(Followup.created_at.desc())
        )
    )