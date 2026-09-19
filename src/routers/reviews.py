"""Review criteria, reviewer assignments, and scoring endpoints."""

from datetime import UTC, datetime
from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from ..database import get_db
from ..dependencies import get_current_user, require_roles
from ..models import (
    Announcement,
    Application,
    Review,
    ReviewAssignment,
    ReviewCriterion,
    Role,
    User,
)
from ..schemas import (
    ReviewAssignmentCreate,
    ReviewAssignmentResponse,
    ReviewCriterionCreate,
    ReviewCriterionResponse,
    ReviewSubmit,
)


router = APIRouter(prefix="/api", tags=["reviews"])
Manager = Annotated[User, Depends(require_roles("administrator", "program_manager"))]
Reviewer = Annotated[User, Depends(require_roles("reviewer"))]


def assignment_response(assignment: ReviewAssignment) -> ReviewAssignmentResponse:
    return ReviewAssignmentResponse(
        id=assignment.id,
        application_id=assignment.application_id,
        reviewer_id=assignment.reviewer_id,
        recused_at=assignment.recused_at,
        recusal_reason=assignment.recusal_reason,
        total_score=sum(review.score for review in assignment.reviews),
        review_count=len(assignment.reviews),
    )


@router.post(
    "/review-criteria",
    response_model=ReviewCriterionResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_review_criterion(
    request: ReviewCriterionCreate,
    _: Manager,
    db: Annotated[Session, Depends(get_db)],
) -> ReviewCriterion:
    if db.get(Announcement, request.announcement_id) is None:
        raise HTTPException(status_code=404, detail="장학 공고를 찾을 수 없습니다.")
    criterion = ReviewCriterion(id=uuid4().hex, **request.model_dump())
    db.add(criterion)
    db.commit()
    db.refresh(criterion)
    return criterion


@router.get(
    "/review-criteria/{announcement_id}",
    response_model=list[ReviewCriterionResponse],
)
def list_review_criteria(
    announcement_id: str,
    _: Manager,
    db: Annotated[Session, Depends(get_db)],
) -> list[ReviewCriterion]:
    return list(
        db.scalars(
            select(ReviewCriterion)
            .where(ReviewCriterion.announcement_id == announcement_id)
            .order_by(ReviewCriterion.created_at)
        )
    )


@router.post(
    "/review-assignments",
    response_model=ReviewAssignmentResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_review_assignment(
    request: ReviewAssignmentCreate,
    _: Manager,
    db: Annotated[Session, Depends(get_db)],
) -> ReviewAssignmentResponse:
    application = db.get(Application, request.application_id)
    if application is None:
        raise HTTPException(status_code=404, detail="신청서를 찾을 수 없습니다.")
    reviewer = db.scalar(
        select(User)
        .join(User.roles)
        .where(User.id == request.reviewer_id, Role.code == "reviewer")
    )
    if reviewer is None:
        raise HTTPException(status_code=400, detail="유효한 심사위원이 아닙니다.")
    assignment = ReviewAssignment(id=uuid4().hex, **request.model_dump())
    db.add(assignment)
    db.commit()
    db.refresh(assignment)
    return assignment_response(assignment)


@router.get("/review-assignments/me", response_model=list[ReviewAssignmentResponse])
def list_my_assignments(
    current_user: Reviewer,
    db: Annotated[Session, Depends(get_db)],
) -> list[ReviewAssignmentResponse]:
    assignments = list(
        db.scalars(
            select(ReviewAssignment)
            .options(selectinload(ReviewAssignment.reviews))
            .where(ReviewAssignment.reviewer_id == current_user.id)
            .order_by(ReviewAssignment.created_at.desc())
        )
    )
    return [assignment_response(assignment) for assignment in assignments]


@router.post("/review-assignments/{assignment_id}/recusal", response_model=ReviewAssignmentResponse)
def recuse_from_assignment(
    assignment_id: str,
    reason: str,
    current_user: Reviewer,
    db: Annotated[Session, Depends(get_db)],
) -> ReviewAssignmentResponse:
    assignment = db.scalar(
        select(ReviewAssignment)
        .options(selectinload(ReviewAssignment.reviews))
        .where(
            ReviewAssignment.id == assignment_id,
            ReviewAssignment.reviewer_id == current_user.id,
        )
    )
    if assignment is None:
        raise HTTPException(status_code=404, detail="본인에게 배정된 심사 건이 아닙니다.")
    if not reason.strip():
        raise HTTPException(status_code=400, detail="회피 사유를 입력해야 합니다.")
    assignment.recused_at = datetime.now(UTC)
    assignment.recusal_reason = reason.strip()
    db.commit()
    db.refresh(assignment)
    return assignment_response(assignment)


@router.put("/review-assignments/{assignment_id}/review", response_model=ReviewAssignmentResponse)
def submit_review(
    assignment_id: str,
    request: ReviewSubmit,
    current_user: Reviewer,
    db: Annotated[Session, Depends(get_db)],
) -> ReviewAssignmentResponse:
    assignment = db.scalar(
        select(ReviewAssignment)
        .options(selectinload(ReviewAssignment.reviews))
        .where(
            ReviewAssignment.id == assignment_id,
            ReviewAssignment.reviewer_id == current_user.id,
        )
    )
    if assignment is None:
        raise HTTPException(status_code=404, detail="본인에게 배정된 심사 건이 아닙니다.")
    if assignment.recused_at is not None:
        raise HTTPException(status_code=400, detail="회피한 심사 건은 평가할 수 없습니다.")
    criterion_ids = {
        criterion.id
        for criterion in db.scalars(
            select(ReviewCriterion).where(
                ReviewCriterion.announcement_id == assignment.application.announcement_id
            )
        )
    }
    if len({score.criterion_id for score in request.scores}) != len(request.scores):
        raise HTTPException(status_code=400, detail="평가 기준을 중복 제출할 수 없습니다.")
    if not {score.criterion_id for score in request.scores} <= criterion_ids:
        raise HTTPException(status_code=400, detail="해당 공고의 평가 기준이 아닙니다.")
    criteria = {
        criterion.id: criterion
        for criterion in db.scalars(
            select(ReviewCriterion).where(ReviewCriterion.id.in_(criterion_ids))
        )
    }
    existing = {review.criterion_id: review for review in assignment.reviews}
    for score_input in request.scores:
        criterion = criteria[score_input.criterion_id]
        if score_input.score > criterion.max_score:
            raise HTTPException(
                status_code=422,
                detail=f"{criterion.name} 점수는 {criterion.max_score} 이하이어야 합니다.",
            )
        review = existing.get(score_input.criterion_id)
        if review is None:
            review = Review(
                id=uuid4().hex,
                assignment_id=assignment.id,
                criterion_id=criterion.id,
            )
            db.add(review)
        review.score = score_input.score
        review.comment = score_input.comment
    db.commit()
    db.refresh(assignment)
    return assignment_response(assignment)