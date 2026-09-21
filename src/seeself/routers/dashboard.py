"""首页监控看板。"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..db import get_db
from ..schemas import DashboardData
from ..services import dashboard_service

router = APIRouter(prefix="/api", tags=["dashboard"])


@router.get("/dashboard", response_model=DashboardData)
def get_dashboard(db: Session = Depends(get_db)) -> DashboardData:
    return dashboard_service.dashboard_data(db)
