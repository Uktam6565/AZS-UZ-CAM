"""add claim_code to queue_tickets

Revision ID: 839ab5be9392
Revises: c6d52c73c44c
Create Date: 2026-02-14 19:01:59.231529

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '839ab5be9392'
down_revision = 'c6d52c73c44c'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("queue_tickets", sa.Column("claim_code", sa.String(length=32), nullable=True))
    op.add_column("queue_tickets", sa.Column("check_in_at", sa.DateTime(timezone=False), nullable=True))
    op.create_index("ix_queue_tickets_claim_code", "queue_tickets", ["claim_code"])


def downgrade() -> None:
    op.drop_index("ix_queue_tickets_claim_code", table_name="queue_tickets")
    op.drop_column("queue_tickets", "check_in_at")
    op.drop_column("queue_tickets", "claim_code")
