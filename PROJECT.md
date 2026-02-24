Project: OpenCommotion

Updated: 2026-02-24

Status:
- Closeout implementation: complete per `docs/CLOSEOUT_PLAN.md`
- Validation gates: passing locally (`make test-complete`)
- Fresh agent-consumer E2E proof: passing (`make fresh-agent-e2e`)

Objective:
- Build a local-first, open-source visual computing platform with synchronized text, voice, and visual agent outputs.
- Enable reusable visual artifact memory with smart save and fast recall.

Implemented system:
- Gateway (`services/gateway/app/main.py`)
  - REST ingress + websocket event fanout
  - Schema validation and stable error envelopes
  - Voice, orchestrate, brush compile, and artifact lifecycle endpoints
- Orchestrator (`services/orchestrator/app/main.py`)
  - Multi-channel turn assembly (text + voice + visual strokes)
  - Timeline metadata composition
- Brush engine (`services/brush_engine/opencommotion_brush/compiler.py`)
  - Deterministic intent-to-patch compilation
- Artifact registry (`services/artifact_registry/opencommotion_artifacts/registry.py`)
  - SQLite index + bundle manifests
  - Lexical, semantic, and hybrid recall
  - Pin/archive lifecycle support
- UI runtime (`apps/ui/src/App.tsx`, `apps/ui/src/runtime/sceneRuntime.ts`)
  - Realtime websocket ingestion
  - Patch-driven scene construction and playback controls
  - Voice input upload + transcript-assisted turn flow
- Protocol validation (`services/protocol/schema_validation.py`)
  - Schema guardrails for strokes, patches, events, and artifact bundles

Current voice engine behavior:
- STT: policy-driven engine routing (`auto`/`faster-whisper`/`vosk`/`text-fallback`) with strict production guardrails (`services/agents/voice/stt/worker.py`)
- TTS: policy-driven engine routing (`auto`/`piper`/`espeak`/`tone-fallback`) with strict production guardrails (`services/agents/voice/tts/worker.py`)
- Voice preflight and runtime capabilities:
  - `GET /v1/voice/capabilities`
  - `make voice-preflight`

Validation coverage:
- Unit tests:
  - `tests/unit/test_brush_compiler.py`
  - `tests/unit/test_protocol_validation.py`
- Integration tests:
  - `tests/integration/test_full_e2e_flow.py`
  - `tests/integration/test_gateway_contracts.py`
  - `tests/integration/test_security_baseline.py`
  - `tests/integration/test_performance_thresholds.py`
  - `tests/integration/test_gateway_health.py`
  - `tests/integration/test_orchestrator_health.py`
- Browser E2E:
  - `tests/e2e/ui-flow.spec.ts`

Gate commands:
- `make test-all`
- `make test-e2e`
- `make security-checks`
- `make perf-checks`
- `make test-complete`
- `make fresh-agent-e2e`
- `make voice-preflight`

Execution and release docs:
- `README.md`
- `docs/AGENT_CONNECTION.md`
- `docs/USAGE_PATTERNS.md`
- `docs/ARCHITECTURE.md`
- `docs/CLOSEOUT_PLAN.md`
- `RELEASE.md`
- `CONTRIBUTING.md`

Parallel agent assets:
- Agent specs: `agents/*.json`
- Skill scaffolds: `agents/scaffolds/`
- Coordination templates: `agents/scaffolds/templates/`
- Workflow DAGs:
  - `runtime/orchestrator/workflow_opencommotion_v1.json`
  - `runtime/orchestrator/workflow_opencommotion_v2_closeout.json`

Open maintenance item:
- If you require a specific high-fidelity STT/TTS backend in production, install and configure those models/binaries explicitly (strict mode enforces this at runtime).
