"""Organization-level finance import and overview endpoints."""

import csv
import io
from datetime import datetime
from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..database import get_db
from ..dependencies import require_roles
from ..models import FinanceTransaction, User
from ..schemas import FinanceOverviewResponse, FinanceTransactionResponse


router = APIRouter(prefix="/api/finance", tags=["finance"])
FinanceManager = Annotated[
    User, Depends(require_roles("administrator", "program_manager", "finance"))
]
REQUIRED_COLUMNS = {
    "transaction_date",
    "transaction_type",
    "amount",
    "description",
    "external_reference",
}


def parse_amount(value: str) -> int:
    try:
        amount = int(value.replace(",", "").strip())
    except ValueError:
        raise HTTPException(status_code=422, detail="amount는 정수여야 합니다.") from None
    if amount <= 0:
        raise HTTPException(status_code=422, detail="amount는 0보다 커야 합니다.")
    return amount


@router.post(
    "/transactions/import",
    response_model=list[FinanceTransactionResponse],
    status_code=status.HTTP_201_CREATED,
)
async def import_transactions(
    current_user: FinanceManager,
    db: Annotated[Session, Depends(get_db)],
    file: UploadFile = File(...),
) -> list[FinanceTransaction]:
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=415, detail="CSV 파일만 업로드할 수 있습니다.")
    content = await file.read()
    try:
        decoded = content.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise HTTPException(status_code=422, detail="UTF-8 CSV 파일만 지원합니다.") from None

    reader = csv.DictReader(io.StringIO(decoded))
    fieldnames = [name.strip() if name is not None else name for name in (reader.fieldnames or [])]
    missing = [column for column in sorted(REQUIRED_COLUMNS) if column not in fieldnames]
    if not fieldnames or missing:
        missing_detail = ", ".join(missing)
        raise HTTPException(
            status_code=400,
            detail=f"필수 컬럼이 누락되었습니다: {missing_detail}",
        )

    transactions: list[FinanceTransaction] = []
    references: set[str] = set()
    for row_number, row in enumerate(reader, start=2):
        reference = (row.get("external_reference") or "").strip()
        transaction_type = (row.get("transaction_type") or "").strip().lower()
        if not reference or reference in references:
            raise HTTPException(status_code=422, detail=f"{row_number}행 external_reference가 중복 또는 비어 있습니다.")
        if transaction_type not in {"income", "expense"}:
            raise HTTPException(status_code=422, detail=f"{row_number}행 transaction_type이 올바르지 않습니다.")
        try:
            transaction_date = datetime.fromisoformat((row.get("transaction_date") or "").strip())
        except ValueError:
            raise HTTPException(status_code=422, detail=f"{row_number}행 transaction_date가 올바르지 않습니다.") from None
        references.add(reference)
        transactions.append(
            FinanceTransaction(
                id=uuid4().hex,
                transaction_date=transaction_date,
                transaction_type=transaction_type,
                amount=parse_amount(row.get("amount") or ""),
                description=(row.get("description") or "").strip(),
                external_reference=reference,
                source_filename=file.filename,
                created_by=current_user.id,
            )
        )
    if not transactions:
        raise HTTPException(status_code=422, detail="CSV에 거래내역이 없습니다.")
    existing = set(
        db.scalars(
            select(FinanceTransaction.external_reference).where(
                FinanceTransaction.external_reference.in_(references)
            )
        )
    )
    if existing:
        raise HTTPException(status_code=409, detail="이미 등록된 external_reference가 포함되어 있습니다.")
    db.add_all(transactions)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="중복 거래번호로 저장할 수 없습니다.") from None
    return transactions


@router.get("/overview", response_model=FinanceOverviewResponse)
def finance_overview(
    _: FinanceManager,
    db: Annotated[Session, Depends(get_db)],
) -> FinanceOverviewResponse:
    income = db.scalar(
        select(func.coalesce(func.sum(FinanceTransaction.amount), 0)).where(
            FinanceTransaction.transaction_type == "income"
        )
    )
    expense = db.scalar(
        select(func.coalesce(func.sum(FinanceTransaction.amount), 0)).where(
            FinanceTransaction.transaction_type == "expense"
        )
    )
    count = db.scalar(select(func.count(FinanceTransaction.id))) or 0
    return FinanceOverviewResponse(
        total_income=int(income or 0),
        total_expense=int(expense or 0),
        balance=int(income or 0) - int(expense or 0),
        transaction_count=int(count),
    )