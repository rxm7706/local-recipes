---
sources:
  - src/shared/packages/pyforge-herald/src/pyforge/herald/cli.py
  - src/shared/packages/pyforge-herald/src/pyforge/herald/db.py
  - src/shared/packages/pyforge-herald/src/pyforge/herald/webhook_host.py
  - src/shared/packages/pyforge-herald/web/package.json
verified: 2026-11-26
---

# Herald's Four Moments

This page explains what Herald's Progress, Success and Operations records are, where they are stored, and why nothing reaches the store or the web dashboard unless an operator runs something. It assumes the current, scaled-down architecture: local storage, explicit writes, no public endpoint.

## What Herald is

Herald is this repo's dream-to-deck bridge CLI (`herald deck ...`, syncing Claude Design decks against `docs/dreams/` and `presentations/`) **and** the CLI + web surface for the "Four Moments" — the operator-facing story of a PyForge Guild station's work over time:

| Moment | Name | What it is |
|---|---|---|
| 1 | **Pitch** | The deck itself. The web dashboard's Pitch tab links out to this repo; there is no in-app panel for it. |
| 2 | **Progress** | Periodic snapshots of what a station shipped, and at what cost (compute hours, token spend, wall-clock hours). |
| 3 | **Success** | A published claim: a thesis about an outcome, backed by evidence links (test results, metrics, adoption signals). |
| 4 | **Operations** | Operational notices: deprecations, fixes, end-of-life announcements, with a lifecycle (draft → published → closed) and an archive. |

The deck workflow is covered in [presentation deck](../how-to/presentation-deck.md). The rest of this page is about Moments 2 to 4.

## How a record gets created

Every record in Moments 2-4 is created one of two ways:

- **An operator runs an explicit `herald` command.** This is the everyday path: see [How to record progress, claims and notices with Herald](../how-to/record-progress-claims-and-notices-with-herald.md).
- **The HMAC-verified webhook handlers** (Story 13.4), mounted behind a real `daphne` ASGI host (Story 13.6). As of Story 19.2 that host runs on your own machine, loopback only: the platform host forwards the two webhook routes to steward's mcp-host sidecar, where herald's webhook writes to your primary checkout's `.herald/herald.db`. See [Run Herald's live backend locally](../how-to/run-herald-live-backend-locally.md) and the [webhook endpoint reference](../reference/herald-webhook-endpoint.md).

The webhook path is additive, not a replacement: an operator can still create every record by hand.

`herald scheduler run` (Story 13.5) keeps evidence validation and the progress snapshot current, and an operator can point an optional local `cron` entry at it. `archive/docs/dreams/herald-moments-2-4-live-backend.md` holds the fuller, live-backend version of this system that has not been fully built, and why.

## Where the data lives

There is no REST API. There is a local database (Story 13.3): `.herald/herald.db` under the directory you run `herald` from, so the repo root when you run it through `pixi run` from there (`success` and `scheduler run` also accept `--repo-root`; `progress` and `notice` always use the current directory). It is a single SQLite file: no server, no network. Operations notices additionally write a git-tracked markdown mirror under `notices/`.

The database runs in WAL mode, so a backup or restore of `.herald/herald.db` must include any `.herald/herald.db-wal`/`.herald/herald.db-shm` sidecar files present alongside it, taken while no `herald` process is running.

## Two surfaces, and why the dashboard can be stale

- **The CLI** (`herald`) is the everyday way an operator's own checkout gets a new record written into it.
- **The web dashboard** (`src/shared/packages/pyforge-herald/web/`, run with `npm run dev` from that directory) is a read-only, static view over pre-generated JSON snapshots of what the CLI has written. See the [web dashboard reference](../reference/herald-web-dashboard.md).

The CLI write and the web snapshot are two separate steps by design. The dashboard reads separately-exported static JSON copies, not the database itself, so after a write it keeps showing the previous state until the matching exporter runs. Nothing breaks and nothing warns.

## Why a merge does not record itself in your checkout

The webhook runs only when you run it: nothing delivers merges to your checkout on its own. To record a real landing, start the local host and sidecar and run `herald-ship-local`, or run `herald progress <station> --update` (or `herald success create`) by hand.

Story 13.6's CI demo is archived as `archive/.github/workflows/herald-live-demo.yml` (Story 36.1). While it ran, it wrote each job into a throwaway store on the runner and never into any checkout's real `.herald/herald.db`.

Two properties of the webhook are worth knowing regardless:

- An `on-ship` delivery *replaces* the whole day's record for that station, so a same-day CLI entry and a same-day webhook delivery overwrite each other rather than merge.
- Holding the webhook secret grants progress-write access that the CLI grants only to a verified operator.

There is no publicly reachable URL, by the operator's ruling. Steward's `deploy perimeter` renders any ASGI callable it is given (`--asgi-application`, steward Story 86.1, which closed DW-13-6-1).

## Why the scheduler is a local cron entry, not a workflow

`.herald/` is gitignored, per-operator state. A GitHub-hosted runner has no access to it and would run `herald scheduler run` against an empty database every time. The documented trigger is therefore an operator-installed local `crontab` entry, and a missed run (the machine was off, the entry was never installed) is a real, if narrow, failure mode.

## Which stations Progress knows

`warden`, `atlas`, `marshal`, `mason`, `doctor`, `scribe`, `steward`, `herald`. The list only powers a "did you mean" error on an unrecognized station name when reading. Recording progress for a station outside the list is not blocked.
