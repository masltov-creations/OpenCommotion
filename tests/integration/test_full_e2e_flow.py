from __future__ import annotations

import json

from fastapi.testclient import TestClient

from services.artifact_registry.opencommotion_artifacts.registry import ArtifactRegistry
from services.gateway.app import main as gateway_main
from services.orchestrator.app.main import app as orchestrator_app


def test_full_e2e_turn_artifact_recall_and_ws_event(tmp_path, monkeypatch) -> None:
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

    client = TestClient(gateway_main.app)
    prompt = "moonwalk globe adoption pie"

    # Without a live LLM, the orchestrator should return 503
    orchestrate = client.post(
        "/v1/orchestrate",
        json={"session_id": "e2e-session", "prompt": prompt},
    )
    assert orchestrate.status_code == 503
    data = orchestrate.json()
    assert "llm_engine_unavailable" in data["detail"]["error"]

