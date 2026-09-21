# see_self · 个人五年计划管理系统

像国家「五年规划」一样管理自己的人生：用 **五年计划 → 季度 OKR → 项目 → 待办** 四层结构，把长期目标逐层拆解到每天的具体行动，并用实时看板量化时间与任务的流逝，对抗「稀里糊涂一周/一月就过去了」的生活惯性。

- 看板：毫秒级实时时钟 + 年/月/周进度条，项目分段进度条与「本月/本周/昨日」推进量；
- 规划：五年计划（导入规划纲要）→ 季度 OKR → 项目 → 多级待办，挂靠可选、级联删除、进度实时聚合；
- 接入：支持 AI 智能体（Agent）通过标准接口读写全部数据（25 个工具，详见 MCP 文档）。

## 快速开始

### 脚本启动（推荐）

一键启停，首次启动自动完成依赖安装、数据库迁移与前端构建：

```bash
bash scripts/dev.sh               # 交互式菜单（↑↓ 选择 + 回车）
bash scripts/dev.sh start         # 启动服务（默认端口 8089）
bash scripts/dev.sh restart       # 重启（不重新构建前端）
bash scripts/dev.sh restart-build # 重启并重新构建前端
bash scripts/dev.sh stop          # 停止服务
bash scripts/dev.sh status        # 查看服务状态
bash scripts/dev.sh build         # 仅构建前端
```

- 端口可用环境变量覆盖：`PORT=8080 bash scripts/dev.sh start`；
- 启动后访问 http://127.0.0.1:8089/ ，API 文档见 /docs，日志在 `~/files/logs/seeSelf/server.log`。

### 后端

```bash
uv sync --extra mysql --extra dev          # 安装依赖
cp .env.example .env                       # 可选：配置 MySQL DATABASE_URL，不配则用本地 SQLite
uv run alembic upgrade head                # SQLite 建表（生产 MySQL 用 scripts/init_mysql.py）
uv run uvicorn seeself.main:app --port 8080 --reload   # 启动 API，文档见 /docs
```

### 前端（开发模式，热更新）

```bash
cd frontend && pnpm install && pnpm dev    # http://127.0.0.1:5173，/api 自动代理到 8080
```

### 生产（单端口）

```bash
cd frontend && pnpm build && cd ..
uv run uvicorn seeself.main:app --port 8080   # 打开 http://127.0.0.1:8080 即为完整应用
```

### 测试

```bash
uv run pytest -q
```

## 文档

| 文档 | 内容 | 适合谁 |
|---|---|---|
| [docs/产品文档.md](docs/产品文档.md) | 功能介绍（不含技术细节） | 使用者 |
| [docs/技术文档.md](docs/技术文档.md) | 技术栈、架构、目录梳理与模块定位 | 开发者 / AI 维护 |
| [docs/MCP配置文档.md](docs/MCP配置文档.md) | MCP 工具清单与接入方式 | 使用 AI 接入的人 |
