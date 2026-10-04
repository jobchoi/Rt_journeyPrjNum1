"""Selection decisions and scholarship disbursement endpoints."""

from datetime import UTC, datetime
from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..database import get_db
from ..dependencies import require_roles
from ..models import Application, FinanceTransaction, Payment, Selection, User
from ..schemas import PaymentCreate, PaymentResponse, SelectionCreate, SelectionResponse


router = APIRouter(prefix="/api", tags=["selection"])
Manager = Annotated[User, Depends(require_roles("administrator", "program_manager"))]
FinanceManager = Annotated[
    User, Depends(require_roles("administrator", "program_manager", "finance"))
]


@router.post("/selections", response_model=SelectionResponse, status_code=status.HTTP_201_CREATED)
def decide_selection(
    request: SelectionCreate,
    current_user: Manager,
    db: Annotated[Session, Depends(get_db)],
) -> Selection:
    application = db.get(Application, request.application_id)
    if application is None:
        raise HTTPException(status_code=404, detail="신청서를 찾을 수 없습니다.")
    if request.status == "selected" and request.amount is None:
        raise HTTPException(status_code=422, detail="선발 시 지급 예정 금액이 필요합니다.")
    if db.scalar(select(Selection).where(Selection.application_id == application.id)):
        raise HTTPException(status_code=409, detail="이미 선발 결정된 신청서입니다.")
    selection = Selection(
        id=uuid4().hex,
        application_id=application.id,
        applicant_id=application.applicant_id,
        decided_by=current_user.id,
        **request.model_dump(exclude={"application_id"}),
    )
    application.status = request.status
    db.add(selection)
    db.commit()
    db.refresh(selection)
    return selection


@router.get("/selections", response_model=list[SelectionResponse])
def list_selections(
    _: Manager,
    db: Annotated[Session, Depends(get_db)],
) -> list[Selection]:
    return list(db.scalars(select(Selection).order_by(Selection.decided_at.desc())))


@router.post(
    "/selections/{selection_id}/payments",
    response_model=PaymentResponse,
    status_code=status.HTTP_201_CREATED,
)
def record_payment(
    selection_id: str,
    request: PaymentCreate,
    current_user: FinanceManager,
    db: Annotated[Session, Depends(get_db)],
) -> Payment:
    selection = db.get(Selection, selection_id)
    if selection is None or selection.status != "selected":
        raise HTTPException(status_code=404, detail="선발된 대상을 찾을 수 없습니다.")
    paid_total = db.scalar(
        select(func.coalesce(func.sum(Payment.amount), 0)).where(
            Payment.selection_id == selection.id,
            Payment.status == "paid",
        )
    ) or 0
    if selection.amount is not None and paid_total + request.amount > selection.amount:
        raise HTTPException(status_code=422, detail="지급 누계가 선발 금액을 초과합니다.")
    transaction = FinanceTransaction(
        id=uuid4().hex,
        transaction_date=datetime.now(UTC),
        transaction_type="expense",
        amount=request.amount,
        description=f"장학금 지급: {selection.id}",
        counterparty=db.get(User, selection.applicant_id).name,
        category="scholarship",
        external_reference=request.external_reference,
        created_by=current_user.id,
    )
    payment = Payment(
        id=uuid4().hex,
        selection_id=selection.id,
        finance_transaction_id=transaction.id,
        status="paid",
        **request.model_dump(),
    )
    db.add_all([transaction, payment])
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="이미 사용된 지급 거래번호입니다.") from None
    db.refresh(payment)
    return payment