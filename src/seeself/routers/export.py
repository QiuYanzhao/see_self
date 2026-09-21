"""数据导出（JSON / CSV 备份）。"""
from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from ..db import get_db
from ..services import export_service

router = APIRouter(prefix="/api/export", tags=["export"])


@router.post("")
def export_all(fmt: str = "json", db: Session = Depends(get_db)):
    if fmt == "csv":
        content = export_service.export_todos_csv(db)
        return Response(
            content=content,
            media_type="text/csv; charset=utf-8",
            headers={"Content-Disposition": "attachment; filename=seeself_todos.csv"},
        )
    content = export_service.export_json(db)
    return Response(
        content=content,
        media_type="application/json; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=seeself_backup.json"},
    )
