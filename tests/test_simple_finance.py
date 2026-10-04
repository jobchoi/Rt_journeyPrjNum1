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
