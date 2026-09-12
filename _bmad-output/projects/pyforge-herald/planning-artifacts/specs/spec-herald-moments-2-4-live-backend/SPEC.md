---
id: SPEC-herald-moments-2-4-live-backend
spec: herald-moments-2-4-live-backend
status: in-progress
owner-dream: docs/dreams/herald-moments-2-4-live-backend.md
surface:
  # LB-1 landed 2026-08-13; LB-2/LB-3 are code-complete but have never run green in the
  # estate and are re-scoped `foundry-side` (2026-09-09). The prose entries below match no
  # tracked file and are therefore silent to the drift check — only the glob governs files.
  - src/shared/packages/pyforge-herald/src/pyforge/herald/**   # storage-layer swap behind the existing function seam
  - a real database (SQLite-with-locking or Postgres) replacing .herald/progress.json / claims.json / notices-index.json   # SATISFIED 2026-08-13 — .herald/herald.db via db.py
  - a webhook HTTP endpoint at /stations/herald/api/v1/webhooks/on-ship and /on-pr-close — CORRECTED 2026-09-09; the shipped /api/herald/... literals are a silent 404 under the platform seam
  - a cron/scheduled-job runner (weekly progress aggregation, 7-day evidence re-validation) — hosting undecided, foundry-side
surface-drift-exclude:
  # 2026-09-12: also governed by the spec(s) named below, which already
  # reconciles each of these files cleanly -- this kernel spec's own
  # memlog does not move for routine story work anymore, so double-
  # claiming them only produced permanent drift-presumed noise here.
  # Coverage is unchanged (still listed under `surface:` above); only
  # this spec's own drift tracking for these specific files is off.
  - src/shared/packages/pyforge-herald/src/pyforge/herald/station_api.py   # also governed by pyforge-marshal/spec-pyforge-core
companions:
  # ADOPTED 2026-08-09 — this Spec takes Steward's pattern instead of building its own
  # backend. Both are load-bearing: the Spec supplies the perimeter and identity contract,
  # the spine's AD-8/AD-9 bind how Herald may consume it. See Constraints for what the
  # adoption did and did not actually buy (re-grounded 2026-09-09).
  - ../../../../pyforge-steward/planning-artifacts/specs/spec-secure-live-dashboards/SPEC.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/architecture/architecture-pyforge-steward-2026-07-25/ARCHITECTURE-SPINE.md
sources:
  - ../../../../../../docs/dreams/herald-moments-2-4-live-backend.md
  - ../research/technical-herald-shipped-architecture-research-2026-08-08.md
  - ../research/domain-engineering-proclamation-four-moments-research-2026-08-08.md
  - ../retros/retro-herald-2026-08-08.md
open_questions:
  # ANSWERED 2026-08-09 (operator): where the backend runs and under whose operational
  # ownership — nominally Steward's perimeter. RE-OPENED 2026-09-09 as the hosting question
  # below, because the adopted perimeter has no executable path for an arbitrary ASGI callable.
  # ANSWERED 2026-08-11 (Story 13.1): SQLite convergence vs per-file fcntl locking — per-file
  # advisory locking (fcntl/msvcrt) shipped first in locking.py; LB-1 then converged the three
  # index stores onto one stdlib-sqlite3 file (db.py, 2026-08-13). Both halves are now decided.
  # ANSWERED 2026-09-09 (operator, batch C11): "is there real pull for this at all?" — NO, and
  # the evidence is one-sided; it is not a demand question any more, it is the hosting question.
  - "Where does a listening Herald process actually run? The adopted `spec-secure-live-dashboards` perimeter cannot target an arbitrary ASGI callable (`deploy.py:484` renders only a hardcoded `myproject.asgi:application`, no `--asgi-application` flag, DW-13-6-1), and `herald-live-demo.yml` is a throwaway `runner.temp` store, not a deployment. Deferred to the python-foundry cutover; until a perimeter exists, LB-2 and LB-3 are `foundry-side` and not chargeable here."
  - "What actually triggers CI to call the webhook — which CI system, and which events? The AUTHENTICATION half is answered: the adopted pattern's AD-9 requires a verifiable HMAC signature, and a machine caller is never granted a human role. Nothing in the estate calls the endpoint today."
---

> **In-progress — decomposed as herald Epic 13, all six stories `done` (2026-08-13), criterion
> unexercised (2026-09-09).** LB-1 shipped and is genuinely closed. LB-2 and LB-3 are
> code-complete, fully unit-tested, and have never run as a real listening process; they are
> re-scoped `foundry-side` and blocked on a perimeter that does not exist yet. `status: ready`
> overstated a Spec whose decomposition is complete and whose success signal has never fired —
> hence `in-progress`. The residual effect work is herald Epic 19 (steward Epic 49 carries the
> index row). Nothing here is required for, or blocks, the shipped v1.

# herald-moments-2-4-live-backend

## Why

Epics 8–10 as planned assumed a genuinely live service: a database, a webhook endpoint
CI calls on every merge/close, and scheduled jobs — records created automatically the
moment a ship happens, with the operator only reviewing/publishing. The shipped v1
(2026-08-08) deliberately replaced every trigger with an operator-run CLI command over
local JSON/SQLite files, because this repo's Herald architecture had never hosted a
persistent service and inventing one silently would have been scope invention. That
pivot traded away the whole point of "automatic": a factory lead must remember to run
`herald progress <station> --update` after a ship — and an unrecorded ship is
indistinguishable from no ship (technical research risk #2). This Spec preserves, as a
contract, what the live version would actually be — grounded in the shipped code's real
seams rather than the pre-pivot epics doc, which was never annotated for the pivot
(retro A1) and must not be read as architectural truth for Epics 8–10.

## Capabilities

- **LB-1 — DB-backed storage layer.** Replace the three local file stores
  (`progress.py` → `.herald/progress.json`, `claims.py` → `.herald/claims.json`,
  `notices.py` → `.herald/notices-index.json`) with a real database carrying the same
  Progress / Claims / Notice schemas the shipped modules already define, with
  migrations. The swap happens **behind the existing function seam**:
  `progress.upsert`, `claims.create/publish`, `notices.author/publish/close` are already
  pure `(path, **fields) → record` functions with no CLI coupling (technical research
  §4.1), and the CLI/web-tab contract must not change shape. Notices' git-tracked
  markdown files remain the durable copy; only the index/cache layer moves.
  - **success:** two writers hitting the same store concurrently never lose an update,
    and the CLI verbs behave identically across the swap.
  - **CLOSED 2026-08-13** (Story 13.3, commit `20b88dd689`): one stdlib-`sqlite3`
    `.herald/herald.db` with WAL, `busy_timeout`, a version-tracked migration runner and
    a one-time legacy-JSON import; the concurrency prerequisite holds via `locking.py`
    (Story 13.1) and `db.transaction`.
- **LB-2 — Webhook endpoint.** A real HTTP endpoint that CI actually calls, creating
  progress records and success-claim drafts automatically instead of CLI-triggered — the
  handler calls the same storage functions the CLI verbs call today. Includes webhook
  signature verification (HMAC), retry/backoff, and operator-alert delivery, all specced
  in the original Epics 8.2/9.2/9.5 stories and meaningless without a live endpoint.
  - **success:** a merged PR produces a progress record with zero operator action.
  - **BUILT, NEVER EXERCISED — `foundry-side` as of 2026-09-09.** `webhook.py` +
    `webhook_host.py` shipped (Stories 13.4/13.6) and are fully unit-tested; no CI system
    calls them, the only workflow that ever started a listening process
    (`herald-live-demo.yml`) is `disabled_manually` with 100 failures in its last 100 runs,
    and its store was a `runner.temp` database discarded at job end. Not chargeable to this
    Spec until a perimeter exists to mount it on.
- **LB-3 — Cron scheduler.** A weekly job aggregating progress and an async job
  re-validating evidence links every 7 days, actually running on a schedule — replacing
  the shipped pass's operator-remembered `herald progress --update` /
  `herald success validate-evidence` equivalents. The 7-day evidence-staleness window
  becomes enforced rather than merely displayed.
  - **success:** the weekly aggregation and the 7-day re-validation both run without
    anyone remembering them.
  - **BUILT, NEVER EXERCISED — `foundry-side` as of 2026-09-09.** `scheduler.py`
    (Story 13.5) composes `claims.revalidate_all` + `progress.write_snapshot` into one
    `herald scheduler run`; the only driver is an operator-local crontab line that no
    machine in the estate installs.

## Constraints

- **The route literals violate the station route contract and must move before any
  mount.** `webhook.ON_SHIP_PATH = "/api/herald/webhooks/on-ship"` /
  `ON_PR_CLOSE_PATH = "/api/herald/webhooks/on-pr-close"` (`webhook.py:183-184`) sit on
  the bare `/api/` namespace the platform FastAPI seam owns: `config/asgi.py:149-150`
  routes every `/api/*` path to `fastapi_application`, and only
  `/stations/<name>/api/v<N>/` is diverted to a station sub-app
  (`config/asgi.py:132-144`, `config/station_api.py:24-32`). Mounting
  `webhook_host:application` in the monolith today is a silent 404. Correct target:
  `/stations/herald/api/v1/webhooks/{on-ship,on-pr-close}`; only warden v1 is registered
  on that seam so far (`station_api.py:146`). `spec-pyforge-unifying-strategy`
  SPEC.md:497 carries this as an Always. Vessel: herald Epic 19 Story 19.1.
- **Concurrency lock is a PREREQUISITE, not a feature.** Every shipped storage module
  inherited `state.py`'s unlocked whole-file read-modify-write, so two concurrent writers
  silently dropped one update (DW-1-4-2) — acceptable single-operator, a real bug the
  moment ANY second writer exists, including this Spec's own webhook or a mere
  git-hook/CI-triggered CLI invocation. **Satisfied 2026-08-11** by Story 13.1's per-file
  advisory locking and 2026-08-13 by `db.transaction`; it remains the precondition any
  future second writer must not regress.
- **No silently-invented hosting — and the adoption did not supply one.** The 2026-08-08
  pivot existed to avoid scope invention, and on 2026-08-09 the operator answered hosting
  by adopting `spec-secure-live-dashboards`. **Re-grounded 2026-09-09:** that adoption
  bought a *design* constraint, not a deployment. `pyforge-herald/pyproject.toml:38-45`
  declares no `pyforge-steward` dependency and `webhook_host.py:77-89` imports only
  `webhook` + `errors`, mounting no Steward middleware — so what AD-8 and AD-9 actually
  bind is `webhook.py`'s shape (a framework-free ASGI3 callable; HMAC machine-caller
  proof), both real and correctly honoured. Hosting is still open, and no hosting may be
  invented outside the python-foundry cutover's perimeter decision.
- **Herald consumes the pattern under AD-8 and AD-9.** AD-8 (the pattern binds at the
  WSGI/request layer, never to a dashboard framework) is what makes adoption possible at
  all, given this Spec commits to no framework. AD-9 (a machine caller authenticates by
  HMAC proof, never by ingress, and is never granted a human role) is what makes LB-2's
  webhook receiver legal under the pattern's trust boundary. Both were added to the
  pattern *because* Herald adopted it.
- **What the adoption does NOT resolve.** The pattern supplies **none** of LB-1's storage
  layer, LB-2's webhook receiver, or LB-3's scheduler: it *emits* security webhooks, it
  does not *receive* them, and its audit store is not a general application store.
- **The v1 CLI/web-tab contract must not change shape.** Only the data-access layer
  swaps and CLI-triggered updates become webhook/cron-triggered underneath the same
  commands. If realizing this Spec would reshape the CLI surface operators already
  learned, the shipped data-access seam was drawn in the wrong place — treat that as a
  design failure, not a migration cost.
- **`herald-live-demo.yml` stays disabled.** Re-enabling it buys a green run against a
  throwaway store that is discarded when the job ends, which is not this Spec's success
  signal and would make an unrealized capability look realized.
- **Sequence behind the serverless intermediates — resolved item by item (Story 13.2,
  2026-08-11).** `herald snapshot`: BUILD, as a non-Epic-13 deferred-work entry.
  Telemetry-derived defaults for `herald progress --update`: SKIP. Locking +
  hook-triggered CLI: SKIP (Story 13.1's lock already closed the race a hook would
  exercise; a hook would duplicate Story 13.4's trigger surface). `herald notice reindex`
  and hosting the static bundle were outside that story's binding scope.

## Non-goals

- **Not required for Herald's shipped v1.** The CLI-triggered/local-storage version
  (Epics 8–10 as actually built, 47/47 stories, merged 2026-08-08) is complete, stands
  on its own, and is tracked under its own story specs and `sprint-status-ledger.yaml`.
  This Spec supersedes nothing shipped and gates nothing shipped.
- **Not re-litigating whether Moments 2–4 should exist** — they should and they do;
  this Spec is about how they're powered, not whether.
- **Not committing a framework, database engine, or scheduler beyond what LB-1 settled.**
  The pre-pivot epics doc's Flask/FastAPI, Postgres/SQLite, APScheduler/Celery Beat were
  illustrative; LB-1 committed stdlib `sqlite3` and nothing else.
- **Not resurrecting the pre-pivot epics doc as the plan.** `epics.md` /
  `epics-with-stories.md` still describe the live-backend shape for Epics 8–10 without
  annotation (retro A1, open); if this Spec is ever taken to build, planning restarts
  from the shipped code + this contract, not from those frozen docs.
- **Not measuring demand.** The 2026-09-09 ruling closed the pull question in the
  negative on hosting evidence, not on user evidence; nobody is to re-open it as a
  demand study.

## Success signal

A PR merges or closes; a progress record or success-claim draft exists in Herald's
store within minutes with zero operator action, and the operator's only touch is
review/publish. The weekly aggregation and 7-day evidence re-validation run without
anyone remembering them. Throughout, an operator's existing `herald progress` /
`herald success` / `herald notice` commands and the three dashboard tabs work
unchanged — and two writers (webhook + CLI) hitting the same store concurrently never
lose an update.

**Realization status (2026-09-09):** only the last clause is true. The concurrent-writer
guarantee is proven (LB-1, Story 13.1 + `db.py`). No ship has ever recorded itself — the
first three clauses have never fired anywhere in the estate.

## Assumptions

- The python-foundry cutover is the event that gives Herald a real perimeter; LB-2 and
  LB-3 are parked against it rather than against a date.
- The prose entries in `surface:` match no tracked file and are silent to
  `spec-surface-check`; only the `pyforge/herald/**` glob governs files (18 at first
  stamp).
