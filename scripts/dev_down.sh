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

# Kill ports recorded by dev_up.sh (handles dynamic port assignment)
if [ -f runtime/agent-runs/ports.env ]; then
  gw_port=""
  orch_port=""
  ui_port=""
  while IFS='=' read -r key val || [ -n "$key" ]; do
    case "$key" in
      GATEWAY_PORT)      gw_port="$val" ;;
      ORCHESTRATOR_PORT) orch_port="$val" ;;
      UI_DEV_PORT)       ui_port="$val" ;;
    esac
  done < runtime/agent-runs/ports.env
  [ -n "$gw_port" ]   && kill_listener_port "$gw_port"
  [ -n "$orch_port" ] && kill_listener_port "$orch_port"
  [ -n "$ui_port" ]   && kill_listener_port "$ui_port"
  rm -f runtime/agent-runs/ports.env
fi

# Fallback: always kill well-known ports (run=8000/8001, dev=8010/8011, vite=5173)
pkill -f "vite --host 127.0.0.1" >/dev/null 2>&1 || true
kill_listener_port 8000
kill_listener_port 8001
kill_listener_port 8010
kill_listener_port 8011
kill_listener_port 5173

docker compose down >/dev/null 2>&1 || true

echo "OpenCommotion dev stack stopped"
