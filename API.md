# 현재 입출금 API

접두사: `/api/finance`. 권한: administrator / program_manager / finance.
기존 Bearer JWT와 access_token 쿠키 인증을 지원한다.

| Method | 경로 | 기능 |
|---|---|---|
| POST | /transactions | 수동 거래 등록 |
| GET | /transactions/{id} | 거래 상세 및 version |
| PUT | /transactions/{id} | 전체 필드 수정, expected_version와 change_reason 필수 |
| GET | /transactions/{id}/history | 최초 등록 정보와 변경 전후 이력 |
| GET | /transactions | 원장 목록 및 검색 |
| POST | /transactions/import | CSV 전체 검증 후 가져오기 |
| GET | /overview | 기존 호환 전체 입금/출금/잔액 |
| GET | /reports | 기간 결산, 출금 대상별/입금처별 집계 |
| GET | /reports/export | 기간 전체 보고서 CSV |
| GET | /template | 가져오기 예시 CSV |

수동 등록 JSON 예시:

```json
{
  "transaction_date": "2026-10-04",
  "transaction_type": "expense",
  "amount": 100000,
  "counterparty": "홍길동",
  "category": "scholarship",
  "description": "10월 장학금"
}
```

external_reference는 선택이다. 생략하면 새 거래번호가 만들어진다.
동일 거래 재시도의 중복을 막으려면 동일 external_reference를 지정해야 한다.
거래번호 충돌은 409, 유효하지 않은 입력은 422, 권한 부족은 403이다.
수정은 등록 필드에 expected_version(현재 버전), change_reason(수정 사유)을 추가한다.
거래번호 생략 시 기존 번호를 유지한다. 동시 수정/지급 연계 거래는 409,
없는 거래는 404이며 변경 없는 저장은 버전과 이력을 추가하지 않는다.
내용(description)은 입금·출금 공통 메모다. 금액은 쉼표 없는 JSON 정수다.
자체 발표 화면은 `/finance/dashboard?start=YYYY-MM-DD&end=YYYY-MM-DD`이며 같은 재정 권한을 요구한다.

목록 쿼리: start/end(YYYY-MM-DD, 양끝 날짜 포함), transaction_type, category, q(거래처/내용), page(1부터), size(1~100).
목록 응답: items/page/size/total. 보고서는 start/end만 사용하며 다른 목록 검색 조건을 적용하지 않는다.
reports 응답: opening_balance, carryover, total_income, interest, total_expense, closing_balance, transaction_count, recipients, sources.
overview는 기존 계약을 유지하며 이월금도 입출금 누계에 포함한다. 기간 결산은 reports를 사용한다.

CSV: UTF-8/BOM, 최대 5MB. 필수 열 transaction_date, transaction_type, amount, description, external_reference.
선택 열 counterparty, category. 분류 생략 시 general. 입력은 부분 성공 없이 전체 저장 또는 전체 실패한다.
다운로드는 UTF-8 BOM과 스프레드시트 수식 방어를 적용한다.

보존된 장학 API의 이전 설계는 `docs/archive/scholarship-mvp/API.md`에 있다.
