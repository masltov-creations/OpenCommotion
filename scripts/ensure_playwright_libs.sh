#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CACHE_ROOT="$ROOT/.cache/pw-deps"
EXTRACT_ROOT="$CACHE_ROOT/root"
LIB_DIR="$EXTRACT_ROOT/usr/lib/x86_64-linux-gnu"

if [[ -f "$LIB_DIR/libnspr4.so" && -f "$LIB_DIR/libnss3.so" ]]; then
  echo "$LIB_DIR"
  exit 0
fi

mkdir -p "$CACHE_ROOT"
pushd "$CACHE_ROOT" >/dev/null

if ! command -v apt-get >/dev/null 2>&1; then
  echo "apt-get is required to fetch Playwright runtime libs without sudo" >&2
  exit 1
fi

apt-get download libnspr4 libnss3 >/dev/null
mkdir -p "$EXTRACT_ROOT"
for deb in ./*.deb; do
  dpkg-deb -x "$deb" "$EXTRACT_ROOT"
done

popd >/dev/null

if [[ ! -f "$LIB_DIR/libnspr4.so" || ! -f "$LIB_DIR/libnss3.so" ]]; then
  echo "failed to prepare Playwright runtime libs in $LIB_DIR" >&2
  exit 1
fi

echo "$LIB_DIR"
