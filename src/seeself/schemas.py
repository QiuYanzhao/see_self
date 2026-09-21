"""Pydantic 请求/响应模型（JSON 字段统一 snake_case）。"""
from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

# ───────────────────────── 五年计划（规划纲要） ─────────────────────────


class IndicatorItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    """指标（约束性 binding / 预期性 expected）。"""
    kind: str = "binding"
    name: str
    baseline: str | None = None
    target: str | None = None
    check_frequency: str | None = None   # 约束性：检查频率
    measure: str | None = None           # 预期性：衡量方式


class DomainItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    """重点领域任务。"""
    domain: str
    status: str = "重点"                  # 重点 / 非重点
    baseline: str | None = None
    five_year_target: str | None = None
    year1_tasks: list[str] = []


class SpecialProjectItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    """重大专项工程。"""
    name: str
    start: str | None = None
    end: str | None = None
    effort: str | None = None
    milestones: list[str] = []
    acceptance_criteria: str | None = None


class RiskItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    """风险研判与保障。"""
    risk_type: str                        # 职业 / 财务 / 健康 / 时间
    trigger: str | None = None
    plan: str | None = None
    reserve: str | None = None


class EvaluationInfo(BaseModel):
    """评估机制。"""
    annual: str | None = None
    midterm: str | None = None
    final: str | None = None


class PlaceholderItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    """待补充清单。"""
    item: str
    note: str | None = None
    impact: str | None = None


class OkrInput(BaseModel):
    """随计划创建的首年 OKR（导入场景）。"""
    quarter: str
    objective: str
    kr_note: str | None = None
    kr_results: list[str] = []


class PlanCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    start_year: int = Field(ge=1900, le=2200)
    end_year: int = Field(ge=1900, le=2200)
    description: str | None = None
    # 纲要（全部可选，可先建壳后补）
    period_start: date | None = None
    period_end: date | None = None
    vision_positioning: str | None = None
    vision_core_goals: list[str] = []
    vision_bottom_lines: list[str] = []
    evaluation: EvaluationInfo | None = None
    year1_goals: list[str] = []
    year1_period: str | None = None
    placeholders: list[PlaceholderItem] = []
    indicators: list[IndicatorItem] = []
    domains: list[DomainItem] = []
    special_projects: list[SpecialProjectItem] = []
    risks: list[RiskItem] = []
    okrs: list[OkrInput] = []


class PlanUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    start_year: int | None = Field(default=None, ge=1900, le=2200)
    end_year: int | None = Field(default=None, ge=1900, le=2200)
    description: str | None = None
    status: str | None = None
    period_start: date | None = None
    period_end: date | None = None
    vision_positioning: str | None = None
    vision_core_goals: list[str] | None = None
    vision_bottom_lines: list[str] | None = None
    evaluation: EvaluationInfo | None = None
    year1_goals: list[str] | None = None
    year1_period: str | None = None
    placeholders: list[PlaceholderItem] | None = None
    indicators: list[IndicatorItem] | None = None
    domains: list[DomainItem] | None = None
    special_projects: list[SpecialProjectItem] | None = None
    risks: list[RiskItem] | None = None


class PlanRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    start_year: int
    end_year: int
    description: str | None
    status: str
    # 纲要
    period_start: date | None = None
    period_end: date | None = None
    vision_positioning: str | None = None
    vision_core_goals: list[str] = []
    vision_bottom_lines: list[str] = []
    evaluation: EvaluationInfo | None = None
    year1_goals: list[str] = []
    year1_period: str | None = None
    placeholders: list[PlaceholderItem] = []
    indicators: list[IndicatorItem] = []
    domains: list[DomainItem] = []
    special_projects: list[SpecialProjectItem] = []
    risks: list[RiskItem] = []
    okrs: list[OkrRead] = []
    okr_count: int = 0
    created_at: datetime


# ───────────────────────── 季度 OKR ─────────────────────────


class OkrCreate(BaseModel):
    plan_id: int | None = None
    quarter: str = Field(min_length=1, max_length=32)
    objective: str = Field(min_length=1, max_length=200)
    kr_note: str | None = None
    kr_results: list[str] = []


class OkrUpdate(BaseModel):
    plan_id: int | None = None
    quarter: str | None = Field(default=None, min_length=1, max_length=32)
    objective: str | None = Field(default=None, min_length=1, max_length=200)
    kr_note: str | None = None
    kr_results: list[str] | None = None


class OkrRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    plan_id: int | None
    quarter: str
    objective: str
    kr_note: str | None
    kr_results: list[str] = []
    project_count: int = 0
    created_at: datetime


# ───────────────────────── 项目 ─────────────────────────


class ProjectCreate(BaseModel):
    okr_id: int | None = None
    name: str = Field(min_length=1, max_length=100)
    description: str | None = None


class ProjectUpdate(BaseModel):
    okr_id: int | None = None
    name: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = None


class TodoNoteRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    todo_id: int
    content: str
    sort_order: int
    created_at: datetime


class TodoNodeRead(BaseModel):
    """事项树节点。"""
    model_config = ConfigDict(from_attributes=True)
    id: int
    project_id: int
    parent_id: int | None
    title: str
    description: str | None
    sort_order: int
    completed_at: datetime | None
    created_at: datetime
    children: list["TodoNodeRead"] = []
    notes: list[TodoNoteRead] = []


class TodoCreate(BaseModel):
    project_id: int
    parent_id: int | None = None
    title: str = Field(min_length=1, max_length=200)
    description: str | None = None
    sort_order: int = 0


class TodoUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    parent_id: int | None = None
    sort_order: int | None = None


class TodoImportNode(BaseModel):
    """项目导入用事项节点：顶层为模块，children 为其下事项，支持多级嵌套。"""

    title: str = Field(min_length=1, max_length=200)
    description: str | None = None
    children: list["TodoImportNode"] = []


class TodoNoteCreate(BaseModel):
    content: str = Field(min_length=1)
    sort_order: int = 0


class TodoNoteUpdate(BaseModel):
    content: str | None = None
    sort_order: int | None = None


class ProgressSegment(BaseModel):
    label: str
    start: float
    end: float
    value: float
    color: str


class ProjectRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    okr_id: int | None
    name: str
    description: str | None
    progress: float = 0.0
    total_leaves: int = 0
    completed_leaves: int = 0
    segments: list[ProgressSegment] = []
    month_delta: float = 0.0
    week_delta: float = 0.0
    yesterday_delta: float = 0.0
    today_delta: float = 0.0
    created_at: datetime


# ───────────────────────── 看板 ─────────────────────────


class TimeProgress(BaseModel):
    now: datetime
    year_progress: float
    month_progress: float
    week_progress: float
    year_label: str
    month_label: str
    week_label: str


class DashboardData(BaseModel):
    time: TimeProgress
    projects: list[ProjectRead]


# ───────────────────────── 设置 ─────────────────────────


class SettingsRead(BaseModel):
    timezone: str


class SettingsUpdate(BaseModel):
    pass
