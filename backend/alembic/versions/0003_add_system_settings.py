"""add system settings table

Revision ID: 0003_add_system_settings
Revises: 0002_add_task_logs
Create Date: 2026-04-24 12:00:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0003_add_system_settings"
down_revision = "0002_add_task_logs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "system_settings",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("system_settings")
