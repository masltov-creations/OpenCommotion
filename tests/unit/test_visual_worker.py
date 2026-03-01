import pytest
from services.agents.text.worker import LLMEngineError
from services.agents.visual.worker import generate_visual_strokes


def test_draw_box_prompt_raises_error_if_llm_is_disabled() -> None:
    with pytest.raises(LLMEngineError):
        generate_visual_strokes("draw a box")


def test_draw_unknown_prompt_raises_error() -> None:
    with pytest.raises(LLMEngineError):
        generate_visual_strokes("draw a rocket with motion")


def test_non_draw_prompt_raises_error() -> None:
    with pytest.raises(LLMEngineError):
        generate_visual_strokes("explain tcp handshake")


def test_draw_prompt_with_relative_xyz_points_raises_error() -> None:
    # This previously tested a fallback that used relative points.
    # Now it should error if the LLM isn't present to handle it.
    with pytest.raises(LLMEngineError):
        generate_visual_strokes("draw shape points 0.2,0.3,0.1 0.6,0.3,0.2 0.8,0.7,0.3 and animate")



def test_llm_visual_path_raises_error_when_provider_is_heuristic(monkeypatch) -> None:
    monkeypatch.delenv("OPENCOMMOTION_LLM_PROVIDER", raising=False)
    with pytest.raises(LLMEngineError, match="not supported"):
        generate_visual_strokes("draw a futuristic city")
