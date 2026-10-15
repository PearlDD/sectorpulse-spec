#!/bin/zsh
set -eu
unsetopt BG_NICE
PROJECT_ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_ROOT"
for candidate in "$PROJECT_ROOT/.venv/bin/python" "$PROJECT_ROOT/../../.venv/bin/python"; do
  if [[ -x "$candidate" ]]; then
    PYTHON_BIN="$candidate"
    break
  fi
done
if [[ -z "${PYTHON_BIN:-}" ]]; then
  echo '没有找到项目运行环境，请先运行项目的 run.sh。'
  read '?按回车关闭'
  exit 1
fi
if curl -fsS --max-time 2 http://127.0.0.1:8000/api/research >/dev/null 2>&1; then
  open http://127.0.0.1:8000/
  exit 0
fi
if lsof -nP -iTCP:8000 -sTCP:LISTEN >/dev/null 2>&1; then
  echo '8000 端口已被其他服务占用，请先检查；没有停止任何进程。'
  read '?按回车关闭'
  exit 1
fi
mkdir -p data
nohup "$PYTHON_BIN" -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000 >data/server.log 2>&1 </dev/null &
for attempt in {1..20}; do
  if curl -fsS --max-time 1 http://127.0.0.1:8000/api/research >/dev/null 2>&1; then
    open http://127.0.0.1:8000/
    echo 'SectorPulse 已启动。关闭此窗口不会停止服务；重启电脑后请重新双击启动。'
    exit 0
  fi
  sleep 0.5
done
echo "未能启动，请查看 $PROJECT_ROOT/data/server.log"
read '?按回车关闭'
exit 1
