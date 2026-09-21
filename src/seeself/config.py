"""全局配置：数据库连接、顺延与高亮阈值等设置。

设置项支持两种来源（优先级从高到低）：
1. 环境变量（如 DATABASE_URL）
2. data/settings.json（用户可通过 /api/settings 修改）
3. 代码内默认值
"""
from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)
SETTINGS_FILE = DATA_DIR / "settings.json"


def _load_dotenv() -> None:
    """轻量加载项目根目录 .env（不引入额外依赖）。

    真实环境变量优先级更高：已存在于 os.environ 的键不被 .env 覆盖。
    典型用途：在 .env 中配置 DATABASE_URL 以切换到 MySQL。
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


@dataclass
class AppSettings:
    # 数据库连接串：默认 SQLite；迁移 MySQL 时改为 mysql+pymysql://user:pass@host:3306/seeself
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
        env_db = os.getenv("DATABASE_URL")
        if env_db:
            values["database_url"] = env_db
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
