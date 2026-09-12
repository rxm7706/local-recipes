---
title: 'CAP-18 — one publisher: run state and savings telemetry reach the supervisor'
type: 'feature'
created: '2026-09-12'
status: 'done'
review_loop_iteration: 1
followup_review_recommended: false
baseline_revision: 'b978aa9b2aaa7cd9ba71fcef046c67216e1ae6fe'
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-run-state-one-publisher/stack.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-run-state-one-publisher/SPEC.md
  - src/shared/packages/pyforge-core/src/pyforge/core/client.py
  - src/shared/packages/pyforge-core/src/pyforge/core/assertion.py
warnings: []
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** Marshal imports `django_pyforge` zero times today, yet two supervisors write run
state only to local journals and bmad-loop `state.json`; the front door `/runs/` board cannot see
live loop or dispatch runs, and `cli/status.py` plus doctor scrape `~/.bmad-loops` for run truth.

**Approach:** Introduce exactly one publisher module (`adapters/publisher_host.py`) that shapes
records in `core/publish.py`, exposes `RunPublisherPort` in `ports/publisher.py`, and reaches
`django_pyforge.supervisor` over the host's `/stations/marshal/mcp` face via
`pyforge.core.client` + `pyforge.core.assertion` — never a direct `django_pyforge` import. Wire
both `supervisor/__main__.py` and `dispatch_supervisor/__main__.py` to call the adapter on
attach, heartbeat, and detach/completion; publish failures become journal findings, never loop
stops (mirror `_publish_run_started_event` best-effort semantics).

## Boundaries & Constraints

**Always:** Exactly one module under `pyforge/marshal/adapters/` imports `pyforge.core.client`
for publishing; `grep -r django_pyforge src/shared/packages/pyforge-marshal/src/` returns nothing;
pure record shaping stays in `core/publish.py` (AD-4, no I/O); supervisor loops continue on
publish/heartbeat/complete errors; MCP tool names are `publish_loop_run`, `heartbeat_loop_run`,
`complete_loop_run` per `stack.md`; bearer comes from `PYFORGE_IDP_BEARER_FILE` env when set,
host base from `PYFORGE_HOST` (default `http://127.0.0.1:8000`).

**Never:** Import `django_pyforge` in marshal; add a second publisher module; wrap bmad-loop in
Celery; block supervisor detach on publish failure; implement steward 49.8 host-side held-run
functions in this story (adapter must tolerate missing tools via findings until 49.8 lands).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| HAPPY_PUBLISH | Valid bearer file + host exposes MCP tools | Returns run handle; journal records publish attempt | No supervisor stop |
| NO_BEARER | `PYFORGE_IDP_BEARER_FILE` unset or unreadable | Skip publish; journal finding names missing credential | Supervisor continues |
| HOST_DOWN | Transport raises on MCP POST | Journal finding; heartbeat/complete also best-effort fail | Supervisor continues |
| HEARTBEAT | Valid handle from prior publish | MCP heartbeat succeeds or finding on failure | Tick loop continues |
| COMPLETE | Terminal detach/completion | MCP complete with status + timing payload | Detach proceeds |
| RE_MINT | Assertion near 300s TTL | `HostMintClient.emit` refreshes before MCP call | Mint failure → finding |

</intent-contract>

## Code Map

- `ports/publisher.py` — **CREATE** `RunPublisherPort` Protocol: `publish(record) -> str | None`, `heartbeat(handle) -> None`, `complete(handle, *, status, result) -> None`
- `core/publish.py` — **CREATE** pure functions: `shape_loop_publish`, `shape_dispatch_publish`, `shape_heartbeat`, `shape_complete` — station slug, story key, phase, commit_sha, run_id, harness_run_id, CAP-7 savings dict
- `adapters/publisher_host.py` — **CREATE** only `pyforge.core.client` publisher; `HostMintClient` re-mint; JSON-RPC MCP POST to `{base}/stations/marshal/mcp`; map errors to optional callback (supervisor passes journal append)
- `supervisor/__main__.py:980-1007,1010,2417,2651` — **MODIFY** call publisher on attach, each heartbeat tick, detach
- `dispatch_supervisor/__main__.py:987,1185,1295` — **MODIFY** call publisher on attach, heartbeat, completion
- `tests/unit/test_publisher.py` — **CREATE** port/adapter/core tests with injected transports
- `tests/meta/test_publisher_single_importer.py` — **CREATE** meta: one client importer, zero django_pyforge imports in marshal src
- `cli/status.py:917-1063` — **READ ONLY this story** — run-state migration to published plane deferred until 49.8 payload exists; do not regress existing reads
- `django_pyforge/supervisor.py:377-432` — **READ** best-effort model for publisher errors
- `spec-run-state-one-publisher/stack.md` — contract for MCP tool names and payload fields

## Tasks & Acceptance

**Execution:**
- `ports/publisher.py` — define `RunPublisherPort` and `PublishRecord` typed dict/dataclass — AD-11 port shape
- `core/publish.py` — pure record shaping from supervisor context (story, phase, savings from budget-usage facts)
- `adapters/publisher_host.py` — `HostPublisher` implementing port; MCP JSON-RPC helper; env config for host/bearer/mint URLs
- `supervisor/__main__.py` — instantiate adapter once per sidecar run; publish on attach; heartbeat each tick; complete on detach
- `dispatch_supervisor/__main__.py` — same pattern for dispatch attach/heartbeat/completion
- `tests/unit/test_publisher.py` — matrix rows with mock transport returning tool results or errors
- `tests/meta/test_publisher_single_importer.py` — enforce single importer + no django_pyforge

**Acceptance Criteria:**
- Given a clean marshal tree, when `grep -r django_pyforge src/shared/packages/pyforge-marshal/src/` runs, then it returns no matches
- Given the meta-test suite, when `pyforge-marshal-test` runs, then exactly one module imports `pyforge.core.client` for publishing and all publisher matrix tests pass
- Given both supervisors wired, when attach/heartbeat/detach journal entries are written locally, then the publisher adapter is invoked at each lifecycle point (provable via unit tests with mock port injected into supervisors or adapter-level integration tests)
- Given host MCP unreachable, when publish is attempted, then a journal finding is recorded and the supervisor loop does not raise or abort

## Spec Change Log

## Review Triage Log

### 2026-09-12 — Review pass
- verdicts: 12 findings — high 0, medium 4, low 3, false 2, maybe-false 3
- findings:
  - `[medium]` `[patch]` heartbeat/complete skipped assertion refresh — fixed `_ensure_assertion()` on both paths
  - `[medium]` `[patch]` dispatch complete after journal could orphan host handle — reordered complete before journal append
  - `[medium]` `[patch]` loop supervisor FsError path skipped complete — added `finally` best-effort complete
  - `[medium]` `[patch]` on_finding callback could abort publish path — wrapped in try/except in `_report`
  - `[medium]` `[patch]` no supervisor lifecycle wiring test — added `test_run_supervisor_invokes_recording_publisher_lifecycle`
  - `[medium]` `[patch]` RE_MINT on heartbeat untested — added `test_heartbeat_re_mints_when_assertion_stale`
  - `[low]` `[reject]` shape_complete unused — complete payload inline is sufficient; shape_complete reserved for future consolidation
  - `[low]` `[reject]` savings omitted on attach publish — intentional: savings on loop complete from final usage snapshot
  - `[low]` `[reject]` MRS-SUPV-010 missing narrative in findings.py — registry entry sufficient for v1
  - `[false]` `[reject]` graph_stats tuple length crash — `layer_savings_dict` already guards tuple length
  - `[false]` `[reject]` meta-test flags any client import — test scans publisher_host module specifically
  - `[maybe-false]` `[defer]` dispatch supervisor wiring test missing — defer until dispatch supervisor unit harness exists (medium unverified)
  - `[maybe-false]` `[defer]` front door `/runs/` live proof — steward 49.8 joint landing (medium unverified)
  - `[maybe-false]` `[defer]` cli/status.py published-plane reads — deferred per spec boundary until host payload live

## Auto Run Result

**Summary:** Landed marshal-side CAP-18 one publisher: `RunPublisherPort`, pure `core/publish.py` shapers, sole `HostPublisher` adapter reaching `/stations/marshal/mcp` via `pyforge.core.client` + `HostMintClient`, wired into loop and dispatch supervisors with best-effort `MRS-SUPV-010` journal findings.

**Files changed:**
- `ports/publisher.py`, `core/publish.py`, `adapters/publisher_host.py` — publisher stack (new)
- `supervisor/__main__.py`, `dispatch_supervisor/__main__.py` — lifecycle publish/heartbeat/complete
- `core/egress.py`, `core/findings.py`, `core/verdict.py` — registry + finding code
- `tests/unit/test_publisher.py`, `tests/meta/test_publisher_single_importer.py` — matrix + meta gates
- `tests/unit/test_supervisor.py` — autouse noop publisher for legacy fixtures
- This spec — story contract + run result

**Review:** 6 patches applied (assertion refresh, complete ordering, finally complete, finding callback guard, wiring test, heartbeat re-mint test). 3 rejected low/cosmetic. 3 deferred (dispatch wiring test harness, 49.8 host tools, status.py migration).

**followup_review_recommended:** false (0 high patches; 4 medium patches but converged)

**Verification:**
- `pixi run -e pyforge-marshal pyforge-marshal-test` — 7850 passed
- `grep -r django_pyforge src/shared/packages/pyforge-marshal/src/` — empty

**Residual risks:** Host MCP tools (`publish_loop_run` / `heartbeat_loop_run` / `complete_loop_run`) land with steward Story 49.8; without them publish fails gracefully. CAP-5 bearer path requires `PYFORGE_IDP_BEARER_FILE`. Ledger row remains `blocked` pending joint 49.8 landing and operator flip.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: full suite green (matches marshal-policy.toml's own `verify_commands`; the recovered 2026-09-12 landing used this exact pair — see Recovery Note below)
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: green

Additional checks (informal, not policy verify commands — kept out of the list above so MRS-GATE-011 never refuses on a byte-mismatch again, exactly as it did on the first 2026-09-12 attempt):
- `pixi run -e pyforge-marshal pyforge-marshal-test -- tests/unit/test_publisher.py tests/meta/test_publisher_single_importer.py` — expect all pass
- `grep -r django_pyforge src/shared/packages/pyforge-marshal/src/` — expect empty output

**Manual checks (if no CLI):**
- Confirm `adapters/publisher_host.py` is the sole `pyforge.core.client` import site used for publishing

## Recovery Note (2026-09-12)

This story's first dispatch attempt (run `pyforge-marshal-20260912T091844811Z-ee317554`) completed all the work above — including its own internal review pass (6 patches applied) and a self-run `pixi run -e pyforge-marshal pyforge-marshal-test` (7850 passed) — but was refused at the MRS-GATE-011 verify gate because this file's own `## Verification` **Commands:** list did not byte-match `marshal-policy.toml`'s declared `verify_commands` (missing `--frozen`, and 3 declared items against the policy's 2). The dev work itself was never at fault; the diff was preserved at `failed/33.4/changes.patch` and recovered by hand: the spec's verify-command mismatch fixed above, the preserved diff applied to a clean branch off `main`, and landed via `feat/marshal-33-4-one-publisher-run-state` after re-running the corrected commands directly.
