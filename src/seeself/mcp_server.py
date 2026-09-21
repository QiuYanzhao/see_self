"""MCP Server：以标准 MCP 协议暴露四类对象的读写能力。

工具命名统一 seeself_ 前缀，与 Web API 共用 Service 层，口径一致。
启动：
    python -m seeself.mcp_server                              # stdio（默认）
    python -m seeself.mcp_server --transport streamable-http  # 远程 SSE/HTTP
"""
from __future__ import annotations

import sys
from datetime import date

from fastmcp import FastMCP

from .db import SessionLocal
from .schemas import (
    OkrCreate,
    OkrUpdate,
    PlanCreate,
    PlanUpdate,
    ProjectCreate,
    ProjectUpdate,
    TodoCreate,
    TodoImportNode,
    TodoUpdate,
)
from .services import (
    okr_service,
    plan_import_service,
    plan_service,
    project_service,
    todo_service,
)

mcp = FastMCP("seeself-mcp")


def _dump(model) -> dict:
    return model.model_dump(mode="json")


# ───────────────────────── 五年计划 ─────────────────────────


@mcp.tool
def seeself_list_plans() -> list[dict]:
    """列出全部五年计划（含聚合进度）。"""
    with SessionLocal() as db:
        return [_dump(p) for p in plan_service.list_plans(db)]


@mcp.tool
def seeself_get_plan(plan_id: int) -> dict:
    """获取单个五年计划详情。plan_id 不存在时返回错误。"""
    with SessionLocal() as db:
        result = plan_service.get_plan_read(db, plan_id)
        if result is None:
            raise ValueError(f"五年计划 {plan_id} 不存在")
        return _dump(result)


@mcp.tool
def seeself_create_plan(name: str, start_year: int, end_year: int, description: str | None = None) -> dict:
    """创建五年计划。start_year/end_year 为四位年份，end_year 必须大于 start_year。"""
    with SessionLocal() as db:
        try:
            return _dump(
                plan_service.create_plan(
                    db, PlanCreate(name=name, start_year=start_year, end_year=end_year, description=description)
                )
            )
        except ValueError as exc:
            raise ValueError(str(exc)) from exc


@mcp.tool
def seeself_update_plan(
    plan_id: int,
    name: str | None = None,
    start_year: int | None = None,
    end_year: int | None = None,
    description: str | None = None,
) -> dict:
    """更新五年计划可改字段（仅传入需要修改的字段）。"""
    with SessionLocal() as db:
        result = plan_service.update_plan(
            db,
            plan_id,
            PlanUpdate(name=name, start_year=start_year, end_year=end_year, description=description),
        )
        if result is None:
            raise ValueError(f"五年计划 {plan_id} 不存在")
        return _dump(result)


@mcp.tool
def seeself_delete_plan(plan_id: int) -> dict:
    """删除五年计划，级联删除其下全部 OKR/项目/待办。"""
    with SessionLocal() as db:
        if not plan_service.delete_plan(db, plan_id):
            raise ValueError(f"五年计划 {plan_id} 不存在")
        return {"ok": True, "deleted": "plan", "id": plan_id}


# ───────────────────────── 季度 OKR ─────────────────────────


@mcp.tool
def seeself_list_okrs(plan_id: int | None = None) -> list[dict]:
    """列出 OKR；传入 plan_id 时只列出挂靠该五年计划的 OKR。"""
    with SessionLocal() as db:
        return [_dump(o) for o in okr_service.list_okrs(db, plan_id)]


@mcp.tool
def seeself_get_okr(okr_id: int) -> dict:
    """获取单个 OKR 详情。"""
    with SessionLocal() as db:
        result = okr_service.get_okr_read(db, okr_id)
        if result is None:
            raise ValueError(f"OKR {okr_id} 不存在")
        return _dump(result)


@mcp.tool
def seeself_create_okr(
    quarter: str, objective: str, plan_id: int | None = None, kr_note: str | None = None
) -> dict:
    """创建季度 OKR。quarter 如 '2026Q3'；plan_id 留空表示独立 OKR。"""
    with SessionLocal() as db:
        return _dump(
            okr_service.create_okr(
                db, OkrCreate(plan_id=plan_id, quarter=quarter, objective=objective, kr_note=kr_note)
            )
        )


@mcp.tool
def seeself_update_okr(
    okr_id: int,
    quarter: str | None = None,
    objective: str | None = None,
    plan_id: int | None = None,
    kr_note: str | None = None,
) -> dict:
    """更新 OKR 可改字段。"""
    with SessionLocal() as db:
        result = okr_service.update_okr(
            db,
            okr_id,
            OkrUpdate(plan_id=plan_id, quarter=quarter, objective=objective, kr_note=kr_note),
        )
        if result is None:
            raise ValueError(f"OKR {okr_id} 不存在")
        return _dump(result)


@mcp.tool
def seeself_delete_okr(okr_id: int) -> dict:
    """删除 OKR，级联删除其下全部项目/待办。"""
    with SessionLocal() as db:
        if not okr_service.delete_okr(db, okr_id):
            raise ValueError(f"OKR {okr_id} 不存在")
        return {"ok": True, "deleted": "okr", "id": okr_id}


# ───────────────────────── 项目 ─────────────────────────


@mcp.tool
def seeself_list_projects(okr_id: int | None = None) -> list[dict]:
    """列出项目（含分段进度）；传入 okr_id 时只列出挂靠该 OKR 的项目。"""
    with SessionLocal() as db:
        return [_dump(p) for p in project_service.list_projects(db, okr_id)]


@mcp.tool
def seeself_get_project(project_id: int) -> dict:
    """获取单个项目详情（含分段进度）。"""
    with SessionLocal() as db:
        result = project_service.get_project_read(db, project_id)
        if result is None:
            raise ValueError(f"项目 {project_id} 不存在")
        return _dump(result)


@mcp.tool
def seeself_create_project(name: str, okr_id: int | None = None, description: str | None = None) -> dict:
    """创建项目。okr_id 留空表示独立项目。"""
    with SessionLocal() as db:
        return _dump(
            project_service.create_project(
                db, ProjectCreate(okr_id=okr_id, name=name, description=description)
            )
        )


@mcp.tool
def seeself_update_project(
    project_id: int, name: str | None = None, okr_id: int | None = None, description: str | None = None
) -> dict:
    """更新项目可改字段。"""
    with SessionLocal() as db:
        result = project_service.update_project(
            db, project_id, ProjectUpdate(okr_id=okr_id, name=name, description=description)
        )
        if result is None:
            raise ValueError(f"项目 {project_id} 不存在")
        return _dump(result)


@mcp.tool
def seeself_delete_project(project_id: int) -> dict:
    """删除项目，级联删除其下全部待办。"""
    with SessionLocal() as db:
        if not project_service.delete_project(db, project_id):
            raise ValueError(f"项目 {project_id} 不存在")
        return {"ok": True, "deleted": "project", "id": project_id}


# ───────────────────────── 待办 ─────────────────────────


@mcp.tool
def seeself_list_todos(project_id: int) -> list[dict]:
    """获取项目的完整事项树（嵌套结构，含子记录）。"""
    with SessionLocal() as db:
        return [_dump(t) for t in todo_service.get_todo_tree(db, project_id)]


@mcp.tool
def seeself_get_todo(todo_id: int) -> dict:
    """获取单个事项。"""
    with SessionLocal() as db:
        todo = todo_service.get_todo(db, todo_id)
        if todo is None:
            raise ValueError(f"事项 {todo_id} 不存在")
        return _dump(todo_service._to_node(todo))


@mcp.tool
def seeself_create_todo(
    project_id: int, title: str, parent_id: int | None = None,
    description: str | None = None
) -> dict:
    """创建事项。parent_id 为父事项 ID（用于多层级嵌套），不传则为顶层事项。"""
    with SessionLocal() as db:
        return _dump(
            todo_service.create_todo(
                db,
                TodoCreate(
                    project_id=project_id,
                    title=title,
                    parent_id=parent_id,
                    description=description,
                ),
            )
        )


@mcp.tool
def seeself_update_todo(
    todo_id: int,
    title: str | None = None,
    parent_id: int | None = None,
    description: str | None = None,
) -> dict:
    """更新事项可改字段。parent_id 传 -1 表示移到顶层。"""
    with SessionLocal() as db:
        result = todo_service.update_todo(
            db,
            todo_id,
            TodoUpdate(
                title=title,
                parent_id=parent_id if parent_id != -1 else None,
                description=description,
            ),
        )
        if result is None:
            raise ValueError(f"事项 {todo_id} 不存在")
        return _dump(result)


@mcp.tool
def seeself_complete_todo(todo_id: int, completed: bool) -> dict:
    """勾选/取消完成待办。completed=true 记录完成时间，false 清除完成时间。"""
    with SessionLocal() as db:
        result = todo_service.set_completed(db, todo_id, completed)
        if result is None:
            raise ValueError(f"待办 {todo_id} 不存在")
        return _dump(result)


@mcp.tool
def seeself_delete_todo(todo_id: int) -> dict:
    """删除待办。"""
    with SessionLocal() as db:
        if not todo_service.delete_todo(db, todo_id):
            raise ValueError(f"待办 {todo_id} 不存在")
        return {"ok": True, "deleted": "todo", "id": todo_id}


# ───────────────────────── 导入与批量操作 ─────────────────────────


@mcp.tool
def seeself_import_plan(outline: dict) -> dict:
    """导入《个人五年规划纲要》JSON（personal-five-year-plan 技能导出格式）。

    系统只保留一份五年计划：已存在则整体覆盖（级联删除旧计划及其 OKR/项目/待办），
    首年季度 OKR 随计划一并导入。outline 即纲要 JSON 对象（含 period.start/end 等字段）。
    """
    with SessionLocal() as db:
        return _dump(plan_import_service.import_outline(db, outline, source="mcp"))


@mcp.tool
def seeself_batch_create_okrs(okrs: list[OkrCreate]) -> dict:
    """批量创建季度 OKR（单事务：任一失败则全部回滚，不产生部分数据）。

    每项字段与创建单个 OKR 一致：quarter（如 '2026Q3'）与 objective 必填，
    plan_id 留空表示独立 OKR，kr_results 为关键结果字符串列表。
    """
    if not okrs:
        raise ValueError("okrs 不能为空")
    items = [o if isinstance(o, OkrCreate) else OkrCreate(**o) for o in okrs]
    with SessionLocal() as db:
        created = okr_service.batch_create_okrs(db, items)
        return {"ok": True, "count": len(created), "created": [_dump(o) for o in created]}


@mcp.tool
def seeself_batch_complete_todos(todo_ids: list[int], completed: bool) -> dict:
    """批量勾选/取消完成待办（单事务：任一 id 不存在则整体回滚）。

    completed=true 记录完成时间，false 清除完成时间。
    """
    if not todo_ids:
        raise ValueError("todo_ids 不能为空")
    with SessionLocal() as db:
        updated = todo_service.batch_set_completed(db, todo_ids, completed)
        return {"ok": True, "count": len(updated), "updated": [_dump(o) for o in updated]}


@mcp.tool
def seeself_import_project(
    name: str,
    okr_id: int | None = None,
    description: str | None = None,
    modules: list[TodoImportNode] | None = None,
) -> dict:
    """导入一个项目及其完整模块/事项树（单事务：任一环节失败整体回滚）。

    modules 为顶层模块列表；每个模块可带 children（其下事项），支持多级嵌套。
    okr_id 留空表示独立项目。
    """
    nodes = [
        m if isinstance(m, TodoImportNode) else TodoImportNode(**m) for m in (modules or [])
    ]
    with SessionLocal() as db:
        return _dump(
            project_service.create_project_with_todos(
                db,
                ProjectCreate(okr_id=okr_id, name=name, description=description),
                nodes,
            )
        )


def main() -> None:
    transport = "stdio"
    if "--transport" in sys.argv:
        idx = sys.argv.index("--transport")
        transport = sys.argv[idx + 1] if idx + 1 < len(sys.argv) else "stdio"
    if transport == "streamable-http":
        port = 8765
        if "--port" in sys.argv:
            idx = sys.argv.index("--port")
            port = int(sys.argv[idx + 1])
        mcp.run(transport="streamable-http", port=port)
    else:
        mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
