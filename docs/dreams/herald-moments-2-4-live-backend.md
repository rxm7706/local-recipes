---
title: Herald Moments 2-4 run on a real live backend, not local-storage/CLI-triggered
type: dream
owner: herald
status: dreamt
---

# Herald Moments 2-4 run on a real live backend, not local-storage/CLI-triggered

## The Dream

`_bmad-output/projects/pyforge-herald/planning-artifacts/epics-with-stories.md`'s Epics
8-10 (Progress/Success/Operations) spec a genuinely live service: a database (PostgreSQL
or SQLite via SQLAlchemy + Alembic migrations), a webhook HTTP endpoint receiving CI
callbacks (`on-ship`, `on-pr-close`), and scheduled jobs (a weekly cron aggregating
progress, an async job re-validating evidence links every 7 days). Records get created
automatically the moment a PR merges or closes, with zero operator action required to
produce the raw data -- an operator only reviews/publishes.

That is the vision this Dream preserves for later. It is explicitly **not** what
Epics 8-10 build first (see [[pyforge-herald]]'s own Epics tier + the 2026-08-08 scope
decision below) -- the first pass is scaled down to local storage (JSON/SQLite files, no
server) with every record created via a CLI command an operator runs by hand, because
nothing else in this repo's Herald architecture (a stateless CLI + a static web dashboard
talking to Claude Design) has ever hosted a persistent service, and inventing one
silently -- with no answer for where it deploys, what triggers CI to call it, or who
operates it -- would have been exactly the kind of scope invention the four behavioral
principles at the top of this repo's `CLAUDE.md` warn against.

## Why It Matters

The scaled-down first pass ships the operator-facing value (progress/claims/notices
records, the CLI, the web tabs) without inventing unrequested infrastructure. But it
trades away the whole point of "automatic": a factory lead currently has to remember to
run `herald progress warden --update` after a ship, rather than a webhook doing it the
moment CI reports success. The live-backend version is what actually delivers on Epic
8's own framing ("Progress records are created automatically when ships happen") and
Epic 9's ("auto-extract on PR-close") -- the scaled-down version is a real, useful
stepping stone, not the destination.

## What is Real

Nothing built yet toward the live-backend shape. What *is* real, as of 2026-08-08: the
scaled-down first pass of Epics 8-10 (local JSON/SQLite storage, CLI-triggered record
creation, the web tabs reading local data) -- tracked under the existing Epics 8/9/10
story numbers in `sprint-status-ledger.yaml`, which this Dream does not duplicate or
supersede.

## What it looks like when real

- A real webhook endpoint (`/api/herald/webhooks/on-ship`, `/api/herald/webhooks/on-pr-close`)
  that CI actually calls -- which first requires deciding where Herald's backend runs
  persistently (a question this Dream deliberately leaves open at `dreamt` stage; not
  Herald's call alone -- likely intersects Steward's estate/deployment ownership).
  a real database replacing the local JSON/SQLite files, with the same schema Epics
  8-10's specs already describe (Progress/Claims/Notice tables, indexes, migrations) --
  the CLI/web-tab surface built in the scaled-down pass should need minimal rework, since
  its data-access layer is the seam this Dream's eventual work slots behind.
- A weekly cron job and an async evidence-revalidation job actually running on a
  schedule, replacing the scaled-down pass's CLI-triggered equivalents
  (`herald progress --update`, a manual `herald success validate-evidence` or similar).
- Retry/backoff, webhook signature verification, and operator-alert delivery (email or
  in-app) -- all specced in Epics 8.2/9.2/9.5 but meaningless without a live endpoint to
  receive real traffic.

## Constraints

- **Do not silently invent server-hosting architecture.** The scaled-down pass exists
  precisely because Epics 8-10 assumed infrastructure this repo has never had an answer
  for. Realizing this Dream requires first answering: where does this run persistently,
  under whose operational ownership, and what actually triggers CI to call it -- likely
  a cross-station question (Herald's data model, Steward's deployment/estate ownership),
  not a unilateral Herald decision.
- **The scaled-down pass's CLI/web-tab contract should not need to change shape** when
  this Dream is realized -- only its data-access layer swaps from local files to a real
  database, and CLI-triggered updates become webhook/cron-triggered ones underneath the
  same commands. If realizing this Dream would require reshaping the CLI surface
  operators already learned, that is a signal the scaled-down pass's data-access seam
  was drawn in the wrong place.

## Non-goals

- Not re-litigating whether Epics 8-10 should exist at all -- they should; this Dream is
  about *how* they're powered, not *whether*.
- Not deciding the specific web framework (Flask/FastAPI), database (Postgres/SQLite), or
  scheduler (APScheduler/Celery Beat) named in the epics doc's Implementation Notes --
  those are illustrative, not committed, and remain open at Spec time.

## Kinships

[[pyforge-herald]] (the constitutive Dream Epics 8-10 belong to; this Dream is a
follow-up on top of it, not a replacement) · [[herald-moments-2-4-missing-surface]]
(archived/superseded predecessor covering the same Moments 2-4 gap at a coarser grain)

## Realization log

- **2026-08-08** — Dream captured. Surfaced mid-execution of Herald's "complete all
  epics and stories" campaign: Epics 8-10's specs assume a live database + webhook
  server + cron scheduler that exist nowhere else in this repo's Herald architecture.
  Flagged to the user rather than silently invented; user chose to build Epics 8-10's
  first pass scaled down to local-storage/CLI-triggered, and asked for this Dream to
  capture the full-spec live-backend version for later.
