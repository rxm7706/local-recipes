---
id: SPEC-herald-moments-2-4-live-backend
spec: herald-moments-2-4-live-backend
status: draft
owner-dream: docs/dreams/herald-moments-2-4-live-backend.md
surface:
  # Authorizes FUTURE work — none of this exists today. Herald's shipped v1 is a
  # stateless CLI + static-snapshot dashboard with no server, no DB, no scheduler.
  - src/shared/packages/pyforge-herald/src/pyforge/herald/**   # storage-layer swap behind the existing function seam
  - a real database (SQLite-with-locking or Postgres) replacing .herald/progress.json / claims.json / notices-index.json
  - a webhook HTTP endpoint (/api/herald/webhooks/on-ship, /api/herald/webhooks/on-pr-close) — hosting location undecided
  - a cron/scheduled-job runner (weekly progress aggregation, 7-day evidence re-validation) — hosting location undecided
sources:
  - ../../../../../../docs/dreams/herald-moments-2-4-live-backend.md
  - ../research/technical-herald-shipped-architecture-research-2026-08-08.md
  - ../research/domain-engineering-proclamation-four-moments-research-2026-08-08.md
  - ../retros/retro-herald-2026-08-08.md
open_questions:
  - "Is there real pull for this at all? The CLI-triggered v1 shipped 2026-08-08 and has zero production-usage evidence yet; the technical research recommends exhausting the serverless intermediate steps (its §4.2) first and letting usage evidence drive the hosting decision. This Dream may stay dreamt."
  - "Where does a persistent Herald backend run, and under whose operational ownership? Explicitly left open by the Dream; likely a Herald x Steward estate/deployment question, not Herald's call alone."
  - "SQLite convergence vs per-file fcntl locking for the concurrency prerequisite: is moving the three .herald/*.json stores to one SQLite file (real locking, same function seam) the right first move, or is file locking sufficient for the hook-trigger intermediate step? (Technical research Open Question 3.)"
  - "What actually triggers CI to call the webhook — which CI system, which events, with what authentication?"
---

> **Draft — deferred, unbuilt.** This Spec exists to satisfy INV-1 (every Dream carries a
> Spec) for a Dream that is real but deliberately deferred. It is the contract for the
> full live-backend version of Herald's Moments 2–4 (Progress / Success / Operations)
> that Epics 8–10 originally specced and were explicitly scaled down from on 2026-08-08
> (see the whole-build retro §4). Nothing here is required for, or blocks, the shipped v1.
> `status: draft` means: authorized to be planned when prioritized, not scheduled.

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
  `notices.py` → `.herald/notices-index.json`) with a real database (SQLite-with-real-
  locking or Postgres; undecided — see Open Questions) carrying the same Progress /
  Claims / Notice schemas the shipped modules already define, with migrations. The swap
  happens **behind the existing function seam**: `progress.upsert`,
  `claims.create/publish`, `notices.author/publish/close` are already pure
  `(path, **fields) → record` functions with no CLI coupling (technical research §4.1),
  and the CLI/web-tab contract must not change shape. Notices' git-tracked markdown
  files remain the durable copy; only the index/cache layer moves.
- **LB-2 — Webhook endpoint.** A real HTTP endpoint
  (`/api/herald/webhooks/on-ship`, `/api/herald/webhooks/on-pr-close`) that CI actually
  calls, creating progress records and success-claim drafts automatically instead of
  CLI-triggered — the handler calls the same storage functions the CLI verbs call
  today. Includes webhook signature verification (HMAC), retry/backoff, and
  operator-alert delivery, all specced in the original Epics 8.2/9.2/9.5 stories and
  meaningless without a live endpoint.
- **LB-3 — Cron scheduler.** A weekly job aggregating progress and an async job
  re-validating evidence links every 7 days, actually running on a schedule — replacing
  the shipped pass's operator-remembered `herald progress --update` /
  `herald success validate-evidence` equivalents. The 7-day evidence-staleness window
  becomes enforced rather than merely displayed.

## Constraints

- **Concurrency lock is a PREREQUISITE, not a feature — this Dream is currently
  self-blocking.** Every shipped storage module (`progress.py`, `claims.py`,
  `notices.py`) inherits `state.py`'s documented lost-update limit: unlocked whole-file
  read-modify-write, so two concurrent writers silently drop one update (DW-1-4-2; each
  module's own docstring). That is acceptable single-operator, and a real bug the moment
  ANY second writer exists — **including this Dream's own webhook, or even a mere
  git-hook/CI-triggered CLI invocation**. The technical research (risk #4, §4.2 item 3)
  is explicit: the unlocked read-modify-write must be replaced with a real
  locking/transactional layer BEFORE any second writer can safely run concurrently with
  CLI-triggered writes. Any realization of LB-2 or LB-3 — or any serverless
  hook-trigger stepping stone — starts here, first.
- **No silently-invented hosting.** Realizing this Spec requires first answering where
  the backend runs persistently, under whose operational ownership, and what triggers
  CI to call it — likely a cross-station Herald × Steward question, not a unilateral
  Herald decision. This is the exact scope-invention risk the 2026-08-08 pivot existed
  to avoid; it does not get waved through at build time.
- **The v1 CLI/web-tab contract must not change shape.** Only the data-access layer
  swaps and CLI-triggered updates become webhook/cron-triggered underneath the same
  commands. If realizing this Spec would reshape the CLI surface operators already
  learned, the shipped data-access seam was drawn in the wrong place — treat that as a
  design failure, not a migration cost.
- **Sequence behind the serverless intermediates.** The technical research (§4.2–4.3)
  prices the full backend's residual unique value honestly: sub-day currency without a
  human, scheduled evidence re-validation, multi-writer correctness. Most of the
  operator-facing "automatic" feel is deliverable serverlessly first (`herald snapshot`,
  telemetry-derived defaults, locking + hook-triggered CLI). Those cheaper steps
  generate the usage evidence a hosting decision needs; this Spec should not be built
  ahead of them without new justification.

## Non-goals

- **Not required for Herald's shipped v1.** The CLI-triggered/local-storage version
  (Epics 8–10 as actually built, 47/47 stories, merged 2026-08-08) is complete, stands
  on its own, and is tracked under its own story specs and `sprint-status-ledger.yaml`.
  This Spec supersedes nothing shipped and gates nothing shipped.
- **Not re-litigating whether Moments 2–4 should exist** — they should and they do;
  this Spec is about how they're powered, not whether.
- **Not committing a framework, database engine, or scheduler.** Flask/FastAPI,
  Postgres/SQLite, APScheduler/Celery Beat in the pre-pivot epics doc were
  illustrative, not committed, and remain open.
- **Not resurrecting the pre-pivot epics doc as the plan.** `epics.md` /
  `epics-with-stories.md` still describe the live-backend shape for Epics 8–10 without
  annotation (retro A1, open); if this Spec is ever taken to build, planning restarts
  from the shipped code + this contract, not from those frozen docs.

## Success signal

A PR merges or closes; a progress record or success-claim draft exists in Herald's
store within minutes with zero operator action, and the operator's only touch is
review/publish. The weekly aggregation and 7-day evidence re-validation run without
anyone remembering them. Throughout, an operator's existing `herald progress` /
`herald success` / `herald notice` commands and the three dashboard tabs work
unchanged — and two writers (webhook + CLI) hitting the same store concurrently never
lose an update.
