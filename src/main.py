"""FastAPI application entry point."""

from contextlib import asynccontextmanager
import os
from uuid import uuid4
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select, text
from sqlalchemy.orm import Session, selectinload

from .auth import create_access_token, decode_access_token, hash_password, verify_password
from .database import SessionLocal, create_database, engine, get_db
from .models import Role, User
from .schemas import LoginRequest, RegisterRequest, TokenResponse, UserResponse


DEFAULT_ROLES = (
    ("role-admin", "administrator", "관리자", "사용자와 기준정보를 관리한다."),
    ("role-manager", "program_manager", "사업 담당자", "사업, 공고, 심사 운영을 관리한다."),
    ("role-reviewer", "reviewer", "장학위원", "배정된 신청을 심사한다."),
    ("role-ministry", "ministry_worker", "사역 담당자", "중보기도와 목회적 돌봄을 담당한다."),
    ("role-finance", "finance", "지급 담당자", "기금과 지급 업무를 담당한다."),
    ("role-applicant", "applicant", "신청자", "본인의 신청과 기도제목을 관리한다."),
)


class RoleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    code: str
    name: str
    description: str | None


def seed_roles() -> None:
    with SessionLocal.begin() as session:
        existing_codes = set(session.scalars(select(Role.code)))
        for role_id, code, name, description in DEFAULT_ROLES:
            if code not in existing_codes:
                session.add(
                    Role(
                        id=role_id,
                        code=code,
                        name=name,
                        description=description,
                    )
                )


@asynccontextmanager
async def lifespan(_: FastAPI):
    create_database()
    seed_roles()
    yield


app = FastAPI(title="Rt Scholarship Platform", lifespan=lifespan)
bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: Annotated[
        HTTPAuthorizationCredentials | None, Depends(bearer_scheme)
    ],
    db: Annotated[Session, Depends(get_db)],
) -> User:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="인증 토큰이 필요합니다.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = decode_access_token(credentials.credentials)
    user = (
        db.scalar(
            select(User)
            .options(selectinload(User.roles))
            .where(User.id == user_id)
        )
        if user_id
        else None
    )
    if user is None or user.status != "active":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="유효하지 않은 인증 토큰입니다.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


def require_role(role_code: str):
    def role_dependency(
        current_user: Annotated[User, Depends(get_current_user)],
    ) -> User:
        if not any(role.code == role_code for role in current_user.roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="이 작업을 수행할 권한이 없습니다.",
            )
        return current_user

    return role_dependency


@app.get("/health")
def health_check() -> dict[str, str]:
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))
    return {"status": "ok"}


@app.post("/auth/register", response_model=UserResponse, status_code=201)
def register_user(
    request: RegisterRequest,
    db: Annotated[Session, Depends(get_db)],
) -> UserResponse:
    if db.scalar(select(User).where(User.email == request.email)) is not None:
        raise HTTPException(status_code=409, detail="이미 등록된 이메일입니다.")

    requested_role = request.role_code
    if requested_role != "applicant" and os.getenv("ALLOW_ROLE_REGISTRATION") != "true":
        raise HTTPException(
            status_code=403,
            detail="일반 가입은 신청자 역할만 생성할 수 있습니다.",
        )

    role = db.scalar(select(Role).where(Role.code == requested_role))
    if role is None:
        raise HTTPException(status_code=400, detail="존재하지 않는 역할입니다.")

    user = User(
        id=uuid4().hex,
        email=request.email,
        password_hash=hash_password(request.password),
        name=request.name,
        roles=[role],
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return UserResponse(
        id=user.id,
        email=user.email,
        name=user.name,
        status=user.status,
        roles=[assigned_role.code for assigned_role in user.roles],
    )


@app.post("/auth/login", response_model=TokenResponse)
def login(
    request: LoginRequest,
    db: Annotated[Session, Depends(get_db)],
) -> TokenResponse:
    user = db.scalar(select(User).where(User.email == request.email))
    if user is None or not verify_password(request.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="이메일 또는 비밀번호가 올바르지 않습니다.",
        )
    if user.status != "active":
        raise HTTPException(status_code=403, detail="비활성화된 사용자입니다.")
    return TokenResponse(access_token=create_access_token(user.id))


@app.get("/roles", response_model=list[RoleResponse])
def list_roles(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_role("administrator"))],
) -> list[Role]:
    return list(db.scalars(select(Role).order_by(Role.code)))