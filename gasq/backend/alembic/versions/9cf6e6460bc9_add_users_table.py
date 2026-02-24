"""add users table

Revision ID: 9cf6e6460bc9
Revises: 0001_init
Create Date: 2026-02-08 05:09:55.482153

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '9cf6e6460bc9'
down_revision = '0001_init'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("username", sa.String(50), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("is_active", sa.Integer, default=1),
        sa.Column("created_at", sa.DateTime),
    )


def downgrade() -> None:
    op.drop_table("users")

