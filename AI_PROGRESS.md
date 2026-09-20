# AI 협업 진행 기록

이 문서는 다른 AI 또는 개발자가 프로젝트 상태를 빠르게 파악하고, 같은 문제를 재현하며, 다음 feature를 이어서 구현하기 위한 인수인계 기록입니다.

## 현재 상태

- 기준 커밋: `e5d2d4d feat: add scholarship management views`
- 이번 작업: 장학금 신청 접수 Step 4
- 현재 브랜치: `feature/application-form`
- 신청 API와 Jinja2 신청 폼 구현 완료

## 완료된 기능

### 인증 및 권한

- bcrypt 비밀번호 해싱
- JWT 발급 및 검증
- 회원가입·로그인 API
- 관리자 전용 역할 목록 API
- 관리자 및 사업 담당자 역할 Dependency

### 프로그램 및 공고 API

- `GET/POST/PATCH/DELETE /api/programs`
- `GET/POST/PATCH/DELETE /api/announcements`
- 인증 사용자의 조회 권한
- `administrator`, `program_manager`의 생성·수정·삭제 권한
- 프로그램·공고 상태값과 날짜·선발 인원 검증
- 프로그램과 공고의 존재하는 외래 참조 확인

### 서버 렌더링 화면

- `GET /admin/dashboard`: 관리자·사업 담당자 전용 대시보드
- `GET /announcements`: 인증 사용자용 공고 목록
- 공통 Glassmorphism 레이아웃과 Inter 폰트
- 관리자 화면의 프로그램 생성 폼과 사업 목록
- 향후 CSV/GAS 연계를 위한 Finance Overview 예고 영역
- 공고 상태, 선발 인원, 모집 기간 카드 표시

### 브라우저 인증 Step 3

- `GET /login`, `GET /register` 화면
- 로그인 화면의 `fetch('/auth/login')` 호출
- 로그인 성공 시 `access_token` 쿠키 저장
- 로그인 응답 역할에 따른 관리자·신청자 리다이렉트
- `get_current_user`가 Authorization Bearer와 `access_token` 쿠키를 모두 지원
- 일반 회원가입은 신청자 역할로 생성

### 장학금 신청 Step 4

- `applications` 모델: 신청자, 공고, 상태, 학업 계획, 경제적 필요, 사역 계획
- 신청자·공고 조합 유니크 제약으로 중복 신청 방지
- `POST /api/applications`: `applicant` 역할 전용 제출
- `GET /api/applications/me`: 본인 신청 내역 조회
- `GET /applications/new?announcement_id=...`: 신청 폼
- 모집 중 공고 카드의 `신청하기` 버튼 연결
- 신청 성공 후 공고 목록으로 이동

### 심사 워크플로 Step 5

- `review_criteria`: 공고별 기준과 최대 점수
- `review_assignments`: 신청 건과 reviewer 배정, 회피 사유
- `reviews`: 배정 건의 기준별 점수와 의견
- `POST /api/review-criteria`: 관리자·사업 담당자 기준 생성
- `POST /api/review-assignments`: 관리자·사업 담당자 배정
- `GET /api/review-assignments/me`: reviewer 본인 배정 조회
- `POST /api/review-assignments/{id}/recusal`: reviewer 회피
- `PUT /api/review-assignments/{id}/review`: 배정된 reviewer의 점수 저장
- 점수는 기준별 `max_score`를 초과할 수 없고 기도제목 테이블과 연결되지 않음

### 장학금 신청 Step 4

- `applications` 모델: 신청자, 공고, 상태, 학업 계획, 경제적 필요, 사역 계획
- 신청자·공고 조합 유니크 제약으로 중복 신청 방지
- `POST /api/applications`: `applicant` 역할 전용 제출
- `GET /api/applications/me`: 본인 신청 내역 조회
- `GET /applications/new?announcement_id=...`: 신청 폼
- 모집 중 공고 카드의 `신청하기` 버튼 연결
- 신청 성공 후 공고 목록으로 이동

## 재현 가능한 검증

의존성 설치:

```bash
/home/jobchoi/miniforge3/bin/python -m pip install -r requirements.txt
```

초기 SQL 정책 검증:

```bash
python scripts/validate_initial_schema.py
```

서버 실행:

```bash
export JWT_SECRET_KEY="local-test-secret"
export ALLOW_ROLE_REGISTRATION=true
/home/jobchoi/miniforge3/bin/python -m uvicorn src.main:app --reload --host 127.0.0.1 --port 8001
```

기본 API:

```bash
curl http://127.0.0.1:8001/health
curl http://127.0.0.1:8001/docs
```

프로그램·공고 API는 Bearer JWT가 필요합니다.

## 검증 결과

- `scripts/validate_initial_schema.py`: 통과
- `src` 및 `scripts` Python compileall: 통과
- VS Code/Pylance 진단: 오류 없음
- OpenAPI에 프로그램·공고 API 등록 확인
- 임시 SQLite DB에서 인증 및 프로그램·공고 CRUD 흐름 통과
- 인증 없는 프로그램 조회: `401`
- 권한 없는 쓰기 요청: `403`
- 관리자 대시보드 HTML 렌더링: `200`
- 신청자 공고 목록 HTML 렌더링: `200`
- 신청자의 관리자 대시보드 접근: `403`
- 심사 기준·배정·평가 흐름: 통과
- 기준 최대점 초과 평가: `422`
- 기도제목과 심사 외래키 분리: 확인

### 사후관리·재정 Step 6

- `followups`: 선발된 신청자의 학업·사역 사후보고
- `POST /api/followups`, `GET /api/followups/me`: 신청자 본인 권한
- `finance_transactions`: 교회 통합기금 입출금 원장
- `POST /api/finance/transactions/import`: UTF-8 CSV 업로드와 거래번호 중복 방지
- `GET /api/finance/overview`: 총 입금·총 지출·잔액·거래 건수
- 관리자 대시보드 Finance Overview에 집계값과 CSV 업로드 UI 연결
- 개인 후원자·1:1 매칭 정보는 저장하지 않음

### 선발·지급·파일 Step 7

- `selections`: 신청서별 최종 선발/미선발 결정과 지급 예정액
- `payments`: 지급 결과와 통합기금 `expense` 거래 연결
- 지급 거래번호 중복 및 선발 금액 초과 지급 방지
- `application_documents`, `followup_documents`: UUID 저장명 기반 증빙 메타데이터
- PDF/JPEG/PNG, 10MB 제한, 신청자 본인 업로드
- 본인·관리자·사업 담당자만 다운로드 가능
- 신청자와 기도제목 데이터는 파일 권한이나 선발 계산에 혼합하지 않음

### 운영 준비·테스트 Step 8

- `alembic.ini`, `alembic/env.py`, `alembic/versions/0001_initial_schema.py` 추가
- 기존 초기 SQL을 Alembic `upgrade head`로 적용하고 `downgrade base`로 롤백 가능
- `tests/conftest.py`, `tests/test_mvp_workflows.py` 추가
- 인증·신청·선발·지급·사후관리·CSV·증빙 핵심 흐름 pytest 정식화
- 관리자 대시보드에 총 신청자·선발자·재정 잔액 지표 추가

### 브라우저 401 UX 보완

- 인증 없는 웹 뷰 요청은 `303 /login`으로 이동
- `/api/` 인증 오류는 기존 `401` JSON 응답 유지
- `tests/test_mvp_workflows.py`에 두 응답 정책 회귀 테스트 추가

### UI/UX 계획 및 누락 화면

- `UI_UX_PLAN.md`에 전체 사이트맵·역할·화면 명세 작성
- `scripts/create_superuser.py`: 공개 역할 가입과 분리된 초기 administrator 생성 CLI
- `GET /reviewer/dashboard`: 배정된 심사 건과 기준별 평가 입력
- `GET /my-page`: 본인 신청 상태와 선발 후 사후보고·증빙 흐름
- `GET /admin/applications/{application_id}`: 관리자 신청 원문·증빙·기도제목·선발·지급
- 세 화면 모두 역할 Dependency와 공통 Glassmorphism 레이아웃 사용
- 로그인·회원가입 화면 렌더링: `200`
- 쿠키만 사용한 관리자 대시보드 접근: `200`
- 쿠키만 사용한 신청자 공고 목록 접근: `200`
- 신청 폼 렌더링: `200`
- 신청서 제출 및 본인 조회: 통과
- 중복 신청: `409`
- 신청자의 관리자 대시보드 접근: `403`
- 선발 신청자의 사후보고 제출·조회: 통과
- 재정 CSV 업로드·잔액 집계·중복 거래번호 차단: 통과
- 선발·지급·재정 expense 연결: 통과
- 증빙 PDF 업로드·다운로드와 파일 권한: 통과
- pytest MVP 회귀 테스트: `3 passed`
- Alembic upgrade/current/downgrade: 통과
- 브라우저 401 리다이렉트·API 401 JSON 회귀 테스트: 통과
- 누락 화면 역할별 렌더링·접근 차단: 통과
- superuser CLI `--help`·문법 검증: 통과
- 신청 폼 렌더링: `200`
- 신청서 제출 및 본인 조회: 통과
- 중복 신청: `409`
- 신청자의 관리자 대시보드 접근: `403`

## 알려진 제한

- `ALLOW_ROLE_REGISTRATION=true`는 로컬 테스트용이며 운영에서 사용하지 않는다.
- `JWT_SECRET_KEY` 기본값은 개발용 placeholder이므로 운영 환경에서 반드시 환경변수로 지정한다.
- 현재 데이터베이스 초기화는 `Base.metadata.create_all` 기반이다. 운영 마이그레이션은 Alembic 도입이 필요하다.
- 로그인 화면은 JavaScript로 쿠키를 설정하며, 현재 HttpOnly 쿠키 발급 방식은 아직 도입하지 않았다.
- 운영 전에는 HTTPS, `Secure`, `HttpOnly`, CSRF 방어를 포함한 쿠키 정책 검토가 필요하다.
- 관리자 생성 폼은 현재 화면 구조를 제공하며 JSON API와의 브라우저 제출 연결은 다음 UI 단계에서 보완한다.
- 실제 운영 DB, 파일 저장소, 세부 심사·신청 도메인은 아직 구현하지 않았다.

## 트러블슈팅 로그

### 2026-09-19: 8000번 포트 충돌

- 증상: Uvicorn 실행 시 `[Errno 98] Address already in use`
- 원인: 기존 Uvicorn 프로세스가 8000번 포트를 사용 중
- 해결: 기존 서버를 재사용하거나 8001번 포트로 실행
- 검증: `curl http://127.0.0.1:8001/health`에서 `{"status":"ok"}` 확인

### 2026-09-19: FastAPI 테스트 클라이언트 초기화

- 증상: lifespan을 실행하지 않은 `TestClient`에서 `roles` 테이블을 찾지 못함
- 원인: 테스트 클라이언트를 context manager로 열지 않아 앱 startup이 실행되지 않음
- 해결: `with TestClient(app) as client:` 형태로 사용
- 검증: 인증·역할·CRUD 통합 흐름 통과

### 2026-09-19: 브라우저 쿠키 인증 추가

- 증상: 브라우저에서 화면 URL을 직접 열면 Authorization 헤더가 없어 `401 Unauthorized`
- 원인: 기존 인증 Dependency가 Bearer 헤더만 확인
- 수정: `src/dependencies.py`에서 `access_token` 쿠키를 fallback으로 확인하고, 로그인 UI에서 성공 토큰을 쿠키에 저장
- 검증: 로그인 응답 역할 확인, 쿠키만으로 관리자 대시보드·공고 목록 접근, 신청자의 대시보드 `403`

### 2026-09-19: 신청 API 검증 중 쿠키 필수 오류

- 증상: Bearer 헤더를 보낸 관리자 API 요청이 `422`로 응답
- 원인: `access_token` Cookie 의존성이 선택값이 아닌 필수값으로 선언됨
- 수정: Cookie 인자의 기본값을 `None`으로 설정
- 검증: 관리자 공고 생성과 applicant 신청 제출 흐름 재통과

### 2026-09-19: Step 6 사후관리·재정 연동

- 설계: 사후보고는 선택된 신청에만 허용하고, 재정은 조직 통합기금 거래번호를 기준으로 멱등성을 확보
- 검증: 사후보고 권한, CSV 필수 컬럼·입출금 집계·중복 방지 흐름 확인

### 2026-09-19: Step 7 선발·지급·파일

- 설계: 지급을 `payments`와 `finance_transactions(expense)`로 함께 기록하고 외부 거래번호를 유일하게 유지
- 보안: 업로드 파일은 UUID 저장명, 확장자·10MB 제한, 소유자/운영자 권한 검사
- 검증: 선발·지급·잔액·파일 업로드/다운로드 전체 흐름 통과

### 2026-09-19: Step 8 운영 준비

- 검증: pytest 정식 테스트 3개 통과, Alembic 초기 migration 적용·롤백 통과

### 2026-09-19: 누락 화면 및 superuser CLI

- 구현: 심사위원·신청자·관리자 화면과 역할 보호 라우터 추가
- 구현: superuser CLI는 비밀번호를 `getpass`로 입력받고 `ALLOW_ROLE_REGISTRATION` 없이 administrator를 생성
- 검증: 세 화면 200/403 접근 정책과 CLI 문법·도움말 확인

### 2026-09-19: 심사 워크플로 구현

- 설계: 심사 기준, 배정, 평가를 별도 테이블로 분리하고 `prayer_requests`를 참조하지 않음
- 검증: 관리자 기준 생성·배정, reviewer 점수 저장, 점수 상한 오류, 권한 분리 통과

### 2026-09-20: 공고 생성 흐름 및 공개 목록 연결

- 증상: 프로그램 생성은 JSON 전송으로 정상 동작하지만, 관리자 대시보드에서 공고 생성이 이어지지 않고 일반 계정의 `/announcements` 목록에 `open` 공고가 보이지 않음
- 원인 1: 관리자 대시보드에 공고 생성 폼이 없고, `POST /api/announcements`를 브라우저가 URL-encoded로 보내는 구조였음
- 원인 2: 공개 목록 뷰에서 `Announcement.status.in_(["open", "reviewing", "finished"])`로 걸러서 일반 계정이 비공개 상태 공고까지 보이게 되어 있었음
- 수정: 관리자 대시보드에 `announcement-form`을 추가하고 `JSON.stringify()` + `application/json` fetch로 생성하도록 변경
- 수정: `/announcements` 뷰를 `status == "open"`으로 제한해 일반 계정 목록의 공개 공고만 렌더링
- 검증: 관리자→프로그램 생성→공고 생성→신청자 목록 조회 흐름을 `TestClient`로 검증하고 `200 OK`와 `open` 공고 노출 확인

### 2026-09-20: E2E 시나리오 문서화 및 시드 스크립트 추가

- 목적: 전체 장학금 관리 사이클을 다른 AI가 빠르게 이해할 수 있도록 문서화하고, UI/백엔드 검증을 위한 테스트 계정/더미 데이터를 자동 생성한다.
- 추가 파일: `E2E_SCENARIO.md`, `scripts/seed_e2e_test.py`
- 문서 내용: 사업 생성 → 공고 등록 → 신청 → 심사위원 배정 및 평가 → 최종 선발 및 지급 → 사후보고까지의 전체 사이클과 각 단계별 의존성 매핑
- 의존성 매핑: `templates/*.html` → `src/routers/*.py` → `src/models.py` → `src/routers/views.py` 흐름을 명시하고, 불필요한 파일을 열지 않도록 추천 읽기 순서를 정리
- 시드 스크립트 내용: 관리자/신청자/심사위원 계정을 자동 생성하고, 사업·공고·신청서·심사배정의 1개 E2E 더미 데이터를 DB에 바로 삽입
- 실행 결과: 터미널에 각 계정의 이메일·비밀번호를 출력하고, 화면 이동 경로를 안내
- 검증: 스크립트 실행 경로와 계정 생성 로직 확인

### 2026-09-20: 공고 목록 신청 여부 직관성 개선

- 증상: 일반 신청자가 `/announcements` 화면에서 자신이 이미 신청한 공고인지 직관적으로 구분할 수 없었음
- 원인: 서버 렌더링 시 `Application` 기반 신청 여부를 템플릿에 전달하지 않아 카드 액션 상태가 표시되지 않음
- 수정: `/announcements` 라우터에서 신청자 역할일 때 `Application.announcement_id` 목록을 조회해 `applied_announcement_ids`로 템플릿에 전달
- 수정: `announcements_list.html`에서 `announcement.id in applied_announcement_ids` 조건을 사용해 신청 완료 버튼을 회색 비활성 상태로 렌더링
- 검증: `TestClient`로 공개 공고 목록을 조회해 신청 완료 상태가 시각적으로 구분되는 HTML을 확인

### 2026-09-20: CSV 업로드 BOM 오류 해결 및 검증 로직 강화

- 증상: Excel이 추가한 BOM 또는 누락된 헤더가 있는 CSV 업로드에서 컬럼 인식 실패와 파싱 오류가 발생함
- 원인: `utf-8-sig` 처리와 필수 컬럼 누락 검증이 명시적으로 구현되지 않아 헤더 인식이 불안정했고, 오류 메시지가 모호했음
- 수정: `src/routers/finance.py`에서 CSV를 `utf-8-sig`로 디코딩하고, 필수 컬럼 `transaction_date`, `transaction_type`, `amount`, `description`, `external_reference` 존재 여부를 엄격히 검사
- 수정: 누락 시 `400` 상태와 `필수 컬럼이 누락되었습니다: ...` 메시지를 JSON으로 반환하도록 예외 메시지를 명확하게 변경
- 수정: `templates/admin_dashboard.html`에서 CSV 업로드 안내 문구를 추가해 필수 헤더 형식을 사용자에게 표시
- 검증: 올바른 BOM 포함 CSV와 누락된 컬럼 CSV를 직접 넣어 정상 처리와 오류 응답을 확인

### 2026-09-20: CSV 업로드 422 에러 및 BOM 파싱 로직 수정

- 증상: 관리자 대시보드에서 CSV 업로드 시 multipart/form-data 전송 구조와 BOM 포함 헤더가 충돌해 `422 Unprocessable Content`가 발생함
- 원인 1: 브라우저가 `FormData`를 보낼 때 `Content-Type`을 직접 설정하면 multipart boundary가 깨지며 업로드 파싱이 실패함
- 원인 2: 엑셀 저장 CSV에 BOM이 포함되면 첫 헤더 이름이 `f...`처럼 인식되어 필수 컬럼 검증이 실패함
- 수정: `templates/admin_dashboard.html`에서 파일 업로드를 `new FormData(event.target)`로 전달하고, `headers`를 제거해 브라우저가 multipart boundary를 자동 생성하도록 변경
- 수정: `src/routers/finance.py`에서 `utf-8-sig` 디코딩, 필수 헤더 검증, 그리고 400 JSON 에러 메시지로 예외 처리를 일관시키도록 보강
- 검증: 정상 CSV 업로드와 누락 헤더 CSV를 직접 넣어 201/400 응답을 확인했다.

### 2026-09-19: 신청 API 검증 중 쿠키 필수 오류

- 증상: Bearer 헤더를 보낸 관리자 API 요청이 `422`로 응답
- 원인: `access_token` Cookie 의존성이 선택값이 아닌 필수값으로 선언됨
- 수정: Cookie 인자의 기본값을 `None`으로 설정
- 검증: 관리자 공고 생성과 applicant 신청 제출 흐름 재통과

## 다음 권장 작업

1. 운영용 HttpOnly/Secure 쿠키와 CSRF 방어 결정
2. 관리자 생성 폼의 API 제출 연결
3. API 자동화 테스트 파일을 `tests/`에 정식 추가
4. 운영용 HttpOnly/Secure 쿠키와 CSRF 방어 결정