"""initial tables

Revision ID: 0001_init
Revises:
Create Date: 2026-02-05
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "0001_init"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # stations
    op.create_table(
        "stations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("owner_user_id", sa.Integer(), nullable=True, index=True),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("address", sa.String(length=300), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("latitude", sa.Float(), nullable=False),
        sa.Column("longitude", sa.Float(), nullable=False),
        sa.Column("fuel_types", sa.String(length=100), nullable=False),
        sa.Column("has_cafe", sa.Boolean(), nullable=False),
        sa.Column("has_shop", sa.Boolean(), nullable=False),
        sa.Column("has_service", sa.Boolean(), nullable=False),
        sa.Column("has_toilet", sa.Boolean(), nullable=False),
        sa.Column("has_wifi", sa.Boolean(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )

    # pumps
    op.create_table(
        "pumps",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("station_id", sa.Integer(), sa.ForeignKey("stations.id", ondelete="CASCADE")),
        sa.Column("name", sa.String(length=50), nullable=False),
        sa.Column("fuel_type", sa.String(length=50), nullable=False),
        sa.Column("price", sa.Float(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("is_busy", sa.Boolean(), nullable=False),
        sa.Column("last_status_change", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )

    # queue_tickets
    op.create_table(
        "queue_tickets",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("station_id", sa.Integer(), sa.ForeignKey("stations.id", ondelete="CASCADE")),
        sa.Column("fuel_type", sa.String(length=50), nullable=False),
        sa.Column("ticket_no", sa.String(length=10), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("driver_phone", sa.String(length=30), nullable=True),
        sa.Column("driver_user_id", sa.Integer(), nullable=True),
        sa.Column("source", sa.String(length=20), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("called_at", sa.DateTime(), nullable=True),
        sa.Column("done_at", sa.DateTime(), nullable=True),
    )

    # ratings
    op.create_table(
        "ratings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("station_id", sa.Integer(), sa.ForeignKey("stations.id", ondelete="CASCADE")),
        sa.Column("driver_user_id", sa.Integer(), nullable=True),
        sa.Column("stars", sa.SmallInteger(), nullable=False),
        sa.Column("title", sa.String(length=120), nullable=True),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )

    # reservations
    op.create_table(
        "reservations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("station_id", sa.Integer(), sa.ForeignKey("stations.id", ondelete="CASCADE")),
        sa.Column("driver_user_id", sa.Integer(), nullable=True),
        sa.Column("driver_phone", sa.String(length=30), nullable=True),
        sa.Column("fuel_type", sa.String(length=50), nullable=False),
        sa.Column("start_time", sa.DateTime(), nullable=False),
        sa.Column("end_time", sa.DateTime(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("reservations")
    op.drop_table("ratings")
    op.drop_table("queue_tickets")
    op.drop_table("pumps")
    op.drop_table("stations")
