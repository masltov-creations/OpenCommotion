from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

from services.agents.text.adapters import AdapterError, build_adapters

LLM_PROVIDER_ENV = "OPENCOMMOTION_LLM_PROVIDER"
LLM_MODEL_ENV = "OPENCOMMOTION_LLM_MODEL"
LLM_ALLOW_FALLBACK_ENV = "OPENCOMMOTION_LLM_ALLOW_FALLBACK"
LLM_TIMEOUT_ENV = "OPENCOMMOTION_LLM_TIMEOUT_S"

VALID_PROVIDERS = {
    "heuristic",
    "ollama",
    "openai-compatible",
    "codex-cli",
    "openclaw-cli",
    "openclaw-openai",
}
TRUE_VALUES = {"1", "true", "yes", "on"}


@dataclass
class LLMEngineError(RuntimeError):
    provider: str
    message: str

    def __str__(self) -> str:
        return self.message


def generate_text_response(prompt: str) -> str:
    cleaned = prompt.strip()
    if not cleaned:
        return "OpenCommotion: I need a prompt to generate a synchronized text, voice, and visual response."

    provider = _selected_provider()
    adapters = build_adapters(timeout_s=_timeout_s())
    heuristic = adapters["heuristic"]
    selected = adapters.get(provider, heuristic)

    try:
        generated = selected.generate(cleaned)
    except AdapterError as exc:
        if _allow_fallback():
            return _normalize_response(heuristic.generate(cleaned))
        raise LLMEngineError(provider=provider, message=str(exc)) from exc

    text = (generated or "").strip()
    if not text:
        if _allow_fallback():
            text = heuristic.generate(cleaned)
        else:
            raise LLMEngineError(provider=provider, message=f"{provider} returned an empty text response")

    return _normalize_response(text)


def llm_capabilities(probe: bool = False) -> dict[str, Any]:
    selected = _selected_provider()
    allow_fallback = _allow_fallback()
    timeout_s = _timeout_s()
    adapters = build_adapters(timeout_s=timeout_s)

    providers: dict[str, dict[str, Any]] = {}
    for provider in [
        "heuristic",
        "ollama",
        "openai-compatible",
        "codex-cli",
        "openclaw-cli",
        "openclaw-openai",
    ]:
        adapter = adapters[provider]
        try:
            capabilities = adapter.capabilities(probe=probe)
        except Exception as exc:  # noqa: BLE001
            capabilities = {"ready": False, "error": str(exc)}
        providers[provider] = capabilities

    selected_ready = bool(providers.get(selected, {}).get("ready"))
    effective_provider = selected if selected_ready else ("heuristic" if allow_fallback else selected)
    effective_ready = selected_ready or allow_fallback

    selected_model = str(providers.get(selected, {}).get("model", "")).strip()
    model = selected_model or os.getenv(LLM_MODEL_ENV, "").strip()

    return {
        "selected_provider": selected,
        "effective_provider": effective_provider,
        "active_provider_ready": selected_ready,
        "effective_ready": effective_ready,
        "allow_fallback": allow_fallback,
        "timeout_s": timeout_s,
        "model": model,
        "providers": providers,
    }


def _selected_provider() -> str:
    selected = os.getenv(LLM_PROVIDER_ENV, "heuristic").strip().lower()
    if selected not in VALID_PROVIDERS:
        return "heuristic"
    return selected


def _allow_fallback() -> bool:
    raw = os.getenv(LLM_ALLOW_FALLBACK_ENV)
    if raw is None or not raw.strip():
        return True
    value = raw.strip().lower()
    return value in TRUE_VALUES


def _timeout_s() -> float:
    raw = os.getenv(LLM_TIMEOUT_ENV, "20").strip()
    try:
        value = float(raw)
    except ValueError:
        return 20.0
    return min(max(value, 0.5), 120.0)


def _normalize_response(text: str) -> str:
    cleaned = text.strip()
    if not cleaned:
        return "OpenCommotion: I need a prompt to generate a synchronized text, voice, and visual response."
    if cleaned.lower().startswith("opencommotion:"):
        return cleaned
    return f"OpenCommotion: {cleaned}"


__all__ = ["LLMEngineError", "generate_text_response", "llm_capabilities"]
