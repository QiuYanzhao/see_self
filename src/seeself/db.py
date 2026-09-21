"""SQLAlchemy 引擎与会话工厂（方言无关）。

SQLite 连接时自动开启外键级联（PRAGMA foreign_keys=ON）；
MySQL（InnoDB）默认支持外键，无需特殊处理。
"""
from __future__ import annotations

from collections.abc import Iterator

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from .config import settings

_connect_args: dict = {}
if settings.database_url.startswith("sqlite"):
    # SQLite 多线程（FastAPI 线程池）下需要放开同线程检查
    _connect_args = {"check_same_thread": False}

engine: Engine = create_engine(
    settings.database_url,
    connect_args=_connect_args,
    echo=False,
    future=True,
    # 连接池配置：避免 MySQL wait_timeout 回收空闲连接后触发重建（远程新建连接 ~400ms）
    pool_pre_ping=True,   # 检出连接前先 ping，失效则自动重建
    pool_recycle=1800,    # 连接存活超过 30 分钟自动回收重建（小于 MySQL 默认 wait_timeout 8h）
    pool_size=5,
    max_overflow=10,
)

if settings.database_url.startswith("sqlite"):

    @event.listens_for(engine, "connect")
    def _sqlite_pragma(dbapi_connection, _connection_record):  # noqa: ANN001
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False, future=True)


def get_db() -> Iterator[Session]:
    """FastAPI 依赖：每请求一个 Session，请求结束关闭。"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
