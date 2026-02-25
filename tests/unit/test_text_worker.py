from __future__ import annotations

import httpx
import pytest

from services.agents.text import adapters
from services.agents.text import worker


def _write_executable(path, content: str) -> None:
    path.write_text(content, encoding="utf-8")
    path.chmod(0o755)


def test_generate_text_response_uses_heuristic_by_default(monkeypatch) -> None:
    monkeypatch.delenv("OPENCOMMOTION_LLM_PROVIDER", raising=False)
    text = worker.generate_text_response("moonwalk adoption chart")
    assert text.startswith("OpenCommotion:")
    assert "moonwalk adoption chart" in text


def test_generate_text_response_falls_back_when_remote_provider_fails(monkeypatch) -> None:
    monkeypatch.setenv("OPENCOMMOTION_LLM_PROVIDER", "openai-compatible")
    monkeypatch.setenv("OPENCOMMOTION_LLM_ALLOW_FALLBACK", "true")
    monkeypatch.setenv("OPENCOMMOTION_LLM_TIMEOUT_S", "0.5")

    def fail_request(*args, **kwargs):  # noqa: ANN002, ANN003
        req = httpx.Request("POST", "http://127.0.0.1:1/v1/chat/completions")
        raise httpx.ConnectError("connection failed", request=req)

    monkeypatch.setattr(adapters.httpx, "post", fail_request)

    text = worker.generate_text_response("ufo landing")
    assert text.startswith("OpenCommotion:")
    assert "ufo landing" in text


def test_generate_text_response_raises_without_fallback(monkeypatch) -> None:
    monkeypatch.setenv("OPENCOMMOTION_LLM_PROVIDER", "openai-compatible")
    monkeypatch.setenv("OPENCOMMOTION_LLM_ALLOW_FALLBACK", "false")
    monkeypatch.setenv("OPENCOMMOTION_LLM_TIMEOUT_S", "0.5")

    def fail_request(*args, **kwargs):  # noqa: ANN002, ANN003
        req = httpx.Request("POST", "http://127.0.0.1:1/v1/chat/completions")
        raise httpx.ConnectError("connection failed", request=req)

    monkeypatch.setattr(adapters.httpx, "post", fail_request)

    with pytest.raises(worker.LLMEngineError):
        worker.generate_text_response("ufo landing")


def test_llm_capabilities_reports_selected_provider(monkeypatch) -> None:
    monkeypatch.setenv("OPENCOMMOTION_LLM_PROVIDER", "ollama")
    monkeypatch.setenv("OPENCOMMOTION_LLM_MODEL", "qwen2.5:7b-instruct")
    caps = worker.llm_capabilities(probe=False)
    assert caps["selected_provider"] == "ollama"
    assert "providers" in caps
    assert "ollama" in caps["providers"]


def test_extract_codex_agent_message_handles_non_json_lines() -> None:
    payload = "\n".join(
        [
            "random warning line",
            '{"type":"item.completed","item":{"type":"reasoning","text":"thinking"}}',
            '{"type":"item.completed","item":{"type":"agent_message","text":"first"}}',
            '{"type":"item.completed","item":{"type":"agent_message","text":"second"}}',
        ]
    )
    assert adapters.extract_codex_agent_message(payload) == "second"


def test_extract_openclaw_text_joins_payload_rows() -> None:
    payload = """
    {
      "payloads": [
        {"text": "hello"},
        {"text": "world"},
        {"mediaUrl": null}
      ]
    }
    """
    assert adapters.extract_openclaw_text(payload) == "hello\n\nworld"


def test_generate_text_response_with_codex_cli_provider(tmp_path, monkeypatch) -> None:
    fake_codex = tmp_path / "fake-codex"
    _write_executable(
        fake_codex,
        """#!/usr/bin/env bash
echo '{"type":"item.completed","item":{"type":"agent_message","text":"codex synthetic reply"}}'
""",
    )
    monkeypatch.setenv("OPENCOMMOTION_LLM_PROVIDER", "codex-cli")
    monkeypatch.setenv("OPENCOMMOTION_LLM_ALLOW_FALLBACK", "false")
    monkeypatch.setenv("OPENCOMMOTION_CODEX_BIN", str(fake_codex))

    text = worker.generate_text_response("draw an orbiting globe")
    assert text == "OpenCommotion: codex synthetic reply"


def test_generate_text_response_with_openclaw_cli_provider(tmp_path, monkeypatch) -> None:
    fake_openclaw = tmp_path / "fake-openclaw"
    _write_executable(
        fake_openclaw,
        """#!/usr/bin/env bash
echo '{"payloads":[{"text":"openclaw synthetic reply"}]}'
""",
    )
    monkeypatch.setenv("OPENCOMMOTION_LLM_PROVIDER", "openclaw-cli")
    monkeypatch.setenv("OPENCOMMOTION_LLM_ALLOW_FALLBACK", "false")
    monkeypatch.setenv("OPENCOMMOTION_OPENCLAW_BIN", str(fake_openclaw))

    text = worker.generate_text_response("render a moonwalk")
    assert text == "OpenCommotion: openclaw synthetic reply"


def test_generate_text_response_with_openclaw_openai_provider(monkeypatch) -> None:
    monkeypatch.setenv("OPENCOMMOTION_LLM_PROVIDER", "openclaw-openai")
    monkeypatch.setenv("OPENCOMMOTION_LLM_ALLOW_FALLBACK", "false")
    monkeypatch.setenv("OPENCOMMOTION_OPENCLAW_OPENAI_BASE_URL", "http://provider.example/v1")
    monkeypatch.setenv("OPENCOMMOTION_OPENCLAW_OPENAI_MODEL", "model-x")

    class FakeResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict:
            return {
                "choices": [
                    {
                        "message": {
                            "content": "openclaw openai synthetic reply",
                        }
                    }
                ]
            }

    def fake_post(url, json, headers, timeout):  # noqa: ANN001, ANN202, ANN003, A002
        assert url == "http://provider.example/v1/chat/completions"
        assert json["model"] == "model-x"
        return FakeResponse()

    monkeypatch.setattr(adapters.httpx, "post", fake_post)
    text = worker.generate_text_response("show adoption chart")
    assert text == "OpenCommotion: openclaw openai synthetic reply"
