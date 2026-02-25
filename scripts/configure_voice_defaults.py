#!/usr/bin/env python3
from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.config.runtime_config import ENV_PATH, parse_env, write_env


def _truthy(value: str | None) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "on"}


def _normalize_path_overrides(values: dict[str, str]) -> bool:
    if _truthy(os.getenv("OPENCOMMOTION_ALLOW_EXTERNAL_PATHS")):
        return False

    defaults = {
        "OPENCOMMOTION_UI_DIST_ROOT": ROOT / "apps" / "ui" / "dist",
        "OPENCOMMOTION_AUDIO_ROOT": ROOT / "data" / "audio",
        "ARTIFACT_DB_PATH": ROOT / "data" / "artifacts" / "artifacts.db",
        "ARTIFACT_BUNDLE_ROOT": ROOT / "data" / "artifacts" / "bundles",
    }

    changed = False
    root_resolved = ROOT.resolve()
    for key, default_path in defaults.items():
        raw = values.get(key, "").strip()
        if not raw:
            continue
        candidate = Path(raw).expanduser()
        if not candidate.is_absolute():
            continue
        try:
            candidate.resolve().relative_to(root_resolved)
            continue
        except ValueError:
            values[key] = str(default_path)
            changed = True
    return changed


def main() -> int:
    if not ENV_PATH.exists():
        return 0

    values = parse_env(ENV_PATH)
    changed = False

    if _normalize_path_overrides(values):
        changed = True

    espeak_bin = os.getenv("OPENCOMMOTION_ESPEAK_BIN_HINT", "").strip()
    if not espeak_bin:
        espeak_bin = shutil.which("espeak-ng") or shutil.which("espeak") or ""

    current_tts = values.get("OPENCOMMOTION_TTS_ENGINE", "").strip().lower()
    if espeak_bin and current_tts in {"", "tone-fallback"}:
        values["OPENCOMMOTION_TTS_ENGINE"] = "espeak"
        changed = True

    if espeak_bin and not values.get("OPENCOMMOTION_ESPEAK_BIN", "").strip():
        values["OPENCOMMOTION_ESPEAK_BIN"] = espeak_bin
        changed = True

    if not values.get("OPENCOMMOTION_STT_ENGINE", "").strip():
        values["OPENCOMMOTION_STT_ENGINE"] = "auto"
        changed = True

    if changed:
        write_env(ENV_PATH, values)
        print("Updated .env defaults for runtime paths and spoken local TTS.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
