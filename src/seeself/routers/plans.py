"""五年计划 CRUD 与纲要导入。"""
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..db import get_db
from ..schemas import PlanCreate, PlanRead, PlanUpdate
from ..services import plan_import_service, plan_service

router = APIRouter(prefix="/api/plans", tags=["plans"])


@router.get("", response_model=list[PlanRead])
def list_plans(db: Session = Depends(get_db)):
    return plan_service.list_plans(db)


@router.get("/{plan_id}", response_model=PlanRead)
def get_plan(plan_id: int, db: Session = Depends(get_db)):
    result = plan_service.get_plan_read(db, plan_id)
    if result is None:
        raise HTTPException(404, "五年计划不存在")
    return result


@router.post("", response_model=PlanRead, status_code=201)
def create_plan(payload: PlanCreate, db: Session = Depends(get_db)):
    try:
        return plan_service.create_plan(db, payload)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc


@router.put("/{plan_id}", response_model=PlanRead)
def update_plan(plan_id: int, payload: PlanUpdate, db: Session = Depends(get_db)):
    try:
        result = plan_service.update_plan(db, plan_id, payload)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    if result is None:
        raise HTTPException(404, "五年计划不存在")
    return result


@router.delete("/{plan_id}")
def delete_plan(plan_id: int, db: Session = Depends(get_db)):
    if not plan_service.delete_plan(db, plan_id):
        raise HTTPException(404, "五年计划不存在")
    return {"ok": True}


@router.post("/import", response_model=PlanRead, status_code=201)
def import_plan(payload: dict[str, Any], db: Session = Depends(get_db)):
    """导入 personal-five-year-plan 技能导出的纲要 JSON。

    系统只保留一份五年计划：已存在则整体覆盖（级联删除旧计划及其 OKR/项目/待办）。
    """
    try:
        return plan_import_service.import_outline(db, payload, source="页面导入")
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
