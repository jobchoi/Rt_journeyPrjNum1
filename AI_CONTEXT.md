# AI 작업 맥락

현재 제품의 기본 범위는 통합기금 입출금 원장과 보고서다. 2026-10-04 사용자가 단순화를 요청했다.

## 읽기 순서

AI_PROGRESS.md → REQUIREMENTS.md → DATABASE.md → API.md → TASKS.md.
전환 전 장학 설계는 docs/archive/scholarship-mvp에 있으며 현재 기본 요구사항으로 취급하지 않는다.

## 구현 원칙

- Python/FastAPI/SQLAlchemy/SQLite/Jinja2를 유지한다.
- 거래 입력에 신청자 계정, 공고, 심사, 선발을 요구하지 않는다.
- 집계 규칙은 src/services/ledger.py에서 API와 화면이 공유한다.
- 기존 장학 API와 데이터는 보존하고 향후 선택적 확장 기능으로 다룬다.
- 기존 데이터베이스 변경은 백업과 Alembic을 사용한다. create_all은 기존 테이블 컬럼을 갱신하지 않는다.
- 이월금을 자동 재등록하거나 이자를 두 번 합산하지 않는다.
- 개인정보·비밀번호·DB 원문을 문서/커밋/로그에 넣지 않는다.
- 사용자 변경인 server.log/server.pid를 커밋하거나 덮어쓰지 않는다.

## 작업 방식

사용자는 중간 진행 보고 없이 최종 결과만 받기를 요청했다.
중단/보류/오류가 생기면 AI_PROGRESS.md에 원인, 완료 범위, 다음 명령을 남긴다.
Git Flow feature 브랜치에서 단계별 커밋하고 검증 후 develop에 병합한다.
Git 커밋은 로컬 코드 백업이며 원격 백업 완료로 표현하지 않는다.
