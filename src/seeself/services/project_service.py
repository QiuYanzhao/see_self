"""项目 CRUD 与进度视图。"""
from __future__ import annotations

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from ..models import Okr, Project, Todo, TodoNote
from ..schemas import (
    ProjectCreate,
    ProjectRead,
    ProjectUpdate,
    ProgressSegment,
    TodoImportNode,
)
from . import todo_service


def _to_read(db: Session, project: Project) -> ProjectRead:
    stats = todo_service.project_progress(db, project.id)
    seg = todo_service.segmented_progress(db, project.id)
    return ProjectRead(
        id=project.id,
        okr_id=project.okr_id,
        name=project.name,
        description=project.description,
        progress=stats["percent"],
        total_leaves=stats["total_leaves"],
        completed_leaves=stats["completed_leaves"],
        segments=[ProgressSegment(**s) for s in seg["segments"]],
        month_delta=seg["month"],
        week_delta=seg["week"],
        yesterday_delta=seg["yesterday"],
        today_delta=seg["today"],
        created_at=project.created_at,
    )


def list_projects(db: Session, okr_id: int | None = None) -> list[ProjectRead]:
    stmt = select(Project).order_by(Project.id)
    if okr_id is not None:
        stmt = stmt.where(Project.okr_id == okr_id)
    projects = db.execute(stmt).scalars().all()
    return [_to_read(db, p) for p in projects]


def get_project(db: Session, project_id: int) -> Project | None:
    return db.get(Project, project_id)


def get_project_read(db: Session, project_id: int) -> ProjectRead | None:
    project = get_project(db, project_id)
    return _to_read(db, project) if project else None


def _ensure_okr_exists(db: Session, okr_id: int | None) -> None:
    if okr_id is not None and db.get(Okr, okr_id) is None:
        raise ValueError(f"OKR {okr_id} 不存在")


def create_project(db: Session, payload: ProjectCreate) -> ProjectRead:
    _ensure_okr_exists(db, payload.okr_id)
    project = Project(okr_id=payload.okr_id, name=payload.name, description=payload.description)
    db.add(project)
    db.commit()
    db.refresh(project)
    return _to_read(db, project)


def update_project(db: Session, project_id: int, payload: ProjectUpdate) -> ProjectRead | None:
    project = get_project(db, project_id)
    if project is None:
        return None
    fields = payload.model_dump(exclude_unset=True)
    if "okr_id" in fields:
        _ensure_okr_exists(db, fields["okr_id"])
    for key, value in fields.items():
        setattr(project, key, value)
    db.commit()
    db.refresh(project)
    return _to_read(db, project)


def delete_project(db: Session, project_id: int) -> bool:
    project = get_project(db, project_id)
    if project is None:
        return False
    # 应用层显式级联删除:先删事项子记录 → 事项 → 项目。
    # 绕开 MySQL 级联删除的表数上限(ER_FK_CASCADE_TOO_MANY 6575),
    # 且不依赖数据库外键级联(外键已移除)。
    todo_ids = db.scalars(select(Todo.id).where(Todo.project_id == project_id)).all()
    if todo_ids:
        ids = todo_service._subtree_ids(db, todo_ids)
        db.execute(delete(TodoNote).where(TodoNote.todo_id.in_(ids)))
        db.execute(delete(Todo).where(Todo.id.in_(ids)))
    db.delete(project)
    db.commit()
    return True


# ───────────────────── 整体导入（项目 + 模块/事项树） ─────────────────────

_MAX_TREE_DEPTH = 10


def _create_todo_tree(
    db: Session,
    project_id: int,
    parent_id: int | None,
    nodes: list[TodoImportNode],
    depth: int = 0,
) -> None:
    """递归创建事项树：顶层为模块（parent_id=None），children 逐级嵌套为事项。"""
    if depth > _MAX_TREE_DEPTH:
        raise ValueError(f"事项树层级超过上限 {_MAX_TREE_DEPTH}")
    for idx, node in enumerate(nodes):
        todo = Todo(
            project_id=project_id,
            parent_id=parent_id,
            title=node.title,
            description=node.description,
            sort_order=idx,
        )
        db.add(todo)
        db.flush()
        if node.children:
            _create_todo_tree(db, project_id, todo.id, node.children, depth + 1)


def create_project_with_todos(
    db: Session, payload: ProjectCreate, modules: list[TodoImportNode]
) -> ProjectRead:
    """创建项目并在同一事务内导入完整模块/事项树；任一环节失败整体回滚。"""
    if payload.okr_id is not None and db.get(Okr, payload.okr_id) is None:
        raise ValueError(f"OKR {payload.okr_id} 不存在")
    project = Project(
        okr_id=payload.okr_id, name=payload.name, description=payload.description
    )
    db.add(project)
    db.flush()
    _create_todo_tree(db, project.id, None, modules)
    db.commit()
    db.refresh(project)
    return _to_read(db, project)
