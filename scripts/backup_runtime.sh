#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

BACKUP_DIR="${1:-$ROOT/runtime/backups}"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
OUT="$BACKUP_DIR/opencommotion-backup-$STAMP.tar.gz"

mkdir -p "$BACKUP_DIR"
mkdir -p data/artifacts runtime/agent-runs

tar -czf "$OUT" \
  data/artifacts/artifacts.db \
  data/artifacts/bundles \
  runtime/agent-runs/agent_manager.db 2>/dev/null || {
  echo "backup created with partial contents (some files may not exist yet): $OUT"
  exit 0
}

echo "backup created: $OUT"
