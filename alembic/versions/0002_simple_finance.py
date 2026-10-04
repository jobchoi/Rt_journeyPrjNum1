"""Extend the existing ledger without deleting scholarship or payment data."""
from alembic import op
import sqlalchemy as sa

revision = "0002_simple_finance"
down_revision = "0001_initial_schema"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("finance_transactions", sa.Column("counterparty", sa.String(200), nullable=True))
    op.add_column("finance_transactions", sa.Column("category", sa.String(50), nullable=False, server_default="general"))
    op.create_index("ix_finance_transactions_date", "finance_transactions", ["transaction_date"])


def downgrade():
    op.drop_index("ix_finance_transactions_date", table_name="finance_transactions")
    op.drop_column("finance_transactions", "category")
    op.drop_column("finance_transactions", "counterparty")
