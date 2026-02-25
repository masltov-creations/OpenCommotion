from __future__ import annotations

from fastapi.testclient import TestClient

from services.artifact_registry.opencommotion_artifacts.registry import ArtifactRegistry
from services.gateway.app import main as gateway_main
from services.orchestrator.app.main import app as orchestrator_app


def _client_with_inprocess_orchestrator(tmp_path, monkeypatch) -> TestClient:
    monkeypatch.setenv("OPENCOMMOTION_AUTH_MODE", "api-key")
    monkeypatch.delenv("OPENCOMMOTION_API_KEYS", raising=False)
    db_path = tmp_path / "artifacts.db"
    bundle_root = tmp_path / "bundles"
    monkeypatch.setattr(
        gateway_main,
        "registry",
        ArtifactRegistry(db_path=str(db_path), bundle_root=str(bundle_root)),
    )

    original_async_client = gateway_main.httpx.AsyncClient

    class RoutedAsyncClient:
        def __init__(self, *args, **kwargs) -> None:
            timeout = kwargs.get("timeout", 20)
            self._client = original_async_client(
                timeout=timeout,
                transport=gateway_main.httpx.ASGITransport(app=orchestrator_app),
                base_url="http://127.0.0.1:8001",
            )

        async def __aenter__(self):
            await self._client.__aenter__()
            return self._client

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            return await self._client.__aexit__(exc_type, exc_val, exc_tb)

    monkeypatch.setattr(gateway_main.httpx, "AsyncClient", RoutedAsyncClient)
    return TestClient(gateway_main.app)


def test_voice_capabilities_endpoint_exposes_engine_readiness(tmp_path, monkeypatch) -> None:
    c = _client_with_inprocess_orchestrator(tmp_path, monkeypatch)
    res = c.get("/v1/voice/capabilities")
    assert res.status_code == 200
    payload = res.json()
    assert "stt" in payload
    assert "tts" in payload
    assert "selected_engine" in payload["stt"]
    assert "selected_engine" in payload["tts"]


def test_strict_mode_rejects_transcribe_without_real_stt(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("OPENCOMMOTION_VOICE_REQUIRE_REAL_ENGINES", "true")
    monkeypatch.setenv("OPENCOMMOTION_STT_ENGINE", "auto")
    monkeypatch.delenv("OPENCOMMOTION_STT_MODEL", raising=False)
    monkeypatch.delenv("OPENCOMMOTION_VOSK_MODEL_PATH", raising=False)

    c = _client_with_inprocess_orchestrator(tmp_path, monkeypatch)
    res = c.post(
        "/v1/voice/transcribe",
        files={"audio": ("sample.wav", b"moonwalk adoption chart", "audio/wav")},
    )

    assert res.status_code == 503
    detail = res.json()["detail"]
    assert detail["error"] == "stt_engine_unavailable"


def test_strict_mode_rejects_synthesize_with_fallback_engine(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("OPENCOMMOTION_VOICE_REQUIRE_REAL_ENGINES", "true")
    monkeypatch.setenv("OPENCOMMOTION_TTS_ENGINE", "tone-fallback")

    c = _client_with_inprocess_orchestrator(tmp_path, monkeypatch)
    res = c.post("/v1/voice/synthesize", json={"text": "render voice now"})
    assert res.status_code == 503
    detail = res.json()["detail"]
    assert detail["error"] == "tts_engine_unavailable"


def test_strict_mode_rejects_orchestrate_with_unavailable_tts(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("OPENCOMMOTION_VOICE_REQUIRE_REAL_ENGINES", "true")
    monkeypatch.setenv("OPENCOMMOTION_TTS_ENGINE", "tone-fallback")

    c = _client_with_inprocess_orchestrator(tmp_path, monkeypatch)
    res = c.post(
        "/v1/orchestrate",
        json={"session_id": "strict-voice", "prompt": "moonwalk adoption chart"},
    )
    assert res.status_code == 503
    detail = res.json()["detail"]
    assert detail["error"] == "tts_engine_unavailable"


def test_openai_stt_requires_cloud_config_when_selected(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("OPENCOMMOTION_STT_ENGINE", "openai-compatible")
    monkeypatch.delenv("OPENCOMMOTION_VOICE_OPENAI_BASE_URL", raising=False)
    monkeypatch.delenv("OPENCOMMOTION_VOICE_STT_MODEL", raising=False)

    c = _client_with_inprocess_orchestrator(tmp_path, monkeypatch)
    res = c.post(
        "/v1/voice/transcribe",
        files={"audio": ("sample.wav", b"wave-content", "audio/wav")},
    )
    assert res.status_code == 503
    detail = res.json()["detail"]
    assert detail["error"] == "stt_engine_unavailable"


def test_openai_tts_requires_cloud_config_when_selected(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("OPENCOMMOTION_TTS_ENGINE", "openai-compatible")
    monkeypatch.delenv("OPENCOMMOTION_VOICE_OPENAI_BASE_URL", raising=False)
    monkeypatch.delenv("OPENCOMMOTION_VOICE_TTS_MODEL", raising=False)

    c = _client_with_inprocess_orchestrator(tmp_path, monkeypatch)
    res = c.post("/v1/voice/synthesize", json={"text": "speak now"})
    assert res.status_code == 503
    detail = res.json()["detail"]
    assert detail["error"] == "tts_engine_unavailable"
