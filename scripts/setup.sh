#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

AUTO_RUN=1
AUTO_OPEN=1
APP_URL="http://127.0.0.1:8000"

for arg in "$@"; do
  case "$arg" in
    --no-run)
      AUTO_RUN=0
      ;;
    --no-open)
      AUTO_OPEN=0
      ;;
    -h|--help)
      echo "Usage: ./scripts/setup.sh [--no-run] [--no-open]"
      echo "  --no-run   complete install + setup wizard, but do not start services"
      echo "  --no-open  do not prompt/open browser after startup"
      exit 0
      ;;
    *)
      echo "Unknown argument: $arg" >&2
      echo "Usage: ./scripts/setup.sh [--no-run] [--no-open]" >&2
      exit 1
      ;;
  esac
done

open_browser() {
  local url="$1"
  if command -v xdg-open >/dev/null 2>&1; then
    xdg-open "$url" >/dev/null 2>&1 &
    return 0
  fi
  if command -v open >/dev/null 2>&1; then
    open "$url" >/dev/null 2>&1 &
    return 0
  fi
  if command -v powershell.exe >/dev/null 2>&1; then
    powershell.exe -NoProfile -Command "Start-Process '$url'" >/dev/null 2>&1 &
    return 0
  fi
  if command -v cmd.exe >/dev/null 2>&1; then
    cmd.exe /c start "" "$url" >/dev/null 2>&1 &
    return 0
  fi
  return 1
}

if ! command -v python3 >/dev/null 2>&1; then
  echo "python3 is required" >&2
  exit 1
fi

python3 scripts/opencommotion.py install

if [[ ! -t 0 ]]; then
  echo "Setup wizard requires an interactive terminal." >&2
  echo "Run this command in an interactive shell: bash scripts/setup.sh" >&2
  exit 1
fi

python3 scripts/opencommotion.py setup

if [[ "$AUTO_RUN" -eq 1 ]]; then
  python3 scripts/opencommotion.py run
  if [[ "$AUTO_OPEN" -eq 1 && -t 0 ]]; then
    read -r -p "Open browser now? [Y/n]: " open_reply
    open_reply="${open_reply:-Y}"
    case "${open_reply,,}" in
      y|yes)
        if open_browser "$APP_URL"; then
          echo "Opened browser: $APP_URL"
        else
          echo "Could not auto-open browser. Open manually: $APP_URL"
        fi
        ;;
      *)
        echo "Open manually: $APP_URL"
        ;;
    esac
  else
    echo "Setup complete. Open: $APP_URL"
  fi
else
  echo "Setup complete."
  echo "Run: python3 scripts/opencommotion.py run"
fi
