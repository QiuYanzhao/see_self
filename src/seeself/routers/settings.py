"""全局设置（时区等）。"""
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pathlib import Path
from sqlalchemy.orm import Session

from ..config import BASE_DIR, settings
from ..db import get_db
from ..models import AppSetting
from ..schemas import SettingsRead, SettingsUpdate

router = APIRouter(prefix="/api/settings", tags=["settings"])

# 上传文件存储目录（项目根目录 data/uploads/）
UPLOAD_DIR = BASE_DIR / "data" / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

ALLOWED_IMAGE_TYPES = {"image/png", "image/jpeg", "image/gif", "image/webp"}
MAX_UPLOAD_SIZE = 10 * 1024 * 1024  # 10MB


@router.get("", response_model=SettingsRead)
def get_settings():
    return SettingsRead(timezone=settings.timezone)


@router.put("", response_model=SettingsRead)
def update_settings(payload: SettingsUpdate, db: Session = Depends(get_db)):
    return get_settings()


# ───────────────────── 外观设置 ─────────────────────

DEFAULT_BG_OPACITY = 0.85   # 背景不透明度(0~1),对应 Ghostty background-opacity
DEFAULT_BG_BLUR = 30        # 背景模糊半径(px),对应 Ghostty background-blur-radius


def _get_setting(db: Session, key: str, default: str | None = None) -> str | None:
    row = db.get(AppSetting, key)
    return row.value if row and row.value else default


def _save_setting(db: Session, key: str, value: str):
    row = db.get(AppSetting, key)
    if row:
        row.value = value
    else:
        db.add(AppSetting(key=key, value=value))


@router.get("/appearance")
def get_appearance(db: Session = Depends(get_db)):
    return {
        "background_image_url": _get_setting(db, "background_image_url"),
        "background_opacity": float(_get_setting(db, "background_opacity", str(DEFAULT_BG_OPACITY))),
        "background_blur_radius": int(_get_setting(db, "background_blur_radius", str(DEFAULT_BG_BLUR))),
    }


@router.put("/appearance")
def update_appearance(payload: dict, db: Session = Depends(get_db)):
    opacity = payload.get("background_opacity")
    if opacity is not None:
        try:
            opacity = max(0.05, min(1.0, float(opacity)))
        except (TypeError, ValueError):
            raise HTTPException(400, "background_opacity 需为 0~1 的数字")
        _save_setting(db, "background_opacity", f"{opacity:.2f}")
    blur = payload.get("background_blur_radius")
    if blur is not None:
        try:
            blur = max(0, min(80, int(blur)))
        except (TypeError, ValueError):
            raise HTTPException(400, "background_blur_radius 需为 0~80 的整数")
        _save_setting(db, "background_blur_radius", str(blur))
    db.commit()
    return get_appearance(db)


@router.post("/background")
async def upload_background(file: UploadFile = File(...), db: Session = Depends(get_db)):
    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(status_code=400, detail=f"不支持的图片类型: {file.content_type}")
    content = await file.read()
    if len(content) > MAX_UPLOAD_SIZE:
        raise HTTPException(status_code=400, detail="图片大小不能超过 10MB")
    ext = Path(file.filename or "bg.png").suffix.lower()
    filename = f"background{ext}"
    filepath = UPLOAD_DIR / filename
    filepath.write_bytes(content)
    url = f"/uploads/{filename}"
    existing = db.get(AppSetting, "background_image_url")
    if existing:
        existing.value = url
    else:
        db.add(AppSetting(key="background_image_url", value=url))
    db.commit()
    return {"background_image_url": url}


@router.delete("/background")
def delete_background(db: Session = Depends(get_db)):
    row = db.get(AppSetting, "background_image_url")
    if row and row.value:
        filename = Path(row.value).name
        filepath = UPLOAD_DIR / filename
        if filepath.exists():
            filepath.unlink()
        db.delete(row)
        db.commit()
    return {"background_image_url": None}
