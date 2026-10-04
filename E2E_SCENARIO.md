# 입출금 E2E 검증

1. 관리자 또는 지급 담당자로 로그인하여 /finance로 이동한다.
2. 원장을 처음 시작하는 경우 이전 잔액을 이월금으로 등록한다.
3. 교회를 입금처로 후원금, 은행을 입금처로 이자를 등록한다.
4. 해당 인원의 이름, 금액, 장학금 등 출금 사유를 등록한다.
5. 날짜 범위와 이름으로 목록을 검색한다.
6. 출금 대상별 합계와 입금처별 합계, 이자를 확인한다.
7. 기말 잔액 = 기초 잔액 + 이월금 + 입금 - 출금인지 확인한다.
8. CSV 보고서와 인쇄/PDF를 확인한다.
9. 중복 거래번호, 잘못된 금액/분류, 다른 역할의 접근을 차단한다.
10. CSV 오류가 있으면 일부 행도 저장되지 않아야 한다.

## 자동 검증

`python -m pytest -q`

- tests/test_simple_finance.py: 기간 경계, 집계, 검색, 화면, 권한, 중복, CSV 원자성, 수식 방어, 백업 migration 및 rollback 데이터 보존
- tests/test_mvp_workflows.py: 기존 장학업무 회귀

연결: templates/finance.html → src/routers/finance.py 및 views.py → src/services/ledger.py → FinanceTransaction.
