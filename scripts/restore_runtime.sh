#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "usage: $0 <backup-tar.gz>" >&2
  exit 1
fi

ARCHIVE="$1"
if [[ ! -f "$ARCHIVE" ]]; then
  echo "backup archive not found: $ARCHIVE" >&2
  exit 1
fi

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

mkdir -p data/artifacts runtime/agent-runs
tar -xzf "$ARCHIVE" -C "$ROOT"
echo "restore complete from: $ARCHIVE"
