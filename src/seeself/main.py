"""FastAPI 应用入口。

- 挂载全部 JSON API 路由
- 开发期允许 Vite dev server 跨域
- 生产期托管 frontend/dist 静态资源（SPA fallback 到 index.html）
"""
from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from .routers import dashboard, export, okrs, plans, projects, settings, todos

app = FastAPI(title="see_self · 个人五年计划管理系统", version="0.1.0")

# 开发期：Vite dev server（5173）跨域访问 API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

for module in (dashboard, plans, okrs, projects, todos, settings, export):
    app.include_router(module.router)


# ───────────────────── 上传文件静态服务 ─────────────────────
UPLOAD_DIR = Path(__file__).resolve().parents[2] / "data" / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")


@app.get("/api/health")
def health():
    return {"status": "ok"}


# ───────────────────── 前端静态资源（生产） ─────────────────────

DIST_DIR = Path(__file__).resolve().parents[2] / "frontend" / "dist"

if DIST_DIR.exists():
    # 静态资源目录（js/css/图片）
    app.mount("/assets", StaticFiles(directory=DIST_DIR / "assets"), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    def spa_fallback(full_path: str):
        # 未命中的 API 路径返回标准 404，其余路径回退到 index.html 交由 Vue Router
        if full_path.startswith("api/"):
            return JSONResponse(status_code=404, content={"detail": "Not Found"})
        candidate = DIST_DIR / full_path
        if full_path and candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(DIST_DIR / "index.html", headers={"Cache-Control": "no-cache, no-store, must-revalidate"})
