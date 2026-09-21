"""首页监控看板聚合：时间进度 + 项目进度概览。"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import Project
from ..schemas import DashboardData
from . import progress as progress_svc
from .project_service import _to_read


def dashboard_data(db: Session) -> DashboardData:
    projects = db.execute(select(Project).order_by(Project.id)).scalars().all()
    items = [_to_read(db, p) for p in projects]
    return DashboardData(
        time=progress_svc.time_progress(),
        projects=items,
    )
