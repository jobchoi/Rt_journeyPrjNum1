"""Scholarship program CRUD endpoints."""

from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..dependencies import get_current_user, require_roles
from ..models import ScholarshipProgram, User
from ..program_schemas import ProgramCreate, ProgramResponse, ProgramUpdate
from ..database import get_db


router = APIRouter(prefix="/api/programs", tags=["programs"])
Manager = Annotated[User, Depends(require_roles("administrator", "program_manager"))]
AuthenticatedUser = Annotated[User, Depends(get_current_user)]


@router.get("", response_model=list[ProgramResponse])
def list_programs(
    _: AuthenticatedUser,
    db: Annotated[Session, Depends(get_db)],
) -> list[ScholarshipProgram]:
    return list(db.scalars(select(ScholarshipProgram).order_by(ScholarshipProgram.created_at.desc())))


@router.post("", response_model=ProgramResponse, status_code=status.HTTP_201_CREATED)
def create_program(
    request: ProgramCreate,
    current_user: Manager,
    db: Annotated[Session, Depends(get_db)],
) -> ScholarshipProgram:
    program = ScholarshipProgram(
        id=uuid4().hex,
        created_by=current_user.id,
        **request.model_dump(),
    )
    db.add(program)
    db.commit()
    db.refresh(program)
    return program


@router.get("/{program_id}", response_model=ProgramResponse)
def get_program(
    program_id: str,
    _: AuthenticatedUser,
    db: Annotated[Session, Depends(get_db)],
) -> ScholarshipProgram:
    program = db.get(ScholarshipProgram, program_id)
    if program is None:
        raise HTTPException(status_code=404, detail="장학 사업을 찾을 수 없습니다.")
    return program


@router.patch("/{program_id}", response_model=ProgramResponse)
def update_program(
    program_id: str,
    request: ProgramUpdate,
    _: Manager,
    db: Annotated[Session, Depends(get_db)],
) -> ScholarshipProgram:
    program = db.get(ScholarshipProgram, program_id)
    if program is None:
        raise HTTPException(status_code=404, detail="장학 사업을 찾을 수 없습니다.")
    for field, value in request.model_dump(exclude_unset=True).items():
        setattr(program, field, value)
    db.commit()
    db.refresh(program)
    return program


@router.delete("/{program_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_program(
    program_id: str,
    _: Manager,
    db: Annotated[Session, Depends(get_db)],
) -> None:
    program = db.get(ScholarshipProgram, program_id)
    if program is None:
        raise HTTPException(status_code=404, detail="장학 사업을 찾을 수 없습니다.")
    db.delete(program)
    db.commit()