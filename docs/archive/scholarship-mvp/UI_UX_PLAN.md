# Rt Journey UI/UX 계획서

## 1. 목적

현재 구현된 서버 렌더링 화면과 앞으로 필요한 운영 화면을 하나의 정보 구조로 정리한다. 모든 화면은 Jinja2와 Tailwind CSS CDN을 사용하며, 별도 프론트엔드 빌드 없이 FastAPI에서 렌더링한다.

핵심 UX 원칙:

- 역할별로 필요한 업무만 노출한다.
- 개인정보와 기도제목은 최소 권한으로 분리한다.
- 운영 화면은 빠른 판단과 반복 업무에 맞춰 정보 밀도와 여백을 균형 있게 구성한다.
- 신청자 화면은 불안감을 줄이고 현재 상태와 다음 행동을 명확하게 보여준다.
- 글래스모피즘, `rounded-2xl`·`rounded-3xl`, `bg-gray-50`, 넉넉한 여백, 은은한 그림자를 공통 시각 언어로 유지한다.

## 2. 역할 및 화면 접근 정책

| 역할 | 주요 화면 | 허용 업무 |
|---|---|---|
| 비로그인 사용자 | `/login`, `/register` | 로그인·신청자 계정 생성 |
| 신청자 | `/announcements`, `/applications/new`, `/my-page` | 공고 확인, 신청, 본인 상태·사후보고 확인 |
| 장학위원 | `/reviewer/dashboard` | 배정된 신청 열람, 기준별 점수·의견 입력, 심사 회피 |
| 사업 담당자 | `/admin/dashboard`, `/admin/applications/{id}` | 사업·공고 운영, 신청서 열람, 심사 배정, 선발 |
| 관리자 | 사업 담당자 화면 전체 | 사용자·역할·기준정보와 운영 정책 관리 |
| 지급 담당자 | `/admin/dashboard`, 지급 관련 상세 | 통합기금 잔액 확인, 지급 처리 |
| 사역 담당자 | 향후 `/care` | 승인된 기도제목의 중보기도·목회적 돌봄 |

브라우저 웹 화면은 쿠키 인증을 사용한다. 인증이 없는 웹 요청은 `/login`으로 303 리다이렉트하고, `/api/` 요청은 JSON 401을 유지한다.

## 3. 전체 사이트맵

```text
/
├── /login                         공개: 로그인
├── /register                      공개: 신청자 계정 생성
├── /announcements                 신청자: 모집 중·심사 중·종료 공고 목록
│   └── /applications/new          신청자: 특정 공고 신청서 작성·제출
├── /my-page                       신청자: 내 신청 상태·지급 상태·사후보고
├── /reviewer/dashboard            장학위원: 내 심사 배정 목록
│   └── /reviewer/assignments/{id} 장학위원: 신청 내용·기준별 평가·회피
├── /admin/dashboard               관리자·사업 담당자: 운영 요약·재정 Overview
├── /admin/applications            관리자·사업 담당자: 신청서 검색·필터 목록
│   └── /admin/applications/{id}   관리자: 신청 상세·서류·선발·지급
├── /admin/programs                관리자·사업 담당자: 사업·공고 관리
├── /admin/reviews                 관리자·사업 담당자: 기준·심사위원 배정
├── /admin/finance                 관리자·지급 담당자: CSV·입출금·잔액
└── /care                          사역 담당자: 승인된 기도제목·돌봄 기록 (향후)
```

현재 구현된 경로:

- `/login`
- `/register`
- `/announcements`
- `/applications/new?announcement_id={id}`
- `/admin/dashboard`

이번 작업에서 추가할 경로:

- `/reviewer/dashboard`
- `/my-page`
- `/admin/applications/{application_id}`

## 4. 공통 레이아웃

대상 파일: `templates/base.html`

- 상단 브랜드와 현재 사용자 표시
- 역할에 따른 메뉴 노출
- 모바일에서는 메뉴를 단순화하고 본문 우선 배치
- 배경: `bg-gray-50`에 아주 약한 radial 분위기
- 패널: 반투명 흰색, `backdrop-blur`, `border-white/80`
- 카드: `rounded-2xl` 또는 `rounded-3xl`
- 버튼: 명확한 텍스트와 익숙한 아이콘을 함께 사용
- 상태 배지: 모집·심사·선발·지급 상태를 색상 하나에 의존하지 않고 텍스트로 병기

## 5. 누락 화면 명세

### 5.1 심사위원 대시보드: `reviewer_dashboard.html`

라우터: `GET /reviewer/dashboard`

권한: `reviewer`

목적:

- 본인에게 배정된 신청 건만 빠르게 확인한다.
- 회피한 건은 평가 대상에서 분리한다.
- 신청서의 학업·경제·사역 정보와 평가 기준을 구분해 보여준다.

화면 구성:

- 상단: `검토 대기`, `작성 완료`, `회피` 요약
- 목록: 신청자 식별자, 공고명, 배정일, 평가 진행률, 상태
- 상세 패널: 기준명·최대 점수·점수 입력·기준별 의견
- 액션: 저장, 제출, 심사 회피

금지 사항:

- 기도제목을 점수 입력 화면에 표시하지 않는다.
- 총점 계산이나 순위에 기도제목 데이터를 연결하지 않는다.
- 배정되지 않은 신청서를 URL 조작으로 열 수 없게 한다.

연결 API:

- `GET /api/review-assignments/me`
- `PUT /api/review-assignments/{assignment_id}/review`
- `POST /api/review-assignments/{assignment_id}/recusal`

### 5.2 신청자 마이페이지: `my_page.html`

라우터: `GET /my-page`

권한: `applicant`

목적:

- 신청자가 자신의 진행 상태를 한 화면에서 이해한다.
- 심사 진행, 선발 결과, 지급 상태, 사후보고 다음 행동을 확인한다.

화면 구성:

- 현재 단계 타임라인: 신청 완료 → 심사 중 → 선발 결과 → 지급 → 사후보고
- 신청 카드: 공고명, 제출일, 현재 상태, 신청 상세 링크
- 선발 시: 지급 예정액과 지급 상태 표시
- 선발 후: 사후보고 작성 버튼과 제출 이력
- 증빙 파일: 본인이 업로드한 파일명·종류·등록일·다운로드

연결 API:

- `GET /api/applications/me`
- `GET /api/followups/me`
- `POST /api/followups`
- `POST /api/applications/{application_id}/documents`
- `GET /api/documents/application/{document_id}`

### 5.3 관리자 신청 상세: `admin_application_detail.html`

라우터: `GET /admin/applications/{application_id}`

권한: `administrator`, `program_manager`

목적:

- 신청서 검토부터 선발·지급까지 한 업무 화면에서 처리한다.
- 첨부파일과 심사 상태를 확인하되, 기도제목을 심사 근거로 노출하지 않는다.

화면 구성:

- 신청자·공고·제출 상태 헤더
- 학업 계획, 경제적 필요, 사역 계획 섹션
- 증빙 파일 목록과 안전한 다운로드 버튼
- 심사 배정·평가 현황
- 선발 패널: 선발/미선발, 지급 예정액
- 지급 패널: 지급 금액, 지급 수단, 거래번호
- 변경 이력과 처리자 표시 영역

연결 API:

- `GET /api/applications/{application_id}` 또는 관리자 전용 상세 API
- `GET /api/documents/application/{document_id}`
- `POST /api/selections`
- `POST /api/selections/{selection_id}/payments`
- `GET /api/finance/overview`

## 6. 관리자 권한 정책

- `administrator`: 전체 운영과 사용자·역할 정책 관리
- `program_manager`: 사업·공고·신청·심사·선발 처리
- `finance`: 재정 CSV, 지급 및 잔액 관련 기능만 접근
- `reviewer`: 배정된 심사 건만 접근
- `applicant`: 자신의 신청·서류·지급·사후보고만 접근
- `ministry_worker`: 승인된 기도제목과 돌봄 데이터만 접근

초기 최고 관리자 생성은 공개 회원가입에서 분리한다. `ALLOW_ROLE_REGISTRATION=true`는 로컬 테스트 전용으로 유지하고, 운영에서는 별도 superuser 생성 명령을 사용한다.

## 7. 구현 순서

승인 후 `feature/missing-views`에서 다음 순서로 진행한다.

1. 화면 라우터의 데이터 조회와 역할 의존성 추가
2. `reviewer_dashboard.html` 작성 및 심사 API 연결
3. `my_page.html` 작성 및 신청·사후보고 API 연결
4. `admin_application_detail.html` 작성 및 선발·지급·파일 API 연결
5. 템플릿 렌더링, 권한 차단, API 호출 흐름 pytest 추가
6. `git flow feature finish missing-views`로 `develop` 병합

## 8. 완료 기준

- 각 역할이 허용된 화면만 열 수 있다.
- 비로그인 웹 요청은 `/login`으로 이동한다.
- reviewer는 배정 건만 평가할 수 있다.
- applicant는 타인의 신청·파일·사후보고를 조회할 수 없다.
- 관리자 신청 상세에서 선발·지급 액션이 API와 연결된다.
- 기도제목은 심사 점수·순위·선발 근거로 노출되거나 사용되지 않는다.
- 데스크톱과 모바일에서 카드·폼·상태 정보가 겹치지 않는다.