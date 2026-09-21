"""五年计划 CRUD（含规划纲要子结构：指标/领域/专项/风险/首年 OKR）。"""
from __future__ import annotations

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from ..models import (
    FiveYearPlan,
    Okr,
    PlanDomain,
    PlanIndicator,
    PlanRisk,
    PlanSpecialProject,
    Project,
    Todo,
    TodoNote,
)
from ..schemas import (
    DomainItem,
    IndicatorItem,
    OkrRead,
    PlanCreate,
    PlanRead,
    PlanUpdate,
    RiskItem,
    SpecialProjectItem,
)
from . import todo_service


def _to_read(db: Session, plan: FiveYearPlan) -> PlanRead:
    okr_count = len(plan.okrs) if plan.okrs is not None else 0
    okrs: list[OkrRead] = []
    if plan.okrs is not None:
        for okr in plan.okrs:
            okrs.append(
                OkrRead(
                    id=okr.id,
                    plan_id=okr.plan_id,
                    quarter=okr.quarter,
                    objective=okr.objective,
                    kr_note=okr.kr_note,
                    kr_results=okr.kr_results or [],
                    project_count=0,  # 五年计划页面不展示 OKR 下的项目数量，避免 N+1 查询
                    created_at=okr.created_at,
                )
            )
    return PlanRead(
        id=plan.id,
        name=plan.name,
        start_year=plan.start_year,
        end_year=plan.end_year,
        description=plan.description,
        status=plan.status,
        period_start=plan.period_start,
        period_end=plan.period_end,
        vision_positioning=plan.vision_positioning,
        vision_core_goals=plan.vision_core_goals or [],
        vision_bottom_lines=plan.vision_bottom_lines or [],
        evaluation=plan.evaluation,
        year1_goals=plan.year1_goals or [],
        year1_period=plan.year1_period,
        placeholders=plan.placeholders or [],
        indicators=[IndicatorItem.model_validate(i) for i in (plan.indicators or [])],
        domains=[DomainItem.model_validate(d) for d in (plan.domains or [])],
        special_projects=[
            SpecialProjectItem.model_validate(s) for s in (plan.special_projects or [])
        ],
        risks=[RiskItem.model_validate(r) for r in (plan.risks or [])],
        okrs=okrs,
        okr_count=okr_count,
        created_at=plan.created_at,
    )


def list_plans(db: Session) -> list[PlanRead]:
    plans = db.execute(select(FiveYearPlan).order_by(FiveYearPlan.id)).scalars().all()
    return [_to_read(db, p) for p in plans]


def get_plan(db: Session, plan_id: int) -> FiveYearPlan | None:
    return db.get(FiveYearPlan, plan_id)


def get_plan_read(db: Session, plan_id: int) -> PlanRead | None:
    plan = get_plan(db, plan_id)
    return _to_read(db, plan) if plan else None


def _validate_years(start: int, end: int) -> None:
    if end <= start:
        raise ValueError("结束年份必须大于开始年份")


def _apply_outline(plan: FiveYearPlan, payload: PlanCreate | PlanUpdate) -> None:
    """把纲要字段写入主表。子表由 _replace_children 处理。"""
    data = payload.model_dump(exclude_unset=True) if isinstance(payload, PlanUpdate) else payload.model_dump()
    for key in (
        "period_start", "period_end", "vision_positioning", "vision_core_goals",
        "vision_bottom_lines", "evaluation", "year1_goals", "year1_period", "placeholders",
    ):
        if key in data and data[key] is not None:
            setattr(plan, key, data[key])


def _replace_children(db: Session, plan: FiveYearPlan, payload: PlanCreate | PlanUpdate) -> None:
    """子表整体替换（个人工具规模小，直接删旧建新，保证与请求一致）。"""
    data = payload.model_dump(exclude_unset=True) if isinstance(payload, PlanUpdate) else payload.model_dump()

    if "indicators" in data and data["indicators"] is not None:
        plan.indicators.clear()
        for idx, item in enumerate(data["indicators"]):
            plan.indicators.append(PlanIndicator(
                kind=item["kind"], name=item["name"], baseline=item.get("baseline"),
                target=item.get("target"), check_frequency=item.get("check_frequency"),
                measure=item.get("measure"), sort_order=idx,
            ))

    if "domains" in data and data["domains"] is not None:
        plan.domains.clear()
        for idx, item in enumerate(data["domains"]):
            plan.domains.append(PlanDomain(
                domain=item["domain"], status=item.get("status", "重点"),
                baseline=item.get("baseline"), five_year_target=item.get("five_year_target"),
                year1_tasks=item.get("year1_tasks") or [], sort_order=idx,
            ))

    if "special_projects" in data and data["special_projects"] is not None:
        plan.special_projects.clear()
        for idx, item in enumerate(data["special_projects"]):
            plan.special_projects.append(PlanSpecialProject(
                name=item["name"], start=item.get("start"), end=item.get("end"),
                effort=item.get("effort"), milestones=item.get("milestones") or [],
                acceptance_criteria=item.get("acceptance_criteria"), sort_order=idx,
            ))

    if "risks" in data and data["risks"] is not None:
        plan.risks.clear()
        for idx, item in enumerate(data["risks"]):
            plan.risks.append(PlanRisk(
                risk_type=item["risk_type"], trigger=item.get("trigger"),
                plan=item.get("plan"), reserve=item.get("reserve"), sort_order=idx,
            ))


def create_plan(db: Session, payload: PlanCreate) -> PlanRead:
    _validate_years(payload.start_year, payload.end_year)
    plan = FiveYearPlan(
        name=payload.name,
        start_year=payload.start_year,
        end_year=payload.end_year,
        description=payload.description,
    )
    _apply_outline(plan, payload)
    db.add(plan)
    db.flush()  # 先拿到 plan.id 供子表外键使用
    _replace_children(db, plan, payload)
    for okr in payload.okrs:  # 首年 OKR 随计划导入
        db.add(Okr(
            plan_id=plan.id, quarter=okr.quarter, objective=okr.objective,
            kr_note=okr.kr_note, kr_results=okr.kr_results or None,
        ))
    db.commit()
    db.refresh(plan)
    return _to_read(db, plan)


def update_plan(db: Session, plan_id: int, payload: PlanUpdate) -> PlanRead | None:
    plan = get_plan(db, plan_id)
    if plan is None:
        return None
    data = payload.model_dump(exclude_unset=True)
    start = data.get("start_year", plan.start_year)
    end = data.get("end_year", plan.end_year)
    _validate_years(start, end)
    for key in ("name", "start_year", "end_year", "description", "status"):
        if key in data:
            setattr(plan, key, data[key])
    _apply_outline(plan, payload)
    _replace_children(db, plan, payload)
    db.commit()
    db.refresh(plan)
    return _to_read(db, plan)


def _delete_plan_records(db: Session, plan_id: int) -> None:
    """删除计划的全部关联记录(不 commit):规划子表 → OKR → 项目 → 事项 → 子记录。"""
    okr_ids = db.scalars(select(Okr.id).where(Okr.plan_id == plan_id)).all()
    if okr_ids:
        project_ids = db.scalars(select(Project.id).where(Project.okr_id.in_(okr_ids))).all()
        if project_ids:
            todo_ids = db.scalars(select(Todo.id).where(Todo.project_id.in_(project_ids))).all()
            if todo_ids:
                ids = todo_service._subtree_ids(db, todo_ids)
                db.execute(delete(TodoNote).where(TodoNote.todo_id.in_(ids)))
                db.execute(delete(Todo).where(Todo.id.in_(ids)))
            db.execute(delete(Project).where(Project.id.in_(project_ids)))
        db.execute(delete(Okr).where(Okr.id.in_(okr_ids)))
    for model in (PlanDomain, PlanIndicator, PlanRisk, PlanSpecialProject):
        db.execute(delete(model).where(model.plan_id == plan_id))


def delete_plan(db: Session, plan_id: int) -> bool:
    plan = get_plan(db, plan_id)
    if plan is None:
        return False
    # 显式级联删除(不依赖数据库外键级联)
    _delete_plan_records(db, plan_id)
    db.delete(plan)
    db.commit()
    return True
