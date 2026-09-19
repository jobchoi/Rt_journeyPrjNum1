"""Run cheap, dependency-free checks for the first database migration."""

from pathlib import Path
import sqlite3


ROOT = Path(__file__).resolve().parents[1]
MIGRATION = ROOT / "database" / "migrations" / "0001_initial_auth_programs.sql"


def main() -> None:
    connection = sqlite3.connect(":memory:")
    connection.execute("PRAGMA foreign_keys = ON")
    connection.executescript(MIGRATION.read_text(encoding="utf-8"))

    tables = {
        row[0]
        for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'"
        )
    }
    expected_tables = {
        "users",
        "roles",
        "user_roles",
        "scholarship_programs",
        "announcements",
        "applications",
        "review_criteria",
        "review_assignments",
        "reviews",
        "fund_categories",
        "prayer_requests",
        "prayer_request_access_logs",
    }
    assert expected_tables <= tables
    assert not tables.intersection(
        {"sponsors", "sponsorship_commitments", "sponsorship_matches"}
    )

    role_count = connection.execute("SELECT COUNT(*) FROM roles").fetchone()[0]
    assert role_count == 6

    prayer_columns = {
        row[1]
        for row in connection.execute("PRAGMA table_info(prayer_requests)")
    }
    assert "content" in prayer_columns
    assert "review_id" not in prayer_columns
    assert "score" not in prayer_columns
    prayer_foreign_keys = {
        row[2]
        for row in connection.execute("PRAGMA foreign_key_list(prayer_requests)")
    }
    assert prayer_foreign_keys == {"users"}

    connection.execute(
        "INSERT INTO users (id, email, password_hash, name) VALUES (?, ?, ?, ?)",
        ("user-1", "admin@example.test", "hash", "관리자"),
    )
    connection.execute(
        "INSERT INTO user_roles (user_id, role_id) VALUES (?, ?)",
        ("user-1", "role-admin"),
    )
    connection.execute(
        "INSERT INTO scholarship_programs (id, name, created_by) VALUES (?, ?, ?)",
        ("program-1", "2026 장학사업", "user-1"),
    )
    connection.execute(
        "INSERT INTO prayer_requests (id, user_id, content) VALUES (?, ?, ?)",
        ("prayer-1", "user-1", "중보기도 제목"),
    )
    connection.execute(
        "INSERT INTO announcements (id, program_id, title, status, created_by) "
        "VALUES (?, ?, ?, ?, ?)",
        ("announcement-1", "program-1", "2026 모집 공고", "open", "user-1"),
    )
    connection.execute(
        "INSERT INTO applications (id, applicant_id, announcement_id, study_plan, financial_need) "
        "VALUES (?, ?, ?, ?, ?)",
        ("application-1", "user-1", "announcement-1", "학업 계획", "경제적 필요"),
    )

    print("Initial schema validation passed.")


if __name__ == "__main__":
    main()