"""Secure application and follow-up evidence file endpoints."""

import os
from pathlib import Path
from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..dependencies import get_current_user
from ..models import (
    Application,
    ApplicationDocument,
    Followup,
    FollowupDocument,
    User,
)
from ..schemas import DocumentResponse


router = APIRouter(prefix="/api", tags=["documents"])
CurrentUser = Annotated[User, Depends(get_current_user)]
UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", "storage/uploads"))
ALLOWED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg"}
MAX_FILE_SIZE = 10 * 1024 * 1024


def ensure_owner_or_manager(user: User, owner_id: str) -> None:
    role_codes = {role.code for role in user.roles}
    if user.id != owner_id and not role_codes & {"administrator", "program_manager"}:
        raise HTTPException(status_code=403, detail="파일에 접근할 권한이 없습니다.")


async def store_upload(file: UploadFile) -> tuple[str, str, int]:
    original = Path(file.filename or "").name
    extension = Path(original).suffix.lower()
    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=415, detail="PDF 또는 이미지 파일만 업로드할 수 있습니다.")
    content = await file.read(MAX_FILE_SIZE + 1)
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="파일 크기는 10MB 이하이어야 합니다.")
    stored = f"{uuid4().hex}{extension}"
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    (UPLOAD_DIR / stored).write_bytes(content)
    return original, stored, len(content)


@router.post(
    "/applications/{application_id}/documents",
    response_model=DocumentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_application_document(
    application_id: str,
    current_user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
    file: UploadFile = File(...),
    document_type: str = Form("evidence"),
) -> ApplicationDocument:
    application = db.get(Application, application_id)
    if application is None or application.applicant_id != current_user.id:
        raise HTTPException(status_code=404, detail="본인의 신청서를 찾을 수 없습니다.")
    original, stored, size = await store_upload(file)
    document = ApplicationDocument(
        id=uuid4().hex,
        application_id=application.id,
        applicant_id=current_user.id,
        document_type=document_type,
        original_filename=original,
        stored_filename=stored,
        content_type=file.content_type or "application/octet-stream",
        size_bytes=size,
    )
    db.add(document)
    db.commit()
    db.refresh(document)
    return document


@router.post(
    "/followups/{followup_id}/documents",
    response_model=DocumentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_followup_document(
    followup_id: str,
    current_user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
    file: UploadFile = File(...),
    document_type: str = Form("evidence"),
) -> FollowupDocument:
    followup = db.get(Followup, followup_id)
    if followup is None or followup.applicant_id != current_user.id:
        raise HTTPException(status_code=404, detail="본인의 사후보고를 찾을 수 없습니다.")
    original, stored, size = await store_upload(file)
    document = FollowupDocument(
        id=uuid4().hex,
        followup_id=followup.id,
        applicant_id=current_user.id,
        document_type=document_type,
        original_filename=original,
        stored_filename=stored,
        content_type=file.content_type or "application/octet-stream",
        size_bytes=size,
    )
    db.add(document)
    db.commit()
    db.refresh(document)
    return document


@router.get("/documents/application/{document_id}")
def download_application_document(
    document_id: str,
    current_user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
) -> FileResponse:
    document = db.get(ApplicationDocument, document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="파일을 찾을 수 없습니다.")
    ensure_owner_or_manager(current_user, document.applicant_id)
    path = UPLOAD_DIR / document.stored_filename
    if not path.is_file():
        raise HTTPException(status_code=404, detail="저장된 파일을 찾을 수 없습니다.")
    return FileResponse(path, media_type=document.content_type, filename=document.original_filename)


@router.get("/documents/followup/{document_id}")
def download_followup_document(
    document_id: str,
    current_user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
) -> FileResponse:
    document = db.get(FollowupDocument, document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="파일을 찾을 수 없습니다.")
    ensure_owner_or_manager(current_user, document.applicant_id)
    path = UPLOAD_DIR / document.stored_filename
    if not path.is_file():
        raise HTTPException(status_code=404, detail="저장된 파일을 찾을 수 없습니다.")
    return FileResponse(path, media_type=document.content_type, filename=document.original_filename)