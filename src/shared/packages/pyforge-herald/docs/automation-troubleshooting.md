# Herald "Automation" Troubleshooting Guide

Story 12.4 (honestly scoped). The original epics spec for this story asked
for "webhook not firing," "cron job missed," "auto-extract failed," and
"stale link warning" diagnoses. "Webhook not firing" now genuinely can
happen, but only inside a specific, bounded surface: Story 13.4 built and
fully unit-tested an HMAC-verified webhook handler
(`src/pyforge/herald/webhook.py`, see
[`cli-runbooks.md`](cli-runbooks.md#the-webhook-endpoint-ci-calls-story-134)),
and Story 13.6 mounted it for real behind `daphne`
(`src/pyforge/herald/webhook_host.py`) — but the ONLY place that host runs
is inside `.github/workflows/herald-live-demo.yml`'s three demonstration
jobs (`on-ship`/`on-pr-close`/`scheduler-demo`), each against its own
scratch, job-local database. There is still no persistent, always-
listening endpoint outside CI for a delivery to fail to reach — "the
webhook isn't firing against MY checkout" is not a bug, it is the
documented boundary (see the [`cli-runbooks.md`](cli-runbooks.md#what-is-not-a-failure-mode-here)
troubleshooting note this section doesn't repeat). What CAN genuinely
fail now, and is worth a section of its own below, is the CI job itself:
[Webhook demo job failing in CI](#webhook-demo-job-failing-in-ci). See
`docs/dreams/herald-moments-2-4-live-backend.md` for the fuller,
live-backend design this is working toward (a persistent host every
checkout shares) — Steward's `deploy perimeter` gaining the ability to
target an arbitrary ASGI callable is the tracked deferred-work gap ahead
of that. "Cron job missed" is a real, if narrow, possibility: Story 13.5
added `herald scheduler run` plus a documented, *opt-in* local `crontab`
entry for an operator's own real database (see
[`cli-runbooks.md`](cli-runbooks.md#how-to-run-the-scheduled-job-evidence-revalidation-and-progress-snapshot)) —
an operator who never installed that entry has nothing to miss, but one
who did and whose machine was off (or whose cron daemon isn't running)
genuinely misses a scheduled revalidation. `herald-live-demo.yml`'s own
`scheduler-demo` job is a separate, unattended proof against its own
scratch data, not a substitute for that cron entry. Neither caveat is
repeated per section below.

What else exists today, and can genuinely misbehave, is the CLI-triggered
equivalent of each of those automations — including "auto-extract" (see
below): Epic 9's `herald success create` is a standing, operator-run
alternative that does the same storage work the `on-pr-close` webhook
handler does, for an operator who wants a record in their own checkout
right now rather than waiting on CI. This guide covers those real,
reproducible failure modes.

## Webhook demo job failing in CI

**Symptom:** `herald-live-demo.yml` (Story 13.6) is red on the Actions
tab, in one of its three jobs.

- **`on-ship`/`on-pr-close` fail at "Start the webhook host (daphne)"
  with "daphne never started listening":** almost always
  `HERALD_WEBHOOK_SECRET` is not configured as a repo secret yet (an
  operational step outside this story's Surface) —
  `webhook_host.application` raises at daphne startup
  (`webhook.resolve_webhook_secret`'s own "never a default fallback"
  guard), so the process exits before ever binding the port, and the
  step's own readiness loop times out and fails loudly rather than
  hanging. Check the step's own `cat daphne-*.log` output in the job log
  for the actual traceback. Configure the secret (`gh secret set
  HERALD_WEBHOOK_SECRET --repo rxm7706/local-recipes`) and re-run.
- **`on-ship` silently does nothing (job green, no POST step ran):** the
  triggering commit's subject matched neither this repo's own
  `bmad-loop`-merge convention nor the `<station>: story N.N` convention
  (`pyforge.doctor.sources.fleet_scan`'s own `_LOOP_DONE`/`_QUALIFIED_STORY`
  patterns) — check the "Derive station + story" step's own log line
  (`subject: ... matched: False ...`). This is the documented, intentional
  no-op (Boundaries & Constraints: "A commit matching neither pattern is
  not a ship"), not a bug — an ordinary docs/chore push looks exactly like
  this.
- **`on-pr-close` returns 400:** the payload's `project_name` came back
  blank (an untitled PR) — the job derives it from
  `github.event.pull_request.title`, and a PR with no title cannot name a
  claim.
- **`scheduler-demo` fails its own JSON assertion:** `claims_checked != 1`
  or `broken_evidence_claim_ids` is non-empty means the seeded evidence URL
  (this repo's own GitHub page) failed to validate — check for a genuine
  GitHub outage or a runner-side network problem before assuming a code
  regression; this URL does not change.

## Stale or broken evidence links (the `herald success validate` scope)

**What it replaces:** the original spec's weekly async re-validation
cron, which would silently re-check every published claim's evidence and
presumably alert on breakage. There is still no operator-alert delivery
(email/Slack/etc. is explicitly out of this story's scope too), but the
revalidation half is now real: `herald scheduler run` (Story 13.5) makes
the same `claims.revalidate_all` call this section's `herald success
validate` does, composed with the progress snapshot export, and can be
put on a local cron cadence (see
[`cli-runbooks.md`](cli-runbooks.md#how-to-run-the-scheduled-job-evidence-revalidation-and-progress-snapshot)).
An operator can still just run `herald success validate` by hand whenever
they want a one-off check.

### Diagnosis

*(The claim id below, `a17e2b60-...`, is from a separate scratch session
than the ones in `cli-runbooks.md`/`operator-guide.md` — every `herald
success create` mints a fresh UUID, so ids don't match across these docs'
independently-captured examples. This one's evidence is deliberately
broken to demonstrate `validate`; the other docs' examples use clean
evidence to demonstrate the happy path.)*

```
$ herald success validate --all
revalidated evidence for 2 claim(s)
```

This never fails loud on its own (its whole point is to surface breakage,
not reject it) — it updates each evidence item's `validated`/
`validated_at` fields in place. To see what actually broke, follow up with
`herald success get <claim-id>` or `herald success review <claim-id>`,
which show each item's `(validated)`/`(unvalidated)` status:

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

`herald success validate` takes exactly one of `<claim-id>` or `--all` —
supplying both, or neither, is a usage error:

```
$ herald success validate --all a17e2b60-...
herald: HeraldError: herald success validate: supply exactly one of <claim-id> or --all
```

The web dashboard's Success tab also shows this per-item, live from the
last export: a ✗ badge means "this link may be broken," a ⚠ badge means
"hasn't been validated recently; review it" (i.e. `validated=false`
without ever being explicitly rechecked). See
[`web-ux-guide.md`](web-ux-guide.md#success-tab).

### Fix

Evidence on an already-published claim cannot be edited in place through
this CLI today (there is no `herald success edit-evidence` or similar).
The practical remedy: fix the broken URL at its source (the linked
system), then re-run `herald success validate <claim-id>` to confirm it
now resolves. If the link is permanently gone, note it in a follow-up
notice/comment — there is no supported way to remove an evidence item from
a published claim.

**Distinct from a *publish-time* failure.** `herald success publish`
itself also validates evidence, but does so *before* writing anything —
see [`cli-runbooks.md`](cli-runbooks.md#evidence-link-validation-failure)
for that case, which is a hard abort (`EvidenceLinkError`, exit 1, claim
stays a draft), not a soft flag like `validate` produces on an already-
published claim.

## "Auto-extract failed" (the `herald success create` scope)

**What it replaces:** the original spec's PR-close webhook, which would
auto-extract a draft claim's `project_name`/`shipped_date`/evidence from
CI's payload the moment a PR merged with all gates green. Story 13.4 built
that webhook handler (`on-pr-close`), and Story 13.6 mounted it for real
behind `daphne` inside `herald-live-demo.yml`'s CI-contained demo jobs
(see [`cli-runbooks.md`](cli-runbooks.md#the-webhook-endpoint-ci-calls-story-134))
— but since each demo job's database is scratch and job-local, an
operator who wants a claim in their OWN checkout still runs
`herald success create <project>` by hand, supplying the same fields
explicitly via flags (see
[`cli-runbooks.md`](cli-runbooks.md#how-to-publish-a-success-claim) for the
full create -> review -> publish walkthrough).

### Diagnosis

There is no "extraction" step to fail — `create` either succeeds (a draft
claim is written) or refuses with a `HeraldError` naming what's wrong.
Two real failure modes:

- **Empty/whitespace-only project name** — refused before any write:
  ```
  $ herald success create "   "
  herald: HeraldError: project_name must not be empty
  ```
  Fix: supply a real project name.

`create` takes evidence via three fixed flags — `--evidence-test-results`,
`--evidence-metrics`, `--evidence-adoption` — each a URL string for that
evidence type; there's no free-form evidence-type flag to mistype, and no
validation of the URLs themselves happens at create time (that's
`success publish`'s job — see [`cli-runbooks.md`](cli-runbooks.md#evidence-link-validation-failure)).

Once created, review the draft with `herald success review <claim-id>`
before publishing (see [`cli-runbooks.md`](cli-runbooks.md#how-to-publish-a-success-claim))
to catch anything the create step accepted but shouldn't have (a wrong
project name, a mistyped evidence URL) before it becomes a published,
citable record.

## Malformed local storage file (the `HeraldError` a corrupt `.herald/herald.db` raises)

**What it replaces:** database-level integrity checks/alerts a real
persistence layer would have — Story 13.3 made this literally true.
Progress/Success/Operations' storage (Notices' markdown mirror aside) is
one shared SQLite database, `.herald/herald.db`; "corruption" means the
database file itself doesn't open, or a nested JSON column
(`shipped_capabilities`/`evidence`/`edit_history`/`revisions`) doesn't
parse.

### Diagnosis

Any read or write against a broken database raises a plain `HeraldError`
naming the file and the problem, exit code 1:

```
$ herald success list
herald: HeraldError: /path/to/.herald/herald.db is not a valid database: file is not a database
```

This is reproducible: truncate or overwrite `.herald/herald.db` with
garbage bytes, and every subsequent `herald` command touching it fails the
same way until it's fixed. A repo still carrying pre-Story-13.3
`.herald/progress.json`/`claims.json`/`notices-index.json` that has never
been migrated fails the same way if one of THOSE is corrupt -- the
one-time legacy import raises naming the specific legacy file.

### Fix

- Restore `.herald/herald.db` from a backup (it is operator-local state,
  not committed to git). The database runs in WAL mode, so a full
  backup/restore must include any `.herald/herald.db-wal`/
  `.herald/herald.db-shm` sidecar files present alongside it, taken while
  no `herald` process is running.
- There is no repair or recovery tool built into `herald` for this.

### Two adjacent failures that are NOT corruption

Both name the database and exit 1 the same way, so they read like the
above at a glance. Neither is fixed by restoring a backup:

```
$ herald success list
herald: HeraldError: /path/to/.herald/herald.db has user_version=2, newer
than this build's latest known migration (1); refusing to overwrite or
downgrade it -- upgrade herald, or point at a different database
```

The database was written by a **newer** `herald` than the one running --
usually an accidental downgrade (an older environment activated, an older
build on `PATH`). `herald` refuses rather than guessing, so nothing is
damaged. Fix: run the newer build, or point at a different database.

```
$ herald progress mason
herald: HeraldError: /path/to/.herald/herald.db: legacy data could not be
imported: UNIQUE constraint failed: progress.station, progress.date
```

Only on the first run against a pre-Story-13.3 repo: the one-time import of
`.herald/{progress,claims,notices-index}.json` hit data the new schema
rejects (here, two `progress.json` records sharing a `(station, date)`).
The whole migration rolls back, so nothing is half-imported and every later
command retries it. Fix: correct the offending legacy file, or move it
aside to skip importing it -- the database itself is fine.

## Stale web snapshot (no live API to "miss" — a manual export that wasn't re-run)

**What it replaces:** the "operator alerts for automation failures" AC.
There is nothing to alert on here because there is no automation to fail —
the web dashboard is a static bundle reading pre-generated JSON, and it is
the operator's job to regenerate that JSON after a CLI write. See
[`web-ux-guide.md`](web-ux-guide.md) for the full explanation and the
per-Moment regeneration commands.

### Diagnosis

The dashboard shows **old data with no error** — this is the most common
and least obvious of the three failure modes in this guide, because
nothing actually breaks. Symptoms:

- You ran `herald progress <station> --update` (or `success publish`, or
  `notice publish`) and the corresponding web tab still shows the
  previous state, or an empty state you thought you'd already cleared.
- `herald <moment> list` (or `get`) at the CLI shows the new/updated
  record, confirming the write itself succeeded.

If instead the panel shows an explicit **error state** ("Could not load
progress.json." / "Could not load success claims." / "Could not load
operations notices."), that's a different, harder failure — the snapshot
file is missing entirely or fails to parse as JSON. All three exporters
(`scripts/export_progress_snapshot.py`, `scripts/export_web_snapshot.py`,
`scripts/export_notices_snapshot.py`) raise on read failure — trace that
back to [Malformed local storage file](#malformed-local-storage-file-the-heralderror-a-corrupt-heraldheralddb-raises)
above if the underlying `.herald/herald.db` itself is broken.

### Fix

Re-run the exporter for whichever Moment changed:

| Moment | Command |
|---|---|
| Progress | `npm run sync-progress` (from `web/`) |
| Success | `python scripts/export_web_snapshot.py --repo-root <repo-root>` |
| Operations | `python scripts/export_notices_snapshot.py --repo-root <repo-root>` |

Then reload the page (or re-run `npm run dev`/`build`, which re-syncs
Progress automatically via its `predev`/`prebuild` hook — Success and
Operations still need the manual step either way, since only Progress's
exporter is wired into an npm script).
