"""Period accounting, ledger access, atomic CSV imports and migration preservation."""
import csv
import io
import sqlite3
from pathlib import Path
from uuid import uuid4

from alembic import command
from alembic.config import Config


def headers(client, role="finance"):
    email = f"ledger-{uuid4().hex}@example.test"
    password = "LedgerPass123"
    assert client.post("/auth/register", json={"email": email, "password": password,
                       "name": "원장 테스트", "role_code": role}).status_code == 201
    token = client.post("/auth/login", json={"email": email, "password": password}).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_period_accounting_and_report(client):
    auth = headers(client)
    marker = uuid4().hex
    def record(day, direction, amount, party, category, description="사용 내용"):
        result = client.post("/api/finance/transactions", headers=auth, json={
            "transaction_date": day, "transaction_type": direction, "amount": amount,
            "counterparty": party, "category": category, "description": description})
        assert result.status_code == 201, result.text
        return result.json()
    record("2040-01-01", "income", 1000, "이전 잔액", "carryover")
    before = client.get("/api/finance/reports?end=2040-01-31", headers=auth).json()["closing_balance"]
    record("2040-02-01", "income", 500, marker + "교회", "donation")
    record("2040-02-02", "income", 20, "은행", "interest")
    record("2040-02-28", "expense", 200, marker + "홍길동", "scholarship")
    record("2040-03-01", "expense", 50, marker + "홍길동", "other")
    response = client.get("/api/finance/reports?start=2040-02-01&end=2040-02-28", headers=auth)
    report = response.json()
    assert report["opening_balance"] == before
    assert report["total_income"] == 520 and report["interest"] == 20
    assert report["total_expense"] == 200 and report["carryover"] == 0
    assert report["closing_balance"] == before + 320
    assert report["recipients"] == [{"name": marker + "홍길동", "amount": 200}]
    assert report["transaction_count"] == 3
    page = client.get("/api/finance/transactions", headers=auth, params={"q": marker, "size": 1}).json()
    assert page["total"] == 3 and len(page["items"]) == 1
    html = client.get("/finance?start=2040-02-01&end=2040-02-28", headers=auth)
    assert html.status_code == 200 and marker + "홍길동" in html.text
    exported = client.get("/api/finance/reports/export?start=2040-02-01&end=2040-02-28", headers=auth)
    assert exported.status_code == 200 and "기말 잔액" in exported.text
    assert marker + "홍길동" in exported.text and "2040-03-01" not in exported.text
    assert client.get("/", headers=auth, follow_redirects=False).headers["location"] == "/finance"


def test_permissions_validation_duplicates_and_csv(client):
    auth = headers(client)
    applicant = headers(client, "applicant")
    for route in ["/api/finance/transactions", "/api/finance/reports", "/api/finance/reports/export", "/api/finance/template"]:
        assert client.get(route, headers=applicant).status_code == 403
        assert client.get(route).status_code == 401
    assert client.get("/finance", headers=applicant).status_code == 403
    assert client.get("/finance", follow_redirects=False).status_code == 303
    body = {"transaction_date": "2041-01-01", "transaction_type": "expense", "amount": 10,
            "counterparty": "=SUM(1,2)", "description": "@SUM(1)", "category": "other", "external_reference": uuid4().hex}
    assert client.post("/api/finance/transactions", headers=auth, json=body).status_code == 201
    assert client.post("/api/finance/transactions", headers=auth, json=body).status_code == 409
    for change in [{"amount": 0}, {"amount": 1.5}, {"category": "interest"}, {"counterparty": "  "}, {"description": " "}]:
        invalid = dict(body, **change, external_reference=uuid4().hex)
        assert client.post("/api/finance/transactions", headers=auth, json=invalid).status_code == 422
    assert client.get("/api/finance/reports?start=2041-02-01&end=2041-01-01", headers=auth).status_code == 422
    exported = client.get("/api/finance/reports/export?start=2041-01-01&end=2041-01-01", headers=auth)
    rows = list(csv.reader(io.StringIO(exported.text.lstrip("\ufeff"))))
    assert any("'=SUM(1,2)" in row and "'@SUM(1)" in row for row in rows)
    marker = uuid4().hex
    base = "\ufefftransaction_date,transaction_type,amount,description,external_reference,counterparty,category\n"
    content = base + f"2042-01-01,income,30,입금,{marker},교회,donation\n2042-01-02,expense,10,오류,{marker}-bad,은행,interest\n"
    assert client.post("/api/finance/transactions/import", headers=auth, files={"file": ("data.csv", content.encode(), "text/csv")}).status_code == 422
    assert client.get("/api/finance/transactions?q=교회&start=2042-01-01", headers=auth).json()["total"] == 0
    content = base + f"2042-01-01,income,30,입금,{marker},교회,donation\n"
    assert client.post("/api/finance/transactions/import", headers=auth, files={"file": ("data.csv", content.encode(), "text/csv")}).status_code == 201
    assert client.post("/api/finance/transactions/import", headers=auth, files={"file": ("data.csv", content.encode(), "text/csv")}).status_code == 409


def test_upgrade_preserves_unversioned_data(tmp_path, monkeypatch):
    from scripts.upgrade_finance import upgrade
    database = tmp_path / "legacy.db"
    with sqlite3.connect(database) as connection:
        connection.executescript(Path("database/migrations/0001_initial_auth_programs.sql").read_text())
        connection.execute("INSERT INTO users (id,email,password_hash,name) VALUES ('u','test@example.test','unused','테스트')")
        connection.execute("INSERT INTO finance_transactions (id,transaction_date,transaction_type,amount,description,external_reference,created_by) VALUES ('t','2026-01-01','income',100,'기존 입금','old-ref','u')")
    previous = __import__('os').environ["DATABASE_URL"]
    monkeypatch.setenv("DATABASE_URL", previous)
    upgrade(database, tmp_path / "backups")
    with sqlite3.connect(database) as connection:
        assert connection.execute("SELECT amount,category,counterparty FROM finance_transactions WHERE id='t'").fetchone() == (100, "general", None)
    assert len(list((tmp_path / "backups").glob("*.db"))) == 1
    config = Config("alembic.ini")
    command.downgrade(config, "0001_initial_schema")
    with sqlite3.connect(database) as connection:
        assert connection.execute("SELECT amount FROM finance_transactions WHERE id='t'").fetchone()[0] == 100
    command.upgrade(config, "head")


def test_corrections_are_persisted_audited_and_conflict_checked(client):
    from sqlalchemy import select
    from src.database import SessionLocal
    from src.models import FinanceTransaction, FinanceTransactionHistory
    auth = headers(client)
    applicant = headers(client, "applicant")
    body = {"transaction_date": "2045-02-01", "transaction_type": "income", "amount": 1234567,
            "counterparty": "수정검증", "category": "general", "description": "입금 메모"}
    original = client.post("/api/finance/transactions", headers=auth, json=body).json()
    route = '/api/finance/transactions/' + original['id']
    update = dict(body, amount=2345678, description="입금 금액 정정", expected_version=1, change_reason="영수증 대조")
    assert client.put(route, headers=applicant, json=update).status_code == 403
    assert client.get(route + '/history', headers=applicant).status_code == 403
    assert client.put(route, json=update).status_code == 401
    assert client.put(route, headers=auth, json=dict(update, change_reason=" ")).status_code == 422
    assert client.put(route, headers=auth, json=dict(update, amount=1.1)).status_code == 422
    result = client.put(route, headers=auth, json=update)
    assert result.status_code == 200, result.text
    assert result.json()['version'] == 2
    assert result.json()['external_reference'] == original['external_reference']
    assert client.put(route, headers=auth, json=update).status_code == 409
    history = client.get(route + '/history', headers=auth).json()['items']
    assert len(history) == 1 and history[0]['reason'] == '영수증 대조'
    assert history[0]['before']['amount'] == 1234567 and history[0]['after']['amount'] == 2345678
    assert history[0]['changed_by'] == '원장 테스트'
    assert client.put(route, headers=auth, json=dict(update, expected_version=2)).status_code == 200
    assert len(client.get(route + '/history', headers=auth).json()['items']) == 1
    with SessionLocal() as db:
        assert db.get(FinanceTransaction, original['id']).amount == 2345678
        assert db.scalar(select(FinanceTransactionHistory).where(FinanceTransactionHistory.transaction_id == original['id'])).after['version'] == 2
    duplicate = client.post('/api/finance/transactions', headers=auth, json=dict(body, external_reference=uuid4().hex)).json()
    assert client.put(route, headers=auth, json=dict(update, expected_version=2, amount=42, external_reference=duplicate['external_reference'])).status_code == 409
    assert client.get(route, headers=auth).json()['amount'] == 2345678
    assert len(client.get(route + '/history', headers=auth).json()['items']) == 1
    assert client.get('/api/finance/transactions/nonexistent/history', headers=auth).status_code == 404
    html = client.get('/finance?start=2045-02-01&end=2045-02-01', headers=auth).text
    assert '2,345,678' in html and '내용 / 메모' in html and 'data-history=' in html


def test_concurrent_corrections_reject_lost_update(client):
    from sqlalchemy.orm.exc import StaleDataError
    from src.database import SessionLocal
    from src.models import FinanceTransaction
    import pytest
    auth = headers(client)
    transaction = client.post('/api/finance/transactions', headers=auth, json={
        'transaction_date':'2046-01-01', 'transaction_type':'income', 'amount':100,
        'counterparty':'동시수정', 'description':'원본'}).json()
    with SessionLocal() as first, SessionLocal() as second:
        a = first.get(FinanceTransaction, transaction['id'])
        b = second.get(FinanceTransaction, transaction['id'])
        a.amount = 200
        first.commit()
        b.amount = 300
        with pytest.raises(StaleDataError):
            second.commit()
        second.rollback()
    assert client.get('/api/finance/transactions/' + transaction['id'], headers=auth).json()['amount'] == 200


def test_presentation_dashboard_aggregates_without_personal_names(client):
    from src.database import SessionLocal
    from src.services.ledger import dashboard_report
    auth = headers(client)
    for direction, amount, category in [('income', 100000, 'donation'), ('expense', 30000, 'operating'), ('income', 20000, 'carryover')]:
        assert client.post('/api/finance/transactions', headers=auth, json={
            'transaction_date':'2047-03-01', 'transaction_type':direction, 'amount':amount,
            'category':category, 'counterparty':'발표에서 숨길 개인이름', 'description':'민감한메모'}).status_code == 201
    from datetime import date
    with SessionLocal() as db:
        data = dashboard_report(db, date(2047, 3, 1), date(2047, 3, 31))
        assert data['monthly'] == [{'month':'2047-03', 'income':100000, 'expense':30000}]
        assert data['categories'] == [{'label':'운영비', 'amount':30000}]
        assert data['summary']['carryover'] == 20000
    response = client.get('/finance/dashboard?start=2047-03-01&end=2047-03-31', headers=auth)
    assert response.status_code == 200
    assert '100,000' in response.text and '월별 입출금 비교' in response.text
    assert '발표에서 숨길 개인이름' not in response.text and '민감한메모' not in response.text
    assert 'cdn.' not in response.text
    assert client.get('/finance/dashboard?start=2047-04-01&end=2047-04-30', headers=auth).status_code == 200
    assert client.get('/finance/dashboard', headers=headers(client, 'applicant')).status_code == 403
    assert client.get('/finance/dashboard', follow_redirects=False).status_code == 303
