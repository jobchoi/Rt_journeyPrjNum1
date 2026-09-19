"""Server-rendered views for program operations and announcements."""

from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..dependencies import get_current_user, require_roles
from ..models import Announcement, Application, ScholarshipProgram, User


TEMPLATES_DIR = Path(__file__).resolve().parents[2] / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
router = APIRouter(tags=["views"])
AuthenticatedUser = Annotated[User, Depends(get_current_user)]
Manager = Annotated[User, Depends(require_roles("administrator", "program_manager"))]


@router.get("/login", name="login_page")
def login_page(request: Request):
    return templates.TemplateResponse(request=request, name="login.html", context={"request": request})


@router.get("/register", name="register_page")
def register_page(request: Request):
    return templates.TemplateResponse(request=request, name="register.html", context={"request": request})


def base_context(user: User) -> dict[str, object]:
    role_codes = {role.code for role in user.roles}
    return {"user": user, "is_admin": bool(role_codes & {"administrator", "program_manager"})}


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
    context = base_context(user)
    context.update(
        {
            "request": request,
            "programs": programs,
            "announcements": announcements,
            "open_count": sum(program.status == "active" for program in programs),
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
            .where(Announcement.status.in_(["open", "reviewing", "finished"]))
            .order_by(Announcement.application_end_at.asc(), Announcement.created_at.desc())
        )
    )
    context = base_context(user)
    context.update({"request": request, "announcements": announcements})
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