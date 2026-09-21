# see_self MCP 配置文档

> 本文档介绍 see_self（个人五年计划管理系统）提供的全部 MCP 工具与三种客户端接入方式（本地 stdio、远程 streamable-http、Spring AI Alibaba）。
> 适用于：Claude Desktop / Cursor / 任意 MCP 客户端 / 自研 Agent。

## 1. 概述

后端通过 **FastMCP 4.x** 暴露 **25 个 `seeself_*` 工具**，覆盖五年计划 → 季度 OKR → 项目 → 待办 四层对象的读写，以及与 Web 前端完全一致的口径（**共用同一套 Service 层、同一个数据库**，MCP 写入的数据在页面上立即可见）。

| 能力 | 传输模式 | 适用场景 |
|---|---|---|
| `stdio` | 标准输入输出 | 本地桌面客户端（Claude Desktop、Cursor 等），由客户端自动拉起进程 |
| `streamable-http` | HTTP（默认 8765 端口） | 远程/局域网接入、多客户端共享、自研 Agent 调用 |

## 2. 快速启动

```bash
# 进入项目目录
cd ~/see_self

# stdio 模式（供桌面 MCP 客户端接入，进程由客户端拉起，无需手动启动）
uv run python -m seeself.mcp_server

# streamable-http 模式（需手动启动常驻服务，默认端口 8765）
uv run python -m seeself.mcp_server --transport streamable-http --port 8765
```

启动前提：依赖已安装（`uv sync --extra mysql --extra dev`）、数据库可连接（生产 MySQL 走 `.env` 的 `DATABASE_URL`，未配置时自动回退本地 SQLite `data/seeself.db`）。

## 3. 工具清单（25 个）

参数说明：`*` 为必填；`null` 表示可选。所有工具返回 JSON。

### 3.1 五年计划（6 个）

| 工具 | 参数 | 说明 |
|---|---|---|
| `seeself_list_plans` | 无 | 列出全部五年计划（含聚合进度） |
| `seeself_get_plan` | `plan_id*` | 获取单个五年计划详情（含纲要与 OKR） |
| `seeself_create_plan` | `name*` `start_year*` `end_year*` `description?` | 创建五年计划，`end_year` 必须大于 `start_year` |
| `seeself_update_plan` | `plan_id*` 及可改字段 | 更新可改字段（仅传需修改的） |
| `seeself_delete_plan` | `plan_id*` | 删除计划，**级联删除**其下全部 OKR/项目/待办 |
| `seeself_import_plan` | `outline*`（JSON 对象） | 导入五年规划纲要（见 4.1），**整体覆盖** |

### 3.2 季度 OKR（6 个）

| 工具 | 参数 | 说明 |
|---|---|---|
| `seeself_list_okrs` | `plan_id?` | 列出 OKR；传 `plan_id` 只列出挂靠该计划的 |
| `seeself_get_okr` | `okr_id*` | 获取单个 OKR 详情 |
| `seeself_create_okr` | `quarter*` `objective*` `plan_id?` `kr_note?` | 创建 OKR，`quarter` 如 `2026Q3`，`plan_id` 留空为独立 OKR |
| `seeself_update_okr` | `okr_id*` 及可改字段 | 更新 OKR 可改字段 |
| `seeself_delete_okr` | `okr_id*` | 删除 OKR，**级联删除**其下全部项目/待办 |
| `seeself_batch_create_okrs` | `okrs*`（数组） | 批量创建 OKR，**单事务**，任一失败全部回滚 |

### 3.3 项目（6 个）

| 工具 | 参数 | 说明 |
|---|---|---|
| `seeself_list_projects` | `okr_id?` | 列出项目（含分段进度）；传 `okr_id` 只列出挂靠该 OKR 的 |
| `seeself_get_project` | `project_id*` | 获取单个项目详情（含分段进度） |
| `seeself_create_project` | `name*` `okr_id?` `description?` | 创建项目，`okr_id` 留空为独立项目 |
| `seeself_update_project` | `project_id*` 及可改字段 | 更新项目可改字段 |
| `seeself_delete_project` | `project_id*` | 删除项目，**级联删除**其下全部待办 |
| `seeself_import_project` | `name*` `okr_id?` `description?` `modules?` | 导入项目 + 完整模块/事项树（见 4.2），**单事务** |

### 3.4 待办（7 个）

| 工具 | 参数 | 说明 |
|---|---|---|
| `seeself_list_todos` | `project_id*` | 获取项目的完整事项树（嵌套结构） |
| `seeself_get_todo` | `todo_id*` | 获取单个事项 |
| `seeself_create_todo` | `project_id*` `title*` `parent_id?` `description?` | 创建事项；`parent_id` 不传为**模块**（顶层），传入为挂到该模块下的事项 |
| `seeself_update_todo` | `todo_id*` 及可改字段 | 更新事项；`parent_id` 传 `-1` 表示移到顶层 |
| `seeself_complete_todo` | `todo_id*` `completed*` | 勾选/取消完成；`true` 记录完成时间，`false` 清除 |
| `seeself_delete_todo` | `todo_id*` | 删除待办 |
| `seeself_batch_complete_todos` | `todo_ids*`（数组） `completed*` | 批量勾选/取消完成，**单事务**，任一 id 不存在全部回滚 |

## 4. 重点工具调用示例

### 4.1 导入五年计划 `seeself_import_plan`

接收 `personal-five-year-plan` 技能导出的纲要 JSON 对象（结构：`period` / `vision` / `indicators` / `domains` / `special_projects` / `risks` / `year1` 等）。

```json
{
  "outline": {
    "plan_name": "个人五年规划纲要",
    "period": { "start": "2026-01-01", "end": "2030-12-31" },
    "vision": {
      "positioning": "成为独立 Agent 开发者",
      "core_goals": ["完成 Agent 转型", "建立稳定现金流"],
      "bottom_lines": ["不裸辞", "不负债创业"]
    },
    "year1": {
      "goals": ["掌握 Spring AI Alibaba", "跑通 3 个 Agent 项目"],
      "okrs": [
        {
          "quarter": "Q1 2026.01-03",
          "objectives": [
            { "objective": "学会 MCP 开发", "key_results": ["完成 4 个 MCP 工具"] }
          ]
        }
      ]
    }
  }
}
```

> ⚠️ **覆盖语义**：系统只保留**一份**五年计划。重复调用会整体覆盖——级联删除旧计划及其全部 OKR/项目/待办后重建，属破坏性操作，Agent 调用前应确认。

### 4.2 导入项目树 `seeself_import_project`

`modules` 为顶层模块数组，每个模块可嵌套 `children`（其下事项），支持多级嵌套（上限 10 层）：

```json
{
  "name": "Spring AI Alibaba 学习",
  "okr_id": 3,
  "modules": [
    {
      "title": "MCP 开发",
      "children": [
        { "title": "看文档", "children": [{ "title": "读 Spring AI 官方文档" }] },
        { "title": "写 4 个工具" }
      ]
    },
    { "title": "Agent 架构" }
  ]
}
```

### 4.3 批量创建 OKR `seeself_batch_create_okrs`

```json
{
  "okrs": [
    { "quarter": "2026Q3", "objective": "完成 Agent 转型", "plan_id": 1, "kr_results": ["跑通 3 个项目"] },
    { "quarter": "2026Q4", "objective": "独立项目上线" }
  ]
}
```

### 4.4 批量完成事项 `seeself_batch_complete_todos`

```json
{ "todo_ids": [12, 13, 14], "completed": true }
```

## 5. 客户端配置

### 5.1 Claude Desktop（stdio）

编辑 `~/Library/Application Support/Claude/claude_desktop_config.json`：

```json
{
  "mcpServers": {
    "seeself": {
      "command": "uv",
      "args": [
        "run",
        "--directory",
        "~/see_self",
        "python",
        "-m",
        "seeself.mcp_server"
      ]
    }
  }
}
```

### 5.2 Cursor（stdio）

项目根目录 `.cursor/mcp.json`（或全局 `~/.cursor/mcp.json`），格式同上：

```json
{
  "mcpServers": {
    "seeself": {
      "command": "uv",
      "args": ["run", "--directory", "~/see_self", "python", "-m", "seeself.mcp_server"]
    }
  }
}
```

> 若 `uv` 不在 PATH 中，将 `command` 换成 `uv` 的绝对路径（`which uv` 查看）。

### 5.3 streamable-http（远程 / 多客户端共享）

先启动常驻服务：

```bash
uv run python -m seeself.mcp_server --transport streamable-http --port 8765
```

客户端配置指向 `http://127.0.0.1:8765/mcp/`（已在 FastMCP 4.0.3 实测确认该端点）：

```json
{
  "mcpServers": {
    "seeself": {
      "url": "http://127.0.0.1:8765/mcp/"
    }
  }
}
```

> 无内置鉴权，仅适合本机或可信内网；如需公网暴露请自行加反向代理 + 鉴权。

### 5.4 Spring AI Alibaba（自研 Agent）

MCP client 工具会自动注册为 `ToolCallback`，可直接注入 `ChatClient` 使用。

**依赖**（二选一，按所用版本）：

```xml
<!-- Spring AI Alibaba 体系 -->
<dependency>
    <groupId>com.alibaba.cloud.ai</groupId>
    <artifactId>spring-ai-alibaba-starter-mcp-client</artifactId>
</dependency>

<!-- 或 Spring AI 原生体系 -->
<dependency>
    <groupId>org.springframework.ai</groupId>
    <artifactId>spring-ai-starter-mcp-client</artifactId>
</dependency>
```

**stdio 模式**（`application.yml`，由 Java 进程拉起 see_self 服务）：

```yaml
spring:
  ai:
    mcp:
      client:
        name: seeself
        stdio:
          servers:
            seeself:
              command: uv
              args:
                - run
                - --directory
                - ~/see_self
                - python
                - -m
                - seeself.mcp_server
```

**streamable-http 模式**（连接已启动的远程服务）：

```yaml
spring:
  ai:
    mcp:
      client:
        name: seeself
        http:
          servers:
            seeself:
              url: http://127.0.0.1:8765/mcp/
```

**Java 中使用**：

```java
import org.springframework.ai.tool.ToolCallbackProvider;
import org.springframework.ai.mcp.McpToolCallbackProvider;
import org.springframework.ai.mcp.client.McpSyncClient;

@Bean
ToolCallbackProvider seeselfTools(McpSyncClient seeselfClient) {
    return new McpToolCallbackProvider(seeselfClient);
}
```

之后在 `ChatClient` 中即可让模型自由调用 25 个 `seeself_*` 工具（自动发现、按 schema 传参）。

## 6. 使用约定与注意事项

1. **单事务语义**：`batch_create_okrs`、`batch_complete_todos`、`import_project` 为单事务——任一失败整体回滚，不会产生部分数据。
2. **破坏性操作**：`import_plan`（整体覆盖）、`delete_plan` / `delete_okr` / `delete_project`（级联删除下层）不可恢复，调用前先 `list` 确认对象。
3. **id 校验**：多数工具对不存在的 id 报错并回滚；Agent 应先通过 `list_*` / `get_*` 拿到真实 id 再操作。
4. **字段口径与 Web 一致**：日期用 `YYYY-MM-DD` 字符串；`quarter` 用 `2026Q3` 或 `2026 Q4`（导入时自动归一化 `Q1 2026.01-03` 这类写法）；`parent_id=-1` 表示移到顶层；模块 = 顶层待办（`parent_id` 为空）。
5. **进度实时聚合**：完成/取消事项后，项目进度、分段进度条、看板由 Service 层实时重算，无需额外刷新。
6. **同一数据库**：MCP 与 Web 前端共用 `DATABASE_URL`（生产 MySQL / 本地 SQLite），任何一端写入另一端立即可见。

## 7. 常见问题

| 现象 | 排查 |
|---|---|
| 客户端连不上 stdio 服务 | 确认 `uv` 在 PATH；换绝对路径；查看客户端日志中的子进程 stderr |
| 端口被占用 | `--port` 换端口，同步改客户端 URL |
| 工具报「XX 不存在」 | id 传错或对象已被级联删除，先 `list_*` 查询 |
| 导入报「缺少 period.start / end」 | 纲要 JSON 结构不完整，对照 4.1 示例补齐 |
| 数据库连接失败 | 检查 `.env` 的 `DATABASE_URL` 与 MySQL 服务；本地可先不配 `.env` 走 SQLite |
| Spring AI 配置不生效 | 配置项随版本演进，以当前版本文档为准；先确认 starter 依赖版本 |

---

*本文档与 `src/seeself/mcp_server.py` 同步维护；工具数量变更后请同步更新第 3 节清单。*
