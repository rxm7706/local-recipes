---
title: "Agent rate limits and run bounds"
type: "feature"
created: "2026-09-02"
status: "in-review"
updated: "2026-09-02"
baseline_commit: "58ee07a0"
baseline_revision: "629ee8c5ceba96dab31bac0251974880c4e821a1"
severity: "HIGH"
context:
  - "_bmad-output/projects/pyforge-steward/planning-artifacts/epics.md"
  - "_bmad-output/projects/pyforge-steward/planning-artifacts/research/architecture-review-pyforge-unifying-strategy-red-team-2026-09-02.md"
  - "_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-unifying-strategy/SPEC.md"
  - "_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-unifying-strategy/resilience-invariants.md"
  - "src/shared/packages/django-pyforge/src/django_pyforge/supervisor.py"
  - "src/shared/packages/django-pyforge/src/django_pyforge/mcp_http.py"
  - "src/shared/packages/django-pyforge/src/django_pyforge/models.py"
warnings: []
deferred:
  - "Semantic circuit breaker (>N builds/min per subject) — after telemetry exists (R-21)."
  - summary: >-
      No `celery beat` process is deployed, so `CELERY_BEAT_SCHEDULE`'s retention
      entry never fires in the cluster.
    evidence: |-
      The chart's only Celery workload is `worker-deployment.yaml`
      (`args: ["celery", "-A", "config", "worker", "-l", "info"]`); `grep -n beat`
      over `compose/compose.yml` and `deploy/charts/platform/values.yaml` returns
      nothing. `CELERY_BEAT_SCHEDULER` has named `django_celery_beat`'s
      DatabaseScheduler since before this story, with nothing running it. Mitigated
      but not closed: `manage.py prune_run_state` makes the sweep runnable by an
      operator or any external scheduler today, and the story's own test drives both
      runners. Adding a beat Deployment belongs with Story 42.4, which owns Celery's
      deployment topology (per-station queues, the `builds` pool, grace periods).
    location: >-
      src/platform/deploy/charts/platform/templates/
    severity: medium
  - summary: >-
      The station and per-subject ceilings are count-then-create, so simultaneous
      starts can overshoot by the number of racing requests.
    evidence: |-
      `enforce_run_bounds` reads `station_queue_depth` / `live_runs_for_subject`
      before `publish_start` opens its transaction; nothing serialises the two
      steps. Deliberate, and documented in `supervisor.py`'s module docstring: the
      failure the bound exists to stop is an agent loop issuing thousands of starts,
      which an off-by-a-few boundary does not restore, and making it exact needs a
      lock on a row that does not exist yet. Revisit only if a bound is ever
      repurposed as a licence/quota rather than backpressure.
    location: >-
      src/shared/packages/django-pyforge/src/django_pyforge/supervisor.py
    severity: low
  - summary: >-
      A silently-failing cache `set` leaves the bucket unwritten for one request
      before the next `get` fails closed.
    evidence: |-
      `django_redis` with `IGNORE_EXCEPTIONS` swallows a write failure into `None`,
      and `set`'s return is backend-dependent (`BaseCache.set` returns `None`
      normally), so it cannot be read as a health signal without coupling the
      limiter to one backend. The following `get` returns `None` and refuses, so the
      window is one request per subject per outage, not an open door.
    location: >-
      src/shared/packages/django-pyforge/src/django_pyforge/rate_limit.py
    severity: low
  - summary: >-
      The scoped spec-surface stamp for `spec-pyforge-unifying-strategy` is not run
      by this story.
    evidence: |-
      `.memlog.md` carries this story's surface entry, which downgrades the drift
      from `fail` to `drift-presumed: warn`, but `--write-baseline --spec
      pyforge-steward/spec-pyforge-unifying-strategy` must run from a CLEAN worktree
      after the commit lands or it bakes uncommitted working-tree bytes into the
      baseline. That spec's baseline also still lags Stories 40.1, 41.2–41.4 and
      42.1 (~60 paths), which this story neither caused nor reconciled.
    location: >-
      scripts/.spec-surface-baseline.json
    severity: low
  - summary: >-
      Nothing outside the pytest settings supplies `PYFORGE_ASSERTION_PUBLIC_KEY`
      (inherited from Story 42.1), so the limiter is unreachable in a deployed run.
    evidence: |-
      The rate limiter sits behind the transport gate, which answers 503 when no
      public key resolves. Until the AD-19 keypair Secret lands (Story 40.1
      territory), no deployed MCP call gets far enough to be counted. Recorded here
      only because it now also gates this story's AC 1; the underlying gap and its
      remedy are already tracked on `spec-42-1-mcp-transport-authorization.md`.
    location: >-
      src/platform/deploy/charts/platform/templates/_helpers.tpl
    severity: medium
---

<intent-contract>

## Intent

**Problem:** Nothing rate-limits `POST /stations/<name>/mcp` per subject. Each supervisor
`start` creates a `RunState` row and a Celery task; an agent loop fills
PostgreSQL and the broker until the broker OOMs and Channels, Celery and the bus
die together. Loop-depth caps only bus recursion. Red-team **A-6**, directive
**R-8**.

**Approach:** Token bucket per `sub` in `redis-cache` on the MCP route and on `start`;
per-station queue-depth ceiling returning 429 with `Retry-After`; a maximum of
concurrent `RUNNING` runs per `sub`; TTL/archival on `RunState`; every Celery
task tagged with `sub` so one command revokes a runaway subject.

## Acceptance Criteria

- Given one `sub` issuing more than the configured rate, when it calls the MCP route, then 429 with `Retry-After` and a structured log; other subjects are unaffected.
- Given the per-station ceiling reached, when `start` is called, then 429 and no `RunState` row is written.
- Given `MAX_RUNNING_PER_SUB` reached, when `start` is called, then 409 with the live run ids.
- Given `pyforge steward revoke --sub <id>`, when run, then queued tasks for that subject are revoked and its RUNNING rows are marked CANCELLED.
- Given `RunState` older than the retention window, when the archival task runs, then rows are pruned or archived and the count is bounded.

## Boundaries & Constraints

**Always:** Write under `_bmad-output/projects/pyforge-steward/planning-artifacts/`
literally. `BMAD_ACTIVE_PROJECT=pyforge-steward` only — never `scripts/bmad-switch`.
Ledger key `42-2-agent-rate-limits-and-run-bounds`. Host never imports `pyforge.*`. Limits live in `redis-cache` (evictable, AD-10). Numbers are settings with documented defaults.

**Block If:** Implementation would put limiter state on the broker, or gate humans and agents by client name instead of `sub`.

**Never:** An unbounded `start`. A limiter that fails open silently when the cache is down (fail closed with a loud log).

</intent-contract>

## Tasks

- [x] Limiter in chrome
- [x] Supervisor ceilings + 429/409
- [x] Revoke duty + Celery `sub` header
- [x] Retention task
- [x] Tests
- [ ] Ledger `42-2-agent-rate-limits-and-run-bounds` → `review` then `done` via `sprint-ledger-sync`.

## Verification

`src/platform/tests/test_warden_portal_audit_start_get.py` extended; new limiter tests; steward duty test.

## Dev Notes

**2026-09-02 — implementation.**

- **Limiter** — `django_pyforge/rate_limit.py`. A token bucket per `sub` per
  scope (`mcp`, `start`), keyed `pyforge:ratelimit:<scope>:<sub>` in
  `CACHES["default"]` — redis-cache in a deployed profile (AD-10), evictable,
  never the `noeviction` broker whose exhaustion the bound exists to prevent.
  Wall-clock, not monotonic, because the bucket is shared across web pods.
  **Fail-closed is the load-bearing detail:** `django_redis` runs with
  `IGNORE_EXCEPTIONS`, so a connection failure comes back as `None` rather than
  raising, and `None` is indistinguishable from a cache miss unless the read
  passes a non-`None` default — so it does, and an unanswered read is refused
  with an `ERROR` log. `consume()` never raises and never returns "allowed"
  because something broke.
- **Route** — `dispatch_station_mcp` charges the verified `sub` *after* the
  42.1 gate and before either transport is chosen, so an unverified caller
  cannot spend the allowance of a subject it merely claims. 429 carries
  `Retry-After`; `TransportRefusal` grew an optional `retry_after` and a
  `headers()` so both gates emit one refusal shape.
- **Supervisor** — three bounds ahead of the transaction, so "429 and no
  `RunState` row" is a property of ordering rather than of a rollback:
  the `start` bucket (429), the per-station live-run ceiling (429 +
  `Retry-After`), and `MAX_RUNNING_PER_SUB` (**409**, naming the live run ids —
  409 rather than 429 because the conflict is the caller's own runs and the ids
  are what it needs to wait on or revoke them). `RunBoundExceeded` carries its
  own status, so the portal face and any future face cannot drift into
  different codes for one condition.
- **Revoke** — `RunState` gained `subject` and `celery_task_id`; the task id is
  minted *before* `apply_async` so the row names a task while it is still only
  queued, which is what makes a queued task revocable at all. The message also
  carries a `sub` header. `supervisor.revoke_subject` revokes then marks rows
  `CANCELLED` (a new terminal status — deliberately not `FAILED`: conflating
  them makes "how often does this station break?" unanswerable), and reports
  `ok=False` when the broker was unreachable rather than claiming success.
  `manage.py revoke_subject` is the write; `pyforge steward revoke --sub <id>`
  is the operator grammar and shells to it, because `run_state` has one writer
  (AD-12) and `pyforge-steward` imports no Django.
- **Retention** — `prune_run_state` is two passes: age (the policy) and a hard
  row cap (the guarantee). Age alone bounds nothing, since a burst inside the
  window is exactly the shape that fills the table. Live rows are never pruned.
  Scheduled via `CELERY_BEAT_SCHEDULE`; also `manage.py prune_run_state`,
  because no `beat` process is deployed today (deferred, above).
- **CAP-9 / AD-9** — migration `0004_run_bounds` ships with Liquibase changeset
  `python-agent-platform:20`, extracted verbatim from `sqlmigrate` and registered
  in `sqlmigrate-map.yaml` + the master changelog. `python -m
  db.sqlmigrate_extraction` reports ok (15 first-party migrations). The rollback
  normalises `cancelled` → `failed` before narrowing the CHECK constraint; the
  pre-42.2 schema has no vocabulary for a revoked run, so a rollback skipping
  that step would simply fail on any estate that had used `revoke`.
- **Suite isolation** — `src/platform/conftest.py` gained an autouse cache
  clear. LocMemCache lives for the whole pytest process, so without it a
  subject's bucket spend would accumulate across tests and the suite's outcome
  would depend on collection order. Clearing keeps the *real* limiter in the
  path instead of stubbing it out.
- **Ledger not advanced**, for the same reason recorded on Story 42.1: this
  dispatch worktree has no `implementation-artifacts/` feed for
  `sprint-ledger-sync` to promote, and the tracked twin is a GENERATED file.
  That is the landing/marshal step.

**Verification run (2026-09-02).** `src/platform` suite under `platform-ci-test`
with helm on PATH and an ephemeral PostgreSQL, diffed against a detached
worktree at the `629ee8c5` baseline:

| | passed | failed | errors |
|---|---|---|---|
| baseline `629ee8c5` | 603 | 13 | 5 |
| this story | 627 | 13 | 5 |

The 13 failures and 5 errors are byte-identical sets on both sides
(redis-broker, host-board row isolation, openfeature cachebox pin, liquibase
DDL governance, transactional-DB teardown) — pre-existing and environmental.
`ruff check .` in `src/platform`: 116 errors on both sides (no delta; `mypy`
crashes constructing the Django plugin on both sides). `pyforge-steward`:
1006 passed / 1 skipped. `scripts/detectors.py --scope repo`: 230 findings at
baseline → 164 here, no new finding introduced (the drop is this spec's memlog
entry downgrading that spec's pending drift to `warn`; see the honesty note in
`.memlog.md`).

## Source

Red-team review: `research/architecture-review-pyforge-unifying-strategy-red-team-2026-09-02.md` (directive and finding ids in the FR/AD line of
`epics.md` Story 42.2). Sprint change proposal:
`sprint-change-proposal-2026-09-02-red-team-high.md`.
