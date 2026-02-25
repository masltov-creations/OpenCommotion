from __future__ import annotations

from prometheus_client import CONTENT_TYPE_LATEST, Counter, Gauge, Histogram, generate_latest

REQUEST_COUNTER = Counter(
    "opencommotion_http_requests_total",
    "Total HTTP requests",
    ["method", "path", "status"],
)

REQUEST_LATENCY = Histogram(
    "opencommotion_http_request_latency_seconds",
    "HTTP request latency seconds",
    ["method", "path"],
    buckets=(0.01, 0.03, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
)

ORCHESTRATE_LATENCY = Histogram(
    "opencommotion_orchestrate_latency_seconds",
    "Orchestrate end-to-end latency seconds",
    ["source"],
    buckets=(0.05, 0.1, 0.2, 0.5, 1.0, 2.5, 5.0, 10.0, 20.0),
)

PROVIDER_ERRORS = Counter(
    "opencommotion_provider_errors_total",
    "Provider error counts by provider/type",
    ["provider", "error_type"],
)

RUN_QUEUE_DEPTH = Gauge(
    "opencommotion_agent_run_queue_depth",
    "Queued prompts per run",
    ["run_id"],
)

RUN_STATUS = Gauge(
    "opencommotion_agent_run_status",
    "Agent run status as numeric enum (idle=0,running=1,paused=2,stopped=3,error=4)",
    ["run_id"],
)


def record_http(method: str, path: str, status_code: int, duration_s: float) -> None:
    status = str(status_code)
    REQUEST_COUNTER.labels(method=method, path=path, status=status).inc()
    REQUEST_LATENCY.labels(method=method, path=path).observe(duration_s)


def record_orchestrate(duration_s: float, source: str) -> None:
    ORCHESTRATE_LATENCY.labels(source=source).observe(duration_s)


def record_provider_error(provider: str, error_type: str) -> None:
    PROVIDER_ERRORS.labels(provider=provider, error_type=error_type).inc()


def set_run_metrics(run_id: str, queued: int, status: str) -> None:
    RUN_QUEUE_DEPTH.labels(run_id=run_id).set(float(max(queued, 0)))
    mapping = {
        "idle": 0.0,
        "running": 1.0,
        "paused": 2.0,
        "stopped": 3.0,
        "error": 4.0,
    }
    RUN_STATUS.labels(run_id=run_id).set(mapping.get(status, 9.0))


def metrics_response() -> tuple[bytes, str]:
    return generate_latest(), CONTENT_TYPE_LATEST

