"""事项树 CRUD、完成状态、进度统计、热力图、时间线。"""
from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, timedelta

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session, selectinload

from ..models import Project, Todo, TodoNote
from ..schemas import (
    TodoCreate,
    TodoNodeRead,
    TodoNoteCreate,
    TodoNoteRead,
    TodoNoteUpdate,
    TodoUpdate,
)


# ───────────────────── 树构建 ─────────────────────


def _build_tree(nodes: list[Todo]) -> list[TodoNodeRead]:
    """将扁平列表构建为嵌套树。"""
    node_map: dict[int, TodoNodeRead] = {}
    for n in nodes:
        notes = [
            TodoNoteRead(
                id=note.id, todo_id=note.todo_id, content=note.content,
                sort_order=note.sort_order, created_at=note.created_at,
            )
            for note in sorted(n.notes, key=lambda x: x.sort_order)
        ]
        node_map[n.id] = TodoNodeRead(
            id=n.id, project_id=n.project_id, parent_id=n.parent_id,
            title=n.title, description=n.description,
            sort_order=n.sort_order, completed_at=n.completed_at,
            created_at=n.created_at, children=[], notes=notes,
        )
    roots = []
    for n in nodes:
        node = node_map[n.id]
        if n.parent_id and n.parent_id in node_map:
            node_map[n.parent_id].children.append(node)
        else:
            roots.append(node)
    # 排序
    for node in node_map.values():
        node.children.sort(key=lambda x: (x.sort_order, x.id))
    roots.sort(key=lambda x: (x.sort_order, x.id))
    return roots


def get_todo_tree(db: Session, project_id: int) -> list[TodoNodeRead]:
    """获取项目的完整事项树。"""
    stmt = (
        select(Todo)
        .where(Todo.project_id == project_id)
        .options(selectinload(Todo.notes))
        .order_by(Todo.sort_order, Todo.id)
    )
    nodes = db.execute(stmt).scalars().all()
    return _build_tree(list(nodes))


# ───────────────────── CRUD ─────────────────────


def _to_node(todo: Todo) -> TodoNodeRead:
    notes = [
        TodoNoteRead(
            id=note.id, todo_id=note.todo_id, content=note.content,
            sort_order=note.sort_order, created_at=note.created_at,
        )
        for note in sorted(todo.notes, key=lambda x: x.sort_order)
    ]
    return TodoNodeRead(
        id=todo.id, project_id=todo.project_id, parent_id=todo.parent_id,
        title=todo.title, description=todo.description,
        sort_order=todo.sort_order, completed_at=todo.completed_at,
        created_at=todo.created_at, children=[], notes=notes,
    )


def get_todo(db: Session, todo_id: int) -> Todo | None:
    return db.get(Todo, todo_id)


def _ensure_parent(db: Session, project_id: int, parent_id: int | None) -> None:
    """校验项目存在、parent_id 对应事项存在且属于同一项目(不依赖数据库外键)。"""
    if db.get(Project, project_id) is None:
        raise ValueError(f"项目 {project_id} 不存在")
    if parent_id is None:
        return
    parent = db.get(Todo, parent_id)
    if parent is None or parent.project_id != project_id:
        raise ValueError(f"父事项 {parent_id} 不存在或不属于该项目 {project_id}")


def create_todo(db: Session, payload: TodoCreate) -> TodoNodeRead:
    _ensure_parent(db, payload.project_id, payload.parent_id)
    todo = Todo(
        project_id=payload.project_id,
        parent_id=payload.parent_id,
        title=payload.title,
        description=payload.description,
        sort_order=payload.sort_order,
    )
    db.add(todo)
    db.commit()
    db.refresh(todo)
    return _to_node(todo)


def update_todo(db: Session, todo_id: int, payload: TodoUpdate) -> TodoNodeRead | None:
    todo = get_todo(db, todo_id)
    if todo is None:
        return None
    fields = payload.model_dump(exclude_unset=True)
    if "parent_id" in fields and fields["parent_id"] is not None:
        parent = db.get(Todo, fields["parent_id"])
        if parent is None or parent.project_id != todo.project_id:
            raise ValueError(f"父事项 {fields['parent_id']} 不存在或不属于该项目 {todo.project_id}")
        # 防环:父事项不能是自身或其任意后代
        if fields["parent_id"] in _subtree_ids(db, [todo.id]):
            raise ValueError("父事项不能是自身或其子事项")
    for key, value in fields.items():
        setattr(todo, key, value)
    db.commit()
    db.refresh(todo)
    return _to_node(todo)


def set_completed(db: Session, todo_id: int, completed: bool) -> TodoNodeRead | None:
    """勾选完成记录完成时间；取消完成清除完成时间。"""
    todo = get_todo(db, todo_id)
    if todo is None:
        return None
    if completed:
        if todo.completed_at is None:
            todo.completed_at = datetime.now()
    else:
        todo.completed_at = None
    db.commit()
    db.refresh(todo)
    return _to_node(todo)


def batch_set_completed(db: Session, todo_ids: list[int], completed: bool) -> list[TodoNodeRead]:
    """批量设置完成状态，单事务：任一 id 不存在则整体回滚，不产生部分数据。"""
    if not todo_ids:
        raise ValueError("todo_ids 不能为空")
    todos: list[Todo] = []
    for todo_id in todo_ids:
        todo = get_todo(db, todo_id)
        if todo is None:
            raise ValueError(f"事项 {todo_id} 不存在")
        if completed:
            if todo.completed_at is None:
                todo.completed_at = datetime.now()
        else:
            todo.completed_at = None
        todos.append(todo)
    db.commit()
    return [_to_node(t) for t in todos]


def _subtree_ids(db: Session, root_ids: list[int]) -> list[int]:
    """返回 root_ids 及其全部后代 todo id(含自身,按 parent_id 树形自引用收集)。"""
    ids = list(root_ids)
    frontier = root_ids
    while frontier:
        kids = db.scalars(select(Todo.id).where(Todo.parent_id.in_(frontier))).all()
        ids.extend(kids)
        frontier = kids
    return ids


def delete_todo(db: Session, todo_id: int) -> bool:
    todo = get_todo(db, todo_id)
    if todo is None:
        return False
    # 显式级联:先删子记录,再删事项及其后代(不依赖数据库外键级联)
    ids = _subtree_ids(db, [todo_id])
    db.execute(delete(TodoNote).where(TodoNote.todo_id.in_(ids)))
    db.execute(delete(Todo).where(Todo.id.in_(ids)))
    db.commit()
    return True


# ───────────────────── 子记录 ─────────────────────


def add_note(db: Session, todo_id: int, payload: TodoNoteCreate) -> TodoNoteRead | None:
    todo = get_todo(db, todo_id)
    if todo is None:
        return None
    note = TodoNote(todo_id=todo_id, content=payload.content, sort_order=payload.sort_order)
    db.add(note)
    db.commit()
    db.refresh(note)
    return TodoNoteRead(
        id=note.id, todo_id=note.todo_id, content=note.content,
        sort_order=note.sort_order, created_at=note.created_at,
    )


def update_note(db: Session, note_id: int, payload: TodoNoteUpdate) -> TodoNoteRead | None:
    note = db.get(TodoNote, note_id)
    if note is None:
        return None
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(note, key, value)
    db.commit()
    db.refresh(note)
    return TodoNoteRead(
        id=note.id, todo_id=note.todo_id, content=note.content,
        sort_order=note.sort_order, created_at=note.created_at,
    )


def delete_note(db: Session, note_id: int) -> bool:
    note = db.get(TodoNote, note_id)
    if note is None:
        return False
    db.delete(note)
    db.commit()
    return True


# ───────────────────── 进度统计 ─────────────────────


def _count_leaves(nodes: list[Todo]) -> tuple[int, int]:
    """统计叶子节点总数和已完成数。"""
    total = 0
    done = 0
    for n in nodes:
        if not n.children:  # 叶子节点
            total += 1
            if n.completed_at is not None:
                done += 1
    return total, done


def project_progress(db: Session, project_id: int) -> dict:
    """项目进度汇总：总叶子数、已完成叶子数、完成度、各一级模块进度。"""
    stmt = (
        select(Todo)
        .where(Todo.project_id == project_id)
        .options(selectinload(Todo.children))
        .order_by(Todo.sort_order, Todo.id)
    )
    all_nodes = db.execute(stmt).scalars().all()

    # 递归统计
    def count_subtree(node: Todo) -> tuple[int, int]:
        if not node.children:
            return (1, 1) if node.completed_at else (1, 0)
        t, d = 0, 0
        for child in node.children:
            ct, cd = count_subtree(child)
            t += ct
            d += cd
        return t, d

    total, done = 0, 0
    modules = []
    for node in all_nodes:
        if node.parent_id is None:
            t, d = count_subtree(node)
            total += t
            done += d
            pct = round(d / t * 100, 1) if t else 0
            # 模块状态：全部完成=done，部分完成=active，未开始=todo
            if d == 0:
                status = "todo"
            elif d == t:
                status = "done"
            else:
                status = "active"
            modules.append({
                "id": node.id, "name": node.title,
                "total": t, "completed": d, "percent": pct, "status": status,
            })

    return {
        "total_leaves": total,
        "completed_leaves": done,
        "percent": round(done / total * 100, 1) if total else 0,
        "modules": modules,
    }


def heatmap_data(db: Session, project_id: int | None = None, days: int = 365) -> list[dict]:
    """热力图数据：最近 N 天每天完成的事项数。project_id 为 None 时统计全部项目。"""
    since = date.today() - timedelta(days=days)
    stmt = (
        select(Todo.completed_at)
        .where(Todo.completed_at.is_not(None))
        .where(func.date(Todo.completed_at) >= since)
    )
    if project_id is not None:
        stmt = stmt.where(Todo.project_id == project_id)
    rows = db.execute(stmt).scalars().all()
    counter: dict[str, int] = defaultdict(int)
    for dt in rows:
        d = dt.date() if hasattr(dt, "date") else dt
        counter[d.isoformat()] += 1
    return [{"date": k, "count": v} for k, v in sorted(counter.items())]


def timeline_data(db: Session, project_id: int) -> list[dict]:
    """时间线数据：已完成事项按完成时间倒序，带子记录。"""
    stmt = (
        select(Todo)
        .where(Todo.project_id == project_id)
        .where(Todo.completed_at.is_not(None))
        .options(selectinload(Todo.notes))
        .order_by(Todo.completed_at.desc())
    )
    nodes = db.execute(stmt).scalars().all()
    result = []
    for n in nodes:
        notes = [
            {"id": note.id, "content": note.content, "sort_order": note.sort_order}
            for note in sorted(n.notes, key=lambda x: x.sort_order)
        ]
        result.append({
            "id": n.id, "title": n.title,
            "completed_at": n.completed_at.isoformat() if n.completed_at else None,
            "notes": notes,
        })
    return result


def pending_items(db: Session, project_id: int) -> list[dict]:
    """未完成叶子事项列表，带模块路径。"""
    # 获取所有节点
    stmt = select(Todo).where(Todo.project_id == project_id).order_by(Todo.sort_order, Todo.id)
    all_nodes = db.execute(stmt).scalars().all()

    # 构建 id→node 映射和 children 判断
    node_map = {n.id: n for n in all_nodes}
    has_children = {n.id: False for n in all_nodes}
    for n in all_nodes:
        if n.parent_id and n.parent_id in has_children:
            has_children[n.parent_id] = True

    # 构建路径
    def get_path(node: Todo) -> str:
        parts = []
        cur = node
        depth = 0
        while cur and cur.parent_id and depth < 10:
            parent = node_map.get(cur.parent_id)
            if parent:
                parts.append(parent.title)
                cur = parent
                depth += 1
            else:
                break
        parts.reverse()
        return " / ".join(parts)

    result = []
    for n in all_nodes:
        if n.completed_at is None and not has_children[n.id]:
            result.append({
                "id": n.id, "title": n.title,
                "parent_path": get_path(n),
            })
    return result


# ───────────────────── 分段进度条 ─────────────────────

# 渐进配色（中等饱和）：灰 -> 蓝 -> 绿 -> 黄 -> 橙，越近越暖越突出
SEG_COLORS = {
    "before_month": "#a8b0bc",
    "month_to_week": "#5aa0f8",
    "week_to_yesterday": "#52cd7c",
    "yesterday": "#f5c531",
    "today": "#f58a4b",
}


def segmented_progress(db: Session, project_id: int, today: date | None = None) -> dict:
    """按 月初/周初/昨日/当前 四个时间快照切分进度条。

    统计各时间点之前已完成的叶子节点数，计算百分比段。
    返回 {"segments": [...], "month": .., "week": .., "yesterday": ..}，
    其中 month=本月1日0点至今、week=本周一0点至今、yesterday=昨天0点至今天0点。
    """
    today = today or date.today()
    # 总叶子数
    stmt_all = select(Todo).where(Todo.project_id == project_id)
    all_nodes = db.execute(stmt_all).scalars().all()
    child_ids = {n.parent_id for n in all_nodes if n.parent_id}
    leaves = [n for n in all_nodes if n.id not in child_ids]
    total = len(leaves)
    if total == 0:
        return {"segments": [], "month": 0.0, "week": 0.0, "yesterday": 0.0, "today": 0.0}

    # 时间快照
    month_start = datetime(today.year, today.month, 1)
    monday = today - timedelta(days=today.weekday())
    week_start = datetime(monday.year, monday.month, monday.day)
    day_start = datetime(today.year, today.month, today.day)
    tomorrow = day_start + timedelta(days=1)

    def done_before(moment: datetime) -> int:
        return sum(1 for n in leaves if n.completed_at and n.completed_at < moment)

    p_month = done_before(month_start) / total * 100
    p_week = done_before(week_start) / total * 100
    p_yesterday = done_before(day_start) / total * 100
    p_now = done_before(tomorrow) / total * 100
    two_days_ago = day_start - timedelta(days=1)
    p_2days = done_before(two_days_ago) / total * 100

    raw = [
        ("月初前", 0.0, p_month, SEG_COLORS["before_month"]),
        ("月初→周初", p_month, p_week, SEG_COLORS["month_to_week"]),
        ("周初→昨日", p_week, p_2days, SEG_COLORS["week_to_yesterday"]),
        ("昨日", p_2days, p_yesterday, SEG_COLORS["yesterday"]),
        ("今日", p_yesterday, p_now, SEG_COLORS["today"]),
    ]
    segments = []
    for label, start, end, color in raw:
        end = max(end, start)
        value = round(end - start, 2)
        if value > 0:
            segments.append({
                "label": label, "start": round(start, 2),
                "end": round(end, 2), "value": value, "color": color,
            })
    return {
        "segments": segments,
        # 口径:本月 = 本月1日0点至今;本周 = 本周一0点至今;昨日 = 昨天0点至今天0点;今日 = 今天0点至实时
        "month": round(p_now - p_month, 2),
        "week": round(p_now - p_week, 2),
        "yesterday": round(p_yesterday - p_2days, 2),
        "today": round(p_now - p_yesterday, 2),
    }
