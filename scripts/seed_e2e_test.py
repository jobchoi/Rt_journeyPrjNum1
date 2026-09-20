"""Seed a full E2E scholarship flow for UI and API validation.

This script creates demo accounts for administrator, applicant, and reviewer roles,
then inserts one end-to-end cycle of data:

- scholarship program
- announcement
- application
- review assignment

The generated credentials are printed at the end so a developer can log in directly
through the browser and inspect the relevant pages.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.auth import hash_password
from src.database import SessionLocal
from src.models import (
    Announcement,
    Application,
    ReviewAssignment,
    ReviewCriterion,
    Role,
    ScholarshipProgram,
    User,
)


def ensure_role(session, code: str, label: str, description: str) -> Role:
    role = session.query(Role).filter_by(code=code).one_or_none()
    if role is None:
        role = Role(id=f"role-{code}", code=code, name=label, description=description)
        session.add(role)
        session.flush()
    return role


def make_user(session, email: str, name: str, role_code: str) -> User:
    existing = session.query(User).filter_by(email=email).one_or_none()
    if existing is not None:
        return existing

    role = ensure_role(session, role_code, _role_label(role_code), _role_description(role_code))
    user = User(
        id=uuid4().hex,
        email=email,
        password_hash=hash_password("Passw0rd!"),
        name=name,
        roles=[role],
    )
    session.add(user)
    session.flush()
    return user


def _role_label(code: str) -> str:
    labels = {
        "administrator": "관리자",
        "program_manager": "사업 담당자",
        "reviewer": "심사위원",
        "applicant": "신청자",
    }
    return labels.get(code, code)


def _role_description(code: str) -> str:
    descriptions = {
        "administrator": "사용자와 기준정보를 관리한다.",
        "program_manager": "사업, 공고, 심사 운영을 관리한다.",
        "reviewer": "배정된 신청을 심사한다.",
        "applicant": "본인의 신청과 기도제목을 관리한다.",
    }
    return descriptions.get(code, code)


def seed_data() -> dict[str, str]:
    with SessionLocal.begin() as session:
        admin = make_user(session, "admin@e2e.local", "관리자 계정", "administrator")
        applicant = make_user(session, "applicant@e2e.local", "신청자 계정", "applicant")
        reviewer = make_user(session, "reviewer@e2e.local", "심사위원 계정", "reviewer")

        program = ScholarshipProgram(
            id=uuid4().hex,
            name="2026 E2E 장학사업",
            description="자동 생성된 E2E 테스트 장학 사업",
            status="active",
            created_by=admin.id,
        )
        session.add(program)
        session.flush()

        announcement = Announcement(
            id=uuid4().hex,
            program_id=program.id,
            title="2026 E2E 장학사업 공고",
            target_description="학업 역량과 사역 실천 의지가 있는 학생을 대상으로 지원합니다.",
            selected_count=1,
            status="open",
            payment_description="선발자 지급 안내",
            created_by=admin.id,
        )
        session.add(announcement)
        session.flush()

        application = Application(
            id=uuid4().hex,
            applicant_id=applicant.id,
            announcement_id=announcement.id,
            status="submitted",
            study_plan="학업 계획: 집중 학습과 사역 병행",
            financial_need="경제적 지원이 필요한 상황",
            ministry_plan="지역 청년 사역에 기여하고 싶습니다.",
        )
        session.add(application)
        session.flush()

        criterion = ReviewCriterion(
            id=uuid4().hex,
            announcement_id=announcement.id,
            code="need",
            name="경제적 필요",
            max_score=10,
            required=True,
        )
        session.add(criterion)
        session.flush()

        assignment = ReviewAssignment(
            id=uuid4().hex,
            application_id=application.id,
            reviewer_id=reviewer.id,
        )
        session.add(assignment)
        session.flush()

        return {
            "admin_email": admin.email,
            "admin_password": "Passw0rd!",
            "applicant_email": applicant.email,
            "applicant_password": "Passw0rd!",
            "reviewer_email": reviewer.email,
            "reviewer_password": "Passw0rd!",
            "program_id": program.id,
            "announcement_id": announcement.id,
            "application_id": application.id,
            "review_assignment_id": assignment.id,
        }


def main() -> int:
    os.environ.setdefault("ALLOW_ROLE_REGISTRATION", "true")
    data = seed_data()
    print("\n=== E2E 테스트 계정 ===")
    print(f"관리자: {data['admin_email']} / Passw0rd!")
    print(f"신청자: {data['applicant_email']} / Passw0rd!")
    print(f"심사위원: {data['reviewer_email']} / Passw0rd!")
    print("\n=== 생성된 기본 데이터 ===")
    print(f"program_id={data['program_id']}")
    print(f"announcement_id={data['announcement_id']}")
    print(f"application_id={data['application_id']}")
    print(f"review_assignment_id={data['review_assignment_id']}")
    print("\n로그인 후 다음 화면을 확인할 수 있습니다:")
    print("- 관리자: /admin/dashboard")
    print("- 신청자: /announcements, /my-page")
    print("- 심사위원: /reviewer/dashboard")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
