---
title: "In-process station port, no self-call"
type: "fix"
created: "2026-09-02"
status: "done"
updated: "2026-09-03"
followup_review_recommended: false
review_loop_iteration: 1
baseline_commit: "b13288d25dc8da31313df976dd8ba6383e16f74f"
baseline_revision: "b13288d25dc8da31313df976dd8ba6383e16f74f"
severity: "HIGH"
context:
  - "_bmad-output/projects/pyforge-steward/planning-artifacts/epics.md"
  - "_bmad-output/projects/pyforge-steward/planning-artifacts/research/architecture-review-pyforge-unifying-strategy-red-team-2026-09-02.md"
  - "_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-unifying-strategy/SPEC.md"
  - "_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-unifying-strategy/resilience-invariants.md"
  - "src/platform/config/settings/base.py"
  - "src/shared/packages/django-pyforge/src/django_pyforge/portals.py"
  - "src/shared/packages/pyforge-core/src/pyforge/core/dispatch.py"
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** Portals call "the host" over `httpx`; the host is the same gunicorn pool, so a
worker awaits a worker and `ATOMIC_REQUESTS = True` pins a PostgreSQL
transaction for the wait. Under load this is a self-call deadlock and latency
amplifier. Red-team **T-3**, directive **R-6**.

**Approach:** Portals call station code through an in-process port (`django-pyforge` client
→ `pyforge.core.dispatch` via the hook registry) when co-located, and over
HTTP only when `STATION_REMOTE=1`; streaming/long views are marked
`non_atomic_requests`; the import boundary is kept by importing through the
registry, never `pyforge.<station>` directly.

## Acceptance Criteria

- Given a portal view in the default profile, when it needs station data, then no HTTP request to the host's own address is made (test asserts zero loopback calls).
- Given `STATION_REMOTE=1`, when the same view runs, then it uses `pyforge.core.client` over HTTP with the assertion.
- Given the SSE / long-poll views, when inspected, then they are `non_atomic_requests` and a policy test lists them.
- Given the host import-linter, when run, then it still passes (no `pyforge.*` import under `src/platform/`).

## Boundaries & Constraints

**Always:** Write under `_bmad-output/projects/pyforge-steward/planning-artifacts/`
literally. `BMAD_ACTIVE_PROJECT=pyforge-steward` only — never `scripts/bmad-switch`.
Ledger key `43-3-in-process-station-port-no-self-call`. Host never imports `pyforge.*`. One assertion format on both paths (AD-7). Import boundary test stays green.

**Block If:** Implementation would import station packages into `src/platform/` directly, or drop `ATOMIC_REQUESTS` globally.

**Never:** A portal view that awaits its own gunicorn pool.

</intent-contract>

## Tasks

- [x] In-process port in chrome
- [x] Profile switch
- [x] Non-atomic sweep + policy test
- [x] Loopback-call test
- [x] Ledger `43-3-in-process-station-port-no-self-call` → `review` then `done` via `sprint-ledger-sync`.

## Review Triage Log

### 2026-09-03 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 2: (medium 1, low 1)
- defer: 1: (low 1)
- reject: 3: (low 3)
- addressed_findings:
  - `[medium]` `[patch]` Strengthen loopback test to forbid urllib in default profile and add ASGI invoker integration test.
  - `[low]` `[patch]` Remove duplicate API_VERSION_HEADER import in loopback test module.

## Auto Run Result

Status: done

**Summary:** Co-located portals now reach station APIs through a registered in-process ASGI invoker (`pyforge.core.station_port` + `config.station_port.asgi_invoke`) instead of HTTP loopback. `STATION_REMOTE=1` selects urllib HTTP via `PyForgeStationClient`. Long-poll views (`get_audit`, atlas `chrome_home`, `runs_board`) are `non_atomic_requests` with a policy registry test.

**Files changed:**
- `pyforge/core/station_port.py` — in-process registry + `STATION_REMOTE` profile switch
- `django_pyforge/station_port.py` — default transport bridge
- `django_pyforge/station_client.py` — auto-select in-process transport
- `django_pyforge/non_atomic.py` — policy registry + decorator
- `config/station_port.py` — host ASGI wiring (no `pyforge.*` import)
- Portal views + `UsersConfig.ready()` wiring
- Tests: loopback, non-atomic policy, pyforge-core unit

**Review:** 2 patches applied; 1 deferred (PortalClient.invoke argv dispatch stub remains for herald projection); 3 rejected as noise.

**Follow-up review:** false (score 1×medium + 1×low = 4 < 5)

**Verification:** `platform-ci-test` pytest — `test_station_port_no_loopback.py`, `test_non_atomic_views.py`, `test_no_pyforge_import.py`, `test_station_api_seam.py` (15 passed); `pyforge-core-test` `test_station_port.py` (5 passed).

**Residual risks:** `PortalClient.invoke` still uses argv projection for herald deck status rather than live CLI dispatch; acceptable for current portal scope but noted as deferred follow-up.

## Verification

`src/platform/tests` import boundary + new loopback test; chrome tests.

## Source

Red-team review: `research/architecture-review-pyforge-unifying-strategy-red-team-2026-09-02.md` (directive and finding ids in the FR/AD line of
`epics.md` Story 43.3). Sprint change proposal:
`sprint-change-proposal-2026-09-02-red-team-high.md`.
