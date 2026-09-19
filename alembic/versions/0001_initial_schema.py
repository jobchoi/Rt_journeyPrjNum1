"""Create the complete local SQLite schema."""

from pathlib import Path
from typing import Sequence, Union

from alembic import op


revision: str = "0001_initial_schema"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


TABLES = (
    "followup_documents",
    "application_documents",
    "payments",
    "selections",
    "reviews",
    "review_assignments",
    "review_criteria",
    "finance_transactions",
    "followups",
    "prayer_request_access_logs",
    "prayer_requests",
    "applications",
    "announcements",
    "fund_categories",
    "scholarship_programs",
    "user_roles",
    "users",
    "roles",
)


def upgrade() -> None:
    sql_path = Path(__file__).resolve().parents[2] / "database" / "migrations" / "0001_initial_auth_programs.sql"
    connection = op.get_bind()
    if connection.dialect.name == "sqlite":
        connection.connection.driver_connection.executescript(sql_path.read_text(encoding="utf-8"))
    else:
        op.execute(sql_path.read_text(encoding="utf-8"))


def downgrade() -> None:
    connection = op.get_bind()
    for table in TABLES:
        connection.exec_driver_sql(f"DROP TABLE IF EXISTS {table}")
