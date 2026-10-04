"""Organization-level finance import and overview endpoints."""

import csv
import io
from datetime import date, datetime, time
from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, Query, status
from fastapi.responses import Response
from pydantic import ValidationError
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..database import get_db
from ..dependencies import require_roles
from ..models import FinanceTransaction, User
from ..schemas import FinanceOverviewResponse, FinanceTransactionResponse, FinanceTransactionCreate


from ..services.ledger import CATEGORY_LABELS, filters, list_transactions, period_report


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
    content = await file.read(5 * 1024 * 1024 + 1)
    if len(content) > 5 * 1024 * 1024:
        raise HTTPException(413, "CSV는 5MB 이하만 지원합니다.")
    try:
        decoded = content.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="UTF-8 CSV 파일만 지원합니다. BOM 제거 및 텍스트 인코딩을 확인해 주세요.") from None

    reader = csv.DictReader(io.StringIO(decoded))
    fieldnames = [name.strip() if name is not None else name for name in (reader.fieldnames or [])]
    reader.fieldnames = fieldnames
    missing = [column for column in sorted(REQUIRED_COLUMNS) if column not in fieldnames]
    if not fieldnames or missing:
        missing_detail = ", ".join(missing) if missing else "알 수 없음"
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
            raise HTTPException(status_code=400, detail=f"{row_number}행 external_reference가 비어 있거나 중복입니다.")
        if transaction_type not in {"income", "expense"}:
            raise HTTPException(status_code=400, detail=f"{row_number}행 transaction_type이 올바르지 않습니다.")
        try:
            transaction_date = datetime.fromisoformat((row.get("transaction_date") or "").strip())
        except ValueError:
            raise HTTPException(status_code=400, detail=f"{row_number}행 transaction_date가 올바르지 않습니다.") from None
        counterparty = (row.get("counterparty") or "").strip()
        category = (row.get("category") or "general").strip()
        try:
            FinanceTransactionCreate(
                transaction_date=transaction_date.date(), transaction_type=transaction_type,
                amount=parse_amount(row.get("amount") or ""),
                counterparty=counterparty or "기존 내역 (미기재)",
                description=(row.get("description") or "").strip(), category=category,
                external_reference=reference,
            )
        except ValidationError:
            raise HTTPException(422, f"{row_number}행의 금액·거래처·분류·내용을 확인하세요.") from None
        references.add(reference)
        transactions.append(
            FinanceTransaction(
                id=uuid4().hex,
                transaction_date=transaction_date,
                transaction_type=transaction_type,
                amount=parse_amount(row.get("amount") or ""),
                description=(row.get("description") or "").strip(),
                external_reference=reference,
                counterparty=counterparty or None,
                category=category,
                source_filename=file.filename,
                created_by=current_user.id,
            )
        )
    if not transactions:
        raise HTTPException(status_code=400, detail="CSV에 거래내역이 없습니다.")
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

@router.post("/transactions", response_model=FinanceTransactionResponse, status_code=201)
def create_transaction(data: FinanceTransactionCreate, current_user: FinanceManager,
                       db: Annotated[Session, Depends(get_db)]):
    values = data.model_dump()
    values["transaction_date"] = datetime.combine(data.transaction_date, time.min)
    values["external_reference"] = data.external_reference or f"manual-{uuid4().hex}"
    transaction = FinanceTransaction(id=uuid4().hex, created_by=current_user.id, **values)
    db.add(transaction)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "이미 등록된 거래번호입니다.") from None
    return transaction


@router.get("/transactions")
def transaction_list(_: FinanceManager, db: Annotated[Session, Depends(get_db)],
                     start: date | None = None, end: date | None = None,
                     transaction_type: str | None = Query(None, pattern="^(income|expense)$"),
                     category: str | None = Query(None, pattern="^(general|donation|interest|carryover|scholarship|operating|other)$"),
                     q: str | None = Query(None, max_length=200),
                     page: int = Query(1, ge=1), size: int = Query(50, ge=1, le=100)):
    result = list_transactions(db, start=start, end=end, transaction_type=transaction_type,
                               category=category, q=q, page=page, size=size)
    result["items"] = [FinanceTransactionResponse.model_validate(item) for item in result["items"]]
    return result


@router.get("/reports")
def report(_: FinanceManager, db: Annotated[Session, Depends(get_db)],
           start: date | None = None, end: date | None = None):
    return period_report(db, start, end)


def csv_cell(value):
    # Prevent spreadsheet formulas in user-provided names and descriptions.
    value = str(value or "")
    return "'" + value if value.lstrip().startswith(("=", "+", "-", "@")) or value.startswith(("\t", "\r", "\n")) else value


@router.get("/reports/export")
def export_report(_: FinanceManager, db: Annotated[Session, Depends(get_db)],
                  start: date | None = None, end: date | None = None):
    summary = period_report(db, start, end)
    output = io.StringIO(newline="")
    writer = csv.writer(output)
    writer.writerow(["거래내역 보고서", str(start or "전체"), str(end or "전체")])
    for key, label in [("opening_balance", "기초 잔액"), ("carryover", "기간 내 이월금"),
                       ("total_income", "입금 합계 (이월금 제외)"), ("interest", "이자 (입금에 포함)"),
                       ("total_expense", "출금 합계 (이월금 제외)"), ("closing_balance", "기말 잔액")]:
        writer.writerow([label, summary[key]])
    for key, label in [("recipients", "출금 대상별"), ("sources", "입금처별")]:
        writer.writerow([])
        writer.writerow([label, "금액"])
        for group in summary[key]:
            writer.writerow([csv_cell(group["name"]), group["amount"]])
    writer.writerow([])
    writer.writerow(["거래일", "입출금", "분류", "이름 / 입금처", "금액", "내용 / 출금 사유", "거래번호"])
    for item in db.scalars(select(FinanceTransaction).where(*filters(start, end)).order_by(
        FinanceTransaction.transaction_date, FinanceTransaction.created_at, FinanceTransaction.id
    )).yield_per(500):
        writer.writerow([item.transaction_date.date().isoformat(), "입금" if item.transaction_type == "income" else "출금",
                         CATEGORY_LABELS.get(item.category, item.category), csv_cell(item.counterparty), item.amount,
                         csv_cell(item.description), csv_cell(item.external_reference)])
    return Response(content="\ufeff" + output.getvalue(), media_type="text/csv; charset=utf-8",
                    headers={"Content-Disposition": 'attachment; filename="finance-report.csv"'})


@router.get("/template")
def csv_template(_: FinanceManager):
    example = "transaction_date,transaction_type,amount,counterparty,category,description,external_reference\n2026-10-01,income,1000,은행,interest,예금 이자,example-interest-001\n2026-10-02,expense,50000,홍길동,scholarship,10월 장학금,example-expense-001\n"
    return Response("\ufeff" + example, media_type="text/csv; charset=utf-8",
                    headers={"Content-Disposition": 'attachment; filename="finance-template.csv"'})
