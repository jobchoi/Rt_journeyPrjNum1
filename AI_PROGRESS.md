# AI 협업 진행 기록

이 문서는 다른 AI 또는 개발자가 프로젝트 상태를 빠르게 파악하고, 같은 문제를 재현하며, 다음 feature를 이어서 구현하기 위한 인수인계 기록입니다.

## 현재 상태

- 기준 커밋: `83681c8 feat: add scholarship program and announcement APIs`
- 이번 작업: 장학 사업 및 공고 화면 Step 2
- 현재 브랜치: `main`
- Jinja2 + Tailwind CDN 화면 구현 완료

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

## 알려진 제한

- `ALLOW_ROLE_REGISTRATION=true`는 로컬 테스트용이며 운영에서 사용하지 않는다.
- `JWT_SECRET_KEY` 기본값은 개발용 placeholder이므로 운영 환경에서 반드시 환경변수로 지정한다.
- 현재 데이터베이스 초기화는 `Base.metadata.create_all` 기반이다. 운영 마이그레이션은 Alembic 도입이 필요하다.
- 화면은 서버 렌더링되며, 브라우저에서 Bearer 인증을 전달할 별도 로그인 UI는 아직 없다.
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

## 다음 권장 작업

1. 브라우저 로그인·토큰 쿠키 또는 프론트 API 클라이언트 결정
2. 관리자 생성 폼의 API 제출 연결
3. API 자동화 테스트 파일을 `tests/`에 정식 추가
4. Alembic 마이그레이션 도입