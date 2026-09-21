"""MCP 新增工具测试：导入五年计划 / 批量 OKR / 批量完成 / 导入项目树。

直接调用 mcp_server 中的工具函数，并把 SessionLocal 指向内存 SQLite，
验证业务逻辑、单事务与失败整体回滚行为。
"""
from __future__ import annotations

import asyncio

import pytest
from sqlalchemy import create_engine, event, func, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import seeself.mcp_server as mcp_server
from seeself.models import Base, FiveYearPlan, Okr, Project, Todo
from seeself.services import todo_service


@pytest.fixture
def mcp_env():
    """把 mcp_server.SessionLocal 指向独立内存库，返回测试用的 sessionmaker。"""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def _pragma(dbapi_connection, _record):  # noqa: ANN001
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(engine)
    TestingSession = sessionmaker(bind=engine, autoflush=False, future=True)
    original = mcp_server.SessionLocal
    mcp_server.SessionLocal = TestingSession
    try:
        yield TestingSession
    finally:
        mcp_server.SessionLocal = original
        Base.metadata.drop_all(engine)


def _count(db, model) -> int:
    return db.execute(select(func.count(model.id))).scalar()


OUTLINE = {
    "plan_name": "测试五年计划",
    "period": {"start": "2026-01-01", "end": "2030-12-31"},
    "vision": {
        "positioning": "成为独立 Agent 开发者",
        "core_goals": ["跑通 MCP"],
        "bottom_lines": ["不裸辞"],
    },
    "year1": {
        "goals": ["掌握 Spring AI Alibaba"],
        "okrs": [
            {
                "quarter": "Q1 2026.01-03",
                "objectives": [
                    {"objective": "学会 MCP", "key_results": ["完成 4 个工具"]}
                ],
            }
        ],
    },
}


def test_tools_registered():
    names = {t.name for t in asyncio.run(mcp_server.mcp.list_tools())}
    assert {
        "seeself_import_plan",
        "seeself_batch_create_okrs",
        "seeself_batch_complete_todos",
        "seeself_import_project",
    } <= names


def test_import_plan_creates_and_overwrites(mcp_env):
    result = mcp_server.seeself_import_plan(OUTLINE)
    assert result["name"].startswith("测试五年计划")
    assert result["start_year"] == 2026
    assert result["end_year"] == 2030
    assert result["okr_count"] == 1
    assert result["okrs"][0]["objective"] == "学会 MCP"
    assert result["okrs"][0]["kr_results"] == ["完成 4 个工具"]

    # 再次导入整体覆盖：数据库里仍只有一份计划，旧 OKR 级联删除
    outline2 = dict(OUTLINE, plan_name="第二个计划")
    mcp_server.seeself_import_plan(outline2)
    db = mcp_env()
    try:
        plans = db.execute(select(FiveYearPlan)).scalars().all()
        okrs = db.execute(select(Okr)).scalars().all()
    finally:
        db.close()
    assert len(plans) == 1
    assert plans[0].name.startswith("第二个计划")
    assert len(okrs) == 1


def test_batch_create_okrs_and_rollback(mcp_env):
    db = mcp_env()
    try:
        plan = FiveYearPlan(name="计划", start_year=2026, end_year=2031)
        db.add(plan)
        db.commit()
        plan_id = plan.id
    finally:
        db.close()

    result = mcp_server.seeself_batch_create_okrs(
        [
            {"quarter": "2026Q3", "objective": "目标A", "plan_id": plan_id, "kr_results": ["KR1"]},
            {"quarter": "2026Q4", "objective": "目标B"},
        ]
    )
    assert result["ok"] is True
    assert result["count"] == 2
    assert result["created"][0]["objective"] == "目标A"
    assert result["created"][0]["plan_id"] == plan_id
    assert result["created"][1]["plan_id"] is None

    # 任一 plan_id 不存在 → 整体回滚，不产生部分数据
    with pytest.raises(ValueError, match="五年计划不存在"):
        mcp_server.seeself_batch_create_okrs(
            [
                {"quarter": "2027Q1", "objective": "合法项"},
                {"quarter": "2027Q2", "objective": "非法项", "plan_id": 9999},
            ]
        )
    db = mcp_env()
    try:
        assert _count(db, Okr) == 2
    finally:
        db.close()


def test_batch_complete_todos_and_rollback(mcp_env):
    db = mcp_env()
    try:
        project = Project(name="学习项目")
        db.add(project)
        db.commit()
        t1 = Todo(project_id=project.id, title="事项1")
        t2 = Todo(project_id=project.id, title="事项2")
        t3 = Todo(project_id=project.id, title="事项3")
        db.add_all([t1, t2, t3])
        db.commit()
        ids = [t1.id, t2.id, t3.id]
    finally:
        db.close()

    result = mcp_server.seeself_batch_complete_todos(ids[:2], True)
    assert result["ok"] is True
    assert result["count"] == 2
    assert result["updated"][0]["completed_at"] is not None

    # 取消完成
    result2 = mcp_server.seeself_batch_complete_todos([ids[0]], False)
    assert result2["updated"][0]["completed_at"] is None

    # 任一 id 不存在 → 整体回滚，先前完成的保持完成
    with pytest.raises(ValueError, match="事项 .* 不存在"):
        mcp_server.seeself_batch_complete_todos([ids[1], 99999], True)
    db = mcp_env()
    try:
        t2 = db.get(Todo, ids[1])
    finally:
        db.close()
    assert t2.completed_at is not None


def test_import_project_with_tree_and_rollback(mcp_env):
    db = mcp_env()
    try:
        plan = FiveYearPlan(name="计划", start_year=2026, end_year=2031)
        db.add(plan)
        db.commit()
        okr = Okr(plan_id=plan.id, quarter="2026Q3", objective="转型")
        db.add(okr)
        db.commit()
        okr_id = okr.id
    finally:
        db.close()

    result = mcp_server.seeself_import_project(
        name="Spring AI Alibaba 学习",
        okr_id=okr_id,
        modules=[
            {
                "title": "模块A",
                "children": [
                    {"title": "事项A1"},
                    {"title": "事项A2", "children": [{"title": "子事项A21"}]},
                ],
            },
            {"title": "模块B"},
        ],
    )
    assert result["name"] == "Spring AI Alibaba 学习"
    assert result["okr_id"] == okr_id
    assert result["total_leaves"] == 3  # A1、A21、B

    db = mcp_env()
    try:
        project = db.execute(
            select(Project).where(Project.name == "Spring AI Alibaba 学习")
        ).scalar_one()
        progress = todo_service.project_progress(db, project.id)
    finally:
        db.close()
    assert progress["modules"][0]["name"] == "模块A"
    assert progress["modules"][0]["total"] == 2  # A1 + A21

    db = mcp_env()
    try:
        todos = db.execute(select(Todo).order_by(Todo.id)).scalars().all()
    finally:
        db.close()
    top = [t for t in todos if t.parent_id is None]
    assert [t.title for t in top] == ["模块A", "模块B"]
    a_children = [t for t in todos if t.parent_id == top[0].id]
    assert [t.title for t in a_children] == ["事项A1", "事项A2"]

    # okr_id 不存在 → 整体回滚，不创建项目
    with pytest.raises(ValueError, match="OKR .* 不存在"):
        mcp_server.seeself_import_project(
            name="非法项目", okr_id=99999, modules=[{"title": "模块X"}]
        )
    db = mcp_env()
    try:
        assert _count(db, Project) == 1
        assert _count(db, Todo) == 5  # 模块A/事项A1/事项A2/子事项A21/模块B
    finally:
        db.close()
