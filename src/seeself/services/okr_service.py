"""季度 OKR CRUD。"""
from __future__ import annotations

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from ..models import FiveYearPlan, Okr, Project, Todo, TodoNote
from ..schemas import OkrCreate, OkrRead, OkrUpdate
from . import todo_service


def _batch_project_counts(db: Session, okr_ids: list[int]) -> dict[int, int]:
    """批量查询多个 OKR 的 project 数量，返回 {okr_id: count}。一条 SQL 替代 N+1。"""
    if not okr_ids:
        return {}
    rows = db.execute(
        select(Project.okr_id, func.count(Project.id))
        .where(Project.okr_id.in_(okr_ids))
        .group_by(Project.okr_id)
    ).all()
    return {okr_id: count for okr_id, count in rows}


def _to_read(okr: Okr, project_count: int = 0) -> OkrRead:
    return OkrRead(
        id=okr.id,
        plan_id=okr.plan_id,
        quarter=okr.quarter,
        objective=okr.objective,
        kr_note=okr.kr_note,
        kr_results=okr.kr_results or [],
        project_count=project_count,
        created_at=okr.created_at,
    )


def list_okrs(db: Session, plan_id: int | None = None) -> list[OkrRead]:
    stmt = select(Okr).order_by(Okr.id)
    if plan_id is not None:
        stmt = stmt.where(Okr.plan_id == plan_id)
    okrs = db.execute(stmt).scalars().all()
    counts = _batch_project_counts(db, [o.id for o in okrs])
    return [_to_read(o, counts.get(o.id, 0)) for o in okrs]


def get_okr(db: Session, okr_id: int) -> Okr | None:
    return db.get(Okr, okr_id)


def get_okr_read(db: Session, okr_id: int) -> OkrRead | None:
    okr = get_okr(db, okr_id)
    if okr is None:
        return None
    counts = _batch_project_counts(db, [okr.id])
    return _to_read(okr, counts.get(okr.id, 0))


def _ensure_plan_exists(db: Session, plan_id: int | None) -> None:
    if plan_id is not None and db.get(FiveYearPlan, plan_id) is None:
        raise ValueError(f"五年计划 {plan_id} 不存在")


def create_okr(db: Session, payload: OkrCreate) -> OkrRead:
    _ensure_plan_exists(db, payload.plan_id)
    okr = Okr(
        plan_id=payload.plan_id,
        quarter=payload.quarter,
        objective=payload.objective,
        kr_note=payload.kr_note,
        kr_results=payload.kr_results or None,
    )
    db.add(okr)
    db.commit()
    db.refresh(okr)
    counts = _batch_project_counts(db, [okr.id])
    return _to_read(okr, counts.get(okr.id, 0))


def batch_create_okrs(db: Session, items: list[OkrCreate]) -> list[OkrRead]:
    """批量创建 OKR，单事务：全部成功才提交，任一失败整体回滚。

    预校验全部 plan_id 存在，避免中途外键失败产生部分数据。
    """
    if not items:
        raise ValueError("items 不能为空")
    plan_ids = {it.plan_id for it in items if it.plan_id is not None}
    if plan_ids:
        existing = set(
            db.execute(select(FiveYearPlan.id).where(FiveYearPlan.id.in_(plan_ids)))
            .scalars()
            .all()
        )
        missing = sorted(plan_ids - existing)
        if missing:
            raise ValueError(f"五年计划不存在: {missing}")
    created: list[Okr] = []
    for item in items:
        okr = Okr(
            plan_id=item.plan_id,
            quarter=item.quarter,
            objective=item.objective,
            kr_note=item.kr_note,
            kr_results=item.kr_results or None,
        )
        db.add(okr)
        created.append(okr)
    db.flush()
    db.commit()
    counts = _batch_project_counts(db, [o.id for o in created])
    return [_to_read(o, counts.get(o.id, 0)) for o in created]


def update_okr(db: Session, okr_id: int, payload: OkrUpdate) -> OkrRead | None:
    okr = get_okr(db, okr_id)
    if okr is None:
        return None
    fields = payload.model_dump(exclude_unset=True)
    if "plan_id" in fields:
        _ensure_plan_exists(db, fields["plan_id"])
    for key, value in fields.items():
        setattr(okr, key, value)
    db.commit()
    db.refresh(okr)
    counts = _batch_project_counts(db, [okr.id])
    return _to_read(okr, counts.get(okr.id, 0))


def delete_okr(db: Session, okr_id: int) -> bool:
    okr = get_okr(db, okr_id)
    if okr is None:
        return False
    # 显式级联删除项目树(不依赖数据库外键级联)
    project_ids = db.scalars(select(Project.id).where(Project.okr_id == okr_id)).all()
    if project_ids:
        todo_ids = db.scalars(select(Todo.id).where(Todo.project_id.in_(project_ids))).all()
        if todo_ids:
            ids = todo_service._subtree_ids(db, todo_ids)
            db.execute(delete(TodoNote).where(TodoNote.todo_id.in_(ids)))
            db.execute(delete(Todo).where(Todo.id.in_(ids)))
        db.execute(delete(Project).where(Project.id.in_(project_ids)))
    db.delete(okr)
    db.commit()
    return True
