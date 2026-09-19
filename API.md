# API 설계

## 1. 기본 원칙

- 기본 경로는 `/api/v1`로 시작한다.
- JSON 요청과 응답을 기본으로 하며 파일은 별도 업로드 규칙을 사용한다.
- 인증이 필요한 API는 인증 토큰과 역할 권한을 확인한다.
- 목록 API는 `page`, `size`, `sort`, 검색 조건을 일관되게 지원한다.
- 상태 변경 API는 중복 요청에 대비한 멱등성 정책을 적용한다.

## 2. 응답 형식 초안

성공 응답은 리소스 또는 목록을 반환하고, 실패 응답은 다음 필드를 기본으로 사용합니다.

```json
{
  "code": "APPLICATION_NOT_FOUND",
  "message": "신청 정보를 찾을 수 없습니다.",
  "requestId": "request-id"
}
```

목록 응답은 `items`, `page`, `size`, `total`을 포함합니다.

## 3. 인증 및 사용자

| Method | Endpoint | 설명 | 권한 |
|---|---|---|---|
| `POST` | `/auth/login` | 로그인 | 공개 |
| `POST` | `/auth/logout` | 로그아웃 | 인증 |
| `GET` | `/me` | 내 정보 조회 | 인증 |
| `GET` | `/users` | 사용자 목록 | 관리자 |
| `PATCH` | `/users/{userId}/roles` | 역할 변경 | 관리자 |

## 4. 사업 및 공고

| Method | Endpoint | 설명 | 권한 |
|---|---|---|---|
| `GET` | `/programs` | 사업 목록 | 인증 |
| `POST` | `/programs` | 사업 생성 | 담당자 |
| `GET` | `/programs/{programId}` | 사업 상세 | 인증 |
| `PATCH` | `/programs/{programId}` | 사업 수정 | 담당자 |
| `GET` | `/announcements` | 공고 목록 | 인증 |
| `POST` | `/programs/{programId}/announcements` | 공고 생성 | 담당자 |
| `PATCH` | `/announcements/{announcementId}/status` | 공고 상태 변경 | 담당자 |

초기 CRUD API는 `/api` 접두사를 사용한다.

| Method | Endpoint | 설명 | 권한 |
|---|---|---|---|
| `GET` | `/api/programs` | 장학 사업 목록 | 인증 사용자 |
| `POST` | `/api/programs` | 장학 사업 생성 | 관리자·사업 담당자 |
| `GET` | `/api/programs/{programId}` | 장학 사업 상세 | 인증 사용자 |
| `PATCH` | `/api/programs/{programId}` | 장학 사업 수정 | 관리자·사업 담당자 |
| `DELETE` | `/api/programs/{programId}` | 장학 사업 삭제 | 관리자·사업 담당자 |
| `GET` | `/api/announcements` | 공고 목록 | 인증 사용자 |
| `POST` | `/api/announcements` | 공고 생성 | 관리자·사업 담당자 |
| `GET` | `/api/announcements/{announcementId}` | 공고 상세 | 인증 사용자 |
| `PATCH` | `/api/announcements/{announcementId}` | 공고 수정 | 관리자·사업 담당자 |
| `DELETE` | `/api/announcements/{announcementId}` | 공고 삭제 | 관리자·사업 담당자 |
| `POST` | `/api/applications` | 장학금 신청서 제출 | 신청자 |
| `GET` | `/api/applications/me` | 내 신청서 목록 | 신청자 |
| `POST` | `/api/review-criteria` | 공고 심사 기준 생성 | 관리자·사업 담당자 |
| `GET` | `/api/review-criteria/{announcementId}` | 공고 심사 기준 조회 | 관리자·사업 담당자 |
| `POST` | `/api/review-assignments` | 신청 건 심사위원 배정 | 관리자·사업 담당자 |
| `GET` | `/api/review-assignments/me` | 내 심사 배정 조회 | 심사위원 |
| `POST` | `/api/review-assignments/{assignmentId}/recusal` | 심사 회피 | 심사위원 |
| `PUT` | `/api/review-assignments/{assignmentId}/review` | 기준별 심사 점수 저장 | 심사위원 |
| `POST` | `/api/followups` | 선발자 사후보고 제출 | 신청자 |
| `GET` | `/api/followups/me` | 내 사후보고 조회 | 신청자 |
| `POST` | `/api/finance/transactions/import` | 통합기금 CSV 거래내역 반영 | 관리자·사업 담당자·지급 담당자 |
| `GET` | `/api/finance/overview` | 입금·지출·잔액 요약 | 관리자·사업 담당자·지급 담당자 |
| `POST` | `/api/selections` | 최종 선발 또는 미선발 결정 | 관리자·사업 담당자 |
| `GET` | `/api/selections` | 선발 결과 목록 | 관리자·사업 담당자 |
| `POST` | `/api/selections/{selectionId}/payments` | 장학금 지급 기록 | 관리자·사업 담당자·지급 담당자 |
| `POST` | `/api/applications/{applicationId}/documents` | 신청 증빙 업로드 | 신청자 본인 |
| `POST` | `/api/followups/{followupId}/documents` | 사후보고 증빙 업로드 | 신청자 본인 |
| `GET` | `/api/documents/application/{documentId}` | 신청 증빙 다운로드 | 본인·관리자·사업 담당자 |
| `GET` | `/api/documents/followup/{documentId}` | 사후보고 증빙 다운로드 | 본인·관리자·사업 담당자 |

## 5. 신청 및 서류

| Method | Endpoint | 설명 | 권한 |
|---|---|---|---|
| `POST` | `/announcements/{announcementId}/applications` | 신청서 생성 | 신청자 |
| `GET` | `/applications` | 신청 목록 | 권한 범위 |
| `GET` | `/applications/{applicationId}` | 신청 상세 | 권한 범위 |
| `PATCH` | `/applications/{applicationId}` | 임시 신청서 수정 | 신청자 |
| `POST` | `/applications/{applicationId}/submit` | 신청서 제출 | 신청자 |
| `POST` | `/applications/{applicationId}/documents` | 서류 업로드 | 신청자 |
| `POST` | `/applications/{applicationId}/supplement` | 보완자료 제출 | 신청자 |

## 6. 심사, 선발, 지급

| Method | Endpoint | 설명 | 권한 |
|---|---|---|---|
| `POST` | `/announcements/{announcementId}/review-assignments` | 심사 배정 | 담당자 |
| `GET` | `/reviews/assignments` | 내 심사 배정 조회 | 심사자 |
| `PUT` | `/review-assignments/{assignmentId}/review` | 심사 결과 저장 | 심사자 |
| `POST` | `/applications/{applicationId}/recusal` | 심사 회피 신청 | 심사자 |
| `POST` | `/announcements/{announcementId}/selection` | 선발 결과 확정 | 담당자 |
| `GET` | `/selections` | 선발 결과 조회 | 권한 범위 |
| `POST` | `/selections/{selectionId}/payments` | 지급 계획 등록 | 담당자 |
| `PATCH` | `/payments/{paymentId}` | 지급 결과 갱신 | 담당자 |

## 7. 통지 및 통계

| Method | Endpoint | 설명 | 권한 |
|---|---|---|---|
| `POST` | `/notifications` | 통지 발송 요청 | 담당자 |
| `GET` | `/notifications` | 통지 이력 조회 | 권한 범위 |
| `GET` | `/statistics/programs/{programId}` | 사업 통계 조회 | 담당자 |

## 8. API 결정 필요 사항

- 인증 토큰 방식과 만료 정책
- 오류 코드 목록과 HTTP 상태 코드 매핑
- 파일 업로드 방식과 저장소
- 비동기 통지 및 지급 처리 방식
- API 문서 도구와 실제 스키마 형식
