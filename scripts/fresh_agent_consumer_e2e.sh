#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if [[ ! -x .venv/bin/python ]]; then
  python3 -m venv .venv
fi

source .venv/bin/activate
pip install -r requirements.txt >/dev/null
npm install --silent >/dev/null

if [[ ! -f .env ]]; then
  cp .env.example .env
fi

bash scripts/dev_up.sh
trap 'bash scripts/dev_down.sh' EXIT

for i in $(seq 1 45); do
  if curl -fsS http://127.0.0.1:8000/health >/dev/null && curl -fsS http://127.0.0.1:8001/health >/dev/null; then
    break
  fi
  sleep 1
done

SUMMARY_FILE="$(mktemp)"
python scripts/agent_examples/robust_turn_client.py \
  --session "fresh-consumer-$(date +%s)" \
  --prompt "fresh agent consumer end-to-end verification turn with moonwalk and chart" \
  --search "moonwalk" > "$SUMMARY_FILE"

python - "$SUMMARY_FILE" <<'PY'
from __future__ import annotations

import json
import sys

path = sys.argv[1]
with open(path, "r", encoding="utf-8") as f:
    payload = json.load(f)

assert payload.get("turn_id"), "missing turn_id"
assert payload.get("patch_count", 0) > 0, "patch_count must be > 0"
assert payload.get("text"), "missing text"
assert payload.get("voice_uri"), "missing voice_uri"

print(
    json.dumps(
        {
            "status": "ok",
            "source": payload.get("source"),
            "turn_id": payload.get("turn_id"),
            "patch_count": payload.get("patch_count"),
            "voice_uri": payload.get("voice_uri"),
        },
        indent=2,
    )
)
PY

rm -f "$SUMMARY_FILE"
echo "fresh-agent-e2e: pass"
