from services.protocol import ProtocolValidationError, ProtocolValidator


def test_protocol_validator_accepts_valid_brush_stroke() -> None:
    validator = ProtocolValidator()
    validator.validate(
        "types/brush_stroke_v1.schema.json",
        {
            "stroke_id": "s1",
            "kind": "spawnCharacter",
            "params": {"actor_id": "guide"},
            "timing": {"start_ms": 0, "duration_ms": 200, "easing": "linear"},
        },
    )


def test_protocol_validator_rejects_bad_brush_kind() -> None:
    validator = ProtocolValidator()
    try:
        validator.validate(
            "types/brush_stroke_v1.schema.json",
            {
                "stroke_id": "s1",
                "kind": "not-a-kind",
                "params": {},
                "timing": {"start_ms": 0, "duration_ms": 200, "easing": "linear"},
            },
        )
    except ProtocolValidationError as exc:
        assert exc.issues
        assert "kind" in exc.issues[0]["path"] or "is not one of" in exc.issues[0]["message"]
        return
    raise AssertionError("Expected ProtocolValidationError for invalid brush kind")


def test_protocol_validator_resolves_refs_for_event_schema() -> None:
    validator = ProtocolValidator()
    validator.validate(
        "events/agent_visual_brush_stroke.schema.json",
        {
            "event_type": "agent.visual.brush.stroke",
            "session_id": "sess-1",
            "turn_id": "turn-1",
            "timestamp": "2026-02-24T00:00:00Z",
            "actor": "visual",
            "payload": {
                "stroke_id": "s1",
                "kind": "spawnCharacter",
                "params": {"actor_id": "guide"},
                "timing": {"start_ms": 0, "duration_ms": 200, "easing": "linear"},
            },
        },
    )
