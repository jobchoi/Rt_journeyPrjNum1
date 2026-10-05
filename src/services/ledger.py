"""Ledger queries and period accounting; closing reports never create transactions."""
from datetime import date, datetime, time, timedelta

from fastapi import HTTPException
from sqlalchemy import case, extract, func, or_, select
from sqlalchemy.orm import Session

from ..models import FinanceTransaction as Transaction

CATEGORY_LABELS = {
    "general": "일반", "donation": "후원금", "interest": "이자",
    "carryover": "이월금", "scholarship": "장학금", "operating": "운영비", "other": "기타",
}


def bounds(start: date | None, end: date | None):
    if start and end and start > end:
        raise HTTPException(422, "시작일은 종료일보다 늦을 수 없습니다.")
    if end == date.max:
        raise HTTPException(422, "종료일은 9999-12-31 이전이어야 합니다.")
    return (datetime.combine(start, time.min) if start else None,
            datetime.combine(end + timedelta(days=1), time.min) if end else None)


def filters(start=None, end=None, transaction_type=None, category=None, q=None):
    lower, upper = bounds(start, end)
    conditions = []
    if lower:
        conditions.append(Transaction.transaction_date >= lower)
    if upper:
        conditions.append(Transaction.transaction_date < upper)
    if transaction_type:
        conditions.append(Transaction.transaction_type == transaction_type)
    if category:
        conditions.append(Transaction.category == category)
    if q:
        pattern = "%" + q.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"
        conditions.append(or_(Transaction.counterparty.ilike(pattern, escape="\\"), Transaction.description.ilike(pattern, escape="\\")))
    return conditions


def list_transactions(db: Session, *, page=1, size=50, **kwargs):
    conditions = filters(**kwargs)
    total = db.scalar(select(func.count(Transaction.id)).where(*conditions)) or 0
    items = list(db.scalars(select(Transaction).where(*conditions).order_by(
        Transaction.transaction_date.desc(), Transaction.created_at.desc(), Transaction.id.desc()
    ).offset((page - 1) * size).limit(size)))
    return {"items": items, "page": page, "size": size, "total": total}


def period_report(db: Session, start=None, end=None):
    lower, _ = bounds(start, end)
    signed = case((Transaction.transaction_type == "income", Transaction.amount), else_=-Transaction.amount)
    opening = int(db.scalar(select(func.coalesce(func.sum(signed), 0)).where(Transaction.transaction_date < lower)) or 0) if lower else 0
    conditions = filters(start, end)
    income, expense, carryover, interest, count = db.execute(select(
        func.coalesce(func.sum(case(((Transaction.transaction_type == "income") & (Transaction.category != "carryover"), Transaction.amount), else_=0)), 0),
        func.coalesce(func.sum(case(((Transaction.transaction_type == "expense") & (Transaction.category != "carryover"), Transaction.amount), else_=0)), 0),
        func.coalesce(func.sum(case((Transaction.category == "carryover", signed), else_=0)), 0),
        func.coalesce(func.sum(case((Transaction.category == "interest", Transaction.amount), else_=0)), 0),
        func.count(Transaction.id),
    ).where(*conditions)).one()
    def grouped(direction):
        rows = db.execute(select(Transaction.counterparty, func.sum(Transaction.amount)).where(
            *conditions, Transaction.transaction_type == direction, Transaction.category != "carryover"
        ).group_by(Transaction.counterparty).order_by(func.sum(Transaction.amount).desc())).all()
        return [{"name": name or "기존 내역 (미기재)", "amount": int(amount)} for name, amount in rows]
    return {"start": start, "end": end, "opening_balance": opening,
            "carryover": int(carryover), "total_income": int(income), "total_expense": int(expense),
            "interest": int(interest), "closing_balance": opening + int(carryover) + int(income) - int(expense),
            "transaction_count": count, "recipients": grouped("expense"), "sources": grouped("income")}


def dashboard_report(db: Session, start=None, end=None):
    summary = period_report(db, start, end)
    conditions = filters(start, end)
    year, month = extract("year", Transaction.transaction_date), extract("month", Transaction.transaction_date)
    rows = db.execute(select(year, month, Transaction.transaction_type, func.sum(Transaction.amount)).where(
        *conditions, Transaction.category != "carryover"
    ).group_by(year, month, Transaction.transaction_type).order_by(year, month)).all()
    monthly = {}
    for y, m, direction, amount in rows:
        key = f"{int(y):04d}-{int(m):02d}"
        monthly.setdefault(key, {"month": key, "income": 0, "expense": 0})[direction] = int(amount)
    categories = db.execute(select(Transaction.category, func.sum(Transaction.amount)).where(
        *conditions, Transaction.transaction_type == "expense", Transaction.category != "carryover"
    ).group_by(Transaction.category).order_by(func.sum(Transaction.amount).desc())).all()
    return {"summary": summary, "monthly": list(monthly.values()),
            "monthly_max": max((max(row["income"], row["expense"]) for row in monthly.values()), default=1) or 1,
            "categories": [{"label": CATEGORY_LABELS.get(code, code), "amount": int(amount)} for code, amount in categories],
            "category_max": max((int(amount) for _, amount in categories), default=1) or 1}
