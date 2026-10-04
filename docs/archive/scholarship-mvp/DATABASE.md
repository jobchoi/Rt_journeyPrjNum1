# 최종 확정 데이터베이스 설계

## 1. 설계 목표

교회 조직이 운영하는 통합 장학 기금으로 Rt를 지원하는 업무를 관리합니다. 신청, 심사, 선발, 지급, 사후관리와 기도제목을 추적하되, 기도제목은 심사 데이터와 완전히 분리합니다.

개인 후원자 계정, 개인 간 1:1 매칭, 후원자와 장학생 간 직접 소통 데이터는 설계하지 않습니다.

## 2. 핵심 엔터티

| 엔터티 | 설명 |
|---|---|
| `users` | 로그인 계정과 기본 사용자 정보 |
| `roles` | 시스템 역할 정의 |
| `user_roles` | 사용자와 역할의 연결 |
| `scholarship_programs` | 장학사업 단위 |
| `announcements` | 사업별 모집 공고와 선택적 후원 카테고리 |
| `applicants` | 신청자 프로필 및 개인정보 |
| `applications` | 신청자의 공고별 신청 건 |
| `application_documents` | 신청서에 첨부된 서류 |
| `review_criteria` | 공고별 심사 기준과 배점 |
| `review_assignments` | 신청 건과 심사위원의 배정 |
| `reviews` | 심사 기준별 점수와 심사 의견 |
| `selections` | 최종 선발 결과 |
| `funds` | 교회 조직이 운영하는 통합 장학 기금 |
| `fund_categories` | 특정 국가, 지역, 전공, 사역 분야 등 선택적 재정 분류 |
| `fund_allocations` | 기금에서 사업 또는 선발자에게 배정된 재정 |
| `payments` | 장학금 지급 계획 및 결과 |
| `prayer_requests` | 중보기도 및 목회적 돌봄을 위한 기도제목 |
| `prayer_request_access_logs` | 기도제목 조회 이력 |
| `followups` | 장학생 사후관리 기록 |
| `followup_documents` | 사후관리 보고 및 활동 증빙 파일 |
| `notifications` | 신청·선발·지급 관련 안내 및 결과 통지 이력 |
| `audit_logs` | 주요 행위 감사 로그 |

## 3. 주요 엔터티 속성

### 3.1 `announcements`

- 모집 기간, 대상, 선발 인원, 지급 기준, 상태를 저장한다.
- 선택적으로 `fund_category_id`를 참조하여 특정 국가, 지역, 전공 또는 사역 분야와 연결할 수 있다.
- 카테고리 지정은 재정 또는 사업 분류를 위한 것이며, 기도제목과 연결하지 않는다.

### 3.2 `applications`

- 신청자, 공고, 신청 상태, 신청서 내용을 저장한다.
- 공고별 신청 양식이 달라질 수 있으므로 신청서 상세 항목은 고정 컬럼 또는 별도 답변 구조로 확정한다.
- 학업, 경제 상황, 사역 및 공동체 활동 정보는 공고에서 요구하는 범위로 저장한다.

### 3.3 `review_criteria`와 `reviews`

- `review_criteria`는 공고별 평가 항목, 배점, 필수 여부를 저장한다.
- `reviews`는 배정된 심사자가 기준별로 입력한 점수와 의견을 저장한다.
- 두 구조 어디에도 `prayer_requests`를 참조하지 않는다.
- 기도제목은 총점, 순위, 선발 상태에 영향을 주는 컬럼이나 계산에 사용하지 않는다.

### 3.4 `funds`, `fund_categories`, `fund_allocations`

- `funds`는 교회 조직 또는 통합 장학 기금의 명칭, 운영 상태, 회계 관리 정보를 저장한다.
- `fund_categories`는 향후 지정 후원을 위한 선택적 분류를 저장한다.
- `fund_allocations`는 기금에서 특정 사업 또는 선발 결과에 배정한 금액을 기록한다.
- 개인 후원자, 개인 후원 약정, 개인 간 매칭 정보는 저장하지 않는다.

### 3.5 `prayer_requests`

- 신청자 또는 장학생과 연결되는 별도 데이터다.
- 기도제목 본문, 상태, 작성자, 작성일, 수정일, 보존 기간을 저장한다.
- 공개 범위 또는 열람 정책은 최소 권한 원칙으로 관리한다.
- 심사 점수, 심사 의견, 선발 순위와 외래키 관계를 갖지 않는다.

### 3.6 `prayer_request_access_logs`

- 기도제목을 조회한 사용자, 조회 시각, 조회 목적, 대상 기도제목을 기록한다.
- 장학위원과 사역 담당자의 중보기도 및 목회적 돌봄 목적 조회를 추적한다.
- 로그에는 기도제목 원문을 복제하지 않는다.

## 4. 주요 관계

- `scholarship_programs` 1 : N `announcements`
- `fund_categories` 1 : N `announcements` 선택 관계
- `announcements` 1 : N `applications`
- `applicants` 1 : N `applications`
- `applications` 1 : N `application_documents`
- `announcements` 1 : N `review_criteria`
- `applications` N : N `users` through `review_assignments`
- `review_assignments` 1 : 1 `reviews` 원칙
- `review_criteria` 1 : N `reviews` 또는 심사 기준별 점수 상세 구조
- `applications` 1 : 0..1 `selections`
- `funds` 1 : N `fund_allocations`
- `fund_allocations` N : 1 `scholarship_programs` 또는 `selections`
- `selections` 1 : N `payments`
- `selections` 1 : N `followups`
- `selections` 1 : N `prayer_requests`
- `prayer_requests` 1 : N `prayer_request_access_logs`
- `followups` 1 : N `followup_documents`

기도제목과 심사 데이터 사이에는 업무 관계는 있을 수 있지만, 심사 점수나 선발 평가를 위한 데이터 관계는 두지 않습니다.

## 5. 공통 컬럼 및 무결성 규칙

주요 테이블은 `id`, `created_at`, `updated_at`를 공통으로 사용하며, 필요한 경우 `created_by`, `updated_by`, `deleted_at`을 둡니다.

- 상태값은 명시적인 코드 체계로 관리한다.
- 신청자 식별정보와 계정 식별정보를 필요 이상으로 중복 저장하지 않는다.
- 금액은 부동소수점이 아닌 정수 기반 화폐 단위로 저장한다.
- 신청서, 심사, 선발, 지급의 상태 전이는 허용된 순서만 가능해야 한다.
- 외래키와 유니크 제약으로 중복 신청, 중복 배정, 중복 지급을 방지한다.
- `prayer_requests`는 심사 점수 및 선발 순위 산정 쿼리에서 제외한다.
- `fund_allocations`와 `payments`는 중복 배정 및 중복 지급을 방지해야 한다.
- 삭제 대신 보존 정책에 맞춘 논리 삭제 또는 익명화를 우선 검토한다.

## 6. 권한 및 개인정보 보호

- 신청자는 본인의 신청 정보와 본인의 기도제목만 조회·수정한다.
- 장학위원은 배정된 신청 건의 심사 정보와 중보기도·목회적 돌봄 목적의 승인된 기도제목만 조회한다.
- 사역 담당자는 담당 범위의 장학생 기도제목을 중보기도·목회적 돌봄 목적으로 조회한다.
- 회계·지급 담당자는 지급에 필요한 기금, 배정, 계좌 및 지급 정보만 조회한다.
- 기도제목은 일반 관리자나 다른 역할에 자동으로 공개하지 않는다.
- 기도제목과 개인정보의 조회는 접근 로그로 남긴다.
- 계좌 정보는 암호화 또는 토큰화하고 일반 목록 응답에서 마스킹한다.
- 파일 저장 위치와 DB 메타데이터를 분리한다.
- `audit_logs`와 접근 로그에는 개인정보, 계좌 정보, 기도제목 원문을 기록하지 않는다.
- 보존 기간이 끝난 개인정보와 기도제목은 정책에 따라 파기 또는 복구 불가능한 익명화를 수행한다.

## 7. 범위에서 제외하는 구조

- `sponsors`: 개인 후원자 계정
- `sponsorship_commitments`: 개인 후원 약정
- `sponsorship_matches`: 개인 후원자와 장학생 간 1:1 매칭
- 후원자와 장학생 간 직접 메시지, 연락처 교환, 연락 차단 이력

교회 조직 또는 통합 장학 기금 자체의 운영 정보만 `funds`로 관리합니다.

## 8. 상세 설계 시 확정할 항목

- 신청서 상세 항목 저장 방식
- 기도제목의 상태와 보존 기간
- 장학위원과 사역 담당자의 담당 범위 계산 방식
- 기금 카테고리의 종류와 공고 연결 규칙
- 기금 배정과 실제 지급의 회계 관계
- DBMS, 인덱스, 마이그레이션 버전 관리
- 백업, 복구, 보존 및 파기 절차
