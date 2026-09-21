"""季度 OKR CRUD。"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..db import get_db
from ..schemas import OkrCreate, OkrRead, OkrUpdate
from ..services import okr_service

router = APIRouter(prefix="/api/okrs", tags=["okrs"])


@router.get("", response_model=list[OkrRead])
def list_okrs(plan_id: int | None = None, db: Session = Depends(get_db)):
    return okr_service.list_okrs(db, plan_id)


@router.get("/{okr_id}", response_model=OkrRead)
def get_okr(okr_id: int, db: Session = Depends(get_db)):
    result = okr_service.get_okr_read(db, okr_id)
    if result is None:
        raise HTTPException(404, "OKR 不存在")
    return result


@router.post("", response_model=OkrRead, status_code=201)
def create_okr(payload: OkrCreate, db: Session = Depends(get_db)):
    try:
        return okr_service.create_okr(db, payload)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc


@router.put("/{okr_id}", response_model=OkrRead)
def update_okr(okr_id: int, payload: OkrUpdate, db: Session = Depends(get_db)):
    try:
        result = okr_service.update_okr(db, okr_id, payload)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    if result is None:
        raise HTTPException(404, "OKR 不存在")
    return result


@router.delete("/{okr_id}")
def delete_okr(okr_id: int, db: Session = Depends(get_db)):
    if not okr_service.delete_okr(db, okr_id):
        raise HTTPException(404, "OKR 不存在")
    return {"ok": True}
