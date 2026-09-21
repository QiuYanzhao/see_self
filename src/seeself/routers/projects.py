"""项目 CRUD。"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..db import get_db
from ..schemas import ProjectCreate, ProjectRead, ProjectUpdate
from ..services import project_service

router = APIRouter(prefix="/api/projects", tags=["projects"])


@router.get("", response_model=list[ProjectRead])
def list_projects(okr_id: int | None = None, db: Session = Depends(get_db)):
    return project_service.list_projects(db, okr_id)


@router.get("/{project_id}", response_model=ProjectRead)
def get_project(project_id: int, db: Session = Depends(get_db)):
    result = project_service.get_project_read(db, project_id)
    if result is None:
        raise HTTPException(404, "项目不存在")
    return result


@router.post("", response_model=ProjectRead, status_code=201)
def create_project(payload: ProjectCreate, db: Session = Depends(get_db)):
    try:
        return project_service.create_project(db, payload)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc


@router.put("/{project_id}", response_model=ProjectRead)
def update_project(project_id: int, payload: ProjectUpdate, db: Session = Depends(get_db)):
    try:
        result = project_service.update_project(db, project_id, payload)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    if result is None:
        raise HTTPException(404, "项目不存在")
    return result


@router.delete("/{project_id}")
def delete_project(project_id: int, db: Session = Depends(get_db)):
    if not project_service.delete_project(db, project_id):
        raise HTTPException(404, "项目不存在")
    return {"ok": True}
