"""数据导出：全量 JSON / 待办 CSV 备份。"""
from __future__ import annotations

import csv
import io
import json
from datetime import date, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import FiveYearPlan, Okr, Project, Todo


def _default(obj):
    if isinstance(obj, (date, datetime)):
        return obj.isoformat()
    raise TypeError(f"不可序列化的类型: {type(obj)}")


def export_json(db: Session) -> str:
    def rows(model):
        return [
            {c.name: getattr(r, c.name) for c in model.__table__.columns}
            for r in db.execute(select(model)).scalars().all()
        ]

    payload = {
        "exported_at": datetime.now().isoformat(),
        "five_year_plans": rows(FiveYearPlan),
        "okrs": rows(Okr),
        "projects": rows(Project),
        "todos": rows(Todo),
    }
    return json.dumps(payload, ensure_ascii=False, indent=2, default=_default)


def export_todos_csv(db: Session) -> str:
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(
        ["id", "project_id", "parent_id", "title", "description", "sort_order", "completed_at", "created_at"]
    )
    for todo in db.execute(select(Todo).order_by(Todo.id)).scalars().all():
        writer.writerow(
            [
                todo.id,
                todo.project_id,
                todo.parent_id or "",
                todo.title,
                todo.description or "",
                todo.sort_order,
                todo.completed_at.isoformat() if todo.completed_at else "",
                todo.created_at.isoformat() if todo.created_at else "",
            ]
        )
    return buffer.getvalue()
