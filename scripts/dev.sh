#!/usr/bin/env bash
# =============================================================================
# see_self 个人五年计划管理系统 —— 本地服务管理脚本
#
# 单端口架构：FastAPI(uvicorn) 同时提供 API 与前端静态文件（frontend/dist），
# 因此只需要守护一个后端进程；前端通过 pnpm build 产出 dist 后由后端托管。
#
# 交互选项（无参数启动，↑↓ 选择 + 回车确认）：
#   1. 重启服务（不重新构建前端）
#   2. 重启服务（重新构建前端）
#   3. 启动服务
#   4. 停止服务
#   5. 查看服务状态
#   6. 检查环境依赖（缺失项用 brew 安装；不启动项目）
#
# 也支持命令行参数直接调用（便于脚本/别名调用）：
#   scripts/dev.sh start | restart | restart-build | stop | status | build | check
# =============================================================================
set -euo pipefail

# ─────────────────────────── 基础路径与常量 ───────────────────────────

# 项目根目录（scripts 的上一级）
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# 运行时目录：存放 PID
RUN_DIR="$ROOT/.run"
# 日志目录（与团队其它项目保持一致，放在用户目录下）
LOG_DIR="${HOME}/files/logs/seeSelf"
mkdir -p "$RUN_DIR" "$LOG_DIR"

PID_FILE="$RUN_DIR/server.pid"
SERVER_LOG="$LOG_DIR/server.log"

# 默认服务端口（可通过环境变量 PORT 覆盖）
PORT="${PORT:-8089}"
HOST="127.0.0.1"
APP="seeself.main:app"

# ANSI 颜色
_BOLD=$'\033[1m'
_DIM=$'\033[2m'
_RESET=$'\033[0m'
_CYAN=$'\033[36m'
_GREEN=$'\033[32m'
_YELLOW=$'\033[33m'
_RED=$'\033[31m'

# 带时间戳的日志打印
log()  { printf "${_CYAN}[%s]${_RESET} %s\n" "$(date '+%H:%M:%S')" "$*"; }
warn() { printf "${_YELLOW}[%s] 警告：%s${_RESET}\n" "$(date '+%H:%M:%S')" "$*"; }
err()  { printf "${_RED}[%s] 错误：%s${_RESET}\n" "$(date '+%H:%M:%S')" "$*" >&2; }

# ─────────────────────────── 工具定位 ───────────────────────────

# 定位 uv：优先 PATH，其次用户目录默认安装位置
find_uv() {
  if command -v uv >/dev/null 2>&1; then
    command -v uv
  elif [[ -x "$HOME/.local/bin/uv" ]]; then
    echo "$HOME/.local/bin/uv"
  else
    echo ""
  fi
}

# 定位 pnpm：优先 PATH，其次取 .nvm 下最新 node 版本内的 pnpm
find_pnpm() {
  if command -v pnpm >/dev/null 2>&1; then
    command -v pnpm
  else
    local latest
    latest="$(ls "$HOME/.nvm/versions/node/" 2>/dev/null | sort -V | tail -1)"
    if [[ -n "$latest" && -x "$HOME/.nvm/versions/node/$latest/bin/pnpm" ]]; then
      echo "$HOME/.nvm/versions/node/$latest/bin/pnpm"
    else
      echo ""
    fi
  fi
}

# ─────────────────────────── 进程判断 ───────────────────────────

read_pid() {
  if [[ -f "$PID_FILE" ]]; then
    cat "$PID_FILE"
  fi
  return 0
}

is_pid_alive() {
  local pid="$1"
  [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null
}

is_running() {
  is_pid_alive "$(read_pid)"
}

# ─────────────────────────── 环境初始化（幂等） ───────────────────────────
# 仅当检测到环境未就绪时才执行，已就绪则跳过，避免每次启动都重复操作。

ensure_backend_env() {
  # 1) Python 虚拟环境 / 依赖
  if [[ ! -x "$ROOT/.venv/bin/python" ]]; then
    local uv_bin
    uv_bin="$(find_uv)"
    if [[ -z "$uv_bin" ]]; then
      err "未找到 uv，且 .venv 不存在，无法自动初始化后端环境。请先安装 uv。"
      exit 1
    fi
    log "检测到虚拟环境缺失，执行 uv sync --extra dev --extra mysql ..."
    (cd "$ROOT" && "$uv_bin" sync --extra dev --extra mysql)
  fi

  # 2) 数据库迁移（SQLite 文件不存在时执行 alembic upgrade head）
  if [[ ! -f "$ROOT/data/seeself.db" ]]; then
    log "检测到数据库未初始化，执行 alembic upgrade head ..."
    (cd "$ROOT" && "$ROOT/.venv/bin/alembic" upgrade head)
  fi
}

ensure_frontend_deps() {
  # 前端依赖缺失时自动 pnpm install
  if [[ ! -d "$ROOT/frontend/node_modules" ]]; then
    local pnpm_bin
    pnpm_bin="$(find_pnpm)"
    if [[ -z "$pnpm_bin" ]]; then
      err "未找到 pnpm，且 frontend/node_modules 不存在，无法构建前端。"
      exit 1
    fi
    log "检测到前端依赖缺失，执行 pnpm install ..."
    (cd "$ROOT/frontend" && "$pnpm_bin" install)
  fi
}

# 构建前端静态文件到 frontend/dist
build_frontend() {
  local pnpm_bin
  pnpm_bin="$(find_pnpm)"
  if [[ -z "$pnpm_bin" ]]; then
    err "未找到 pnpm，无法构建前端。"
    exit 1
  fi
  ensure_frontend_deps
  log "构建前端（pnpm build）..."
  (cd "$ROOT/frontend" && "$pnpm_bin" build)
  log "前端构建完成：$ROOT/frontend/dist"
}

# ─────────────────────────── 环境依赖检查 ───────────────────────────
# 首次启动前检查本地工具依赖（brew / uv / python / node / pnpm / curl），
# 缺失项使用 brew 安装。只负责检查与安装，不初始化项目、不启动服务；
# 项目内状态（.venv / node_modules / dist / 数据库 / .env）仅做报告，
# 首次启动（start/restart）时由对应步骤自动初始化。

# 是否存在可用的 Python >= 3.12（PATH 中 python3，或 brew 的 python@3.12）
python_ok() {
  if command -v python3 >/dev/null 2>&1 && python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 12) else 1)' >/dev/null 2>&1; then
    return 0
  fi
  local bp
  for bp in "$(brew --prefix)/opt/python@3.12/bin/python3" "$(brew --prefix)/opt/python@3.12/bin/python3.12"; do
    if [[ -x "$bp" ]] && "$bp" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 12) else 1)' >/dev/null 2>&1; then
      return 0
    fi
  done
  return 1
}

# 输出当前可用 Python 的版本描述（优先 PATH 中满足 >=3.12 的 python3）
python_version_label() {
  local py
  py="$(command -v python3 2>/dev/null || true)"
  if [[ -n "$py" ]] && "$py" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 12) else 1)' >/dev/null 2>&1; then
    "$py" -c 'import sys; print(f"Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")' 2>/dev/null
    return
  fi
  for py in "$(brew --prefix)/opt/python@3.12/bin/python3" "$(brew --prefix)/opt/python@3.12/bin/python3.12"; do
    if [[ -x "$py" ]] && "$py" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 12) else 1)' >/dev/null 2>&1; then
      "$py" -c 'import sys; print(f"Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")' 2>/dev/null
      return
    fi
  done
  echo "未知"
}

# 是否存在 Node >= 18（Vite 5 构建要求）
node_ok() {
  if ! command -v node >/dev/null 2>&1; then
    return 1
  fi
  local ver
  ver="$(node -v 2>/dev/null | sed 's/^v//; s/\..*//')"
  [[ -n "$ver" ]] && (( ver >= 18 ))
}

check_env() {
  log "================================================"
  log "see_self 环境依赖检查"
  log "（仅检查本地工具依赖，缺失项用 brew 安装；不初始化项目、不启动服务）"
  log "================================================"

  local fail_count=0 uv_bin pnpm_bin

  # 1) Homebrew：后续所有 brew 安装的前提
  if command -v brew >/dev/null 2>&1; then
    log "  [1/6] Homebrew    已安装（$(command -v brew)）"
  else
    err "  [1/6] Homebrew 未安装，无法自动安装其它依赖。"
    err "        请先执行官方安装命令："
    err "        /bin/bash -c \"\$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\""
    err "        安装完成后重新运行本选项（scripts/dev.sh check）。"
    exit 1
  fi

  # 2) uv：后端依赖管理，负责创建 .venv 与同步依赖
  uv_bin="$(find_uv)"
  if [[ -n "$uv_bin" ]]; then
    log "  [2/6] uv          已安装（${uv_bin}）"
  else
    warn "  [2/6] uv 未找到，正在使用 brew 安装 ..."
    if brew install uv; then
      uv_bin="$(find_uv)"
      if [[ -n "$uv_bin" ]]; then
        log "  ✓ uv 安装成功（${uv_bin}）"
      else
        err "  ✗ uv 已安装但不在 PATH，请重开终端或执行 source ~/.zprofile 后重试"
        fail_count=$((fail_count + 1))
      fi
    else
      err "  ✗ brew install uv 失败，请检查网络后重试"
      fail_count=$((fail_count + 1))
    fi
  fi

  # 3) Python >= 3.12（pyproject.toml 的 requires-python）
  if python_ok; then
    log "  [3/6] Python      已安装（$(python_version_label)）"
  else
    warn "  [3/6] 未找到 Python 3.12+，正在使用 brew 安装 python@3.12 ..."
    if brew install python@3.12; then
      if python_ok; then
        log "  ✓ Python 3.12+ 已就绪（$(python_version_label)）"
      else
        warn "  python@3.12 已安装但不在 PATH；uv 可自动使用它。如需直接用 python3，请执行："
        warn "  export PATH=\"$(brew --prefix)/opt/python@3.12/bin:\$PATH\""
      fi
    else
      err "  ✗ brew install python@3.12 失败，请检查网络后重试"
      fail_count=$((fail_count + 1))
    fi
  fi

  # 4) Node >= 18（Vite 5 构建要求）
  if node_ok; then
    log "  [4/6] Node        已安装（$(node -v 2>/dev/null)）"
  else
    warn "  [4/6] 未找到 Node 18+，正在使用 brew 安装 node ..."
    if brew install node; then
      if node_ok; then
        log "  ✓ Node 安装成功（$(node -v 2>/dev/null)）"
      else
        err "  ✗ node 已安装但不在 PATH，请重开终端或执行 source ~/.zprofile 后重试"
        fail_count=$((fail_count + 1))
      fi
    else
      err "  ✗ brew install node 失败，请检查网络后重试"
      fail_count=$((fail_count + 1))
    fi
  fi

  # 5) pnpm：前端依赖管理与构建
  pnpm_bin="$(find_pnpm)"
  if [[ -n "$pnpm_bin" ]]; then
    log "  [5/6] pnpm        已安装（${pnpm_bin}）"
  else
    warn "  [5/6] pnpm 未找到，正在使用 brew 安装 ..."
    if brew install pnpm; then
      pnpm_bin="$(find_pnpm)"
      if [[ -n "$pnpm_bin" ]]; then
        log "  ✓ pnpm 安装成功（${pnpm_bin}）"
      else
        err "  ✗ pnpm 已安装但不在 PATH，请重开终端或执行 source ~/.zprofile 后重试"
        fail_count=$((fail_count + 1))
      fi
    else
      err "  ✗ brew install pnpm 失败，请检查网络后重试"
      fail_count=$((fail_count + 1))
    fi
  fi

  # 6) curl：健康检查用（macOS 自带，缺失时才需要安装）
  if command -v curl >/dev/null 2>&1; then
    log "  [6/6] curl        已安装（$(command -v curl)）"
  else
    warn "  [6/6] curl 未找到，正在使用 brew 安装 ..."
    if brew install curl; then
      log "  ✓ curl 安装成功"
    else
      err "  ✗ brew install curl 失败，请检查网络后重试"
      fail_count=$((fail_count + 1))
    fi
  fi

  # 项目内状态：仅报告，不自动处理（首次启动对应步骤会自动初始化）
  log "----------------------------------------"
  log "项目状态（仅报告；首次启动 start/restart 会自动初始化）"
  if [[ -x "$ROOT/.venv/bin/python" ]]; then
    log "  .venv                 已就绪"
  else
    warn "  .venv                 未创建（启动时自动执行 uv sync）"
  fi
  if [[ -d "$ROOT/frontend/node_modules" ]]; then
    log "  frontend/node_modules 已就绪"
  else
    warn "  frontend/node_modules 未安装（启动时自动执行 pnpm install）"
  fi
  if [[ -f "$ROOT/frontend/dist/index.html" ]]; then
    log "  frontend/dist         已构建"
  else
    warn "  frontend/dist         未构建（启动时自动执行 pnpm build）"
  fi
  if [[ -f "$ROOT/data/seeself.db" ]]; then
    log "  data/seeself.db       已初始化"
  else
    warn "  data/seeself.db       未初始化（启动时自动执行 alembic upgrade head）"
  fi
  if [[ -f "$ROOT/.env" ]]; then
    if grep -qE '^(DATABASE_URL=mysql|DB_HOST=)' "$ROOT/.env" 2>/dev/null; then
      warn "  .env                  存在且配置了 MySQL（请确保 MySQL 服务可用；本地可用 brew install mysql 或 Docker）"
    else
      log "  .env                  存在（默认 SQLite，零外部依赖）"
    fi
  else
    warn "  .env                  不存在（默认 SQLite 可直接运行；如需自定义配置可执行 cp .env.example .env）"
  fi

  log "----------------------------------------"
  if (( fail_count > 0 )); then
    err "环境检查未通过：${fail_count} 项依赖安装失败，请修复后重新执行本选项。"
    exit 1
  fi
  log "环境检查通过：所有本地工具依赖已就绪。"
  log "提示：接下来执行 start / restart 即可启动服务（首次会自动初始化 .venv、数据库与前端）。"
}

# ─────────────────────────── 健康检查 ───────────────────────────

# 轮询 /api/health，最多等待约 15 秒，成功返回 0
wait_for_health() {
  local i
  for i in $(seq 1 30); do
    if curl -sf "http://$HOST:$PORT/api/health" >/dev/null 2>&1; then
      return 0
    fi
    sleep 0.5
  done
  return 1
}

# ─────────────────────────── 服务动作 ───────────────────────────

# 真正拉起后端进程（内部函数，不做“是否已运行”判断）
_launch() {
  ensure_backend_env

  # dist 缺失时兜底构建，否则后端只会提供 API、没有页面
  if [[ ! -f "$ROOT/frontend/dist/index.html" ]]; then
    warn "前端 dist 不存在，先自动构建一次前端。"
    build_frontend
  fi

  log "启动服务（uvicorn ${APP}，端口 ${PORT}）..."
  (
    cd "$ROOT"
    nohup "$ROOT/.venv/bin/python" -m uvicorn "$APP" \
      --host "$HOST" --port "$PORT" >>"$SERVER_LOG" 2>&1 &
    echo $! > "$PID_FILE"
  )

  if wait_for_health; then
    print_banner "服务已启动"
  else
    err "服务在 15 秒内未通过健康检查，请查看日志：$SERVER_LOG"
    echo "-------- 日志尾部 --------"
    tail -n 20 "$SERVER_LOG" 2>/dev/null || true
    # 启动失败则清理残留 PID
    rm -f "$PID_FILE"
    exit 1
  fi
}

print_banner() {
  local title="$1"
  echo ""
  echo "=================================="
  echo "  $title"
  echo "  应用:   http://$HOST:$PORT/"
  echo "  API文档: http://$HOST:$PORT/docs"
  echo "  健康检查: http://$HOST:$PORT/api/health"
  echo "  日志:   $SERVER_LOG"
  echo "=================================="
}

# 启动服务（要求当前未运行）
start_server() {
  if is_running; then
    warn "服务已在运行（PID $(read_pid)），如需重启请选择重启。"
    status_server
    exit 1
  fi
  _launch
}

# 停止服务
stop_server() {
  local pid
  pid="$(read_pid)"
  if is_pid_alive "$pid"; then
    log "停止服务（PID ${pid}）..."
    kill "$pid" 2>/dev/null || true
    # 最多等待 5 秒优雅退出，仍未退出则强杀
    local i
    for i in $(seq 1 10); do
      is_pid_alive "$pid" || break
      sleep 0.5
    done
    if is_pid_alive "$pid"; then
      warn "进程未优雅退出，执行强制结束。"
      kill -9 "$pid" 2>/dev/null || true
    fi
  else
    log "服务当前未运行。"
  fi
  rm -f "$PID_FILE"
}

# 重启服务：rebuild=1 时先重新构建前端，否则沿用现有 dist（缺失仍会兜底构建）
restart_server() {
  local rebuild="${1:-0}"
  local rebuild_text="否"
  [[ "$rebuild" == "1" ]] && rebuild_text="是"
  log "重启服务（重新构建前端：${rebuild_text}）"
  stop_server
  sleep 1
  if [[ "$rebuild" == "1" ]]; then
    build_frontend
  fi
  _launch
}

# 查看状态
status_server() {
  local pid
  pid="$(read_pid)"
  if is_pid_alive "$pid"; then
    # 进程存活时再确认接口是否真正可用
    if curl -sf "http://$HOST:$PORT/api/health" >/dev/null 2>&1; then
      printf "  服务  ${_GREEN}运行中${_RESET} (PID %s)  http://$HOST:$PORT/  [健康检查通过]\n" "$pid"
    else
      printf "  服务  ${_YELLOW}进程存在但接口未就绪${_RESET} (PID %s)\n" "$pid"
    fi
  else
    printf "  服务  ${_DIM}未运行${_RESET}\n"
    rm -f "$PID_FILE"
  fi
}

usage() {
  cat <<'EOF'
用法: scripts/dev.sh <start|restart|restart-build|stop|status|build|check>

  start          启动服务（已运行则提示；dist 缺失会自动构建）
  restart        重启服务，不重新构建前端
  restart-build  重启服务，并重新构建前端
  stop           停止服务
  status         查看服务状态
  build          仅构建前端
  check          检查本地环境依赖（uv/python/node/pnpm 等），缺失项用 brew 安装；不启动项目
  无参数          打开交互式菜单
EOF
}

# ─────────────────────────── 命令行参数模式 ───────────────────────────

if [[ $# -gt 0 ]]; then
  case "$1" in
    start)         start_server ;;
    restart)       restart_server 0 ;;
    restart-build) restart_server 1 ;;
    build)         build_frontend ;;
    stop)          stop_server ;;
    status)        status_server ;;
    check|check-env) check_env ;;
    -h|--help|help) usage ;;
    *)             usage; exit 1 ;;
  esac
  exit 0
fi

# ─────────────────────────── 交互式菜单 ───────────────────────────

# 菜单项（序号显示用 | 分隔动作与描述）
MENU_ITEMS=(
  "restart       | 重启服务（不重新构建前端）"
  "restart-build | 重启服务（重新构建前端）"
  "start         | 启动服务"
  "stop          | 停止服务"
  "status        | 查看服务状态"
  "check-env     | 检查环境依赖并安装缺失项"
)
MENU_COUNT=${#MENU_ITEMS[@]}

show_status_line() {
  local pid
  pid="$(read_pid)"
  if is_pid_alive "$pid"; then
    if curl -sf "http://$HOST:$PORT/api/health" >/dev/null 2>&1; then
      printf "  当前状态  ${_GREEN}运行中${_RESET} (PID %s)  http://$HOST:$PORT/\n" "$pid"
    else
      printf "  当前状态  ${_YELLOW}进程存在但接口未就绪${_RESET} (PID %s)\n" "$pid"
    fi
  else
    printf "  当前状态  ${_DIM}未运行${_RESET}\n"
  fi
}

draw_menu() {
  local selected=$1
  printf '\033[H\033[J'   # 光标回到顶部并清屏
  echo "=================================="
  echo "  see_self 本地服务管理 (端口 $PORT)"
  echo "=================================="
  echo ""
  show_status_line
  echo ""
  echo "  ${_DIM}↑↓ 移动  回车确认  q 退出${_RESET}"
  echo ""
  local i item action desc
  for i in "${!MENU_ITEMS[@]}"; do
    item="${MENU_ITEMS[$i]}"
    desc="${item#*|}"
    if [[ $i -eq $selected ]]; then
      printf "  ${_CYAN}${_BOLD}❯ %s${_RESET}\n" "$desc"
    else
      printf "    ${_DIM}%s${_RESET}\n" "$desc"
    fi
  done
}

run_action() {
  case $1 in
    0) restart_server 0 ;;
    1) restart_server 1 ;;
    2) start_server ;;
    3) stop_server ;;
    4) status_server ;;
    5) check_env ;;
  esac
}

# 隐藏菜单光标，退出时恢复
printf '\033[?25l'
trap 'printf "\033[?25h"' EXIT

selected=0
draw_menu "$selected"

while true; do
  read -rsn1 key
  case "$key" in
    # 方向键为 ESC [ A/B 转义序列
    $'\033')
      read -rsn2 -t 1 seq 2>/dev/null || true
      if [[ "$seq" == "[A" ]]; then
        ((selected--)) || true
        [[ $selected -lt 0 ]] && selected=$((MENU_COUNT - 1))
        draw_menu "$selected"
      elif [[ "$seq" == "[B" ]]; then
        ((selected++)) || true
        [[ $selected -ge $MENU_COUNT ]] && selected=0
        draw_menu "$selected"
      fi
      ;;
    # 回车：执行选中项
    "")
      printf '\033[?25h'
      trap - EXIT
      echo ""
      run_action "$selected"
      exit 0
      ;;
    # q 退出
    q|Q)
      printf '\033[?25h'
      trap - EXIT
      echo "已退出"
      exit 0
      ;;
  esac
done
