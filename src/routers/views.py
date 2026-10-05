"""Server-rendered views for program operations and announcements."""

from datetime import date
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Query
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..database import get_db
from ..dependencies import get_current_user, require_roles
from ..models import (
    Announcement,
    Application,
    ApplicationDocument,
    FinanceTransaction,
    Followup,
    PrayerRequest,
    ReviewAssignment,
    ReviewCriterion,
    Selection,
    ScholarshipProgram,
    User,
)


TEMPLATES_DIR = Path(__file__).resolve().parents[2] / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
router = APIRouter(tags=["views"])
AuthenticatedUser = Annotated[User, Depends(get_current_user)]
Manager = Annotated[User, Depends(require_roles("administrator", "program_manager"))]
Reviewer = Annotated[User, Depends(require_roles("reviewer"))]
Applicant = Annotated[User, Depends(require_roles("applicant"))]


@router.get("/login", name="login_page")
def login_page(request: Request):
    return templates.TemplateResponse(request=request, name="login.html", context={"request": request})


@router.get("/register", name="register_page")
def register_page(request: Request):
    return templates.TemplateResponse(request=request, name="register.html", context={"request": request})


def base_context(user: User) -> dict[str, object]:
    role_codes = {role.code for role in user.roles}
    return {"user": user, "is_admin": bool(role_codes & {"administrator", "program_manager"}),
            "finance_access": bool(role_codes & {"administrator", "program_manager", "finance"})}


@router.get("/admin/dashboard", name="admin_dashboard")
def admin_dashboard(
    request: Request,
    user: Manager,
    db: Annotated[Session, Depends(get_db)],
):
    programs = list(
        db.scalars(select(ScholarshipProgram).order_by(ScholarshipProgram.created_at.desc()))
    )
    announcements = list(
        db.scalars(select(Announcement).order_by(Announcement.created_at.desc()))
    )
    total_income = db.scalar(
        select(func.coalesce(func.sum(FinanceTransaction.amount), 0)).where(
            FinanceTransaction.transaction_type == "income"
        )
    ) or 0
    total_expense = db.scalar(
        select(func.coalesce(func.sum(FinanceTransaction.amount), 0)).where(
            FinanceTransaction.transaction_type == "expense"
        )
    ) or 0
    transaction_count = db.scalar(select(func.count(FinanceTransaction.id))) or 0
    applicant_count = db.scalar(select(func.count(Application.id))) or 0
    selected_count = db.scalar(
        select(func.count(Application.id)).where(Application.status == "selected")
    ) or 0
    context = base_context(user)
    context.update(
        {
            "request": request,
            "programs": programs,
            "announcements": announcements,
            "open_count": sum(program.status == "active" for program in programs),
            "finance": {
                "income": int(total_income),
                "expense": int(total_expense),
                "balance": int(total_income) - int(total_expense),
                "count": int(transaction_count),
            },
            "applicant_count": int(applicant_count),
            "selected_count": int(selected_count),
        }
    )
    return templates.TemplateResponse(request=request, name="admin_dashboard.html", context=context)


@router.get("/announcements", name="announcements_list")
def announcements_list(
    request: Request,
    user: AuthenticatedUser,
    db: Annotated[Session, Depends(get_db)],
):
    announcements = list(
        db.scalars(
            select(Announcement)
            .where(Announcement.status == "open")
            .order_by(Announcement.application_end_at.asc(), Announcement.created_at.desc())
        )
    )
    applied_announcement_ids = []
    if "applicant" in {role.code for role in user.roles}:
        applied_announcement_ids = list(
            db.scalars(
                select(Application.announcement_id)
                .where(Application.applicant_id == user.id)
                .distinct()
            )
        )
    context = base_context(user)
    context.update(
        {
            "request": request,
            "announcements": announcements,
            "applied_announcement_ids": applied_announcement_ids,
        }
    )
    return templates.TemplateResponse(request=request, name="announcements_list.html", context=context)


@router.get("/applications/new", name="application_form")
def application_form(
    request: Request,
    announcement_id: str,
    user: Annotated[User, Depends(require_roles("applicant"))],
    db: Annotated[Session, Depends(get_db)],
):
    announcement = db.get(Announcement, announcement_id)
    if announcement is None:
        raise HTTPException(status_code=404, detail="장학 공고를 찾을 수 없습니다.")
    if announcement.status != "open":
        raise HTTPException(status_code=400, detail="현재 신청할 수 없는 공고입니다.")
    existing = db.scalar(
        select(Application).where(
            Application.applicant_id == user.id,
            Application.announcement_id == announcement_id,
        )
    )
    context = base_context(user)
    context.update(
        {"request": request, "announcement": announcement, "existing_application": existing}
    )
    return templates.TemplateResponse(request=request, name="application_form.html", context=context)


@router.get("/reviewer/dashboard", name="reviewer_dashboard")
def reviewer_dashboard(
    request: Request,
    user: Reviewer,
    db: Annotated[Session, Depends(get_db)],
):
    assignments = list(
        db.scalars(
            select(ReviewAssignment)
            .where(ReviewAssignment.reviewer_id == user.id)
            .order_by(ReviewAssignment.created_at.desc())
        )
    )
    review_items = []
    for assignment in assignments:
        application = db.get(Application, assignment.application_id)
        criteria = list(
            db.scalars(
                select(ReviewCriterion).where(
                    ReviewCriterion.announcement_id == application.announcement_id
                )
            )
        ) if application else []
        review_items.append({"assignment": assignment, "application": application, "criteria": criteria})
    context = base_context(user)
    context.update({"request": request, "review_items": review_items})
    return templates.TemplateResponse(request=request, name="reviewer_dashboard.html", context=context)


@router.get("/my-page", name="my_page")
def my_page(
    request: Request,
    user: Applicant,
    db: Annotated[Session, Depends(get_db)],
):
    applications = list(
        db.scalars(
            select(Application)
            .where(Application.applicant_id == user.id)
            .order_by(Application.created_at.desc())
        )
    )
    followups = list(
        db.scalars(
            select(Followup)
            .where(Followup.applicant_id == user.id)
            .order_by(Followup.created_at.desc())
        )
    )
    selections = list(
        db.scalars(select(Selection).where(Selection.applicant_id == user.id))
    )
    context = base_context(user)
    context.update(
        {"request": request, "applications": applications, "followups": followups, "selections": selections}
    )
    return templates.TemplateResponse(request=request, name="my_page.html", context=context)


@router.get("/admin/applications/{application_id}", name="admin_application_detail")
def admin_application_detail(
    request: Request,
    application_id: str,
    user: Manager,
    db: Annotated[Session, Depends(get_db)],
):
    application = db.get(Application, application_id)
    if application is None:
        raise HTTPException(status_code=404, detail="신청서를 찾을 수 없습니다.")
    documents = list(
        db.scalars(select(ApplicationDocument).where(ApplicationDocument.application_id == application_id))
    )
    prayer_requests = list(
        db.scalars(
            select(PrayerRequest).where(
                PrayerRequest.user_id == application.applicant_id,
                PrayerRequest.status == "active",
            )
        )
    )
    selection = db.scalar(select(Selection).where(Selection.application_id == application_id))
    context = base_context(user)
    context.update(
        {
            "request": request,
            "application": application,
            "documents": documents,
            "prayer_requests": prayer_requests,
            "selection": selection,
        }
    )
    return templates.TemplateResponse(request=request, name="admin_application_detail.html", context=context)

FinanceManager = Annotated[User, Depends(require_roles("administrator", "program_manager", "finance"))]


@router.get("/finance/dashboard", name="finance_presentation")
def finance_presentation(request: Request, user: FinanceManager,
                         db: Annotated[Session, Depends(get_db)],
                         start: date | None = None, end: date | None = None):
    from ..services.ledger import dashboard_report
    return templates.TemplateResponse(request=request, name="finance_dashboard.html", context={
        **base_context(user), "finance_access": True,
        "dashboard": dashboard_report(db, start, end),
    })


@router.get("/")
def home(user: AuthenticatedUser):
    roles = {role.code for role in user.roles}
    destination = "/finance" if roles & {"administrator", "program_manager", "finance"} else "/announcements"
    return RedirectResponse(destination, status_code=303)


@router.get("/finance", name="finance_dashboard")
def finance_dashboard(request: Request, user: FinanceManager,
                      db: Annotated[Session, Depends(get_db)],
                      start: date | None = None, end: date | None = None,
                      transaction_type: str | None = Query(None, pattern="^(income|expense)$"),
                      category: str | None = Query(None, pattern="^(general|donation|interest|carryover|scholarship|operating|other)$"),
                      q: str | None = Query(None, max_length=200), page: int = Query(1, ge=1)):
    from ..services.ledger import CATEGORY_LABELS, list_transactions, period_report
    ledger = list_transactions(db, start=start, end=end, transaction_type=transaction_type,
                               category=category, q=q, page=page)
    query = dict(request.query_params)
    previous = request.url.include_query_params(page=max(1, page - 1))
    following = request.url.include_query_params(page=page + 1)
    return templates.TemplateResponse(request=request, name="finance.html", context={
        **base_context(user), "finance_access": True, "finance_mode": True,
        "ledger": ledger, "report": period_report(db, start, end), "categories": CATEGORY_LABELS,
        "query": query, "previous": previous, "following": following,
    })
