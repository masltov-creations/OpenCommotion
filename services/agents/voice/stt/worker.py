from __future__ import annotations

import importlib.util
import io
import os
import tempfile
import wave
from functools import lru_cache
from pathlib import Path
from re import findall

from services.agents.voice.common import normalized_env, require_real_voice_engines
from services.agents.voice.errors import VoiceEngineError

STT_ENGINE_ENV = "OPENCOMMOTION_STT_ENGINE"
STT_MODEL_ENV = "OPENCOMMOTION_STT_MODEL"
STT_COMPUTE_TYPE_ENV = "OPENCOMMOTION_STT_COMPUTE_TYPE"
VOSK_MODEL_PATH_ENV = "OPENCOMMOTION_VOSK_MODEL_PATH"

VALID_STT_ENGINES = {"auto", "hint", "faster-whisper", "vosk", "text-fallback"}
REAL_STT_ENGINES = {"faster-whisper", "vosk"}


def transcribe_audio(audio: bytes, hint: str = "") -> dict:
    selected_engine = _selected_engine()

    if hint.strip() and selected_engine in {"auto", "hint"}:
        return {
            "partial": "",
            "final": hint.strip(),
            "confidence": 0.95,
            "engine": "hint",
        }

    if selected_engine == "faster-whisper":
        result = _transcribe_with_faster_whisper(audio, required=True)
        return {
            "partial": "",
            "final": result[0],
            "confidence": result[1],
            "engine": "faster-whisper",
        }

    if selected_engine == "vosk":
        result = _transcribe_with_vosk(audio, required=True)
        return {
            "partial": "",
            "final": result[0],
            "confidence": result[1],
            "engine": "vosk",
        }

    if selected_engine == "text-fallback":
        return _fallback_transcript(audio)

    auto_faster = _transcribe_with_faster_whisper(audio, required=False)
    if auto_faster:
        return {
            "partial": "",
            "final": auto_faster[0],
            "confidence": auto_faster[1],
            "engine": "faster-whisper",
        }

    auto_vosk = _transcribe_with_vosk(audio, required=False)
    if auto_vosk:
        return {
            "partial": "",
            "final": auto_vosk[0],
            "confidence": auto_vosk[1],
            "engine": "vosk",
        }

    if require_real_voice_engines():
        capabilities = stt_capabilities()
        raise VoiceEngineError(
            engine="stt",
            message=(
                "No real STT engine is configured or available. "
                f"selected={capabilities['selected_engine']}, "
                f"faster_whisper_ready={capabilities['faster_whisper']['ready']}, "
                f"vosk_ready={capabilities['vosk']['ready']}"
            ),
        )

    return _fallback_transcript(audio)


def stt_capabilities() -> dict:
    selected_engine = _selected_engine()
    whisper_model = os.getenv(STT_MODEL_ENV, "").strip()
    whisper_importable = _module_importable("faster_whisper")
    whisper_ready = bool(whisper_model) and whisper_importable

    vosk_model_path = os.getenv(VOSK_MODEL_PATH_ENV, "").strip()
    vosk_importable = _module_importable("vosk")
    vosk_ready = bool(vosk_model_path) and Path(vosk_model_path).is_dir() and vosk_importable

    return {
        "selected_engine": selected_engine,
        "strict_real_engines": require_real_voice_engines(),
        "real_engines": sorted(REAL_STT_ENGINES),
        "faster_whisper": {
            "importable": whisper_importable,
            "model": whisper_model,
            "ready": whisper_ready,
        },
        "vosk": {
            "importable": vosk_importable,
            "model_path": vosk_model_path,
            "ready": vosk_ready,
        },
    }


def _selected_engine() -> str:
    selected = normalized_env(STT_ENGINE_ENV, default="auto")
    if selected not in VALID_STT_ENGINES:
        return "auto"
    return selected


def _fallback_transcript(audio: bytes) -> dict:
    decoded = _decode_text_payload(audio)
    if decoded:
        return {
            "partial": "",
            "final": decoded,
            "confidence": 0.72,
            "engine": "text-fallback",
        }
    return {
        "partial": "",
        "final": "voice input received",
        "confidence": 0.4,
        "engine": "fallback",
    }


def _transcribe_with_faster_whisper(audio: bytes, required: bool) -> tuple[str, float] | None:
    model_name = os.getenv(STT_MODEL_ENV, "").strip()
    if not model_name:
        if required:
            raise VoiceEngineError(
                engine="faster-whisper",
                message=f"Missing {STT_MODEL_ENV} for faster-whisper transcription",
            )
        return None

    if not _module_importable("faster_whisper"):
        if required:
            raise VoiceEngineError(
                engine="faster-whisper",
                message="faster-whisper package is not installed",
            )
        return None

    compute_type = os.getenv(STT_COMPUTE_TYPE_ENV, "int8").strip() or "int8"
    try:
        model = _whisper_model(model_name, compute_type)
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp.write(audio)
            tmp_path = Path(tmp.name)
        try:
            segments, _ = model.transcribe(str(tmp_path), beam_size=1, vad_filter=True)
            parts = []
            for segment in segments:
                text = getattr(segment, "text", "").strip()
                if text:
                    parts.append(text)
            if not parts:
                return None
            transcript = " ".join(parts).strip()
            return transcript, 0.9
        finally:
            tmp_path.unlink(missing_ok=True)
    except Exception as exc:
        if required:
            raise VoiceEngineError(
                engine="faster-whisper",
                message=f"faster-whisper transcription failed: {exc}",
            ) from exc
        return None


def _transcribe_with_vosk(audio: bytes, required: bool) -> tuple[str, float] | None:
    model_path = os.getenv(VOSK_MODEL_PATH_ENV, "").strip()
    if not model_path:
        if required:
            raise VoiceEngineError(
                engine="vosk",
                message=f"Missing {VOSK_MODEL_PATH_ENV} for vosk transcription",
            )
        return None

    if not Path(model_path).is_dir():
        if required:
            raise VoiceEngineError(
                engine="vosk",
                message=f"Configured vosk model path does not exist: {model_path}",
            )
        return None

    if not _module_importable("vosk"):
        if required:
            raise VoiceEngineError(engine="vosk", message="vosk package is not installed")
        return None

    try:
        import json

        from vosk import KaldiRecognizer

        model = _vosk_model(model_path)
        with wave.open(io.BytesIO(audio), "rb") as wav_reader:
            recognizer = KaldiRecognizer(model, wav_reader.getframerate())
            while True:
                chunk = wav_reader.readframes(4000)
                if not chunk:
                    break
                recognizer.AcceptWaveform(chunk)
            final = json.loads(recognizer.FinalResult())
            transcript = str(final.get("text", "")).strip()
            if not transcript:
                return None
            return transcript, 0.78
    except Exception as exc:
        if required:
            raise VoiceEngineError(engine="vosk", message=f"vosk transcription failed: {exc}") from exc
        return None


@lru_cache(maxsize=2)
def _whisper_model(model_name: str, compute_type: str):
    from faster_whisper import WhisperModel

    return WhisperModel(model_name, device="cpu", compute_type=compute_type)


@lru_cache(maxsize=2)
def _vosk_model(model_path: str):
    from vosk import Model

    return Model(model_path=model_path)


def _module_importable(module_name: str) -> bool:
    return importlib.util.find_spec(module_name) is not None


def _decode_text_payload(audio: bytes) -> str:
    try:
        decoded = audio.decode("utf-8", errors="ignore").strip()
    except Exception:
        return ""
    if not decoded:
        return ""
    tokens = findall(r"[A-Za-z0-9']+", decoded)
    if len(tokens) < 2:
        return ""
    if tokens[:2] == ["RIFF", "WAVEfmt"] or tokens[:1] == ["RIFF"]:
        return ""
    cleaned = " ".join(tokens).strip()
    if len(cleaned) > 160:
        return cleaned[:160].rstrip()
    return cleaned


__all__ = ["transcribe_audio", "stt_capabilities"]
