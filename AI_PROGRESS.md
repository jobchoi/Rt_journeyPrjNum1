# AI 협업 진행 기록

## 현재 작업: 2026-10-04 입출금 중심 단순화

- 현재 브랜치: develop
- 보존된 기능 백업 브랜치: feature/simple-finance (Git Flow 생성 및 병합 완료)
- 사용자 요청: 입출금, 이자·이월금·결산, 대상 이름과 출금액, 입금처, 거래 보고서, 출금 사유를 기본으로 단순화
- 기존 장학 모델과 API·데이터는 보존하고 기본 메뉴와 관리자 로그인 이동은 /finance로 변경
- 서비스: src/services/ledger.py, API: src/routers/finance.py, UI: templates/finance.html
- migration: 0002_simple_finance, 백업/업그레이드: scripts/upgrade_finance.py
- 이전 진행 기록과 설계: docs/archive/scholarship-mvp/

## 완료된 작업

- 독립 수동 원장, 이름/입금처, 거래 내용, 거래 분류
- 검색/페이지네이션, 기간 잔액 및 이자·이월금 분리 계산
- 대상별·입금처별 집계, CSV 보고서, 인쇄/PDF, CSV 예시 양식
- 권한 차단, 중복 번호, 원자적 CSV 입력, 다운로드 수식 방어
- 새 장학 지급 기록도 수취인 이름과 scholarship 분류를 원장에 기록
- 실제 로컬 database/rt.db: SQLite 백업 후 0002 migration 적용 완료. 백업은 storage/backups에 있음

## 검증 / 이어서 할 일

- 최종 전체 회귀 테스트: `/home/jobchoi/miniforge3/bin/python -m pytest -q` → 8 passed (8.51초)
- `/home/jobchoi/miniforge3/bin/python -m compileall -q src scripts tests` → 통과
- `git diff --check` → 통과
- 로컬 DB version 확인 → 0002_simple_finance, 원장 신규 컬럼 확인
- 구현 백업 커밋: fc42a39 feat: simplify fund management around ledger and reports
- 검증 기록 백업 커밋: a8a69e4 docs: record finance verification and database upgrade
- `git flow feature finish -k simple-finance` 성공: develop 병합 및 기능 브랜치 보존
- 요청된 구현·검증·로컬 Git 백업 완료. 중단된 구현 작업 없음
- 사용: 서버 재시작 후 /login → 재정 권한 계정 로그인 → /finance
- 경고: Starlette BlockingPortal 및 Alembic path_separator 관련 의존성 deprecation 5개, 테스트 실패 없음
- 실제 실행 중 서버의 재시작은 수행하지 않음. 새 코드 적용에는 서버 재시작 필요
- 원격 push는 수행하지 않음. 코드 커밋과 Git Flow는 로컬 백업

## 트러블슈팅 / 작업 중단 기록

### Git Flow 브랜치 생성 권한

- 증상: .git/config와 index.lock 생성 실패 (읽기 전용)
- 원인: 환경의 .git 쓰기 제한
- 조치: 실행 권한 승인을 받아 git flow feature start simple-finance 성공

### 격리 환경 테스트 대기

- 증상: pytest가 출력 없이 대기하여 중단
- 조치: 격리 환경 밖에서 승인된 테스트 실행으로 전체 8개 통과
- 테스트 DB는 운영 데이터가 아닌 database/pytest_mvp.db 사용

## 알려진 한계

- 결산은 계산 보고서이며 확정 마감 기능이 아니다.
- 같은 이름의 거래처를 합산한다. 기존 거래처 미기재 데이터는 그대로 유지한다.
- 수정/삭제/정정 흐름은 후속 확장이다.
- 기존 브라우저 인증 방식과 Tailwind CDN은 유지했다. 운영 보안 강화는 후속 범위다.

## 서버 관리 스크립트 수정 (2026-10-05)

- 증상: `./manage.sh restart`에서 `venv/bin/activate`가 없는데도 실행 성공을 출력함.
- 재현: 프로젝트에 venv 없이 현재 Conda/PATH 환경의 uvicorn으로 실행.
- 원인: 가상환경 경로 고정, 활성화 실패 무시, 실제 프로세스 시작/종료 확인 누락.
- 수정: `.venv` → `venv` → PATH Python 자동 선택, VENV_DIR 명시 지원, `python -m uvicorn` 실행. 프로젝트 루트 고정, 시작 완료/실패 확인, PID 유효성 및 프로세스 확인, 종료 대기 추가. README 실행 안내 및 런타임 파일 gitignore 반영.
- 검증: bash 문법 및 git diff --check 통과. 없는 VENV_DIR에서 실패 반환 확인. 8000 포트 충돌 시 로그 출력/실패 반환 확인. 호스트에서 기존 서버 PID 복원 후 restart/status 성공, `/health` → `{"status":"ok"}`. 전체 pytest 8 passed (기존 deprecation 경고 5개).
- 환경: 격리 환경에서는 호스트 PID/소켓에 접근할 수 없어 실제 서버 검증과 pytest는 호스트 실행으로 완료.
