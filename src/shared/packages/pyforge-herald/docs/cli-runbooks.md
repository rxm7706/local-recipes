# Herald CLI Runbooks & Troubleshooting

Story 12.1. Practical, copy-pasteable walkthroughs for the two most common
operator tasks — authoring a notice and publishing a success claim — plus a
troubleshooting section for the failure modes that actually exist in this
codebase today.

**Scope note.** Herald's Moments 2-4 (Progress/Success/Operations) are
**local-storage** — storage is a local SQLite file, `.herald/herald.db`
(Story 13.3) — and records are created two ways: an operator running an
explicit `herald` command by hand, or the HMAC-verified webhook handlers
Story 13.4 built (`src/pyforge/herald/webhook.py`'s `on-ship`/
`on-pr-close`, see [The webhook endpoint](#the-webhook-endpoint-ci-calls-story-134)
below), mounted behind a real ASGI host as of Story 13.6
(`src/pyforge/herald/webhook_host.py`). **This package still ships no
persistent, always-on webhook listener** — the mount point is
`.github/workflows/herald-live-demo.yml`, a bounded, CI-contained
demonstration that starts `webhook_host:application` behind `daphne` for
one job's lifetime and discards it when the job ends (proven real on
every push to `main`, every PR close, and a weekly schedule), never a
publicly-reachable deployment. An operator can still create every record
by hand at any time; the webhook path is additive, not a replacement.
`herald scheduler run`'s derived-state refresh (Story 13.5, see [How to
run the scheduled
job](#how-to-run-the-scheduled-job-evidence-revalidation-and-progress-snapshot)
below) is likewise proven unattended by that same workflow's
`scheduler-demo` job, though its own documented trigger for a real
checkout remains an operator-local `cron` entry (a GitHub-hosted runner
never has the gitignored `.herald/herald.db` a real repo checkout would).
Persistent, publicly-reachable hosting behind Steward's live perimeter is
tracked as deferred work (`_bmad-output/implementation-artifacts/deferred-work.md`),
not built here. See `docs/dreams/herald-moments-2-4-live-backend.md` for
the fuller live-backend version and why the rest of that scope was cut
down. This runbook documents the system as it exists, not that Dream.

All examples below were captured by actually running `herald` (built via
`pixi run --frozen -e pyforge-herald herald ...`) in a scratch directory.
`herald` is not on `PATH` in a bare shell — see
[`operator-guide.md`'s Prerequisites section](operator-guide.md#prerequisites-getting-herald-on-your-command-line)
if a copy-pasted command below returns "command not found."

## How to author a notice

`herald notice` manages Moment 4 (Operations notices — deprecations,
fixes, EOL announcements). Listing and `get` are read-only and require no
auth; `author`/`publish`/`close`/`archive` write local storage and require
the **operator role** (see [Satisfying the operator-role
gate](#satisfying-the-operator-role-gate) below).

### Draft, then publish (two steps)

```
$ export HERALD_TOKEN=operator:<opaque-token>
$ herald notice author --type deprecation --component auth-api-v1 \
    --what "Old auth API" --why "Superseded by v2" \
    --migration "Switch to /v2/auth" --deadline 2026-09-01
Continue? [Y/n] y
authored notice 'auth-api-v1' (draft) -> notices/2026-08/deprecation/auth-api-v1.md

$ herald notice publish auth-api-v1
Continue? [Y/n] y
published notice 'auth-api-v1'
```

Any flag you omit (`--type`, `--component`, `--what`, `--why`,
`--migration`; `--deadline` is optional) is prompted for interactively
instead — useful when authoring by hand rather than scripting it.

### Author and publish in one step

Add `--publish` to skip the draft stage:

```
$ herald notice author --type deprecation --component auth-api-v1 \
    --what "Old auth API" --why "Superseded by v2" \
    --migration "Switch to /v2/auth" --deadline 2026-09-01 --publish
Continue? [Y/n] y
authored notice 'auth-api-v1' (published) -> notices/2026-08/deprecation/auth-api-v1.md
```

`--type` must be one of `deprecation`, `fix`, `eol` (`notices.NOTICE_TYPES`
in `src/pyforge/herald/notices.py`).

### Read it back

```
$ herald notice get auth-api-v1
[published] deprecation/auth-api-v1 (deadline 2026-09-01)
what: Old auth API
why: Superseded by v2
migration: Switch to /v2/auth
path: notices/2026-08/deprecation/auth-api-v1.md

$ herald notice list
[published] deprecation/auth-api-v1 (deadline 2026-09-01)
```

`herald notice` (bare, no subcommand) is equivalent to `herald notice
list`. Draft notices are excluded from listings by default — pass
`--status draft` or `--status all` to see them.

### Closing and archiving

```
$ herald notice close auth-api-v1 --reason "migration complete"
$ herald notice archive --rename auth-api-v1 auth-api-v2
```

`archive --rename` is bookkeeping only (a redirect record in local
storage) — there is no HTTP server to serve an actual redirect from.

## How to publish a claim (Success proclamation)

`herald success` manages Moment 3. `create` makes a draft -- the same
`claims.create` call the `on-pr-close` webhook handler makes once it is
mounted (see [The webhook endpoint](#the-webhook-endpoint-ci-calls-story-134)
below); until then, this CLI command is the only way to make one.
`review` shows it read-only; `publish` requires the operator role and
validates every evidence link before writing anything.

```
$ herald success create "Marshal S-1.10" \
    --evidence-test-results https://ci.example/run/42 \
    --evidence-metrics https://dash.example/marshal
created draft claim 9c3590d4-01d9-4797-8a43-bf2b3b654195 for 'Marshal S-1.10'
review with: herald success review 9c3590d4-01d9-4797-8a43-bf2b3b654195

$ herald success review 9c3590d4-01d9-4797-8a43-bf2b3b654195
claim 9c3590d4-01d9-4797-8a43-bf2b3b654195: Marshal S-1.10 (status=draft)
shipped: 2026-08-08
thesis: (none yet)
evidence:
  - [test_results] test results: https://ci.example/run/42 (unvalidated)
  - [metrics] metrics: https://dash.example/marshal (unvalidated)
to publish: herald success publish 9c3590d4-01d9-4797-8a43-bf2b3b654195 --thesis "..."

$ export HERALD_TOKEN=operator:<opaque-token>
$ herald success publish 9c3590d4-01d9-4797-8a43-bf2b3b654195 --thesis "Shipped X"
Continue? [Y/n] y
published claim 9c3590d4-01d9-4797-8a43-bf2b3b654195 for Marshal S-1.10 on 2026-08-08
```

`publish` re-checks every evidence link *before* writing anything — see
[Evidence link validation failure](#evidence-link-validation-failure)
below for what happens when one is broken.

`--thesis` is required the first time a claim is published (a claim with
no thesis yet). Evidence links are optional per-type flags on `create`:
`--evidence-test-results`, `--evidence-metrics`, `--evidence-adoption`.

Other read commands: `herald success list [--status draft|published|closed]`
and `herald success get <claim-id>` (full detail, including edit history).

## The webhook endpoint (CI calls, Story 13.4/13.6)

`src/pyforge/herald/webhook.py` is a second, CI-triggered path onto the
same storage `herald progress --update`/`herald success create` write:
an HMAC-verified ASGI3 callable (`webhook.create_app(repo_root, secret)`),
built and fully unit-tested in isolation, and — as of Story 13.6 —
demonstrably real: `src/pyforge/herald/webhook_host.py` mounts it behind
`daphne` (a stable `application` object, `daphne pyforge.herald.webhook_host:application`),
and `.github/workflows/herald-live-demo.yml` starts that host for real on
every push to `main` and every PR close, POSTs a real signed request, and
tears the process down at the end of the job. There is still no
persistent, always-reachable URL to `curl` from outside CI — that
deployment shape stays out of Surface (see the Scope note above) — but
`herald progress --update`/`herald success create` are no longer the
*only* way a record gets created outside a Python test.

The shape:

- **Routes:** `POST /api/herald/webhooks/on-ship` (calls the same
  `progress.upsert` `herald progress <station> --update` calls) and
  `POST /api/herald/webhooks/on-pr-close` (calls the same `claims.create`
  `herald success create` calls, only when the payload's own `merged` and
  `gates_passed` are both `true` — any other combination is a 202 no-op,
  never an error). Mounted under a prefix, the routes are served at
  `<prefix>/api/herald/webhooks/...` — per the ASGI spec `path` includes
  `root_path`, and the route literals already begin with `/api`, so
  mounting under `/api` yields `/api/api/herald/webhooks/...`.
- **`on-ship` REPLACES the day's record; it does not merge into it.**
  `progress.upsert` is keyed `(station, date)`, and the handler substitutes
  the CLI's own flag defaults (`[]`/`0.0`/`0`/`0.0`/`""`) for every field
  the payload omits — so a second delivery for one station on one day
  resets whatever the first recorded and is answered `201` either way.
  Send the day's cumulative figures on every delivery, or fire `on-ship`
  once per day rather than once per push. The replace is across *sources*,
  not just across deliveries: one `on-ship` call also overwrites whatever
  an operator entered by hand with `herald progress <station> --update`
  earlier that day. Note also that `station` is
  **not** validated against the known-station list (`progress.upsert`
  accepts any name by design, unlike the CLI, which rejects an
  unrecognized one): a typo'd or unrendered station records a row that no
  station-scoped `herald` command or dashboard will ever surface.
  Surrounding whitespace is stripped, but case is not normalized.
- **Auth:** every request must carry an `X-Hub-Signature-256: sha256=<hex>`
  header AND an `X-Hub-Timestamp: <unix-seconds>` header, the latter folded
  into the signed content itself
  (`hmac.new(secret, timestamp + "." + raw_body, hashlib.sha256)`; hex in
  either case) and rejected if it is more than 5 minutes off the server's
  own clock in either direction — a missing/mismatched signature, a
  missing timestamp, or a stale one is a 401 before the body is even
  parsed as JSON. (Before Story 13.6 the HMAC covered the body alone, so
  a captured signed request stayed a valid replay forever; folding in a
  time-boxed timestamp closes that.) The secret itself comes from the
  `HERALD_WEBHOOK_SECRET` env var, read once at mount time
  (`webhook.resolve_webhook_secret`) — never a literal or a default
  fallback, and never provisioned by this package (Steward's `keys`
  surface is a deployment concern, out of this story's Surface).
  **That secret is a privilege boundary, not just a spam filter.** The
  CLI's `herald progress --update` runs behind
  `auth.require_operator_role` (AD-16); the webhook deliberately does not,
  because AD-9's point is that a machine caller authenticates by proof
  rather than by an operator identity it does not have. So anything
  holding `HERALD_WEBHOOK_SECRET` gets progress-write access the CLI
  grants only to a verified operator — scope it accordingly.
- **Reliability:** a storage-layer failure (`errors.HeraldError` from
  `progress.upsert`/`claims.create`) is retried up to 3 times, sleeping 1s
  then 2s between them — never after the last attempt, so the retry budget
  adds at most ~3s, not 7s — before giving up; giving up logs one
  structured JSON `ERROR`-level record (there is no email/Slack/other
  operator-alert channel in this repo to build against) and answers with a
  non-2xx status so CI's own webhook-delivery retry can re-fire the call
  later. Sizing a CI step timeout off that 3s alone is not safe, though:
  each attempt can additionally wait up to SQLite's 30s busy timeout for
  the write lock.
- **Other responses:** a body over 1 MB, or one arriving in more than
  10,000 chunks, is a 413 (both checked before the signature, so an
  unauthenticated caller can neither make the process buffer an oversized
  body nor hold a request open forever by trickling empty chunks); an
  unknown path is a 404 and any method but `POST` a 405, both before the
  body is read at all; a malformed or duplicate-keyed JSON body, or one
  whose fields are the wrong type/out of range, is a 400 before any
  storage call. The request path is forgiving about a trailing or doubled
  slash, and about the prefix it is mounted under, but nothing else.
- **Also 400 — the full list worth knowing when writing the producer:**
  **any field the route does not recognize** (both routes reject unknown
  fields outright rather than ignoring them — on `on-ship` a silently
  ignored `token_spends` typo would not just fail to record the figure, it
  would *wipe* the one already there, and the producer is a hand-written
  YAML with no schema to catch it); a `shipped_date` that is not exactly
  `YYYY-MM-DD` (other ISO forms like `20260813` parse but sort wrong in
  the dashboard's date filter and would be stored verbatim); a blank
  `event_id`; a blank `station`/`project_name`; any string field carrying
  a lone surrogate; and an `evidence` entry of type `notice` whose `url`
  does not name a notice that actually exists (that field is a Notice
  component name, and both publish and revalidate treat a notice entry as
  trivially valid, so an unchecked one would sail through the entire
  evidence gate — the CLI makes the same check).
- **Deduplication:** a redelivery of an already-recorded `on-pr-close`
  event returns the claim already stored rather than creating a second one
  — **supply a per-event `event_id`** in the payload so two different PRs
  shipping the same project on the same day are told apart, and so a
  redelivery that arrives after midnight UTC still dedupes. Make it
  **globally** unique, not merely unique to one repo: a bare PR number
  collides across repositories, and because the `event_id` branch
  deliberately ignores the date, such a collision is permanent rather than
  same-day. `${{ github.repository }}#${{ github.event.number }}` or the
  delivery GUID both work. Without an `event_id` the handler falls back to
  the payload's `evidence` list plus the date, which discriminates less
  well; with a *blank* one it would discriminate not at all, which is why
  that is rejected rather than accepted.

## How to run the scheduled job (evidence revalidation and progress snapshot)

`herald scheduler run` (Story 13.5) composes the two operations above that
otherwise need remembering by hand into one invocation: it revalidates
every claim's evidence (the same `claims.revalidate_all` call `herald
success validate --all` makes) and rewrites the Progress tab's
`progress.json` snapshot (the same `progress.write_snapshot` call
`scripts/export_progress_snapshot.py` makes). Never requires the operator
role — like `success validate`, it only refreshes derived state, never
claim/progress content.

```
$ herald scheduler run --repo-root /path/to/repo
progress: 1 record(s) aggregated -> /path/to/repo/web/public/progress.json
evidence: 1 claim(s) revalidated, 1 with broken evidence: 8e90b277-0190-4742-bda3-713ccc0bd486
```

A claim with broken evidence is named, never raised — the same
never-raise contract `success validate` has (exit code 0 either way). With
`--json`:

```
$ herald scheduler run --repo-root /path/to/repo --json
{"claims_checked": 1, "broken_evidence_claim_ids": ["8e90b277-0190-4742-bda3-713ccc0bd486"], "records_aggregated": 1, "snapshot_path": "/path/to/repo/web/public/progress.json"}
```

`--out-dir` overrides where `progress.json` is written (default:
`<repo-root>/web/public`, matching `export_progress_snapshot.py`'s own
default for a normal checkout).

### Installing the weekly trigger

Both jobs run unconditionally on every invocation — the ~weekly
evidence-staleness window (`evidence.STALE_AFTER`) is enforced by how
often you run this command, not by anything inside it. Install a local
`crontab` entry for *your own* real, durable `.herald/herald.db` — never
a GitHub Actions workflow: `.herald/` is gitignored, per-operator state,
so a GitHub-hosted runner has no access to it and would run this against
an empty database every time (see this story's spec Design Notes for the
full reasoning). `herald-live-demo.yml`'s `scheduler-demo` job (Story
13.6) *does* run `herald scheduler run --json` inside GitHub Actions, but
only to prove the command runs unattended — it seeds and revalidates its
own throwaway scratch database, never yours; it is a proof this machinery
works, not a substitute for installing the cron entry below. `cd` into `pyforge-herald`'s own package
directory first, not an arbitrary checkout: unlike `deck`'s `--repo-root`
(any `presentations/<slug>/`-holding project), `scheduler`/`progress`/
`success`/`notice` treat `--repo-root` as *this package's own* checkout
by convention — it is where `.herald/herald.db` lives AND (via
`--out-dir`'s default) where the web dashboard's `web/public/` actually
is; pointing it elsewhere silently refreshes an unrelated `web/public`
instead of the one `npm run dev` serves. The `flock -n` wrapper skips a
run outright rather than overlapping with one still in progress (evidence
revalidation makes one real HTTP request per link, unbounded by claim
count, so a slow run and the next week's firing could otherwise overlap):

```cron
# Weekly Sunday 03:00 -- evidence revalidation + progress snapshot
# refresh (Story 13.5). Runs from the same checkout an operator actually
# uses `herald` from -- .herald/herald.db is gitignored, so a different
# checkout (or a CI runner) has nothing real to revalidate. flock -n
# skips this firing outright if the previous run is still going, rather
# than overlapping two writers against the same .herald/herald.db.
0 3 * * 0  cd /path/to/repo/src/shared/packages/pyforge-herald && \
    flock -n /tmp/herald-scheduler.lock \
    pixi run -e pyforge-herald herald scheduler run \
        >> ~/.cache/herald-scheduler.log 2>&1
```

Install with `crontab -e`. Adjust the path for your own checkout; there
is no packaged default location this can assume.

## Satisfying the operator-role gate

Every write subcommand (`progress <station> --update`, `success publish`,
`notice author`/`publish`/`close`/`archive`) calls the same gate
(`auth.require_operator_role`, `src/pyforge/herald/auth.py`) before doing
anything else. It resolves an auth context from, in order:

1. **`HERALD_TOKEN` env var**, format `<role>:<opaque-token>` (a single
   `:` splits the two), e.g. `export HERALD_TOKEN=operator:x`. Any
   non-empty opaque token works today — this is a role-presence stub, not
   real credential verification (see `auth.py`'s module docstring). A
   value with no `:` is ignored (treated as no auth context).
2. **`~/.herald/config`** — a JSON file `{"role": "operator"}`. Overridable
   per test but not per CLI flag in production.

If neither resolves, the write refuses with exit code 1:

```
herald: OperatorAuthorizationError: auth context missing. Configure with `herald auth login` or set HERALD_TOKEN env var
```

**Known wording gap:** that message says `herald auth login`, but no such
subcommand exists in this CLI (`herald --help` lists only `deck`,
`progress`, `success`, `notice`). The message is locked to Story 6.3's
original acceptance criteria and its test (`tests/test_auth.py`); it has
not been corrected. Ignore the `herald auth login` half of the message —
set `HERALD_TOKEN` or write `~/.herald/config` instead.

If a role resolves but is not `operator` (e.g. `HERALD_TOKEN=viewer:x`),
the refusal is more specific:

```
herald: OperatorAuthorizationError: unauthorized: operator role required (found role 'viewer')
```

Every write subcommand also prompts `Continue? [Y/n]` before writing —
answering anything but blank/`y`/`yes` aborts with no write and exit 0
(e.g. `aborted: publish not confirmed`).

## Troubleshooting

### Operator-role refusal

See [Satisfying the operator-role gate](#satisfying-the-operator-role-gate)
above. Exit code 1 either way.

### Evidence link validation failure

`herald success publish` validates every evidence link before writing.
A broken link aborts the publish entirely — nothing is persisted. (This is
a separate scratch claim, `a17e2b60-...`, deliberately created with a
broken evidence link to demonstrate the failure — not the same
`9c3590d4-...` claim from the walkthrough above, which had a clean link
and published successfully.)

```
$ herald success publish a17e2b60-... --thesis "Shipped it"
Continue? [Y/n] y
herald: EvidenceLinkError: claim 'a17e2b60-...' has 1 broken evidence link(s): https://example.com/nonexistent-9999 (Evidence link broken: https://example.com/nonexistent-9999. Fix or remove before publishing.). Fix or remove before publishing.
```

Exit code 1. Fix: either fix the URL and re-run `herald success review
<claim-id>` to confirm, or drop the offending evidence and re-`create` the
claim (there is currently no "edit evidence on an existing draft"
subcommand). See also `herald success validate` in
[`automation-troubleshooting.md`](automation-troubleshooting.md) for
re-checking evidence on claims that are already published.

### Malformed local storage file

Progress/Success/Operations' local storage is one shared SQLite database,
`.herald/herald.db`, in the repo root (Story 13.3; Notices' markdown files
under `notices/` are the separate, git-tracked durable copy). A corrupted
database file, or a corrupted JSON value inside one of its nested columns
(`shipped_capabilities`/`evidence`/`edit_history`/`revisions`), fails loud,
not silently:

```
$ herald success list
herald: HeraldError: /path/to/.herald/herald.db is not a valid database: file is not a database
```

Exit code 1. Fix: restore `.herald/herald.db` from a backup (it is
operator-local state, not committed) -- there is no repair tool. The
database runs in WAL mode, so a backup or restore must include any
`.herald/herald.db-wal`/`.herald/herald.db-shm` sidecar files present
alongside it, taken while no `herald` process is running. A first-ever run
against a pre-Story-13.3 repo importing legacy
`.herald/progress.json`/`claims.json`/`notices-index.json` fails the same
way, naming the offending legacy file, if one of those is itself corrupt.

### `--date-range` usage errors

`--date-range` takes `<start>..<end>` as `YYYY-MM-DD..YYYY-MM-DD` (a
literal `..` separator). A single date, wrong format, or `start > end` all
fail the same way, exit code 1 (not argparse's exit 2, since this is
parsed *after* argument parsing):

```
$ herald progress --date-range "2026-08-01"
herald: InvalidDateRangeError: Invalid date format: '2026-08-01'; expected <start>..<end> as YYYY-MM-DD..YYYY-MM-DD
```

With `--json`, the same failure renders as one JSON object on stderr
instead of plain text:

```
$ herald progress --date-range "2026-08-01" --json
{"tool": "herald", "error": "InvalidDateRangeError", "message": "Invalid date format: '2026-08-01'; expected <start>..<end> as YYYY-MM-DD..YYYY-MM-DD"}
```

### `--json` usage

`--json`/`-j` is a global flag (`progress`, `success`, `notice`, and
`notice list`) that switches output to machine-readable JSON — NDJSON (one
JSON object per line) for list-shaped output, a single JSON object for
single-record output, and a single JSON object on stderr for any error on
those paths. It never colorizes and never mixes with the human-readable
prose output.

### Unknown station / unknown claim / unknown notice component

Each of these is a plain `HeraldError`, exit code 1, with the valid set
named in the message:

```
$ herald progress bogus-station
herald: HeraldError: Station 'bogus-station' not found. Available: warden, atlas, marshal, mason, doctor, scribe, steward, herald. Use --list to see recorded stations.
```

An unrecognized station is only rejected by this check — `herald progress
<station> --update` itself will happily record progress for a station
outside this list; the check exists purely to produce this helpful
message on a probable typo.

### Unknown subcommand / flag / no command given

Argparse-level usage errors, exit code 2:

```
$ herald bogus
usage: herald [-h] [--version] command ...
herald: error: unknown command 'bogus'; valid subcommands: 'deck', 'progress', 'success', 'notice', 'scheduler'
See --help for available options.
```

Running `herald` with no arguments at all is a slightly different case —
not an argparse usage error, exit code 1:

```
$ herald
usage: herald [-h] [--version] command ...
herald: error: no command given; valid subcommands: deck, progress, success, notice, scheduler
```

### What is *not* a failure mode here

**"My local `.herald/herald.db` doesn't have the record `herald-live-demo.yml` just created in CI" is not a bug.**
As of Story 13.6 the webhook handlers (`webhook.py`, [above](#the-webhook-endpoint-ci-calls-story-134))
fire for real on every push to `main` and every PR close
(`.github/workflows/herald-live-demo.yml`'s `on-ship`/`on-pr-close`
jobs) — but each job writes into a scratch, JOB-LOCAL
`.herald/herald.db` under the runner's temp directory, discarded the
moment the job ends. This is a bounded, CI-contained demonstration that
the wiring works, never a persistent, publicly-reachable deployment (see
the Scope note above) — it does **not** write into any checkout's real
`.herald/herald.db`, yours included. If you want a record in *your* local
store, run the CLI command yourself
(`herald progress <station> --update` / `herald success create`, see
[`operator-guide.md`](operator-guide.md)'s FAQ); the webhook path and the
CLI path are two independent writers onto two independent stores in this
demo shape, not one shared source of truth yet.

The failure mode actually worth watching for is `herald-live-demo.yml`
itself going red — check the Actions tab, not your local database. One
specific way it fails loudly rather than silently: if
`HERALD_WEBHOOK_SECRET` is not configured as a repo secret,
`webhook_host.application` raises at daphne startup (the same fail-fast
`resolve_webhook_secret` always guaranteed) and the job's "wait for daphne
to start listening" step fails with a clear error, rather than the
workflow quietly no-op'ing.

`herald scheduler run`
(Story 13.5, [above](#how-to-run-the-scheduled-job-evidence-revalidation-and-progress-snapshot))
has the identical split: `herald-live-demo.yml`'s `scheduler-demo` job
proves the command runs unattended (weekly schedule + manual
`workflow_dispatch`), against its own scratch seed data — the documented
trigger for *your* real, durable `.herald/herald.db` is still an
operator-installed local `crontab` entry, because a GitHub-hosted runner
never has the gitignored database a real checkout would. A *missed* run
of that local cron entry (the machine was off, the entry was never
installed) is a real, if narrow, failure mode.

## Escalation path

1. Check this file and [`automation-troubleshooting.md`](automation-troubleshooting.md)
   for the specific error text you're seeing.
2. If the failure looks like it should have been automatic (a webhook not
   yet mounted, a cron job, an email/in-app alert), read
   [The webhook endpoint](#the-webhook-endpoint-ci-calls-story-134) above
   and `docs/dreams/herald-moments-2-4-live-backend.md` first — it is very
   likely the gap you're hitting is the documented, intentional scope cut,
   not a bug.
3. Otherwise, file an issue against `rxm7706/local-recipes` describing the
   exact command, flags, and error text (or JSON, if `--json` was used).
   There is no separate Herald issue tracker or team inbox — this repo's
   GitHub issues are it.
