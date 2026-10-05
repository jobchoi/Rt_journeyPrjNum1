"""Version ledger corrections and retain before/after audit records."""
from alembic import op
import sqlalchemy as sa

revision = "0003_finance_history"
down_revision = "0002_simple_finance"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("finance_transactions", sa.Column("version", sa.Integer(), nullable=False, server_default="1"))
    op.create_table(
        "finance_transaction_history",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("transaction_id", sa.String(), sa.ForeignKey("finance_transactions.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("changed_by", sa.String(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("changed_at", sa.DateTime(), server_default=sa.func.current_timestamp(), nullable=False),
        sa.Column("reason", sa.String(1000), nullable=False),
        sa.Column("before", sa.JSON(), nullable=False),
        sa.Column("after", sa.JSON(), nullable=False),
        sa.UniqueConstraint("transaction_id", "version"),
    )
    op.create_index("ix_finance_transaction_history_transaction_id", "finance_transaction_history", ["transaction_id"])


def downgrade():
    op.drop_table("finance_transaction_history")
    op.drop_column("finance_transactions", "version")
