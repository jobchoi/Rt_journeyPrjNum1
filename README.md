# Rt 통합기금 입출금 관리

입출금 원장과 거래 보고서를 중심으로 사용하는 간단한 기금 관리 시스템입니다.

## 현재 핵심 기능

1. 입금·출금 수동 등록 및 기간·분류·이름·내용 검색
2. 출금 대상 이름과 금액, 입금처 기록
3. 출금 사유와 거래 내용 기록
4. 이자·이월금 분류 및 기간 결산
5. 거래내역 보고서, 대상별·입금처별 합계, CSV 다운로드, 인쇄/PDF
6. 기존 CSV 가져오기 및 거래번호 중복 방지
7. 거래 수정과 사유·변경 전후·수정자·시각 이력
8. 발표용 자체 대시보드(월별 입출금·분류별 출금), 전체화면 및 인쇄/PDF

관리자·사업 담당자·지급 담당자의 로그인 후 기본 화면은 `/finance`입니다.
이름과 입금처는 직접 입력하며 신청서나 장학생 계정을 먼저 만들 필요가 없습니다.

## 실행

```bash
python -m pip install -r requirements.txt
python scripts/upgrade_finance.py
python scripts/create_superuser.py --email admin@example.com --name "기금 관리자"
# JWT_SECRET_KEY를 로컬 환경에 지정한 뒤 실행
python -m uvicorn src.main:app --reload --host 127.0.0.1 --port 8001
```

브라우저에서 `/login`에 접속합니다. 관리자 생성 명령은 비밀번호를 터미널에서 입력받습니다.
기존 서버가 실행 중이면 새 코드를 적용하려면 재시작해야 합니다.
백그라운드 실행은 `./manage.sh start`, 재시작은 `./manage.sh restart`를 사용합니다.
스크립트는 `.venv`, `venv`, 현재 PATH의 Python 순서로 실행 환경을 선택합니다.
특정 환경은 `VENV_DIR=/path/to/venv ./manage.sh restart`로 지정합니다.
기본 주소는 `0.0.0.0:8000`이며 `HOST`, `PORT` 환경변수로 변경할 수 있습니다.
`./manage.sh status`로 프로세스 상태, `./manage.sh log`로 로그를 확인합니다.
의존성은 선택한 환경에 미리 설치해야 하며, 시작 실패 시 로그를 출력하고 실패 코드로 종료합니다.
`upgrade_finance.py`는 기존 SQLite DB를 `storage/backups/`에 백업한 뒤 migration을 적용합니다.
새 DB와 Alembic 버전이 없는 초기 MVP DB도 처리하며, 알 수 없는 스키마는 중단합니다.
다른 DB 파일에는 `--database /path/to/db`를 사용합니다. 운영 DBMS 변경은 별도 작업입니다.

## 결산 기준

- 금액은 원 단위 양의 정수입니다. 입출금 방향으로 증감을 표현합니다.
- 최초 원장의 이전 잔액만 이월금으로 등록합니다. 결손 이월은 출금 방향입니다.
- 다음 기간의 기초 잔액은 이전 거래 누계에서 자동 계산합니다. 같은 잔액을 다시 등록하지 않습니다.
- 기말 잔액 = 기초 잔액 + 기간 내 이월금 + 입금 − 출금.
- 이자는 입금 합계에 포함하며 별도 표시합니다. 이월금은 입금·출금 실적에서 분리합니다.
- 결산은 조회 시 계산하는 보고서이며 확정·마감·잠금이나 새 거래 생성 기능은 아닙니다.

## 구조와 확장

FastAPI + SQLAlchemy + SQLite + Jinja2. `src/services/ledger.py`에 집계와 조회 규칙을 두고 API와 화면이 공유합니다.
기존 장학사업 코드는 확장 기능으로 보존하고 기본 메뉴에서는 제외했습니다. 기존 API와 데이터는 유지됩니다.
거래 목록의 수정/이력 버튼을 사용합니다. 수정 사유는 필수이며 동시 수정은 충돌로 안내합니다.
내용/메모는 입출금 공통이고 금액은 입력·출력에 천 단위 쉼표를 표시하며 DB에는 정수로 저장합니다.
보고서의 발표 대시보드 버튼으로 `/finance/dashboard`에 이동합니다. 도표는 외부 서비스 없이 자체 표시하며,
개인 이름·입금처·메모를 제외합니다. 발표 모드는 Esc로 종료하고 인쇄/PDF로 자료를 저장할 수 있습니다.
GAS 연결은 하지 않습니다. 취소·증빙·계좌별 원장·승인·결산 확정은 향후 확장 대상입니다.
DB·백업·CSV·Excel·PDF·로그 등 로컬 자료는 Git에서 제외됩니다.

- [REQUIREMENTS.md](REQUIREMENTS.md): 현재 범위
- [DATABASE.md](DATABASE.md): 원장 데이터
- [API.md](API.md): 실제 API
- [UI_UX_PLAN.md](UI_UX_PLAN.md): 기본 화면
- [E2E_SCENARIO.md](E2E_SCENARIO.md): 검증 시나리오
- [AI_PROGRESS.md](AI_PROGRESS.md): 진행 기록 및 인수인계
- [DEVELOPMENT.md](DEVELOPMENT.md): 개발 규칙
- `docs/archive/scholarship-mvp/`: 전환 전 문서 (현재 요구사항 기준이 아님)

```bash
python -m pytest -q
```
