from services.brush_engine.opencommotion_brush.compiler import compile_brush_batch


def test_compile_spawns_character() -> None:
    patches = compile_brush_batch(
        [
            {
                "stroke_id": "s1",
                "kind": "spawnCharacter",
                "params": {"actor_id": "guide"},
                "timing": {"start_ms": 0, "duration_ms": 100, "easing": "linear"},
            }
        ]
    )
    assert patches
    assert patches[0]["path"] == "/actors/guide"


def test_unknown_kind_generates_warning_patch() -> None:
    patches = compile_brush_batch(
        [
            {
                "stroke_id": "s2",
                "kind": "bad-kind",
                "params": {},
                "timing": {"start_ms": 0, "duration_ms": 50, "easing": "linear"},
            }
        ]
    )
    assert "Unsupported stroke kind" in patches[0]["value"]["text"]


def test_compile_fish_scene_primitives() -> None:
    patches = compile_brush_batch(
        [
            {
                "stroke_id": "render-mode",
                "kind": "setRenderMode",
                "params": {"mode": "3d"},
                "timing": {"start_ms": 0, "duration_ms": 100, "easing": "linear"},
            },
            {
                "stroke_id": "spawn-fish",
                "kind": "spawnSceneActor",
                "params": {"actor_id": "goldfish", "actor_type": "fish", "x": 300, "y": 210},
                "timing": {"start_ms": 30, "duration_ms": 100, "easing": "linear"},
            },
            {
                "stroke_id": "fx-bubble",
                "kind": "emitFx",
                "params": {"fx_id": "bubble_emitter", "seed": 11, "count": 6},
                "timing": {"start_ms": 60, "duration_ms": 500, "easing": "linear"},
            },
        ]
    )
    assert any(p["path"] == "/render/mode" and p["value"] == "3d" for p in patches)
    assert any(p["path"] == "/actors/goldfish" and p["value"]["type"] == "fish" for p in patches)
    bubble_patch = next(p for p in patches if p["path"] == "/fx/bubble_emitter")
    assert bubble_patch["value"]["type"] == "bubble_emitter"
    assert len(bubble_patch["value"]["particles"]) == 6


def test_compile_shader_validation_fallback() -> None:
    patches = compile_brush_batch(
        [
            {
                "stroke_id": "mat-bad",
                "kind": "applyMaterialFx",
                "params": {
                    "material_id": "fish_bowl_glass",
                    "shader_id": "glass_refraction_like",
                    "uniforms": {"ior": 9.0},
                },
                "timing": {"start_ms": 100, "duration_ms": 100, "easing": "linear"},
            }
        ]
    )
    material = next(p for p in patches if p["path"] == "/materials/fish_bowl_glass")
    assert material["value"]["fallback"] is True
    assert "reason" in material["value"]
    warning = next(p for p in patches if p["path"] == "/annotations/-")
    assert "Material fallback" in warning["value"]["text"]


def test_compile_market_growth_chart_hardening() -> None:
    patches = compile_brush_batch(
        [
            {
                "stroke_id": "line-growth",
                "kind": "drawAdoptionCurve",
                "params": {
                    "trend": "growth",
                    "points": [[100, 20], [0, 92], [60, 80], [40, 86]],
                },
                "timing": {"start_ms": 200, "duration_ms": 1400, "easing": "linear"},
            },
            {
                "stroke_id": "pie-growth",
                "kind": "drawPieSaturation",
                "params": {
                    "slices": [
                        {"label": "Core", "value": 4},
                        {"label": "Attach", "value": 4},
                        {"label": "Expansion", "value": 2},
                    ]
                },
                "timing": {"start_ms": 300, "duration_ms": 1200, "easing": "linear"},
            },
            {
                "stroke_id": "attach-bars",
                "kind": "drawSegmentedAttachBars",
                "params": {
                    "segments": [
                        {"label": "Enterprise", "target": 120, "color": "#22d3ee"},
                        {"label": "SMB", "target": -8, "color": "#f59e0b"},
                    ]
                },
                "timing": {"start_ms": 500, "duration_ms": 1800, "easing": "linear"},
            },
        ]
    )
    line = next(p for p in patches if p["path"] == "/charts/adoption_curve")["value"]
    assert line["points"][0][0] == 0.0
    assert line["points"][-1][0] == 100.0
    assert all(line["points"][idx + 1][1] <= line["points"][idx][1] for idx in range(len(line["points"]) - 1))
    assert line["duration_ms"] == 1400

    pie = next(p for p in patches if p["path"] == "/charts/saturation_pie")["value"]
    assert sum(int(row["value"]) for row in pie["slices"]) == 100

    segmented = next(p for p in patches if p["path"] == "/charts/segmented_attach")["value"]
    assert segmented["segments"][0]["target"] == 100.0
    assert segmented["segments"][1]["target"] == 0.0


def test_compile_lyrics_track_generates_words_path() -> None:
    patches = compile_brush_batch(
        [
            {
                "stroke_id": "lyrics",
                "kind": "setLyricsTrack",
                "params": {"words": ["The", "cow", "jumps"], "start_ms": 300, "step_ms": 250},
                "timing": {"start_ms": 280, "duration_ms": 1200, "easing": "linear"},
            }
        ]
    )
    lyric_patch = next(p for p in patches if p["path"] == "/lyrics/words")
    assert lyric_patch["value"]["items"][0]["text"] == "The"
    assert lyric_patch["value"]["items"][1]["at_ms"] == 550


def test_compile_run_screen_script_rect_op_creates_rect_actor() -> None:
    patches = compile_brush_batch(
        [
            {
                "stroke_id": "script-rect",
                "kind": "runScreenScript",
                "params": {
                    "program": {
                        "commands": [
                            {
                                "op": "rect",
                                "id": "house_walls",
                                "point": [270, 168],
                                "width": 180,
                                "height": 130,
                                "fill": "#f59e0b",
                                "stroke": "#e2e8f0",
                                "line_width": 2,
                            }
                        ]
                    }
                },
                "timing": {"start_ms": 0, "duration_ms": 1000, "easing": "linear"},
            }
        ]
    )
    actor = next(p for p in patches if p["path"] == "/actors/house_walls")
    assert actor["value"]["type"] == "rect"
    assert actor["value"]["x"] == 270
    assert actor["value"]["y"] == 168
    assert actor["value"]["style"]["width"] == 180
    assert actor["value"]["style"]["height"] == 130
    assert actor["value"]["style"]["fill"] == "#f59e0b"


def test_compile_run_screen_script_ellipse_op_creates_ellipse_actor() -> None:
    patches = compile_brush_batch(
        [
            {
                "stroke_id": "script-ellipse",
                "kind": "runScreenScript",
                "params": {
                    "program": {
                        "commands": [
                            {
                                "op": "ellipse",
                                "id": "planet_ring",
                                "point": [360, 180],
                                "rx": 92,
                                "ry": 22,
                                "fill": "none",
                                "stroke": "#f59e0b",
                                "line_width": 4,
                            }
                        ]
                    }
                },
                "timing": {"start_ms": 0, "duration_ms": 1000, "easing": "linear"},
            }
        ]
    )
    actor = next(p for p in patches if p["path"] == "/actors/planet_ring")
    assert actor["value"]["type"] == "ellipse"
    assert actor["value"]["x"] == 360
    assert actor["value"]["y"] == 180
    assert actor["value"]["style"]["rx"] == 92
    assert actor["value"]["style"]["ry"] == 22
    assert actor["value"]["style"]["fill"] == "none"   # ring outline preserved


def test_compile_run_screen_script_text_op_creates_text_actor() -> None:
    patches = compile_brush_batch(
        [
            {
                "stroke_id": "script-text",
                "kind": "runScreenScript",
                "params": {
                    "program": {
                        "commands": [
                            {
                                "op": "text",
                                "id": "label_title",
                                "point": [360, 50],
                                "text": "Hello OpenCommotion",
                                "fill": "#f8fafc",
                                "font_size": 24,
                            }
                        ]
                    }
                },
                "timing": {"start_ms": 0, "duration_ms": 1000, "easing": "linear"},
            }
        ]
    )
    actor = next(p for p in patches if p["path"] == "/actors/label_title")
    assert actor["value"]["type"] == "text"
    assert actor["value"]["x"] == 360
    assert actor["value"]["y"] == 50
    assert actor["value"]["style"]["text"] == "Hello OpenCommotion"
    assert actor["value"]["style"]["font_size"] == 24
    assert actor["value"]["style"]["fill"] == "#f8fafc"


def test_compile_run_screen_script_generates_primitives_and_motion() -> None:
    patches = compile_brush_batch(
        [
            {
                "stroke_id": "script",
                "kind": "runScreenScript",
                "params": {
                    "program": {
                        "commands": [
                            {
                                "op": "polygon",
                                "id": "shape_1",
                                "relative": True,
                                "points": [[0.2, 0.2, 0.1], [0.5, 0.2, 0.2], [0.4, 0.5, 0.3]],
                                "fill": "#22d3ee",
                            },
                            {
                                "op": "move",
                                "target_id": "shape_1",
                                "relative": True,
                                "duration_ms": 2800,
                                "loop": True,
                                "path_points": [[0.2, 0.2, 0.1], [0.4, 0.35, 0.2], [0.2, 0.2, 0.1]],
                            },
                        ]
                    }
                },
                "timing": {"start_ms": 100, "duration_ms": 3200, "easing": "linear"},
            }
        ]
    )
    polygon_patch = next(p for p in patches if p["path"] == "/actors/shape_1")
    assert polygon_patch["value"]["type"] == "polygon"
    points = polygon_patch["value"]["style"]["points"]
    assert points[0][0] == 144.0  # 0.2 * 720
    assert points[0][1] == 72.0   # 0.2 * 360
    motion_patch = next(p for p in patches if p["path"] == "/actors/shape_1/motion")
    assert motion_patch["value"]["loop"] is True
    assert len(motion_patch["value"]["path_points"]) == 3
