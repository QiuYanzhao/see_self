"""SQLAlchemy 2.0 ORM 模型：五年计划（纲要）→ 季度 OKR → 项目 → 待办。

字段类型全部使用方言无关的通用类型，SQLite / MySQL 均可映射。
多值结构化内容（指标、领域、专项、风险）拆为子表；低密度文档结构（总纲、
评估机制、待补充清单）以 JSON 字段承载，均可在 SQLite(Text) 与 MySQL(JSON) 间平滑迁移。
"""
from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    mapped_column,
    relationship,
)


class Base(DeclarativeBase):
    pass


def _now() -> datetime:
    return datetime.now()


class FiveYearPlan(Base):
    __tablename__ = "five_year_plan"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    start_year: Mapped[int] = mapped_column(Integer, nullable=False)
    end_year: Mapped[int] = mapped_column(Integer, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="ACTIVE")

    # ── 规划纲要（period 精确到日）──
    period_start: Mapped[date | None] = mapped_column(Date)
    period_end: Mapped[date | None] = mapped_column(Date)
    # 五年总纲
    vision_positioning: Mapped[str | None] = mapped_column(Text)   # 定位（5 年后成为谁）
    vision_core_goals: Mapped[list | None] = mapped_column(JSON)   # 核心目标 [str]
    vision_bottom_lines: Mapped[list | None] = mapped_column(JSON)  # 底线约束 [str]
    # 评估机制 {annual, midterm, final}
    evaluation: Mapped[dict | None] = mapped_column(JSON)
    # 首年拆解：年度目标 [str] 与周期文本；季度 OKR 存 okr 表（plan_id 挂靠）
    year1_goals: Mapped[list | None] = mapped_column(JSON)
    year1_period: Mapped[str | None] = mapped_column(String(100))
    # 待补充清单 [{item, note, impact}]
    placeholders: Mapped[list | None] = mapped_column(JSON)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_now, onupdate=_now)

    okrs: Mapped[list["Okr"]] = relationship(
        back_populates="plan",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    indicators: Mapped[list["PlanIndicator"]] = relationship(
        back_populates="plan",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="PlanIndicator.sort_order",
    )
    domains: Mapped[list["PlanDomain"]] = relationship(
        back_populates="plan",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="PlanDomain.sort_order",
    )
    special_projects: Mapped[list["PlanSpecialProject"]] = relationship(
        back_populates="plan",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="PlanSpecialProject.sort_order",
    )
    risks: Mapped[list["PlanRisk"]] = relationship(
        back_populates="owner",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="PlanRisk.sort_order",
    )


class Okr(Base):
    __tablename__ = "okr"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    plan_id: Mapped[int | None] = mapped_column(
        ForeignKey("five_year_plan.id", ondelete="CASCADE")
    )
    quarter: Mapped[str] = mapped_column(String(32), nullable=False)  # 如 2026Q3 / Q1 2026.10-12
    objective: Mapped[str] = mapped_column(String(200), nullable=False)
    kr_note: Mapped[str | None] = mapped_column(Text)                 # 备注（兼容旧数据）
    kr_results: Mapped[list | None] = mapped_column(JSON)             # 关键结果列表 [str]
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_now, onupdate=_now)

    plan: Mapped["FiveYearPlan | None"] = relationship(back_populates="okrs")
    projects: Mapped[list["Project"]] = relationship(
        back_populates="okr",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class PlanIndicator(Base):
    """五年计划·指标体系（约束性 binding / 预期性 expected）。"""

    __tablename__ = "plan_indicator"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    plan_id: Mapped[int] = mapped_column(
        ForeignKey("five_year_plan.id", ondelete="CASCADE"), nullable=False
    )
    kind: Mapped[str] = mapped_column(String(10), nullable=False)   # binding / expected
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    baseline: Mapped[str | None] = mapped_column(Text)
    target: Mapped[str | None] = mapped_column(Text)
    check_frequency: Mapped[str | None] = mapped_column(String(50))  # 约束性：检查频率
    measure: Mapped[str | None] = mapped_column(String(200))         # 预期性：衡量方式
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    plan: Mapped["FiveYearPlan"] = relationship(back_populates="indicators")


class PlanDomain(Base):
    """五年计划·重点领域任务（人力资本/经济与资产/健康民生/社会关系/生活与精神）。"""

    __tablename__ = "plan_domain"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    plan_id: Mapped[int] = mapped_column(
        ForeignKey("five_year_plan.id", ondelete="CASCADE"), nullable=False
    )
    domain: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(10), nullable=False, default="重点")  # 重点/非重点
    baseline: Mapped[str | None] = mapped_column(Text)
    five_year_target: Mapped[str | None] = mapped_column(Text)
    year1_tasks: Mapped[list | None] = mapped_column(JSON)           # 第一年任务 [str]
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    plan: Mapped["FiveYearPlan"] = relationship(back_populates="domains")


class PlanSpecialProject(Base):
    """五年计划·重大专项工程（集中资源攻坚 1-2 年）。"""

    __tablename__ = "plan_special_project"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    plan_id: Mapped[int] = mapped_column(
        ForeignKey("five_year_plan.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    start: Mapped[str | None] = mapped_column(String(50))            # 起止时间（文本，如 2026-09）
    end: Mapped[str | None] = mapped_column(String(50))
    effort: Mapped[str | None] = mapped_column(Text)                 # 投入估算
    milestones: Mapped[list | None] = mapped_column(JSON)            # 里程碑节点 [str]
    acceptance_criteria: Mapped[str | None] = mapped_column(Text)    # 验收标准
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    plan: Mapped["FiveYearPlan"] = relationship(back_populates="special_projects")


class PlanRisk(Base):
    """五年计划·风险研判与保障（职业/财务/健康/时间）。"""

    __tablename__ = "plan_risk"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    plan_id: Mapped[int] = mapped_column(
        ForeignKey("five_year_plan.id", ondelete="CASCADE"), nullable=False
    )
    risk_type: Mapped[str] = mapped_column(String(20), nullable=False)  # 职业/财务/健康/时间
    trigger: Mapped[str | None] = mapped_column(Text)                 # 触发信号
    plan: Mapped[str | None] = mapped_column(Text)                    # 预案（列名 plan，与 JSON 字段一致）
    reserve: Mapped[str | None] = mapped_column(Text)                 # 资源储备
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    # 注意：列名 plan 与 JSON 的预案字段一致，relationship 命名为 owner 避免同名冲突
    owner: Mapped["FiveYearPlan"] = relationship(back_populates="risks")


class Project(Base):
    __tablename__ = "project"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    okr_id: Mapped[int | None] = mapped_column(
        ForeignKey("okr.id", ondelete="CASCADE")
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_now, onupdate=_now)

    okr: Mapped["Okr | None"] = relationship(back_populates="projects")
    todos: Mapped[list["Todo"]] = relationship(
        back_populates="project",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class Todo(Base):
    __tablename__ = "todo"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[int] = mapped_column(
        ForeignKey("project.id", ondelete="CASCADE"), nullable=False
    )
    parent_id: Mapped[int | None] = mapped_column(
        ForeignKey("todo.id", ondelete="CASCADE")
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_now, onupdate=_now)

    project: Mapped["Project"] = relationship(back_populates="todos")
    children: Mapped[list["Todo"]] = relationship(
        back_populates="parent",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    parent: Mapped["Todo | None"] = relationship(back_populates="children", remote_side=[id])
    notes: Mapped[list["TodoNote"]] = relationship(
        back_populates="todo",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="TodoNote.sort_order",
    )


class TodoNote(Base):
    """事项子记录（完成时的 bullet points）。"""

    __tablename__ = "todo_note"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    todo_id: Mapped[int] = mapped_column(
        ForeignKey("todo.id", ondelete="CASCADE"), nullable=False
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)

    todo: Mapped["Todo"] = relationship(back_populates="notes")


class AppSetting(Base):
    """全局应用设置（key-value），如外观、背景图片等。"""

    __tablename__ = "app_setting"

    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    value: Mapped[str | None] = mapped_column(Text)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_now, onupdate=_now)
