# Herald Operator Guide — Getting Started

Story 12.3. What Herald is, the Four Moments, a realistic how-to for each
of Progress/Success/Operations with real command output, and an FAQ for
the confusions the scaled-down (no live backend) architecture actually
produces.

## What is Herald?

Herald is this repo's dream-to-deck bridge CLI (`herald deck ...`, syncing
Claude Design decks against `docs/dreams/` and `presentations/`) **and**
the CLI + web surface for the "Four Moments" — the operator-facing story
of a PyForge Guild station's work over time:

1. **Pitch** — the deck itself (the web dashboard's Pitch tab links out to
   this repo directly; there's no separate in-app panel for it).
2. **Progress** (Moment 2) — periodic snapshots of what a station shipped,
   and at what cost (compute hours, token spend, wall-clock hours).
3. **Success** (Moment 3) — a published claim: a thesis about an outcome,
   backed by evidence links (test results, metrics, adoption signals).
4. **Operations** (Moment 4) — operational notices: deprecations, fixes,
   end-of-life announcements, with a lifecycle (draft → published →
   closed) and an archive.

**Architecture, in one sentence:** every record in Moments 2-4 is created
either by an operator running an explicit `herald` command, or by the
HMAC-verified webhook handlers Story 13.4 built, mounted behind a real
`daphne` ASGI host as of Story 13.6 (see
[`cli-runbooks.md`](cli-runbooks.md#the-webhook-endpoint-ci-calls-story-134))
— but the ONLY place that webhook host runs today is inside
`.github/workflows/herald-live-demo.yml`'s bounded, CI-contained
demonstration jobs, each writing to its own scratch database that is
discarded when the job ends, never a persistent host an operator's own
checkout can reach. A local SQLite database (`.herald/herald.db`, Story
13.3) backs *your* real storage, and `herald scheduler run` (Story 13.5)
keeps evidence validation and the progress snapshot current — an operator
can point an optional local `cron` entry at it
(see [`cli-runbooks.md`](cli-runbooks.md#how-to-run-the-scheduled-job-evidence-revalidation-and-progress-snapshot)).
See `docs/dreams/herald-moments-2-4-live-backend.md` for the fuller,
live-backend version of this system that hasn't been fully built yet, and
why.

Two surfaces exist side by side:

- **The CLI** (`herald`) — the only way an operator's own checkout gets a
  new record written into it. (The webhook can also write a record, but
  only inside the CI demo's own throwaway database — see above.)
- **The web dashboard** (`web/`, run with `npm run dev` from
  `src/shared/packages/pyforge-herald/web/`) — a read-only, static view
  over pre-generated JSON snapshots of what the CLI has written. See
  [`web-ux-guide.md`](web-ux-guide.md) for the full tour, especially the
  "you must re-export the snapshot" caveat.

## Prerequisites: getting `herald` on your command line

`herald` is not on `PATH` in a bare shell -- it's a console-script entry
point inside this repo's `pyforge-herald` pixi environment. Every command
in this guide (and the other three docs) assumes one of:

```
$ pixi run --frozen -e pyforge-herald herald <subcommand> ...
```

or, for a whole session instead of prefixing every command:

```
$ pixi shell -e pyforge-herald
(pyforge-herald) $ herald <subcommand> ...
```

Run either from the repo root. If `herald <subcommand>` on its own returns
"command not found," this is almost always why -- you're in a bare shell,
not the `pyforge-herald` pixi environment.

## Per-Moment how-to

All output below is real, captured by running the built `herald` binary
(`pixi run --frozen -e pyforge-herald herald ...`) in a scratch directory
on 2026-08-08.

### Progress

Record today's progress for a station (requires the operator role — see
[`cli-runbooks.md`](cli-runbooks.md#satisfying-the-operator-role-gate)):

```
$ export HERALD_TOKEN=operator:x
$ herald progress warden --update \
    --shipped "Harness Policy" --compute-hours 3.5 \
    --token-spend 42000 --wall-clock-hours 6
Unblock narrative for warden on 2026-08-08 (blank for none): none
Progress updated for warden
```

`--unblock-narrative` can be given on the command line instead of
prompted interactively; `--shipped` is repeatable for multiple shipped
capabilities in one update.

Read it back:

```
$ herald progress warden
station: warden
date: 2026-08-08
shipped_capabilities: Harness Policy
compute_hours: 3.5
token_spend: 42000
wall_clock_hours: 6.0
unblock_narrative: none
```

List everything (no auth required — reads are always public):

```
$ herald progress
2026-08-08  warden  1 capabilities  compute=3.5h  token_spend=42000  wall_clock=6.0h
```

Filter with `--station`/`--date-range`, or get NDJSON with `--json`.

**Web tab:** Progress. After `--update`, run `npm run sync-progress` (or a
full `npm run dev`/`build`) inside `web/` to see it reflected — see
[`web-ux-guide.md`](web-ux-guide.md).

### Success

Create a draft claim, review its evidence, then publish it:

```
$ herald success create "Marshal S-1.10" --evidence-metrics https://dash.example/marshal
created draft claim 9c3590d4-01d9-4797-8a43-bf2b3b654195 for 'Marshal S-1.10'
review with: herald success review 9c3590d4-01d9-4797-8a43-bf2b3b654195

$ herald success review 9c3590d4-01d9-4797-8a43-bf2b3b654195
claim 9c3590d4-01d9-4797-8a43-bf2b3b654195: Marshal S-1.10 (status=draft)
shipped: 2026-08-08
thesis: (none yet)
evidence:
  - [metrics] metrics: https://dash.example/marshal (unvalidated)
to publish: herald success publish 9c3590d4-01d9-4797-8a43-bf2b3b654195 --thesis "..."

$ export HERALD_TOKEN=operator:x
$ herald success publish 9c3590d4-01d9-4797-8a43-bf2b3b654195 --thesis "Shipped the harness policy gate"
Continue? [Y/n] y
published claim 9c3590d4-01d9-4797-8a43-bf2b3b654195 for Marshal S-1.10 on 2026-08-08
```

**Web tab:** Success. Run `python scripts/export_web_snapshot.py
--repo-root <repo-root>` after publishing to refresh it — nothing does
this automatically. Full walkthrough (including what a broken evidence
link does at publish time): [`cli-runbooks.md`](cli-runbooks.md#how-to-publish-a-claim-success-proclamation).

### Operations

Author and publish a deprecation notice in one step:

```
$ export HERALD_TOKEN=operator:x
$ herald notice author --type deprecation --component auth-api-v1 \
    --what "Old auth API" --why "Superseded by v2" \
    --migration "Switch to /v2/auth" --deadline 2026-09-01 --publish
Continue? [Y/n] y
authored notice 'auth-api-v1' (published) -> notices/2026-08/deprecation/auth-api-v1.md

$ herald notice list
[published] deprecation/auth-api-v1 (deadline 2026-09-01)
```

**Web tab:** Operations. Run `python scripts/export_notices_snapshot.py
--repo-root <repo-root>` after authoring/publishing/closing a notice.
Full walkthrough: [`cli-runbooks.md`](cli-runbooks.md#how-to-author-a-notice).

## FAQ

**Q: Why doesn't a PR merge against MY OWN checkout automatically show up
in `herald progress`/`herald success list`?**

Because the webhook that does this (Story 13.4, mounted for real behind
`daphne` as of Story 13.6 — see
[`cli-runbooks.md`](cli-runbooks.md#the-webhook-endpoint-ci-calls-story-134))
only runs inside `.github/workflows/herald-live-demo.yml`'s bounded,
CI-contained demonstration jobs, each writing into its OWN scratch
database that is discarded the moment the job ends — never a persistent
host, and never your checkout's real `.herald/herald.db`. Run
`herald progress <station> --update` (or `herald success create`) by hand
for a record you actually want to keep. Two things worth knowing about
the webhook's own behavior regardless: an `on-ship` delivery *replaces*
the whole day's record for that station, so a same-day CLI entry and a
same-day webhook delivery would overwrite each other rather than merge;
and holding the webhook secret grants progress-write access that the CLI
grants only to a verified operator. The fuller live-backend version this
is working toward — a persistent host every checkout shares — is captured
in `docs/dreams/herald-moments-2-4-live-backend.md`; making Steward's
`deploy perimeter` able to target an arbitrary ASGI callable (it only
renders a hardcoded Django placeholder today) is tracked as deferred
work.

**Q: I ran `herald success publish`, but the web dashboard still shows the
old data (or nothing). Is the write broken?**

No — the CLI write and the web snapshot are two separate steps by design.
Re-run the matching exporter (`python scripts/export_web_snapshot.py` for
Success, `python scripts/export_notices_snapshot.py` for Operations, `npm
run sync-progress` for Progress). See [`web-ux-guide.md`](web-ux-guide.md).

**Q: I get `auth context missing. Configure with 'herald auth login' or
set HERALD_TOKEN env var` — where's `herald auth login`?**

It doesn't exist yet; `herald --help` only lists `deck`, `progress`,
`success`, `notice`. Ignore that half of the message and set
`HERALD_TOKEN=operator:<anything>` (or write `~/.herald/config` with
`{"role": "operator"}`) instead. Documented as a known wording gap in
[`cli-runbooks.md`](cli-runbooks.md#satisfying-the-operator-role-gate).

**Q: `herald success publish` failed with `EvidenceLinkError` — did it
publish partially?**

No. Evidence links are validated *before* anything is written; a broken
link aborts the whole publish with nothing persisted. Fix the link (or
drop it and re-`create` the claim) and try again.

**Q: How do I know if a published claim's evidence is still good weeks
later?**

Run `herald success validate <claim-id>` or `herald success validate
--all` by hand, or install `herald scheduler run` (Story 13.5) as a
weekly `crontab` entry so it happens without remembering — see [How to
run the scheduled job](cli-runbooks.md#how-to-run-the-scheduled-job-evidence-revalidation-and-progress-snapshot)
in `cli-runbooks.md` and
[`automation-troubleshooting.md`](automation-troubleshooting.md).

**Q: Where's the REST API / database?**

There's no REST API. There is a local database (Story 13.3): `.herald/herald.db`
in the repo root (or wherever `herald` was run from) is where
Progress/Success/Operations' storage lives — a single SQLite file, no
server, no network. Operations Notices additionally write a git-tracked
markdown mirror under `notices/`. The web dashboard reads
separately-exported static JSON copies, not the database itself. It runs
in WAL mode, so a backup or restore of `.herald/herald.db` must include
any `.herald/herald.db-wal`/`.herald/herald.db-shm` sidecar files present
alongside it, taken while no `herald` process is running.

**Q: Which stations does `herald progress` know about?**

`warden`, `atlas`, `marshal`, `mason`, `doctor`, `scribe`, `steward`,
`herald` — this list only powers a "did you mean" error message on an
unrecognized station name; recording progress for a station outside this
list is not actually blocked.
