"""方向纠偏：Todo 改多层级事项树，删 planned_date，新增 todo_note 子记录表。

Revision ID: 0004_todo_tree
Revises: 0003_app_setting
Create Date: 2026-09-15
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0004_todo_tree"
down_revision: Union[str, None] = "0003_app_setting"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. todo 表加 parent_id（自引用）和 sort_order。
    #    SQLite 不支持 ALTER TABLE ADD CONSTRAINT，且最新 schema 不建外键约束
    #    （关联由应用层维护），故只加列与索引。
    op.add_column("todo", sa.Column("parent_id", sa.Integer(), nullable=True))
    op.add_column("todo", sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"))
    op.create_index("idx_todo_parent", "todo", ["parent_id"])

    # 2. 新建 todo_note 子记录表（无外键约束，仅建索引）
    op.create_table(
        "todo_note",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("todo_id", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("idx_note_todo", "todo_note", ["todo_id"])

    # 3. 删除 planned_date 列（SQLite 3.35+ 支持 DROP COLUMN）
    op.drop_column("todo", "planned_date")


def downgrade() -> None:
    op.add_column("todo", sa.Column("planned_date", sa.Date(), nullable=True))
    op.drop_index("idx_note_todo", table_name="todo_note")
    op.drop_table("todo_note")
    op.drop_index("idx_todo_parent", table_name="todo")
    op.drop_column("todo", "parent_id")
    op.drop_column("todo", "sort_order")
