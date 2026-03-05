"""reconcile manual schema changes

Revision ID: 8f1c2d3e4b5a
Revises: 839ab5be9392
Create Date: 2026-03-06 03:30:00
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision = "8f1c2d3e4b5a"
down_revision = "839ab5be9392"
branch_labels = None
depends_on = None


def has_column(table_name: str, column_name: str) -> bool:
    bind = op.get_bind()
    inspector = inspect(bind)
    columns = [col["name"] for col in inspector.get_columns(table_name)]
    return column_name in columns


def has_table(table_name: str) -> bool:
    bind = op.get_bind()
    inspector = inspect(bind)
    return table_name in inspector.get_table_names()


def upgrade() -> None:
    # users.phone
    if not has_column("users", "phone"):
        op.add_column("users", sa.Column("phone", sa.String(length=20), nullable=True))

    # users.is_active -> boolean
    if has_column("users", "is_active"):
        op.alter_column(
            "users",
            "is_active",
            existing_type=sa.Boolean(),
            type_=sa.Boolean(),
            existing_nullable=False,
            nullable=False,
            postgresql_using="is_active::boolean",
        )

    # users.username -> nullable
    if has_column("users", "username"):
        op.alter_column(
            "users",
            "username",
            existing_type=sa.String(length=255),
            nullable=True,
        )

    # stations.avg_service_min
    if not has_column("stations", "avg_service_min"):
        op.add_column("stations", sa.Column("avg_service_min", sa.Integer(), nullable=True))

    # stations.pumps_count
    if not has_column("stations", "pumps_count"):
        op.add_column("stations", sa.Column("pumps_count", sa.Integer(), nullable=True))

    # queue_tickets.driver_state
    if not has_column("queue_tickets", "driver_state"):
        op.add_column("queue_tickets", sa.Column("driver_state", sa.String(length=50), nullable=True))

    # queue_tickets.heading_at
    if not has_column("queue_tickets", "heading_at"):
        op.add_column("queue_tickets", sa.Column("heading_at", sa.DateTime(timezone=True), nullable=True))

    # queue_tickets.arrived_at
    if not has_column("queue_tickets", "arrived_at"):
        op.add_column("queue_tickets", sa.Column("arrived_at", sa.DateTime(timezone=True), nullable=True))

    # queue_tickets.cancelled_at
    if not has_column("queue_tickets", "cancelled_at"):
        op.add_column("queue_tickets", sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True))

    # queue_tickets.cancel_reason
    if not has_column("queue_tickets", "cancel_reason"):
        op.add_column("queue_tickets", sa.Column("cancel_reason", sa.Text(), nullable=True))

    # queue_tickets.pump_no
    if not has_column("queue_tickets", "pump_no"):
        op.add_column("queue_tickets", sa.Column("pump_no", sa.Integer(), nullable=True))

    # notifications table
    if not has_table("notifications"):
        op.create_table(
            "notifications",
            sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=True),
            sa.Column("ticket_id", sa.Integer(), nullable=True),
            sa.Column("type", sa.String(length=50), nullable=False),
            sa.Column("title", sa.String(length=255), nullable=False),
            sa.Column("body", sa.Text(), nullable=True),
            sa.Column("is_read", sa.Boolean(), nullable=False, server_default=sa.text("false")),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        )


def downgrade() -> None:
    # Обычно reconciliation downgrade либо не используют,
    # либо делают только частичный откат.
    # Оставляем явный pass, чтобы не сломать уже приведённую вручную схему.
    pass