"""测试夹具：每个测试使用独立的临时 SQLite 数据库。"""
from __future__ import annotations

from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from seeself.db import get_db
from seeself.main import app
from seeself.models import Base, Okr, Project, Todo, FiveYearPlan


@pytest.fixture
def db_session():
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
    session = TestingSession()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)


@pytest.fixture
def client(db_session):
    def _override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def seed_layer(db) -> dict:
    """构造 计划→OKR→项目→待办 的测试数据，返回各对象 id。"""
    plan = FiveYearPlan(name="转型五年计划", start_year=2026, end_year=2031)
    db.add(plan)
    db.flush()
    okr = Okr(plan_id=plan.id, quarter="2026Q3", objective="完成 Agent 转型")
    db.add(okr)
    db.flush()
    project = Project(okr_id=okr.id, name="Spring AI Alibaba 学习")
    db.add(project)
    db.flush()
    return {"plan_id": plan.id, "okr_id": okr.id, "project_id": project.id}
