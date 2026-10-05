# 입출금 원장 데이터 설계

## 활성 모델

`finance_transactions`를 독립 원장으로 사용한다. 신청서·선발 결과 생성 없이 기록할 수 있다.

| 컬럼 | 의미 |
|---|---|
| id | 거래 식별자 |
| transaction_date | 거래일, 수동 입력은 날짜의 00:00 |
| transaction_type | income 또는 expense |
| amount | 원 단위 양의 정수 |
| counterparty | 출금 대상 이름 또는 입금처; 기존 데이터는 NULL 유지 |
| category | general/donation/interest/carryover/scholarship/operating/other |
| description | 입금·출금 공통 내용 / 메모 |
| version | 수정 버전; 기본 1, 동시 수정 충돌 방어 |
| external_reference | 유일한 거래번호; 수동 입력에서 생략하면 자동 생성 |
| source_filename | CSV 입력 출처; 수동 입력은 NULL |
| created_by / created_at | 작성자 / 생성 시각 |

## 계산

기간 이전의 입금−출금 누계가 기초 잔액이다. 기간 내 carryover는 별도 순액으로 계산한다.
이월금을 제외한 입출금과 기간 내 이월금을 더해 기말 잔액을 계산한다.
보고서의 이자는 입금 합계에 포함된다. 집계 보고서를 다시 조회해도 거래가 늘지 않는다.
같은 이름은 합산한다. 기존 NULL 거래처는 '기존 내역 (미기재)' 그룹에 표시한다.

## 마이그레이션

- `0001_initial_schema`: 기존 MVP 스키마
- `0002_simple_finance`: counterparty, category 추가 및 거래일 인덱스
- `0003_finance_history`: version 및 finance_transaction_history 추가
- 기존 금액·내용·거래번호·지급 참조는 보존한다.
- 이미 기록된 원장에는 이월금을 자동 삽입하지 않는다.
- `python scripts/upgrade_finance.py`: SQLite 백업 후 버전 확인/이관
- Git은 DB를 포함하지 않는다. DB 백업은 storage/backups에 따로 보관한다.

기존 장학 모델은 보존되며 상세 설계는 `docs/archive/scholarship-mvp/DATABASE.md`를 참고한다.

`finance_transaction_history`는 거래 ID, 수정 후 버전, 수정자 ID, UTC 시각, 사유,
변경 전/후 JSON을 보존한다. 거래 변경과 이력은 함께 커밋/롤백한다.
수정 전 기록도 첫 수정의 before에 보존하며, 기능 도입 이전의 변경 내역은 복원하지 않는다.
직접 SQL로 DB를 변경하면 앱의 이력 기록을 우회하므로 수정은 앱을 통해 수행한다.
