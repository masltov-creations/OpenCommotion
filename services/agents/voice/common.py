from __future__ import annotations

import os
from urllib.parse import urlparse

TRUE_VALUES = {"1", "true", "yes", "on"}
VOICE_REQUIRE_REAL_ENV = "OPENCOMMOTION_VOICE_REQUIRE_REAL_ENGINES"
LOCAL_VOICE_HOSTS = {"127.0.0.1", "localhost", "0.0.0.0", "::1"}


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


def voice_openai_api_key_required(base_url: str) -> bool:
    parsed = urlparse(base_url)
    host = (parsed.hostname or "").strip().lower()
    if not host:
        return False
    return host not in LOCAL_VOICE_HOSTS


def voice_openai_ready(base_url: str, model: str, api_key: str) -> bool:
    if not base_url or not model:
        return False
    if voice_openai_api_key_required(base_url) and not api_key:
        return False
    return True
