"""五年计划纲要扩展：主表加纲要字段 + 指标/领域/专项/风险子表 + OKR 关键结果。

Revision ID: 0002_plan_outline
Revises: 0001_initial
Create Date: 2026-09-13
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0002_plan_outline"
down_revision: Union[str, None] = "0001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 主表：纲要字段（JSON 以方言无关方式声明，SQLite 落 Text、MySQL 落 JSON）
    op.add_column("five_year_plan", sa.Column("period_start", sa.Date(), nullable=True))
    op.add_column("five_year_plan", sa.Column("period_end", sa.Date(), nullable=True))
    op.add_column("five_year_plan", sa.Column("vision_positioning", sa.Text(), nullable=True))
    op.add_column("five_year_plan", sa.Column("vision_core_goals", sa.JSON(), nullable=True))
    op.add_column("five_year_plan", sa.Column("vision_bottom_lines", sa.JSON(), nullable=True))
    op.add_column("five_year_plan", sa.Column("evaluation", sa.JSON(), nullable=True))
    op.add_column("five_year_plan", sa.Column("year1_goals", sa.JSON(), nullable=True))
    op.add_column("five_year_plan", sa.Column("year1_period", sa.String(100), nullable=True))
    op.add_column("five_year_plan", sa.Column("placeholders", sa.JSON(), nullable=True))

    # OKR：季度加宽（支持 "Q1 2026.10-12"）+ 关键结果列表
    op.alter_column(
        "okr", "quarter",
        existing_type=sa.String(10),
        type_=sa.String(32),
        existing_nullable=False,
    )
    op.add_column("okr", sa.Column("kr_results", sa.JSON(), nullable=True))

    # 子表：指标体系
    op.create_table(
        "plan_indicator",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "plan_id",
            sa.Integer(),
            sa.ForeignKey("five_year_plan.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("kind", sa.String(10), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("baseline", sa.Text(), nullable=True),
        sa.Column("target", sa.Text(), nullable=True),
        sa.Column("check_frequency", sa.String(50), nullable=True),
        sa.Column("measure", sa.String(200), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
    )

    # 子表：重点领域
    op.create_table(
        "plan_domain",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "plan_id",
            sa.Integer(),
            sa.ForeignKey("five_year_plan.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("domain", sa.String(50), nullable=False),
        sa.Column("status", sa.String(10), nullable=False, server_default="重点"),
        sa.Column("baseline", sa.Text(), nullable=True),
        sa.Column("five_year_target", sa.Text(), nullable=True),
        sa.Column("year1_tasks", sa.JSON(), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
    )

    # 子表：重大专项工程
    op.create_table(
        "plan_special_project",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "plan_id",
            sa.Integer(),
            sa.ForeignKey("five_year_plan.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("start", sa.String(50), nullable=True),
        sa.Column("end", sa.String(50), nullable=True),
        sa.Column("effort", sa.Text(), nullable=True),
        sa.Column("milestones", sa.JSON(), nullable=True),
        sa.Column("acceptance_criteria", sa.Text(), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
    )

    # 子表：风险研判
    op.create_table(
        "plan_risk",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "plan_id",
            sa.Integer(),
            sa.ForeignKey("five_year_plan.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("risk_type", sa.String(20), nullable=False),
        sa.Column("trigger", sa.Text(), nullable=True),
        sa.Column("plan", sa.Text(), nullable=True),
        sa.Column("reserve", sa.Text(), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
    )

    op.create_index("idx_indicator_plan", "plan_indicator", ["plan_id"])
    op.create_index("idx_domain_plan", "plan_domain", ["plan_id"])
    op.create_index("idx_special_plan", "plan_special_project", ["plan_id"])
    op.create_index("idx_risk_plan", "plan_risk", ["plan_id"])


def downgrade() -> None:
    op.drop_index("idx_risk_plan", table_name="plan_risk")
    op.drop_index("idx_special_plan", table_name="plan_special_project")
    op.drop_index("idx_domain_plan", table_name="plan_domain")
    op.drop_index("idx_indicator_plan", table_name="plan_indicator")
    op.drop_table("plan_risk")
    op.drop_table("plan_special_project")
    op.drop_table("plan_domain")
    op.drop_table("plan_indicator")

    op.drop_column("okr", "kr_results")
    op.alter_column(
        "okr", "quarter",
        existing_type=sa.String(32),
        type_=sa.String(10),
        existing_nullable=False,
    )

    op.drop_column("five_year_plan", "placeholders")
    op.drop_column("five_year_plan", "year1_period")
    op.drop_column("five_year_plan", "year1_goals")
    op.drop_column("five_year_plan", "evaluation")
    op.drop_column("five_year_plan", "vision_bottom_lines")
    op.drop_column("five_year_plan", "vision_core_goals")
    op.drop_column("five_year_plan", "vision_positioning")
    op.drop_column("five_year_plan", "period_end")
    op.drop_column("five_year_plan", "period_start")
