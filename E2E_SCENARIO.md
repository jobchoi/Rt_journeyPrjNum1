# E2E 시나리오 문서

## 1. 목적

이 문서는 장학금 관리 전반의 비즈니스 사이클을 빠르게 검증할 때 필요한 중심 흐름과, 다른 AI 에이전트가 어떤 파일을 열어야 하는지 정리한 문서다.

주요 목표는 다음과 같다.

- 사업 생성 → 공고 등록 → 신청 접수 → 심사위원 배정 → 최종 선발 → 재정 지급 → 사후보고까지의 전체 사이클을 재현한다.
- 화면 단위 UI와 API 단위 로직이 어떤 파일에 연결되는지 명확히 기록한다.
- 향후 작업자가 불필요한 파일을 읽지 않고, 지금 단계에서 필요한 파일만 열 수 있게 만든다.

---

## 2. 전체 비즈니스 사이클

### 단계 1: 사업 생성

- 관리자 또는 사업 담당자가 운영 대시보드에서 장학 사업을 생성한다.
- 사업 기본 정보는 `ScholarshipProgram` 모델에 저장된다.
- 이 단계에서 브라우저와 서버의 연결은 다음과 같다.

  - 프론트엔드: `templates/admin_dashboard.html`
  - 백엔드: `src/routers/programs.py`
  - DB 모델: `src/models.py`의 `ScholarshipProgram`

- 주요 점:
  - 관리자 대시보드의 `program-form`은 `POST /api/programs`를 호출한다.
  - `ProgramCreate` 스키마는 `name`, `description`, `status`, `application_start_at`, `application_end_at`을 검증한다.
  - `created_by`는 로그인한 관리자의 사용자 ID가 연결된다.

### 단계 2: 공고 등록

- 생성된 사업을 기준으로 공고를 공개 상태로 등록한다.
- 신청자가 접근할 수 있는 목록은 `/announcements`에서 렌더링된다.
- 연결 파일:

  - 프론트엔드: `templates/admin_dashboard.html`
  - 프론트엔드(공개 목록): `templates/announcements_list.html`
  - 백엔드: `src/routers/announcements.py`
  - DB 모델: `src/models.py`의 `Announcement`
  - 뷰 라우트: `src/routers/views.py`의 `announcements_list()`

- 주요 점:
  - 관리자 화면의 `announcement-form`이 `POST /api/announcements`를 전송한다.
  - 공고는 `program_id`, `title`, `target_description`, `selected_count`, `status` 등을 담아 저장한다.
  - 공개 목록은 `Announcement.status == "open"` 조건을 만족하는 공고만 렌더링해야 한다.

### 단계 3: 렘넌트 신청

- 신청자가 `/announcements`에서 공고를 보고 신청서를 제출한다.
- 신청서는 `Application` 모델에 저장된다.
- 연결 파일:

  - 프론트엔드: `templates/announcements_list.html`
  - 프론트엔드: `templates/application_form.html`
  - 백엔드: `src/routers/applications.py`
  - DB 모델: `src/models.py`의 `Application`
  - 뷰 라우트: `src/routers/views.py`의 `application_form()`

- 주요 점:
  - 신청은 `POST /api/applications`를 사용하며, 신청자와 공고 조합이 중복되지 않게 제약된다.
  - `Application.applicant_id`와 `Application.announcement_id`는 `UniqueConstraint`로 보호된다.
  - `announcement.status`가 `open`이어야 접근 가능하다.

### 단계 4: 심사위원 배정 및 평가

- 관리자는 신청서를 선택하고 심사위원을 배정한다.
- 심사기준과 점수는 `ReviewCriterion`, `ReviewAssignment`, `Review` 모델이 담당한다.
- 연결 파일:

  - 프론트엔드: `templates/reviewer_dashboard.html`
  - 백엔드: `src/routers/reviews.py`
  - DB 모델: `src/models.py`의 `ReviewCriterion`, `ReviewAssignment`, `Review`
  - 뷰 라우트: `src/routers/views.py`의 `reviewer_dashboard()`

- 주요 점:
  - 심사 기준은 특정 공고와 연결되며 `announcement_id`와 `code` 조합이 유일해야 한다.
  - 심사위원은 `reviewer` 역할 사용자를 지정하고, `ReviewAssignment`으로 배정된다.
  - `PUT /api/review-assignments/{assignment_id}/review`로 점수 제출이 가능하다.

### 단계 5: 최종 선발 및 지급

- 심사 결과를 바탕으로 관리자가 `Selection`을 생성한다.
- 지급 담당자는 `Payment`와 `FinanceTransaction`을 연결해 금액을 처리한다.
- 연결 파일:

  - 백엔드: `src/routers/selections.py`
  - 백엔드: `src/routers/finance.py`
  - DB 모델: `src/models.py`의 `Selection`, `Payment`, `FinanceTransaction`
  - 프론트엔드: `templates/admin_dashboard.html`의 Finance Overview 영역

- 주요 점:
  - `Selection.status`는 `selected` 또는 `rejected`만 허용한다.
  - 지급은 `finance_transactions`의 `expense` 레코드와 연결되며, 중복 거래번호를 막는 제약이 있다.

### 단계 6: 사후보고

- 최종 선발자는 본인 페이지에서 사후보고를 제출한다.
- 연결 파일:

  - 프론트엔드: `templates/my_page.html`
  - 백엔드: `src/routers/followups.py`
  - DB 모델: `src/models.py`의 `Followup`

- 주요 점:
  - 신청자 본인의 `Followup` 기록을 관리한다.
  - 본인 신청 건과 연결되며, 제출 이후 운영자가 확인할 수 있게 한다.

---

## 3. 파일 의존성 매핑

다음 표는 각 단계별로 어떤 파일을 함께 열어야 하는지 정리한 표다.

| 단계 | 템플릿 | 백엔드 라우터 | DB 모델 | 핵심 확인 포인트 |
| --- | --- | --- | --- | --- |
| 사업 생성 | `templates/admin_dashboard.html` | `src/routers/programs.py` | `ScholarshipProgram` | 관리자 대시보드에서 `/api/programs` 호출 |
| 공고 등록 | `templates/admin_dashboard.html`, `templates/announcements_list.html` | `src/routers/announcements.py`, `src/routers/views.py` | `Announcement` | 공고 공개 상태와 목록 렌더링 |
| 신청서 제출 | `templates/announcements_list.html`, `templates/application_form.html` | `src/routers/applications.py`, `src/routers/views.py` | `Application` | `announcement_id`와 사용자 매핑, 중복 신청 방지 |
| 심사 배정 | `templates/reviewer_dashboard.html` | `src/routers/reviews.py` | `ReviewCriterion`, `ReviewAssignment`, `Review` | 배정된 심사 건의 평점 및 기준 점수 |
| 선발/지급 | `templates/admin_dashboard.html` | `src/routers/selections.py`, `src/routers/finance.py` | `Selection`, `Payment`, `FinanceTransaction` | 지급 내역과 재정 집계 연결 |
| 사후보고 | `templates/my_page.html` | `src/routers/followups.py` | `Followup` | 신청자별 결과 보고 및 추적 |

---

## 4. 디렉터리 관계

### 프로젝트 구조 상 의존성

- `templates/`는 브라우저에서 사용자 화면을 렌더링하는 템플릿 디렉터리다.
- `src/routers/`는 FastAPI route 파일들이 들어 있는 디렉터리다.
- `src/models.py`는 데이터베이스 테이블 정의의 중심 파일이다.
- `src/main.py`는 App 실행, 라우터 등록, 공통 예외 처리, 기본 역할 생성 등을 담당한다.
- `src/database.py`는 SQLAlchemy 엔진과 세션 팩토리를 제공한다.

### 실제 연결 흐름

1. 브라우저에서 템플릿을 렌더링한다.
2. 템플릿이 `fetch()` 또는 폼 제출로 API를 호출한다.
3. `src/routers/*.py`가 요청을 받아 처리한다.
4. 라우터는 `Session`을 사용해 `src/models.py`의 ORM 객체를 조회하거나 저장한다.
5. 결과를 템플릿 혹은 JSON 응답으로 반환한다.

예시:

- `admin_dashboard.html` -> `POST /api/programs` -> `src/routers/programs.py` -> `ScholarshipProgram`
- `announcements_list.html` -> `GET /announcements` -> `src/routers/views.py` -> `Announcement`
- `reviewer_dashboard.html` -> `GET /api/review-assignments/me` -> `src/routers/reviews.py` -> `ReviewAssignment`

---

## 5. 다른 AI가 작업할 때 권장하는 열기 순서

다른 AI 에이전트가 이 프로젝트를 이어서 작업할 때는 아래 순서로 파일을 여는 것이 안전하다.

1. `src/main.py` — 앱 등록 및 핵심 라우터 확인
2. `src/models.py` — 어떤 DB 테이블과 관계가 있는지 확인
3. `src/routers/{step}.py` — 실제 비즈니스 로직과 권한 체크 확인
4. `templates/{step}.html` — UI 입력 폼과 결과 렌더링 확인
5. `src/routers/views.py` — 서버 렌더링 경로 및 인증 정책 확인

이 순서를 지키면 작업 범위를 좁혀서 불필요한 파일 전반을 열 필요가 없다.

---

## 6. E2E 검증 포인트

실제 UI/백엔드 E2E 검증을 수행할 때는 다음 포인트를 맞춰야 한다.

- 관리자 로그인 후 `/admin/dashboard`에서 대상 사업 생성 가능
- 공고 생성 후 `/announcements`에서 공고 카드 렌더링 확인
- 신청자 로그인 후 신청 폼에서 신청 성공 확인
- 심사위원 계정으로 `/reviewer/dashboard` 진입 및 배정 건 확인
- 심사 점수 저장 확인
- 관리자 최종 선발 및 지급 처리 확인
- 신청자 `my-page`에서 사후보고 제출 가능 여부 확인

---

## 7. 요약

장학금 관리 전체 사이클은 단일 DB 모델이 아니라 여러 모델과 템플릿, 라우터가 서로 연결된 흐름이다.

- `templates/*.html`: 사용자 입력과 화면 표시
- `src/routers/*.py`: 비즈니스 로직과 API 계약
- `src/models.py`: 영속 데이터와 관계 정의
- `src/routers/views.py`: 서버 렌더링 페이지와 권한 제어

이 구조를 기준으로 E2E 흐름을 검증하면, 데이터의 흐름을 정확하게 추적할 수 있고 불필요한 파일 열기를 줄일 수 있다.
