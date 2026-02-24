from __future__ import annotations

import os

TRUE_VALUES = {"1", "true", "yes", "on"}
VOICE_REQUIRE_REAL_ENV = "OPENCOMMOTION_VOICE_REQUIRE_REAL_ENGINES"


def env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in TRUE_VALUES


def require_real_voice_engines() -> bool:
    return env_bool(VOICE_REQUIRE_REAL_ENV, default=False)


def normalized_env(name: str, default: str = "") -> str:
    value = os.getenv(name, default)
    return value.strip().lower()
