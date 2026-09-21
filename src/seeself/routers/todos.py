"""事项树 CRUD、子记录、进度统计 API。"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..db import get_db
from ..schemas import (
    TodoCreate,
    TodoNodeRead,
    TodoNoteCreate,
    TodoNoteRead,
    TodoNoteUpdate,
    TodoUpdate,
)
from ..services import todo_service

router = APIRouter(prefix="/api/todos", tags=["todos"])


@router.get("/tree/{project_id}", response_model=list[TodoNodeRead])
def get_tree(project_id: int, db: Session = Depends(get_db)):
    return todo_service.get_todo_tree(db, project_id)


@router.post("", response_model=TodoNodeRead, status_code=201)
def create_todo(payload: TodoCreate, db: Session = Depends(get_db)):
    try:
        return todo_service.create_todo(db, payload)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc


@router.put("/{todo_id}", response_model=TodoNodeRead)
def update_todo(todo_id: int, payload: TodoUpdate, db: Session = Depends(get_db)):
    try:
        result = todo_service.update_todo(db, todo_id, payload)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    if result is None:
        raise HTTPException(404, "事项不存在")
    return result


@router.put("/{todo_id}/toggle", response_model=TodoNodeRead)
def toggle_todo(todo_id: int, body: dict, db: Session = Depends(get_db)):
    completed = body.get("completed", False)
    result = todo_service.set_completed(db, todo_id, completed)
    if result is None:
        raise HTTPException(404, "事项不存在")
    return result


@router.delete("/{todo_id}")
def delete_todo(todo_id: int, db: Session = Depends(get_db)):
    if not todo_service.delete_todo(db, todo_id):
        raise HTTPException(404, "事项不存在")
    return {"ok": True}


# ───────────────────── 子记录 ─────────────────────


@router.post("/{todo_id}/notes", response_model=TodoNoteRead, status_code=201)
def add_note(todo_id: int, payload: TodoNoteCreate, db: Session = Depends(get_db)):
    result = todo_service.add_note(db, todo_id, payload)
    if result is None:
        raise HTTPException(404, "事项不存在")
    return result


@router.put("/notes/{note_id}", response_model=TodoNoteRead)
def update_note(note_id: int, payload: TodoNoteUpdate, db: Session = Depends(get_db)):
    result = todo_service.update_note(db, note_id, payload)
    if result is None:
        raise HTTPException(404, "子记录不存在")
    return result


@router.delete("/notes/{note_id}")
def delete_note(note_id: int, db: Session = Depends(get_db)):
    if not todo_service.delete_note(db, note_id):
        raise HTTPException(404, "子记录不存在")
    return {"ok": True}


# ───────────────────── 进度统计 ─────────────────────


@router.get("/progress/{project_id}")
def project_progress(project_id: int, db: Session = Depends(get_db)):
    return todo_service.project_progress(db, project_id)


@router.get("/heatmap/{project_id}")
def project_heatmap(project_id: int, db: Session = Depends(get_db)):
    return todo_service.heatmap_data(db, project_id)


@router.get("/heatmap")
def global_heatmap(db: Session = Depends(get_db)):
    """全站推进热力图：统计所有项目每日完成事项数。"""
    return todo_service.heatmap_data(db, None)


@router.get("/timeline/{project_id}")
def project_timeline(project_id: int, db: Session = Depends(get_db)):
    return todo_service.timeline_data(db, project_id)


@router.get("/pending/{project_id}")
def project_pending(project_id: int, db: Session = Depends(get_db)):
    return todo_service.pending_items(db, project_id)
