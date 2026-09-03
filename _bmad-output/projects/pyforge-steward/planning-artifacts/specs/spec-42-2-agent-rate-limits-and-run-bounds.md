---
title: "Agent rate limits and run bounds"
type: "feature"
created: "2026-09-02"
status: "done"
updated: "2026-09-02"
baseline_commit: "58ee07a0"
baseline_revision: "629ee8c5ceba96dab31bac0251974880c4e821a1"
followup_review_recommended: true
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
      `test_mcp_start_audit_returns_handle` leaks a committed live `RunState` row
      per run, which `MAX_RUNNING_PER_SUB` now counts.
    evidence: |-
      Found during the review pass. `TestClient` drives the app in a worker thread
      whose connection is in autocommit, so a row the tool creates is committed
      OUTSIDE the test transaction and survives rollback — the leak predates this
      story (subject `agent-10-2`, one row per run). Harmless until now; with the
      42.2 ceilings in place, five `--reuse-db` runs against the same database
      exhaust that subject's allowance and the sixth run reds a pre-existing test.
      CI is unaffected (a fresh PostgreSQL service per job), so the exposure is
      repeated local runs without `--create-db`. This story's own MCP tests are
      immune by construction (`_fresh_subject`), which is why they were written
      that way rather than seeding a fixed subject.
    location: >-
      src/platform/tests/test_warden_portal_audit_start_get.py
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
  - summary: >-
      `enforce_run_bounds` spends a `start` token before it checks either
      ceiling, so a subject parked at a ceiling burns its rate allowance on
      refusals.
    evidence: |-
      Raised independently by three review layers. After ~30 refused attempts in
      a minute the caller receives 429 `rate limited` instead of the 409 that
      names its live run ids — the response AC 3 exists to deliver, and the one
      the caller needs in order to wait on or revoke its own runs. Kept as-is
      because the bucket is the cheap cache check standing in front of two
      indexed COUNT queries: checking ceilings first would let an unbounded
      caller drive unbounded database work, which is the failure this story
      exists to stop. Revisit if the 409 path ever becomes the common case.
    location: >-
      src/shared/packages/django-pyforge/src/django_pyforge/supervisor.py
    severity: low
  - summary: >-
      The token bucket is a non-atomic read-modify-write, so concurrent requests
      across web pods lose updates and the effective ceiling exceeds `burst`.
    evidence: |-
      `consume()` does `store.get` -> compute -> `store.set` with no `INCR`, no
      CAS and no Lua script. N simultaneous requests read the same token count
      and the last write wins. Same class as the documented count-then-create
      race on the ceilings, and tolerable for the same reason — an agent loop
      issuing thousands of calls is still stopped, and a boundary off by the
      concurrency count does not restore that failure. Recorded because the
      module's docstring argues its other properties carefully and is silent on
      this one. Wall clock compounds it: a pod with a fast clock mints tokens,
      and only backwards skew is guarded (`max(0.0, moment - updated_at)`).
    location: >-
      src/shared/packages/django-pyforge/src/django_pyforge/rate_limit.py
    severity: medium
  - summary: >-
      Migration 0004 adds `subject` without backfilling it, so every pre-existing
      run counts against nobody's ceiling and cannot be revoked by subject.
    evidence: |-
      `McpHandle.subject` already carries the value, so a `RunPython` backfill
      joining `run_state` to `mcp_handles` would be mechanical. Left out because
      it is a data migration over an estate whose row count is unknown, and
      because the safe guard landed instead: `revoke_subject` now refuses an
      empty subject, so the `subject=""` cohort cannot be cancelled wholesale by
      accident. Until backfilled, those rows are invisible to
      `MAX_RUNNING_PER_SUB` and unreachable by `steward revoke --sub`.
    location: >-
      src/shared/packages/django-pyforge/src/django_pyforge/migrations/0004_run_bounds.py
    severity: medium
  - summary: >-
      Neither the Helm chart nor compose exposes the eight new tunables, so
      "tunable without a code change" holds only for whoever can set pod env.
    evidence: |-
      `grep -rn "MAX_RUNNING_PER_SUB|MCP_RATE_LIMIT|RUN_STATE_RETENTION"` over
      `src/platform/deploy/` and `src/platform/compose/` returns nothing. The
      settings themselves are correct — every number is an `env.int` with a
      documented default, which is what the spec's Always clause requires — but
      an operator tuning them today edits the Deployment rather than
      `values.yaml`. Belongs with the same chart pass that adds the `beat`
      Deployment (Story 42.4).
    location: >-
      src/platform/deploy/charts/platform/values.yaml
    severity: low
  - summary: >-
      The `pyforge-steward` skill card's duty list omits `revoke` (this story)
      and `restore` (Story 41.1), and that file is context-injected.
    evidence: |-
      `.claude/skills/pyforge-steward/0.1.0/pyforge-steward/SKILL.md` line 90
      enumerates the duties ending at `validate-fast`, citing `cli.py:L41-L55`;
      its grammar block has no `steward revoke --sub` line. The only `revoke` on
      that page is the unrelated `steward keys revoke` subcommand, which makes
      the omission actively misleading. An agent reading the card will not know
      the duty exists. Not fixed here because the card is SKF-compiled output
      that `skf-update-skill` regenerates, and because Story 41.1 established
      that the refresh is a separate pass — but that backlog is now two duties
      deep.
    location: >-
      .claude/skills/pyforge-steward/0.1.0/pyforge-steward/SKILL.md
    severity: medium
  - summary: >-
      Celery tasks outside `execute_supervised_run` carry no `sub` header, so
      `revoke --sub` does not reach them.
    evidence: |-
      The spec's Approach says "every Celery task tagged with `sub`". Live
      untagged enqueues remain: `run_compliance_job.delay`
      (`django_warden_fabric/views.py`), `run_django_task.delay`
      (`platformapp/front_door/celery_task_backend.py`), plus the langflow and
      dbgpt integrations. The narrower reading was implemented — the Problem
      paragraph describes only the supervisor `start` path, which is the only
      one that creates a `RunState` row — so a revoked subject can still hold
      work on those queues. Widening needs each of those call sites to carry a
      verified subject, which most of them do not have today.
    location: >-
      src/shared/packages/django-warden/src/django_warden_fabric/views.py
    severity: medium
  - summary: >-
      No `RateLimit-*` response headers, so a well-behaved agent can only
      discover its limit by tripping it.
    evidence: |-
      `Decision` already carries `remaining`, `retry_after`, `rate_per_minute`
      and `burst`; everything except `Retry-After` on a refusal is discarded.
      For an agent-facing platform the `RateLimit-Limit` / `-Remaining` /
      `-Reset` triple is the difference between a client that self-throttles and
      one that must fail first. Related: the MCP bucket is charged for reads as
      well as writes, so a client polling `get_run` once a second while holding
      its permitted runs is throttled for waiting; no cheaper read cost and no
      documented safe poll cadence exist yet.
    location: >-
      src/shared/packages/django-pyforge/src/django_pyforge/mcp_http.py
    severity: low
  - summary: >-
      `manage.py revoke_subject` exits 0 when the broker revoke failed, so a
      shell or cron caller reads a partial revoke as success.
    evidence: |-
      `handle()` writes `revoke error: ...` to stderr and returns `None`. Only
      the steward duty gets this right, because it parses `ok` out of the JSON
      report — which is what its own `test_a_partial_revoke_is_not_reported_as_
      success` pins. The command's contract should match its wrapper's; a
      `CommandError` on `report["revoke_error"]` would do it. Low because the
      sanctioned operator grammar is `pyforge steward revoke`, not the
      management command.
    location: >-
      src/shared/packages/django-pyforge/src/django_pyforge/management/commands/revoke_subject.py
    severity: low
  - summary: >-
      The steward `revoke` duty exposes neither `--reason` nor `--json`, though
      the command it drives accepts both.
    evidence: |-
      `manage.py revoke_subject` takes `--reason` (recorded on every cancelled
      run's `result`), so every revoke driven through the operator grammar is
      logged as the default "revoked by operator" with no incident reference.
      `_add_revoke_arguments` also omits the `--json` flag its sibling duties
      (`init`/`shell-init`/`setup`/`initrepo`/`validate-fast`) carry, even
      though `RevokeDuty` already returns the full report in `details`.
    location: >-
      src/shared/packages/pyforge-steward/src/pyforge/steward/cli.py
    severity: low
  - summary: >-
      `_restore` returns a FULL bucket for stored state that is present but
      malformed, a fail-open path in a module that promises not to have one.
    evidence: |-
      A non-dict value, a missing key, or a non-finite number all return
      `(burst, now)`. The module docstring says "silently allowing traffic
      because the cache is down is the one outcome this module must never
      produce"; a poisoned or schema-drifted key produces exactly that. Kept
      deliberately: the alternative — treating malformed state as unavailable —
      would lock out every subject during a rolling deploy that changed the
      stored shape, which is a worse failure than one refill. The narrower real
      bug (an unbounded `Retry-After` from a negative token count) was patched
      in this pass; only the full-bucket-on-garbage policy remains.
    location: >-
      src/shared/packages/django-pyforge/src/django_pyforge/rate_limit.py
    severity: low
  - summary: >-
      Six new `spec-surface` `drift: fail` rows for this story's four new files
      land under three OTHER specs' globs and need scoped stamps at landing.
    evidence: |-
      Measured against a detached worktree at the `629ee8c5` baseline: 196 fails
      before, 136 after, and the comm-diff shows exactly six new rows, all of
      kind "added" — `revoke.py` and `test_revoke_duty.py` under
      `pyforge-steward/spec-pyforge-steward`, and the 0004 changeset plus
      `test_agent_rate_limits_and_run_bounds.py` under both
      `pyforge-steward/spec-python-agent-platform` and
      `pyforge-mason/spec-django-accelerator-framework`. Not stamped here for
      two reasons: `--write-baseline` reads the WORKING TREE, so stamping from a
      dirty dispatch worktree bakes in uncommitted bytes, and a foreign spec's
      baseline needs the three-check procedure first. Landing-pass work, scoped
      per spec — never a bare `--write-baseline`.
    location: >-
      scripts/.spec-surface-baseline.json
    severity: low
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

There is no pixi task for the `src/platform` suite; CI runs the `platform-ci-test`
env directly, and a local run additionally needs helm on PATH, a real PostgreSQL,
and a `seed_lane1_homepage` shim. From `src/platform`:

```bash
python -m pytest -q --create-db     # the platform suite, incl. the files below
ruff check .
python -m db.sqlmigrate_extraction  # CAP-9 / AD-9 changeset extraction gate
```

```bash
pixi run -e pyforge-steward pyforge-steward-test   # the revoke duty
```

The tests this story added or extended:

- `src/platform/tests/test_agent_rate_limits_and_run_bounds.py` (added) — limiter,
  ceilings, revoke, retention, and the two `tools/call` bound tests.
- `src/platform/tests/test_warden_portal_audit_start_get.py` (extended) — the
  portal `start` face refusing 429/409.
- `src/platform/tests/test_start_get_survives_disconnect.py` (extended).
- `src/shared/packages/pyforge-steward/tests/unit/test_revoke_duty.py` (added).

The platform suite's pre-existing failures are environmental and must be diffed
against a baseline worktree, never read as this story's regression.

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
| this story (implementation) | 627 | 13 | 5 |
| this story (after review patches) | 636 | 13 | 5 |

The 13 failures and 5 errors are byte-identical sets on both sides
(redis-broker, host-board row isolation, openfeature cachebox pin, liquibase
DDL governance, transactional-DB teardown) — pre-existing and environmental.
`ruff check .` in `src/platform`: 116 errors on both sides (no delta; `mypy`
crashes constructing the Django plugin on both sides). `pyforge-steward`: 1007
passed. `python -m db.sqlmigrate_extraction`: ok (15 first-party migrations).
`scripts/detectors.py --scope repo`: 230 findings at baseline → 141 here (the
drop is this spec's memlog entry downgrading that spec's pending drift to
`warn`; see the honesty note in `.memlog.md`). The only genuinely new findings
are mechanical: six `spec-surface` "added" rows for this story's new files under
three OTHER specs' globs (`pyforge-steward/spec-pyforge-steward`,
`pyforge-steward/spec-python-agent-platform`,
`pyforge-mason/spec-django-accelerator-framework`) plus the frontmatter
deferrals below. Both are landing-pass work — the foreign specs are deliberately
not edited from this story (`feedback_foreign_spec_surface_finding_reconcile`),
and `scripts/deferred_work_intake.py --fix` mirrors the deferrals.

## Review Triage Log

### 2026-09-02 — Review pass

Four layers ran in parallel over the full diff (blind hunter, edge-case hunter,
verification-gap, intent-alignment). Three of the four independently reached the
same top finding — the bounds were undelivered on the MCP face — which is the
one that decided this pass.

- intent_gap: 0
- bad_spec: 0
- patch: 8: (high 4, medium 3, low 1)
- defer: 11: (high 0, medium 4, low 7)
- reject: 10: (high 0, medium 0, low 10)
- addressed_findings:
  - `[high]` `[patch]` **The bounds were invisible on the agent surface they exist for.**
    Both MCP `start` tools called `publish_start` bare, so a `RunBoundExceeded`
    was a *crash* as far as the SDK is concerned — and the SDK withholds a
    crash's text, delivering `Error executing tool start_audit` and nothing
    else. Not `str(exc)`, as first assumed: the SDK preserves a message only for
    its own `ToolError` ("a failure you anticipated"). So ACs 2 and 3 were
    undelivered to agents while passing on the portal. Fixed with one shared
    projection — `bound_refusal_payload` (used by the portal too, so the two
    faces are now byte-identical) raised through `_tool_refusal`, which lazily
    imports the SDK's `ToolError` and falls back to `BoundedStartRefused` when
    the SDK is absent. Covered by two real `tools/call` tests.
  - `[high]` `[patch]` **A finishing worker could overwrite a revoked run.**
    `control.revoke` cannot recall a task that has started, and `complete_run`
    updated unconditionally — so the worker's `succeeded` replaced the
    operator's `CANCELLED`, destroying the record AC 4 had just created.
    `complete_run` now refuses to rewrite a terminal row (and logs the dropped
    write); `revoke` passes `terminate=True`.
  - `[high]` `[patch]` **A failed enqueue left an immortal live row.** Retention never
    prunes live rows, so five broker failures exhausted `MAX_RUNNING_PER_SUB`
    permanently — a denial of service this story introduced. The row now
    terminalises before the exception propagates.
  - `[high]` `[patch]` **`revoke_subject("")` would cancel the whole legacy estate**
    (migration 0004 defaults `subject=""`). The guard moved into the single
    writer (AD-12); the management command projects it to a `CommandError`.
  - `[medium]` `[patch]` `RUN_STATE_PRUNE_INTERVAL_SECONDS` bypassed validation and could
    ship `0` into beat's `schedule` as a hot loop. Now validated at
    settings-load (where beat consumes it) and covered by the documented-knob
    test.
  - `[medium]` `[patch]` A negative stored token flowed into `ceil((1 - tokens) / rate)`
    and emitted an unbounded `Retry-After` — a lockout dressed as backpressure.
    Tokens now clamp into `[0, burst]` and `retry_after` is capped.
  - `[low]` `[patch]` `expired_handles` read element 0 of `delete()` — the grand total,
    the exact fiction `_deleted_runs` existed to prevent. Both counts now go
    through one per-model read (`_deleted`), and the test gives the aged run two
    handles so a grand-total read fails it.
  - `[medium]` `[patch]` The cap pass issued one unbounded `pk__in` DELETE, which on the
    first post-deploy sweep can exceed `CELERY_TASK_SOFT_TIME_LIMIT` and never
    complete. Every pass is now bounded by `RUN_STATE_PRUNE_BATCH`, the two
    passes share one budget, and the report carries `truncated` so a bounded
    sweep cannot read as "the table is now in policy".

## Auto Run Result

Status: done
Blocking condition: none

**Implemented change.** `POST /stations/<name>/mcp` and supervisor `start` are
now bounded per verified `sub`. A token bucket in `CACHES["default"]`
(redis-cache, AD-10 — never the `noeviction` broker) charges the MCP route after
the 42.1 transport gate; `publish_start` enforces three bounds *before* its
transaction, so "429 and no `RunState` row" is a property of ordering rather
than of a rollback. `RunState` gained `subject`, `celery_task_id` and a terminal
`cancelled` status, every supervised task is published with a pre-minted id and
a `sub` header, `pyforge steward revoke --sub <id>` stops one runaway subject,
and a two-pass retention sweep (age policy + hard row cap, both batch-bounded)
keeps the table finite.

**Files changed.**

- `django_pyforge/rate_limit.py` (added) — the token bucket; fails **closed**
  with an `ERROR` log when the store does not answer.
- `django_pyforge/supervisor.py` — `enforce_run_bounds`, the `RunBoundExceeded`
  family carrying its own HTTP shape, `revoke_subject`, `prune_run_state`; still
  the only writer of `run_state` / `mcp_handles` (AD-12).
- `django_pyforge/mcp_http.py` — charges the verified `sub`; 429 + `Retry-After`.
- `django_pyforge/mcp_auth.py` — `TransportRefusal` grew `retry_after`/`headers()`.
- `django_pyforge/models.py` — `subject`, `celery_task_id`, `CANCELLED`, two
  named bound indexes, widened CHECK constraint.
- `django_pyforge/tasks.py` — `enqueue_supervised_run`, `prune_run_state_task`.
- `django_pyforge/mcp_start_get.py`, `django_warden_fabric/mcp_asgi.py`,
  `django_warden_fabric/views.py` — all three `start` faces project a refused
  bound through one shared payload builder.
- `django_pyforge/migrations/0004_run_bounds.py` + changeset
  `python-agent-platform:20` (+ `sqlmigrate-map.yaml`, master changelog) — CAP-9.
- `django_pyforge/management/commands/{revoke_subject,prune_run_state}.py` (added).
- `pyforge/steward/revoke.py` (added) + `cli.py` — `revoke` is the 15th duty.
- `config/settings/base.py` — nine documented `env.int` knobs + the beat entry.
- `src/platform/conftest.py` — autouse cache clear (LocMemCache outlives a test).
- Tests: one new platform module, one new steward module, three extended.

**Review findings.** 8 patched (high 4, medium 3, low 1); 17 deferred (6 carried
in from implementation, 11 added by this pass); 10 rejected as noise (import
style and line length, the `len(DUTIES) == 15` tripwire, duplicated status
vocabulary, defaults restated in two modules, `baseline_commit` vs
`baseline_revision`, the heterogeneous `deferred` shapes, missing operator docs,
the out-of-order changeset id, and the pre-existing `ruff`/`mypy` state — all
confirmed identical at baseline).

Follow-up review recommended: **true** — 4 of the patched findings were `high`
severity (score rule: any high ⇒ true; the medium/low score was
`3 × 3 + 1 × 1 = 10`, itself ≥ 5).

**Verification performed.** `src/platform` suite under `platform-ci-test` with
helm on PATH and an ephemeral PostgreSQL, each run diffed against a detached
worktree at `629ee8c5`: baseline 603 passed / 13 failed / 5 errors →
implementation 627 → after review patches **636**, with the failure and error
sets byte-identical to baseline at every step (18 entries; `comm`-diffed, not
eyeballed). `pixi run -e pyforge-steward pyforge-steward-test`: 1007 passed.
`ruff check .`: 116 on both sides, no delta. `python -m db.sqlmigrate_extraction`:
ok. `deferred-work` detector: 32 fails → 3 (steward 29 → 0) after
`scripts/deferred_work_intake.py --fix --project steward`. `spec-surface`: 196
fails → 136, with exactly six new rows, all mechanical "added" entries under
three other specs (deferred above). `pixi_version_check` fails identically at
baseline (`ModuleNotFoundError: pixi_version_registry`) — environmental.

**Residual risks.** AC 1 is unreachable in a deployed run until the AD-19 keypair
Secret lands, since the limiter sits behind the 42.1 gate (deferred, inherited).
The retention sweep has no `beat` process deployed, so it is operator-run until
Story 42.4. Both ceilings and the bucket itself are approximate under
concurrency (count-then-create; non-atomic read-modify-write) — backpressure,
not a semaphore. Six `spec-surface` scoped stamps and the ledger promotion are
landing-pass work, deliberately not done from this dirty dispatch worktree.

## Source

Red-team review: `research/architecture-review-pyforge-unifying-strategy-red-team-2026-09-02.md` (directive and finding ids in the FR/AD line of
`epics.md` Story 42.2). Sprint change proposal:
`sprint-change-proposal-2026-09-02-red-team-high.md`.
