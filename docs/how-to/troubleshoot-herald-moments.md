---
sources:
  - src/shared/packages/pyforge-herald/src/pyforge/herald/cli.py
  - src/shared/packages/pyforge-herald/src/pyforge/herald/auth.py
  - src/shared/packages/pyforge-herald/src/pyforge/herald/db.py
  - src/shared/packages/pyforge-herald/src/pyforge/herald/evidence.py
  - src/shared/packages/pyforge-herald/tests/unit/test_auth.py
verified: 2026-11-17
---

# How to troubleshoot Herald's progress, claims and notices

Use this page to diagnose a `herald progress`, `herald success`, `herald notice` or `herald scheduler` command that refused, a claim whose evidence went bad, a broken local store, or a web dashboard that shows old data. Each section gives the exact error text, what it means and the fix.

## When to use this

- A write refused with `OperatorAuthorizationError`.
- `herald success publish` failed with `EvidenceLinkError`, or a published claim's evidence may have gone stale.
- A command fails with `HeraldError` naming `.herald/herald.db`.
- The dashboard still shows the previous state after a write.
- A landing or a scheduled run you expected is not in your store.

> [!NOTE]
> **Prerequisites.** Run `herald` through its pixi environment from the repo root, as in [How to record progress, claims and notices with Herald](record-progress-claims-and-notices-with-herald.md). For failures of the local webhook host and sidecar (a `401`, `404`, `502`, `503`, or DW-13-6-2's repeated timeouts), start from the Troubleshooting table in [Run Herald's live backend locally](run-herald-live-backend-locally.md) instead.

## Operator-role refusal

If neither `HERALD_TOKEN` nor `~/.herald/config` resolves an auth context, a write refuses with exit code 1:

```
herald: OperatorAuthorizationError: auth context missing. Configure with `herald auth login` or set HERALD_TOKEN env var
```

That message names `herald auth login`, but no such subcommand exists: `herald --help` lists only `deck`, `progress`, `success`, `notice` and `scheduler`. The wording is locked to Story 6.3's acceptance criteria and its test (`src/shared/packages/pyforge-herald/tests/unit/test_auth.py`). Ignore that half of the message and set `HERALD_TOKEN=operator:<anything>`, or write `~/.herald/config` with `{"role": "operator"}`.

If a role resolves but is not `operator` (e.g. `HERALD_TOKEN=viewer:x`), the refusal is more specific:

```
herald: OperatorAuthorizationError: unauthorized: operator role required (found role 'viewer')
```

## Evidence link fails at publish time

`herald success publish` validates every evidence link before writing. A broken link aborts the publish entirely: nothing is persisted and the claim stays a draft.

```
$ herald success publish a17e2b60-... --thesis "Shipped it"
Continue? [Y/n] y
herald: EvidenceLinkError: claim 'a17e2b60-...' has 1 broken evidence link(s): https://example.com/nonexistent-9999 (Evidence link broken: https://example.com/nonexistent-9999. Fix or remove before publishing.). Fix or remove before publishing.
```

Exit code 1. Fix the URL at its source and re-run `herald success review <claim-id>` to confirm, or drop the offending evidence and re-`create` the claim. There is no "edit evidence on an existing draft" subcommand.

## Stale or broken evidence on a published claim

`herald success validate` never fails loud on its own (its whole point is to surface breakage, not reject it). It updates each evidence item's `validated`/`validated_at` fields in place. `herald scheduler run` makes the same `claims.revalidate_all` call. There is no operator-alert delivery (email, Slack) in this repo.

```
$ herald success validate --all
revalidated evidence for 2 claim(s)
```

To see what actually broke, follow up with `herald success get <claim-id>` or `herald success review <claim-id>`, which show each item's `(validated)`/`(unvalidated)` status:

```
$ herald success review a17e2b60-4c8f-4e11-9d02-f6a3b0d8c721
...
evidence:
  - [test_results] test results: https://example.com/nonexistent-9999 (unvalidated)
```

Or check a single claim directly:

```
$ herald success validate a17e2b60-4c8f-4e11-9d02-f6a3b0d8c721
revalidated claim a17e2b60-4c8f-4e11-9d02-f6a3b0d8c721: 0/1 evidence link(s) valid
```

`herald success validate` takes exactly one of `<claim-id>` or `--all`. Supplying both, or neither, is a usage error:

```
$ herald success validate --all a17e2b60-...
herald: HeraldError: herald success validate: supply exactly one of <claim-id> or --all
```

The dashboard's Success tab also shows this per item, as of the last export: a ✗ badge means "this link may be broken," a ⚠ badge means "hasn't been validated recently; review it".

**Fix.** Evidence on an already-published claim cannot be edited in place through this CLI. Fix the broken URL at its source (the linked system), then re-run `herald success validate <claim-id>` to confirm it now resolves. If the link is permanently gone, note it in a follow-up notice: there is no supported way to remove an evidence item from a published claim.

## `herald success create` refuses

There is no "extraction" step to fail: `create` either succeeds (a draft claim is written) or refuses with a `HeraldError` naming what is wrong. An empty or whitespace-only project name is refused before any write:

```
$ herald success create "   "
herald: HeraldError: project_name must not be empty
```

The URL evidence flags are not validated at create time (that is `success publish`'s job). Review the draft with `herald success review <claim-id>` before publishing to catch a wrong project name or a mistyped evidence URL before it becomes a published, citable record.

## Malformed local storage

Progress, Success and Operations share one SQLite database, `.herald/herald.db` (Story 13.3; notices' markdown files under `notices/` are the separate, git-tracked durable copy). A corrupted database file, or a corrupted JSON value inside one of its nested columns (`shipped_capabilities`/`evidence`/`edit_history`/`revisions`), fails loud:

```
$ herald success list
herald: HeraldError: /path/to/.herald/herald.db is not a valid database: file is not a database
```

Exit code 1, on every command touching it until it is fixed. Restore `.herald/herald.db` from a backup (it is operator-local state, not committed). There is no repair tool. The database runs in WAL mode, so a backup or restore must include any `.herald/herald.db-wal`/`.herald/herald.db-shm` sidecar files present alongside it, taken while no `herald` process is running.

A first-ever run against a pre-Story-13.3 repo importing legacy `.herald/progress.json`/`claims.json`/`notices-index.json` fails the same way, naming the offending legacy file, if one of those is itself corrupt.

## Two store errors that are not corruption

Both name the database and exit 1 the same way. Neither is fixed by restoring a backup.

```
$ herald success list
herald: HeraldError: /path/to/.herald/herald.db has user_version=2, newer
than this build's latest known migration (1); refusing to overwrite or
downgrade it -- upgrade herald, or point at a different database
```

The database was written by a **newer** `herald` than the one running, usually an accidental downgrade (an older environment activated, an older build on `PATH`). `herald` refuses rather than guessing, so nothing is damaged. Run the newer build, or point at a different database. The version numbers in the message are whatever the two builds carry.

```
$ herald progress mason
herald: HeraldError: /path/to/.herald/herald.db: legacy data could not be
imported: UNIQUE constraint failed: progress.station, progress.date
```

Only on the first run against a pre-Story-13.3 repo: the one-time import of `.herald/{progress,claims,notices-index}.json` hit data the new schema rejects (here, two `progress.json` records sharing a `(station, date)`). The whole migration rolls back, so nothing is half-imported and every later command retries it. Correct the offending legacy file, or move it aside to skip importing it. The database itself is fine.

## Stale web snapshot

The dashboard shows **old data with no error**. This is the most common and least obvious failure here, because nothing actually breaks:

- You ran `herald progress <station> --update` (or `success publish`, or `notice publish`) and the corresponding web tab still shows the previous state, or an empty state you thought you had already cleared.
- `herald <moment> list` (or `get`) at the CLI shows the new record, confirming the write itself succeeded.

Re-run the exporter for whichever Moment changed (step 5 of [How to record progress, claims and notices with Herald](record-progress-claims-and-notices-with-herald.md)), then reload. `npm run dev`/`build` re-syncs Progress automatically; Success and Operations always need the manual step.

If instead the panel shows an explicit **error state** ("Could not load progress.json." / "Could not load success claims." / "Could not load operations notices."), the snapshot file is missing or fails to parse as JSON. All three exporters raise on a read failure, so trace that back to the malformed-storage section above if the underlying `.herald/herald.db` is broken. The states are listed in the [web dashboard reference](../reference/herald-web-dashboard.md).

## Usage errors

`--date-range` takes `<start>..<end>` as `YYYY-MM-DD..YYYY-MM-DD` (a literal `..` separator). A single date, wrong format, or `start > end` all fail the same way, exit code 1 (not argparse's exit 2, since this is parsed *after* argument parsing):

```
$ herald progress --date-range "2026-08-01"
herald: InvalidDateRangeError: Invalid date format: '2026-08-01'; expected <start>..<end> as YYYY-MM-DD..YYYY-MM-DD
```

`--json`/`-j` (on `progress`, `success`, `notice`, `notice list` and `scheduler run`) switches output to machine-readable JSON: NDJSON for list-shaped output, a single JSON object for single-record output, and a single JSON object on stderr for any error on those paths:

```
$ herald progress --date-range "2026-08-01" --json
{"tool": "herald", "error": "InvalidDateRangeError", "message": "Invalid date format: '2026-08-01'; expected <start>..<end> as YYYY-MM-DD..YYYY-MM-DD"}
```

An unknown station, claim or notice component is a plain `HeraldError`, exit code 1, with the valid set named in the message:

```
$ herald progress bogus-station
herald: HeraldError: Station 'bogus-station' not found. Available: warden, atlas, marshal, mason, doctor, scribe, steward, herald. Use --list to see recorded stations.
```

That check exists to catch a probable typo on a read; `herald progress <station> --update` itself records progress for a station outside the list.

An unknown subcommand or flag is an argparse-level usage error, exit code 2. Running `herald` with no arguments at all exits 1:

```
$ herald bogus
usage: herald [-h] [--version] command ...
herald: error: unknown command 'bogus'; valid subcommands: 'deck', 'progress', 'success', 'notice', 'scheduler'
See --help for available options.

$ herald
usage: herald [-h] [--version] command ...
herald: error: no command given; valid subcommands: deck, progress, success, notice, scheduler
```

## What is not a failure

**"My local `.herald/herald.db` has no record of a landing" is not a bug.** Nothing delivers landings to your checkout on its own. To record a landing in *your* store, deliver it through the local host and sidecar with `herald-ship-local` (see [Run Herald's live backend locally](run-herald-live-backend-locally.md)), or run the CLI command yourself. The reasons are in [Herald's Four Moments](../explanation/herald-four-moments.md).

A *missed* run of the local scheduler cron entry (the machine was off, the entry was never installed) is a real, if narrow, failure mode. An operator who never installed the entry has nothing to miss.

The CI live-demo workflow that once exercised the webhook and the scheduler is archived (`archive/.github/workflows/herald-live-demo.yml`, Story 36.1), so its job failures no longer occur.

## Escalation path

1. Check this page for the specific error text you are seeing.
2. If the failure looks like it should have been automatic (a webhook, a cron job, an email or in-app alert), read [Herald's Four Moments](../explanation/herald-four-moments.md) and `archive/docs/dreams/herald-moments-2-4-live-backend.md` first: the gap is very likely the documented, intentional scope cut, not a bug. Deferred items are tracked in `_bmad-output/projects/pyforge-herald/planning-artifacts/deferred-work-ledger.md`.
3. Otherwise, file an issue against `rxm7706/local-recipes` describing the exact command, flags, and error text (or JSON, if `--json` was used). There is no separate Herald issue tracker or team inbox.
