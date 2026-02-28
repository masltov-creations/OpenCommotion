from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any

from services.agents.text.adapters import AdapterError, build_adapters

LLM_PROVIDER_ENV = "OPENCOMMOTION_LLM_PROVIDER"
LLM_MODEL_ENV = "OPENCOMMOTION_LLM_MODEL"
LLM_ALLOW_FALLBACK_ENV = "OPENCOMMOTION_LLM_ALLOW_FALLBACK"
LLM_TIMEOUT_ENV = "OPENCOMMOTION_LLM_TIMEOUT_S"
PROMPT_REWRITE_ENABLED_ENV = "OPENCOMMOTION_PROMPT_REWRITE_ENABLED"
PROMPT_REWRITE_MAX_CHARS_ENV = "OPENCOMMOTION_PROMPT_REWRITE_MAX_CHARS"
NARRATION_CONTEXT_ENABLED_ENV = "OPENCOMMOTION_NARRATION_CONTEXT_ENABLED"

VALID_PROVIDERS = {
    "heuristic",
    "ollama",
    "openai-compatible",
    "codex-cli",
    "openclaw-cli",
    "openclaw-openai",
}
TRUE_VALUES = {"1", "true", "yes", "on"}
CLARIFICATION_PREFIXES = (
    "do you want",
    "would you like",
    "can you clarify",
    "which do you want",
    "should i",
    "single image",
)
NON_ACTIONABLE_HINTS = (
    "i can't",
    "i cannot",
    "can't do",
    "cannot do",
    "i'm unable",
    "unable to",
    "need more context",
    "need more detail",
    "need more details",
    "insufficient information",
)


@dataclass
class LLMEngineError(RuntimeError):
    provider: str
    message: str

    def __str__(self) -> str:
        return self.message


def _context_field(context: Any, name: str) -> str | None:
    if context is None:
        return None
    if isinstance(context, dict):
        value = context.get(name)
        return str(value).strip() if isinstance(value, str) and value.strip() else None
    value = getattr(context, name, None)
    if isinstance(value, str):
        value = value.strip()
    return value


def _build_contextual_invocation(scene_brief: str | None, capability_brief: str | None, turn_phase: str | None) -> str:
    parts: list[str] = []
    if turn_phase:
        parts.append(f"Turn phase: {turn_phase}")
    if scene_brief:
        parts.append(f"Scene state: {scene_brief}")
    if capability_brief:
        parts.append(f"Capabilities: {capability_brief}")
    base = _default_invocation_context()
    parts.append(base)
    return "\n".join(parts)


def generate_text_response(prompt: str, context: Any | None = None) -> str:
    cleaned = prompt.strip()
    if not cleaned:
        return "OpenCommotion: I need a prompt to generate a synchronized text, voice, and visual response."

    provider = _selected_provider()
    adapters = build_adapters(timeout_s=_timeout_s())
    heuristic = adapters["heuristic"]
    selected = adapters.get(provider, heuristic)
    scene_brief = _context_field(context, "scene_brief")
    capability_brief = _context_field(context, "capability_brief")
    turn_phase = _context_field(context, "turn_phase")
    invocation_context = _build_contextual_invocation(scene_brief, capability_brief, turn_phase)
    request_prompt = cleaned
    if _narration_context_enabled() and provider != "heuristic":
        request_prompt = _build_narration_request(cleaned, invocation_context)
    system_prompt_override = _context_field(context, "system_prompt_override")

    try:
        generated = selected.generate(request_prompt, system_prompt_override=system_prompt_override)
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
    elif _looks_like_clarification_request(text):
        if _allow_fallback():
            text = heuristic.generate(cleaned)
        else:
            text = f"{cleaned}. I will proceed with synchronized narration and visuals."
    elif _looks_non_actionable(text):
        if _allow_fallback():
            text = heuristic.generate(cleaned)
        else:
            text = f"{cleaned}. I will proceed with synchronized narration and visuals."

    return _normalize_response(text)


def rewrite_visual_prompt(prompt: str, *, context: str, first_turn: bool) -> tuple[str, dict[str, Any]]:
    cleaned = prompt.strip()
    provider = _selected_provider()
    metadata: dict[str, Any] = {
        "provider": provider,
        "scene_request": False,
        "warnings": [],
    }
    if not cleaned:
        return "", metadata
    if not _rewrite_enabled():
        metadata["warnings"] = ["prompt_rewrite_disabled"]
        return cleaned, metadata

    adapters = build_adapters(timeout_s=_timeout_s())
    selected = adapters.get(provider, adapters["heuristic"])
    request = _build_rewrite_request(prompt=cleaned, context=context, first_turn=first_turn)

    try:
        raw = (selected.generate(request) or "").strip()
    except AdapterError as exc:
        if _allow_fallback():
            metadata["warnings"] = [f"prompt_rewrite_provider_error:{provider}"]
            return cleaned, metadata
        raise LLMEngineError(provider=provider, message=str(exc)) from exc

    rewritten, scene_request = _parse_rewrite_response(raw=raw, fallback=cleaned)
    metadata["scene_request"] = scene_request
    if scene_request:
        metadata["warnings"] = [f"prompt_rewrite_scene_request:{provider}"]
    elif rewritten != cleaned:
        metadata["warnings"] = [f"prompt_rewrite_provider_applied:{provider}"]
    return rewritten, metadata


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


def _looks_like_clarification_request(text: str) -> bool:
    clean = text.strip().lower()
    if not clean:
        return False
    if "?" not in clean:
        return False
    return any(clean.startswith(prefix) or f" {prefix}" in clean for prefix in CLARIFICATION_PREFIXES)


def _looks_non_actionable(text: str) -> bool:
    clean = text.strip().lower()
    if not clean:
        return True
    return any(hint in clean for hint in NON_ACTIONABLE_HINTS)


def _narration_context_enabled() -> bool:
    raw = os.getenv(NARRATION_CONTEXT_ENABLED_ENV)
    if raw is None or not raw.strip():
        return True
    return raw.strip().lower() in TRUE_VALUES


def _default_invocation_context() -> str:
    return (
        "OpenCommotion orchestrator turn. "
        "The agent is already connected to a live visual runtime and must proceed without clarification loops. "
        "Return concise narration aligned to active visual rendering."
    )


def _build_narration_request(prompt: str, context: str) -> str:
    return (
        "You are OpenCommotion narration agent.\n"
        "Invocation context:\n"
        f"{context}\n\n"
        "Rules:\n"
        "- Do not ask clarifying questions.\n"
        "- Assume rendering tools are active.\n"
        "- Respond in 1-3 concise sentences.\n"
        "- Describe what is being shown and how it will animate.\n\n"
        "User prompt:\n"
        f"{prompt}"
    )


def _rewrite_enabled() -> bool:
    raw = os.getenv(PROMPT_REWRITE_ENABLED_ENV)
    if raw is None or not raw.strip():
        return True
    return raw.strip().lower() in TRUE_VALUES


def _rewrite_max_chars() -> int:
    raw = os.getenv(PROMPT_REWRITE_MAX_CHARS_ENV, "320").strip()
    try:
        value = int(raw)
    except ValueError:
        return 320
    return max(80, min(1200, value))


def _build_rewrite_request(prompt: str, context: str, first_turn: bool) -> str:
    example_block = (
        "Concise example:\n"
        "{\n"
        "  \"visual_prompt\": \"draw two circles and animate both with bounce motion\",\n"
        "  \"scene_request\": \"no\",\n"
        "  \"tool_handles\": [\"spawnSceneActor\", \"setActorMotion\"],\n"
        "  \"foundation_entities\": [\"actors\"],\n"
        "  \"language_semantics\": [\"imperative\", \"count-explicit\", \"motion-explicit\"]\n"
        "}\n"
    )
    mode_note = (
        "Turn mode: first turn. Build a complete initial scene with explicit actors and motion."
        if first_turn
        else "Turn mode: follow-up. Prefer small deterministic updates over full rebuilds."
    )
    return (
        "You are OpenCommotion prompt-planner. Rewrite user input into a concrete render/update prompt.\n"
        "Runtime context instructions:\n"
        "- You are inside OpenCommotion orchestrator and your output feeds a visual scene compiler.\n"
        "- You must return executable visual intent; never ask clarification questions.\n"
        "- If first turn: compose a complete initial scene. If follow-up: apply minimal deterministic updates.\n"
        "- Keep nouns explicit and counted when provided (fish, bowl, ball, chart, labels, segments).\n"
        "\n"
        "User context semantics (how to interpret context):\n"
        "- scene_brief: current scene summary (ids, counts, phase).\n"
        "- capability_brief: runtime/render + provider constraints.\n"
        "- turn_phase: first-turn or follow-up, controls create-vs-update strategy.\n"
        "- entity_details: known entity ids to preserve/reuse on follow-up turns.\n"
        "- system_prompt_override: hard guardrail text that must be honored if present.\n"
        "\n"
        "Available handles (use as needed):\n"
        "- tool_handles: setRenderMode, spawnSceneActor, setActorMotion, setActorAnimation, runScreenScript, annotateInsight, emitFx, setEnvironmentMood, setCameraMove, setLyricsTrack, applyMaterialFx, sceneMorph.\n"
        "- template_handles: spawnCharacter, animateMoonwalk, orbitGlobe, ufoLandingBeat, drawAdoptionCurve, drawPieSaturation, drawSegmentedAttachBars.\n"
        "- foundation_entities: actors, charts, camera, environment, materials, fx, annotations, lyrics timeline.\n"
        "- language_semantics: imperative verb first (draw/update/show), continuity-aware ids, explicit motion verbs, explicit timing hints, explicit counts, style/mood tags.\n"
        f"{mode_note}\n\n"
        f"Scene context snapshot:\n{context}\n\n"
        f"{example_block}\n"
        f"User prompt:\n{prompt}\n\n"
        "Return EXACTLY one JSON object with this schema:\n"
        "{\n"
        "  \"visual_prompt\": \"<one-line imperative prompt starting with draw/update/show>\",\n"
        "  \"scene_request\": \"<yes|no>\",\n"
        "  \"tool_handles\": [\"<subset of handles you used>\"],\n"
        "  \"foundation_entities\": [\"<entities touched>\"],\n"
        "  \"language_semantics\": [\"<semantic choices used>\"]\n"
        "}\n"
    )


def _parse_rewrite_response(raw: str, fallback: str) -> tuple[str, bool]:
    clean = raw.strip().replace("\r", "")
    scene_request = False
    prompt_line = ""

    if clean.startswith("{") and clean.endswith("}"):
        try:
            payload = json.loads(clean)
        except json.JSONDecodeError:
            payload = None
        if isinstance(payload, dict):
            candidate_prompt = str(payload.get("visual_prompt", "")).strip()
            raw_scene_request = str(payload.get("scene_request", "")).strip().lower()
            scene_request = raw_scene_request in {"yes", "true", "1"}
            if candidate_prompt:
                candidate_prompt = candidate_prompt.strip("`\"' ")
                candidate_prompt = " ".join(candidate_prompt.split())
                if candidate_prompt and not _looks_like_clarification_request(candidate_prompt):
                    limit = _rewrite_max_chars()
                    if len(candidate_prompt) > limit:
                        candidate_prompt = candidate_prompt[:limit].rstrip()
                    return candidate_prompt, scene_request

    for line in clean.split("\n"):
        row = line.strip()
        if not row:
            continue
        lower = row.lower()
        if lower.startswith("scene_request:"):
            scene_request = "yes" in lower
            continue
        if lower.startswith("visual_prompt:"):
            prompt_line = row.split(":", 1)[1].strip()
            continue
        if not prompt_line:
            prompt_line = row

    candidate = (prompt_line or clean).strip()
    if candidate.lower().startswith("opencommotion:"):
        candidate = candidate.split(":", 1)[1].strip()
    candidate = candidate.strip("`\"' ")
    candidate = " ".join(candidate.split())
    if not candidate or _looks_like_clarification_request(candidate):
        return fallback, scene_request
    limit = _rewrite_max_chars()
    if len(candidate) > limit:
        candidate = candidate[:limit].rstrip()
    return candidate, scene_request


__all__ = ["LLMEngineError", "generate_text_response", "llm_capabilities", "rewrite_visual_prompt"]
