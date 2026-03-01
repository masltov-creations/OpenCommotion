from fastapi.testclient import TestClient

from services.brush_engine.opencommotion_brush.compiler import compile_brush_batch
from services.orchestrator.app.main import app


def test_orchestrate_response_shape() -> None:
    c = TestClient(app)
    res = c.post('/v1/orchestrate', json={'session_id': 't1', 'prompt': 'moonwalk chart'})
    assert res.status_code == 200
    payload = res.json()
    assert 'text' in payload
    assert 'visual_strokes' in payload
    assert 'voice' in payload
    assert 'timeline' in payload


def test_orchestrate_fish_and_bubble_prompt_raises_503_when_llm_unavailable() -> None:
    c = TestClient(app)
    res = c.post(
        "/v1/orchestrate",
        json={
            "session_id": "fish-script",
            "prompt": "fish swimming in a bowl with bubbles",
        },
    )
    assert res.status_code == 503
    assert "llm_engine_unavailable" in res.json()["detail"]["error"]


def test_orchestrate_draw_box_prompt_raises_503_when_llm_unavailable() -> None:
    c = TestClient(app)
    res = c.post(
        "/v1/orchestrate",
        json={
            "session_id": "shape-box",
            "prompt": "draw a box",
        },
    )
    assert res.status_code == 503


def test_orchestrate_draw_fish_prompt_raises_503_when_llm_unavailable() -> None:
    c = TestClient(app)
    res = c.post(
        "/v1/orchestrate",
        json={
            "session_id": "shape-fish",
            "prompt": "draw a fish",
        },
    )
    assert res.status_code == 503


def test_orchestrate_draw_unknown_prompt_raises_503_when_llm_unavailable() -> None:
    c = TestClient(app)
    res = c.post(
        "/v1/orchestrate",
        json={
            "session_id": "shape-rocket",
            "prompt": "draw a rocket with motion",
        },
    )
    assert res.status_code == 503
