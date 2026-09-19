"""Create the first administrator without enabling public role registration."""

import argparse
import getpass
import sys
from pathlib import Path
from uuid import uuid4

from sqlalchemy import select

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.auth import hash_password
from src.database import SessionLocal
from src.models import Role, User


ADMIN_ROLE = ("role-admin", "administrator", "관리자", "사용자와 기준정보를 관리한다.")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create an initial Rt administrator.")
    parser.add_argument("--email", required=True)
    parser.add_argument("--name", required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    password = getpass.getpass("관리자 비밀번호: ")
    confirmation = getpass.getpass("비밀번호 확인: ")
    if len(password) < 8:
        print("비밀번호는 8자 이상이어야 합니다.", file=sys.stderr)
        return 1
    if password != confirmation:
        print("비밀번호가 일치하지 않습니다.", file=sys.stderr)
        return 1

    email = args.email.strip().lower()
    with SessionLocal.begin() as session:
        if session.scalar(select(User).where(User.email == email)) is not None:
            print("이미 등록된 이메일입니다.", file=sys.stderr)
            return 1
        role = session.scalar(select(Role).where(Role.code == ADMIN_ROLE[1]))
        if role is None:
            role = Role(id=ADMIN_ROLE[0], code=ADMIN_ROLE[1], name=ADMIN_ROLE[2], description=ADMIN_ROLE[3])
            session.add(role)
            session.flush()
        session.add(
            User(
                id=uuid4().hex,
                email=email,
                password_hash=hash_password(password),
                name=args.name.strip(),
                roles=[role],
            )
        )
    print(f"최고 관리자 계정을 생성했습니다: {email}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
