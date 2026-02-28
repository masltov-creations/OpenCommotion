Project: OpenCommotion

Updated: 2026-02-28

Current status:
- Overall project status: Streams E/F/G complete — no active stream
- Stream E status: complete
- Stream F status: complete
- Stream G status: complete (committed cbe9b12)

Latest verification evidence:
- `python -m pytest --tb=no -q` → 130 passed
- `python scripts/opencommotion.py test-complete` (pass)
- `python scripts/check_project_plan_sync.py` (pass)
- `python scripts/prompt_compat_probe.py --inprocess` (pass, `required_failures=0`)
- `python scripts/prompt_compat_probe.py` against live local services (pass, `required_failures=0`)
- `python scripts/opencommotion.py fresh-agent-e2e` (pass)

Progress checklist:
- [x] V2 gateway/orchestrator prompt-context plumbing stabilized
- [x] Agent runtime manager concurrency hardening and recovery tests
- [x] Forced-progress narration guard and follow-up render reuse behavior
- [x] Runtime UI dist move to untracked path (`runtime/ui-dist`) to avoid pull conflicts
- [x] Pull/update flow hardened for generated dist churn (`opencommotion update` path)
- [x] Full automated verification gate on this branch (`test-complete`)
- [x] Stream E closeout and synchronization checks
- [x] Prompt probe bug-candidate remediation (4 required scenarios closed)
- [x] Final production readiness sign-off for Streams E/F scope
- [x] Stream G — hard-delete all pre-canned visual scenes (fish, balls, lines, legacy env-gated blocks)

Active tasks:
- None. All streams complete.

Change log:
- 2026-02-27: Closed Windows `test-complete` blockers by fixing npm resolution and replacing bash-only orchestration paths with Windows-safe execution.
- 2026-02-27: Stream E fully passed (`test`, `ui:test`, `e2e`, security, perf).
- 2026-02-27: Started Stream F governance; plan-sync check passed and prompt probe surfaced 4 required bug candidates for remediation.
- 2026-02-27: Completed Stream F prompt-probe remediation by restoring required template scene routing defaults; prompt compatibility probe now returns `required_failures=0`.
- 2026-02-27: Completed live-stack prompt compatibility probe with `required_failures=0`, closing Stream E and Stream F scope.
- 2026-02-28: Stream G complete (`cbe9b12`) — hard-deleted all pre-canned visual scenes (fish, bouncing balls, line-composition, legacy env-gated blocks). All related tests removed/renamed. 130 passing.
