"""initial schema: five_year_plan / okr / project / todo

Revision ID: 0001_initial
Revises:
Create Date: 2026-09-11
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "five_year_plan",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("start_year", sa.Integer(), nullable=False),
        sa.Column("end_year", sa.Integer(), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("status", sa.String(20), nullable=False, server_default="ACTIVE"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )

    op.create_table(
        "okr",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "plan_id",
            sa.Integer(),
            sa.ForeignKey("five_year_plan.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column("quarter", sa.String(10), nullable=False),
        sa.Column("objective", sa.String(200), nullable=False),
        sa.Column("kr_note", sa.Text()),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )

    op.create_table(
        "project",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "okr_id",
            sa.Integer(),
            sa.ForeignKey("okr.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )

    op.create_table(
        "todo",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "project_id",
            sa.Integer(),
            sa.ForeignKey("project.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("planned_date", sa.Date(), nullable=False),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )

    op.create_index("idx_okr_plan", "okr", ["plan_id"])
    op.create_index("idx_project_okr", "project", ["okr_id"])
    op.create_index("idx_todo_project", "todo", ["project_id"])
    op.create_index("idx_todo_completed", "todo", ["completed_at"])


def downgrade() -> None:
    op.drop_index("idx_todo_completed", table_name="todo")
    op.drop_index("idx_todo_project", table_name="todo")
    op.drop_index("idx_project_okr", table_name="project")
    op.drop_index("idx_okr_plan", table_name="okr")
    op.drop_table("todo")
    op.drop_table("project")
    op.drop_table("okr")
    op.drop_table("five_year_plan")
