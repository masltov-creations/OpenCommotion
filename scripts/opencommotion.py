#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]


def _venv_python() -> str:
    candidate = ROOT / ".venv" / "bin" / "python"
    if candidate.exists():
        return str(candidate)
    return sys.executable


def _env_with_pythonpath() -> dict[str, str]:
    env = os.environ.copy()
    root = str(ROOT)
    current = env.get("PYTHONPATH", "").strip()
    if current:
        parts = [part for part in current.split(":") if part]
        if root not in parts:
            env["PYTHONPATH"] = f"{root}:{current}"
    else:
        env["PYTHONPATH"] = root
    return env


def _run(command: list[str]) -> int:
    completed = subprocess.run(
        command,
        cwd=str(ROOT),
        check=False,
        env=_env_with_pythonpath(),
    )
    return int(completed.returncode)


def cmd_install() -> int:
    return _run(["bash", "scripts/install_local.sh"])


def cmd_setup() -> int:
    return _run([_venv_python(), "scripts/setup_wizard.py"])


def cmd_run() -> int:
    return _run(["bash", "scripts/dev_up.sh", "--ui-mode", "dist"])


def cmd_dev() -> int:
    return _run(["bash", "scripts/dev_up.sh", "--ui-mode", "dev"])


def cmd_down() -> int:
    return _run(["bash", "scripts/dev_down.sh"])


def cmd_preflight() -> int:
    return _run([_venv_python(), "scripts/voice_preflight.py"])


def cmd_test() -> int:
    return _run(
        [
            _venv_python(),
            "-m",
            "pytest",
            "-q",
            "-s",
            "--capture=no",
            "tests/unit",
            "tests/integration",
        ]
    )


def cmd_test_ui() -> int:
    return _run(["npm", "run", "ui:test"])


def cmd_test_e2e() -> int:
    return _run(["bash", "-lc", "set -euo pipefail; bash scripts/dev_up.sh --ui-mode dev; trap 'bash scripts/dev_down.sh' EXIT; PW_LIB_DIR=\"$(bash scripts/ensure_playwright_libs.sh)\"; for i in $(seq 1 30); do curl -fsS http://127.0.0.1:8000/health >/dev/null && curl -fsS http://127.0.0.1:8001/health >/dev/null && break; sleep 1; done; LD_LIBRARY_PATH=\"$PW_LIB_DIR:${LD_LIBRARY_PATH:-}\" npm run e2e"])


def cmd_test_complete() -> int:
    sequence = [
        ("test", cmd_test),
        ("test-ui", cmd_test_ui),
        ("test-e2e", cmd_test_e2e),
        ("security", lambda: _run(["bash", "-lc", ". .venv/bin/activate && python -m pip check && python -m pip install -q pip-audit && pip-audit -r requirements.txt --no-deps --disable-pip --progress-spinner off --timeout 10 && PYTHONPATH=$(pwd) pytest -q -s --capture=no tests/integration/test_security_baseline.py && npm audit --audit-level=high"])),
        ("perf", lambda: _run(["bash", "-lc", ". .venv/bin/activate && PYTHONPATH=$(pwd) pytest -q -s --capture=no tests/integration/test_performance_thresholds.py && npm --workspace @opencommotion/ui run test -- src/runtime/sceneRuntime.test.ts"])),
    ]
    for _, fn in sequence:
        code = fn()
        if code != 0:
            return code
    return 0


def cmd_fresh_agent_e2e() -> int:
    return _run(["bash", "scripts/fresh_agent_consumer_e2e.sh"])


def _tool_exists(name: str) -> bool:
    return shutil.which(name) is not None


def cmd_doctor() -> int:
    checks: list[tuple[str, bool, str]] = []
    checks.append(("python3", _tool_exists("python3"), "required"))
    checks.append(("node", _tool_exists("node"), "required for UI dev/test"))
    checks.append(("npm", _tool_exists("npm"), "required for UI dev/test"))
    checks.append(("codex", _tool_exists("codex"), "recommended for codex-cli provider"))
    checks.append(("openclaw", _tool_exists("openclaw"), "recommended for openclaw-cli provider"))
    checks.append(("espeak/espeak-ng", _tool_exists("espeak") or _tool_exists("espeak-ng"), "optional local TTS"))
    checks.append(("piper", _tool_exists("piper"), "optional high-quality local TTS"))

    failures = 0
    for label, ok, note in checks:
        state = "ok" if ok else "missing"
        print(f"{label:15} {state:7} {note}")
        if label in {"python3"} and not ok:
            failures += 1

    print("\nvoice preflight:")
    preflight_code = cmd_preflight()
    if preflight_code != 0:
        failures += 1

    print("\nservice status:")
    status_code = cmd_status()
    if status_code != 0:
        print("stack not running (this is okay if you have not started it yet)")
    return 1 if failures else 0


def cmd_quickstart() -> int:
    sequence = [
        ("install", cmd_install),
        ("setup", cmd_setup),
        ("run", cmd_run),
        ("status", cmd_status),
    ]
    for _, fn in sequence:
        code = fn()
        if code != 0:
            return code
    return 0


def _check_url(url: str) -> tuple[bool, str]:
    try:
        with urlopen(url, timeout=2) as response:
            return True, f"{response.status}"
    except URLError as exc:
        return False, str(exc.reason)
    except Exception as exc:  # noqa: BLE001
        return False, str(exc)


def cmd_status() -> int:
    checks = [
        ("gateway", "http://127.0.0.1:8000/health"),
        ("orchestrator", "http://127.0.0.1:8001/health"),
        ("ui", "http://127.0.0.1:8000/"),
    ]

    failures = 0
    for label, url in checks:
        ok, detail = _check_url(url)
        state = "ok" if ok else "down"
        print(f"{label:13} {state:4} {url} ({detail})")
        if not ok:
            failures += 1
    return 0 if failures == 0 else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="opencommotion",
        description="OpenCommotion no-make CLI.",
    )
    parser.add_argument(
        "command",
        choices=[
            "install",
            "setup",
            "run",
            "dev",
            "down",
            "preflight",
            "status",
            "test",
            "test-ui",
            "test-e2e",
            "test-complete",
            "fresh-agent-e2e",
            "doctor",
            "quickstart",
        ],
        help="Command to execute",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    command = args.command
    if command == "install":
        return cmd_install()
    if command == "setup":
        return cmd_setup()
    if command == "run":
        return cmd_run()
    if command == "dev":
        return cmd_dev()
    if command == "down":
        return cmd_down()
    if command == "preflight":
        return cmd_preflight()
    if command == "status":
        return cmd_status()
    if command == "test":
        return cmd_test()
    if command == "test-ui":
        return cmd_test_ui()
    if command == "test-e2e":
        return cmd_test_e2e()
    if command == "test-complete":
        return cmd_test_complete()
    if command == "fresh-agent-e2e":
        return cmd_fresh_agent_e2e()
    if command == "doctor":
        return cmd_doctor()
    if command == "quickstart":
        return cmd_quickstart()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
