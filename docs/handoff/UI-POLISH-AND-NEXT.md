# 작업 지시서 — 가져오기 화면 다듬기 + 추후 확장 결정안

- 지시: Claude Code · 구현: Codex · 검증: Claude Code(데모 DB로 브라우저 확인)
- 브랜치: `feature/bank-excel-import` (변경·커밋·push 금지)
- 먼저 읽을 것: AI_CONTEXT.md 순서(AI_PROGRESS → REQUIREMENTS → DATABASE → API → TASKS), templates/finance.html, src/services/bank_import.py, tests/test_bank_import.py

## A. 구현(Claude 화면 QC에서 발견)
1. "은행 거래내역 가져오기"의 "열 불러오기"가 버튼처럼 보이지 않음 → 다른 버튼과 같은 스타일.
2. 미리보기 표: 잔액에 천 단위 쉼표, 날짜는 `2026-11-01 09:12`처럼 사람이 읽는 형식(현재 `2026-11-01T09:12:00`).
3. 미리보기 표에 머리글 행(선택, 행, 상태, 날짜, 구분, 금액, 잔액, 내용, 사유) 추가.
4. 암호가 걸린 xlsx를 올리면 "암호가 걸린 파일입니다. 은행 앱에서 암호 없이 내보내거나 엑셀에서 암호를 해제한 뒤 올려 주세요." 안내(현재 일반 손상 메시지). 테스트 추가(암호 파일 시그니처로 판별, 실제 은행 파일 불필요).
5. 테스트 추가·기존 테스트 유지, `python -m pytest -q` 통과.

## B. 문서만(구현 금지): TASKS "추후 확장" 4개의 결정안
`docs/handoff/NEXT_DECISIONS.md`에 항목별로: 하려는 일, 선택지 2~3개(장단점), 권장안, 사용자가 답해야 할 질문(회계 규칙·권한·보존 기간 등). 대상: 거래 취소·정정, 증빙 첨부·계좌별 원장·동명이인, 결산 확정·잠금·승인, 운영 인증 쿠키·배포·복구·모니터링.

## 하지 말 것
- 실제 거래내역·DB·개인정보 사용, 결산·취소 로직 구현(결정 전), 의존성 추가
- 커밋·push·브랜치 변경, TASKS.md·AI_PROGRESS.md 수정(Claude가 검증 후 기록)

## 보고
1. 수정 파일 2. A1~5 충족/미충족/미검증 + 근거 3. pytest 결과 4. NEXT_DECISIONS.md 요약
