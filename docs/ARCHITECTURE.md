# OpenCommotion Architecture (Bootstrapped)

## Core Services

- Gateway: API ingress + schema validation + WebSocket event fanout
- Orchestrator: multi-agent turn planning and timeline merging
- Agent Run Manager: durable autonomous run queue + control loop (`run_once|pause|resume|stop|drain`)
- Brush Engine: helper intents to deterministic scene patches
- Artifact Registry: local artifact memory (SQLite + bundles + semantic embeddings)
- UI Runtime: patch-driven visual stage and timeline playback
- Security + Setup: API-key/network-trust auth middleware + runtime setup APIs
- Observability: Prometheus metrics endpoints + Grafana dashboards

## Real-Time Flow

1. User sends typed/voice request.
2. Gateway creates turn envelope.
3. Orchestrator delegates to text, voice, and visual workers.
4. Visual worker emits brush intents.
5. Brush engine compiles intents to `ScenePatchV1`.
6. Gateway validates patch/event contracts before fanout.
7. UI applies patches and syncs with text/voice events.
8. Registry stores favored artifacts for lexical + semantic recall.
9. Optional run manager executes queued prompts and emits lifecycle events (`agent.run.state`, `agent.turn.*`).
