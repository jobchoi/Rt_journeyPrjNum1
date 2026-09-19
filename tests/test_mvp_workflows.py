"""Regression coverage for the MVP workflows."""

from uuid import uuid4

def register_and_login(client, role: str = "applicant") -> tuple[dict, dict]:
    email = f"{role}-{uuid4().hex}@example.test"
    password = "MvpPass123"
    response = client.post(
        "/auth/register",
        json={"email": email, "password": password, "name": role, "role_code": role},
    )
    assert response.status_code == 201, response.text
    token = client.post(
        "/auth/login", json={"email": email, "password": password}
    ).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}, {"email": email, "password": password}


def create_open_announcement(client, admin_headers: dict) -> dict:
    program = client.post(
        "/api/programs",
        headers=admin_headers,
        json={"name": "pytest 사업", "status": "active"},
    ).json()
    response = client.post(
        "/api/announcements",
        headers=admin_headers,
        json={"program_id": program["id"], "title": "pytest 공고", "status": "open"},
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_browser_unauthenticated_pages_redirect_to_login(client):
    dashboard = client.get("/admin/dashboard", follow_redirects=False)
    announcements = client.get("/announcements", follow_redirects=False)
    api_response = client.get("/api/applications/me", follow_redirects=False)
    assert dashboard.status_code == 303
    assert dashboard.headers["location"] == "/login"
    assert announcements.status_code == 303
    assert announcements.headers["location"] == "/login"
    assert api_response.status_code == 401
    assert api_response.json()["detail"] == "인증 토큰이 필요합니다."


def test_auth_and_application_flow(client):
    admin_headers, _ = register_and_login(client, "administrator")
    applicant_headers, _ = register_and_login(client)
    announcement = create_open_announcement(client, admin_headers)

    application = client.post(
        "/api/applications",
        headers=applicant_headers,
        json={
            "announcement_id": announcement["id"],
            "study_plan": "학업 계획",
            "financial_need": "경제적 필요",
            "ministry_plan": "사역 계획",
        },
    )
    assert application.status_code == 201, application.text
    assert client.get("/api/applications/me", headers=applicant_headers).status_code == 200
    assert client.post("/api/applications", headers=admin_headers, json={}).status_code == 403


def test_review_selection_payment_and_followup(client):
    admin_headers, _ = register_and_login(client, "administrator")
    applicant_headers, _ = register_and_login(client)
    finance_headers, _ = register_and_login(client, "finance")
    announcement = create_open_announcement(client, admin_headers)
    application = client.post(
        "/api/applications",
        headers=applicant_headers,
        json={
            "announcement_id": announcement["id"],
            "study_plan": "학업 계획",
            "financial_need": "경제적 필요",
        },
    ).json()

    criterion = client.post(
        "/api/review-criteria",
        headers=admin_headers,
        json={"announcement_id": announcement["id"], "code": "need", "name": "필요성", "max_score": 10},
    ).json()
    selection = client.post(
        "/api/selections",
        headers=admin_headers,
        json={"application_id": application["id"], "status": "selected", "amount": 500000},
    )
    assert selection.status_code == 201, selection.text
    payment = client.post(
        f"/api/selections/{selection.json()['id']}/payments",
        headers=finance_headers,
        json={"amount": 500000, "payment_method": "transfer", "external_reference": uuid4().hex},
    )
    assert payment.status_code == 201, payment.text
    followup = client.post(
        "/api/followups",
        headers=applicant_headers,
        json={"application_id": application["id"], "academic_update": "보고", "ministry_update": "사역 보고"},
    )
    assert followup.status_code == 201, followup.text
    assert criterion["max_score"] == 10


def test_finance_import_and_document_access(client):
    admin_headers, _ = register_and_login(client, "administrator")
    applicant_headers, _ = register_and_login(client)
    announcement = create_open_announcement(client, admin_headers)
    application = client.post(
        "/api/applications",
        headers=applicant_headers,
        json={
            "announcement_id": announcement["id"],
            "study_plan": "학업",
            "financial_need": "필요",
        },
    ).json()
    csv = "transaction_date,transaction_type,amount,description,external_reference\n2026-09-19,income,100000,입금,pytest-1\n"
    imported = client.post(
        "/api/finance/transactions/import",
        headers=admin_headers,
        files={"file": ("ledger.csv", csv, "text/csv")},
    )
    assert imported.status_code == 201, imported.text
    overview = client.get("/api/finance/overview", headers=admin_headers).json()
    assert overview["total_income"] >= 100000 and overview["transaction_count"] >= 2
    uploaded = client.post(
        f"/api/applications/{application['id']}/documents",
        headers=applicant_headers,
        files={"file": ("proof.pdf", b"pdf-test", "application/pdf")},
    )
    assert uploaded.status_code == 201, uploaded.text
    document = client.get(
        f"/api/documents/application/{uploaded.json()['id']}", headers=applicant_headers
    )
    assert document.status_code == 200 and document.content == b"pdf-test"
