# OpenCommotion

OpenCommotion is a local-first orchestration runtime for synchronized text, voice, and visual patch playback.
Prompt in, animated response out.

## 1) Install and run (no `make` required)

Prereqs:
- Python 3.11+
- Node.js 20+
- npm

```bash
python3 scripts/opencommotion.py install
python3 scripts/opencommotion.py setup
python3 scripts/opencommotion.py run
```

Open:
- UI: `http://127.0.0.1:8000`
- Gateway docs: `http://127.0.0.1:8000/docs`
- Orchestrator docs: `http://127.0.0.1:8001/docs`

Stop:

```bash
python3 scripts/opencommotion.py down
```

## 2) Runtime auth defaults

Default `.env.example` uses API-key mode:
- `OPENCOMMOTION_AUTH_MODE=api-key`
- `OPENCOMMOTION_API_KEYS=dev-opencommotion-key`

HTTP clients should send:
- `x-api-key: dev-opencommotion-key` (or your configured key)

WebSocket clients should use:
- `ws://127.0.0.1:8000/v1/events/ws?api_key=<key>`

## 3) Quick checks

```bash
python3 scripts/opencommotion.py status
python3 scripts/opencommotion.py preflight
python3 scripts/opencommotion.py doctor
```

## 4) Use the UI end-to-end

In the UI:
1. Use **Setup Wizard** (LLM/voice/auth).
2. Click **Validate Setup** then **Save Setup**.
3. Run a turn with **Run Turn**.
4. Optional voice input via **Transcribe Audio**.
5. Save/search artifacts.
6. Use **Agent Run Manager** to create runs, enqueue prompts, and control `run_once|pause|resume|stop|drain`.

## 5) Agent/client usage

### Robust default client

```bash
. .venv/bin/activate
python3 scripts/agent_examples/robust_turn_client.py \
  --session demo-1 \
  --prompt "moonwalk adoption chart with synchronized narration"
```

### Codex/OpenClaw provider examples

```bash
. .venv/bin/activate
python3 scripts/agent_examples/codex_cli_turn_client.py
python3 scripts/agent_examples/openclaw_cli_turn_client.py
python3 scripts/agent_examples/openclaw_openai_turn_client.py --base-url http://127.0.0.1:8002/v1
```

### Baseline REST + WS example

```bash
. .venv/bin/activate
python3 scripts/agent_examples/rest_ws_agent_client.py --session demo-2 --prompt "ufo landing with pie chart"
```

## 6) LLM provider modes

`OPENCOMMOTION_LLM_PROVIDER` supports:
- `heuristic`
- `ollama`
- `openai-compatible`
- `codex-cli`
- `openclaw-cli`
- `openclaw-openai`

Capabilities are exposed via:
- `GET /v1/runtime/capabilities`

## 7) Voice engine modes (hybrid local + cloud)

STT:
- `auto|faster-whisper|vosk|openai-compatible|text-fallback`

TTS:
- `auto|piper|espeak|openai-compatible|tone-fallback`

Production strict mode:
- `OPENCOMMOTION_VOICE_REQUIRE_REAL_ENGINES=true`

Voice capabilities:
- `GET /v1/voice/capabilities`

## 8) New control/setup APIs

- `GET /v1/setup/state`
- `POST /v1/setup/validate`
- `POST /v1/setup/state`
- `POST /v1/agent-runs`
- `GET /v1/agent-runs`
- `GET /v1/agent-runs/{run_id}`
- `POST /v1/agent-runs/{run_id}/enqueue`
- `POST /v1/agent-runs/{run_id}/control`

WebSocket lifecycle events:
- `agent.run.state`
- `agent.turn.started`
- `agent.turn.completed`
- `agent.turn.failed`

## 9) Production deployment (Compose on VM)

Artifacts included:
- `docker-compose.prod.yml`
- `docker/Dockerfile.gateway`
- `docker/Dockerfile.orchestrator`
- `deploy/nginx/opencommotion.conf`
- `deploy/prometheus/*`
- `deploy/grafana/*`

Deploy:
1. Copy `.env.example` to `.env` and set production values.
2. Place TLS certs in `deploy/nginx/certs/` (`fullchain.pem`, `privkey.pem`).
3. Run `docker compose -f docker-compose.prod.yml up -d --build`.

Observability:
- Prometheus: `http://<host>:9090`
- Grafana: `http://<host>:3000` (default `admin/admin`)

## 10) Backup and restore

```bash
bash scripts/backup_runtime.sh
bash scripts/restore_runtime.sh <backup-tar.gz>
```

Backed up:
- `data/artifacts/artifacts.db`
- `data/artifacts/bundles/`
- `runtime/agent-runs/agent_manager.db`

## 11) Test gates

```bash
python3 scripts/opencommotion.py test
python3 scripts/opencommotion.py test-ui
python3 scripts/opencommotion.py test-e2e
python3 scripts/opencommotion.py test-complete
python3 scripts/opencommotion.py fresh-agent-e2e
```

## 12) Where to customize

- Gateway APIs and run manager wiring: `services/gateway/app/main.py`
- Orchestrator: `services/orchestrator/app/main.py`
- LLM adapters: `services/agents/text/adapters.py`
- Voice engines: `services/agents/voice/stt/worker.py`, `services/agents/voice/tts/worker.py`
- UI runtime and wizard: `apps/ui/src/App.tsx`

## 13) Docs

- Agent connection guide: `docs/AGENT_CONNECTION.md`
- Usage patterns: `docs/USAGE_PATTERNS.md`
- Architecture: `docs/ARCHITECTURE.md`
- Active project plan/status: `PROJECT.md`
- Release runbook: `RELEASE.md`
