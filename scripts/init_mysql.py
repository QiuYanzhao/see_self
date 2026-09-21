#!/usr/bin/env python3
"""see_self MySQL 数据库初始化脚本。

功能：
  1. 从一个 .env 文件读取 MySQL 连接信息（DB_HOST/DB_PORT/DB_USER/DB_PASSWORD）；
  2. 连接 MySQL 服务器，创建目标数据库（默认 see_life）；
  3. 执行 scripts/sql/schema_mysql.sql，在目标库中创建全部表、索引与外键；
  4. 校验建表结果并打印连接串（密码打码）。

脚本幂等：数据库与表都使用 IF NOT EXISTS，可重复执行，不会清空已有数据。

用法（在项目根目录、用项目虚拟环境运行）：
  uv run python scripts/init_mysql.py
  uv run python scripts/init_mysql.py --env /path/to/.env
  uv run python scripts/init_mysql.py --db see_life --sql scripts/sql/schema_mysql.sql

依赖：pymysql（pyproject 的 mysql extra，已通过 `uv sync --extra mysql` 安装）。
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pymysql
from pymysql.constants import CLIENT

# 项目根目录（scripts 的上一级）
ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SQL = ROOT / "scripts" / "sql" / "schema_mysql.sql"
# 默认读取的数据库连接配置（项目根目录 .env，可用 --env 覆盖）
DEFAULT_ENV = ROOT / ".env"
DEFAULT_DB = "see_life"


def parse_env(path: Path) -> dict[str, str]:
    """解析简单的 KEY=VALUE .env 文件，忽略注释与空行，去除两侧引号。"""
    if not path.exists():
        raise FileNotFoundError(f".env 文件不存在：{path}")
    result: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        result[key.strip()] = value.strip().strip('"').strip("'")
    return result


def log(msg: str) -> None:
    print(f"[init_mysql] {msg}")


def connect_server(env: dict[str, str], db: str | None = None):
    """建立 MySQL 连接；db=None 时不绑定具体数据库（用于 CREATE DATABASE）。"""
    return pymysql.connect(
        host=env["DB_HOST"],
        port=int(env.get("DB_PORT", "3306")),
        user=env["DB_USER"],
        password=env.get("DB_PASSWORD", ""),
        database=db,
        charset="utf8mb4",
        # 允许一次执行含多条语句的 .sql 脚本
        client_flag=CLIENT.MULTI_STATEMENTS,
        autocommit=True,
        connect_timeout=10,
    )


def drain_results(cursor) -> None:
    """消费 MULTI_STATEMENTS 产生的全部结果集，避免 Commands out of sync。"""
    while cursor.nextset():
        pass


def masked_dsn(env: dict[str, str], db: str) -> str:
    """生成打码的连接串用于展示。"""
    pwd = env.get("DB_PASSWORD", "")
    masked = "***" if pwd else ""
    return (
        f"mysql+pymysql://{env['DB_USER']}:{masked}@"
        f"{env['DB_HOST']}:{env.get('DB_PORT', '3306')}/{db}?charset=utf8mb4"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="初始化 see_self 的 MySQL 数据库 see_life")
    parser.add_argument("--env", default=str(DEFAULT_ENV), help="数据库连接配置 .env 路径")
    parser.add_argument("--db", default=DEFAULT_DB, help="目标数据库名（默认 see_life）")
    parser.add_argument("--sql", default=str(DEFAULT_SQL), help="建表 SQL 脚本路径")
    args = parser.parse_args()

    env_path = Path(args.env)
    sql_path = Path(args.sql)
    db_name = args.db

    log(f"读取连接配置：{env_path}")
    env = parse_env(env_path)
    for key in ("DB_HOST", "DB_USER"):
        if key not in env:
            log(f"配置缺少 {key}，终止。")
            return 1
    log(f"目标服务器：{env['DB_HOST']}:{env.get('DB_PORT', '3306')}，用户 {env['DB_USER']}，目标库 {db_name}")

    if not sql_path.exists():
        log(f"SQL 脚本不存在：{sql_path}")
        return 1
    sql_text = sql_path.read_text(encoding="utf-8")
    # 若指定了非默认库名，把脚本中的 see_life 替换为目标库名
    if db_name != DEFAULT_DB:
        sql_text = sql_text.replace(f"`{DEFAULT_DB}`", f"`{db_name}`")

    # 1) 连接服务器并执行整段建库建表脚本
    try:
        conn = connect_server(env)
    except Exception as exc:  # noqa: BLE001
        log(f"连接 MySQL 失败：{type(exc).__name__}: {exc}")
        return 1

    try:
        with conn.cursor() as cur:
            log("执行建库建表脚本 ...")
            cur.execute(sql_text)
            drain_results(cur)
        log("脚本执行完成。")
    except Exception as exc:  # noqa: BLE001
        log(f"执行 SQL 失败：{type(exc).__name__}: {exc}")
        return 1
    finally:
        conn.close()

    # 2) 连接到目标库做结果校验
    try:
        conn = connect_server(env, db_name)
        with conn.cursor() as cur:
            cur.execute("SHOW TABLES")
            tables = [row[0] for row in cur.fetchall()]
            expected = ["five_year_plan", "okr", "project", "todo"]
            log(f"目标库 `{db_name}` 现有表：{tables}")
            missing = [t for t in expected if t not in tables]
            if missing:
                log(f"缺少预期表：{missing}")
                return 1
            for table in expected:
                cur.execute(f"SELECT COUNT(*) FROM `{table}`")
                count = cur.fetchone()[0]
                log(f"  - 表 {table:<14} 行数 {count}")
            # 外键级联校验
            cur.execute(
                """
                SELECT TABLE_NAME, CONSTRAINT_NAME, REFERENCED_TABLE_NAME
                FROM information_schema.KEY_COLUMN_USAGE
                WHERE TABLE_SCHEMA = %s AND REFERENCED_TABLE_NAME IS NOT NULL
                ORDER BY TABLE_NAME
                """,
                (db_name,),
            )
            fks = cur.fetchall()
            log(f"外键约束 {len(fks)} 条：")
            for table, constraint, ref in fks:
                log(f"  - {table}.{constraint} -> {ref} (ON DELETE CASCADE)")
        conn.close()
    except Exception as exc:  # noqa: BLE001
        log(f"结果校验失败：{type(exc).__name__}: {exc}")
        return 1

    log("数据库初始化成功 ✅")
    log("应用连接串（DATABASE_URL，密码已打码）：")
    print("    " + masked_dsn(env, db_name))
    log("将其写入项目根目录 .env 的 DATABASE_URL 即可让应用使用该 MySQL 库。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
