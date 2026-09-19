"""Reusable authentication and authorization dependencies."""

from typing import Annotated

from fastapi import Cookie, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from .auth import decode_access_token
from .database import get_db
from .models import User


bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    db: Annotated[Session, Depends(get_db)],
    credentials: Annotated[
        HTTPAuthorizationCredentials | None, Depends(bearer_scheme)
    ],
    access_token: Annotated[str | None, Cookie()],
) -> User:
    token = credentials.credentials if credentials else access_token
    if token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="인증 토큰이 필요합니다.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = decode_access_token(token)
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


def require_roles(*role_codes: str):
    def role_dependency(
        current_user: Annotated[User, Depends(get_current_user)],
    ) -> User:
        if not any(role.code in role_codes for role in current_user.roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="이 작업을 수행할 권한이 없습니다.",
            )
        return current_user

    return role_dependency


def require_role(role_code: str):
    return require_roles(role_code)