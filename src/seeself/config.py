"""全局配置：数据库连接、顺延与高亮阈值等设置。

设置项支持三种来源（优先级从高到低）：
1. 环境变量：MySQL 分段配置 DB_HOST/DB_PORT/DB_USER/DB_PASSWORD/DB_NAME（推荐，
   密码按原文填写，由 SQLAlchemy URL.create 自动转义，规避特殊字符编码问题）；
   兼容旧方式 DATABASE_URL 单串。
2. data/settings.json（用户可通过 /api/settings 修改）
3. 代码内默认值
"""
from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
from pathlib import Path

from sqlalchemy.engine import URL

BASE_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)
SETTINGS_FILE = DATA_DIR / "settings.json"


def _load_dotenv() -> None:
    """轻量加载项目根目录 .env（不引入额外依赖）。

    真实环境变量优先级更高：已存在于 os.environ 的键不被 .env 覆盖。
    典型用途：在 .env 中配置 DB_HOST/DB_PORT/DB_USER/DB_PASSWORD/DB_NAME 以切换到 MySQL。
    """
    env_file = BASE_DIR / ".env"
    if not env_file.exists():
        return
    for raw in env_file.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key, value = key.strip(), value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


_load_dotenv()

DEFAULT_DATABASE_URL = f"sqlite:///{DATA_DIR / 'seeself.db'}"


def _build_database_url() -> str:
    """按 DB_* 分段配置构造 MySQL 连接串；未配置 DB_HOST 时回退 DATABASE_URL / SQLite。

    密码无需手动 URL 编码：URL.create 会按 RFC 3986 自动转义特殊字符。
    """
    db_host = os.getenv("DB_HOST")
    if db_host:
        try:
            port = int(os.getenv("DB_PORT")) if os.getenv("DB_PORT") else None
        except ValueError:
            port = None
        return URL.create(
            "mysql+pymysql",
            username=os.getenv("DB_USER") or "",
            password=os.getenv("DB_PASSWORD") or "",
            host=db_host,
            port=port,
            database=os.getenv("DB_NAME") or "",
        ).render_as_string(hide_password=False)
    env_db = os.getenv("DATABASE_URL")
    if env_db:
        return env_db
    return DEFAULT_DATABASE_URL


@dataclass
class AppSettings:
    # 数据库连接串：默认 SQLite；配置 DB_* 环境变量后自动切换 MySQL
    database_url: str = DEFAULT_DATABASE_URL
    # 时区（应用层统一）
    timezone: str = "Asia/Shanghai"

    @classmethod
    def load(cls) -> "AppSettings":
        values: dict = {}
        if SETTINGS_FILE.exists():
            try:
                values = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                values = {}
        values["database_url"] = _build_database_url()
        known = {k: v for k, v in values.items() if k in cls.__dataclass_fields__}
        return cls(**known)

    def save(self) -> None:
        SETTINGS_FILE.write_text(
            json.dumps(asdict(self), ensure_ascii=False, indent=2), encoding="utf-8"
        )

    def update(self, **kwargs) -> "AppSettings":
        for key, value in kwargs.items():
            if key in self.__dataclass_fields__ and value is not None:
                setattr(self, key, value)
        self.save()
        return self


settings = AppSettings.load()
