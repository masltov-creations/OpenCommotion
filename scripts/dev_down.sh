#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

kill_listener_port() {
  local port="$1"
  local pids
  pids="$(ss -ltnp "sport = :$port" 2>/dev/null | sed -n 's/.*pid=\([0-9]\+\).*/\1/p' | sort -u)"
  if [ -z "$pids" ]; then
    return 0
  fi
  for pid in $pids; do
    kill "$pid" >/dev/null 2>&1 || true
  done
}

for f in runtime/agent-runs/gateway.pid runtime/agent-runs/orchestrator.pid runtime/agent-runs/ui.pid; do
  if [ -f "$f" ]; then
    kill "$(cat "$f")" >/dev/null 2>&1 || true
    rm -f "$f"
  fi
done

pkill -f "vite --host 127.0.0.1 --port 5173" >/dev/null 2>&1 || true
kill_listener_port 8000
kill_listener_port 8001
kill_listener_port 5173

docker compose down >/dev/null 2>&1 || true

echo "OpenCommotion dev stack stopped"
