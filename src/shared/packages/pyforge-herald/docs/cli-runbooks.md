# Herald CLI Runbooks & Troubleshooting

Story 12.1. Practical, copy-pasteable walkthroughs for the two most common
operator tasks — authoring a notice and publishing a success claim — plus a
troubleshooting section for the failure modes that actually exist in this
codebase today.

**Scope note.** Herald's Moments 2-4 (Progress/Success/Operations) are
**local-storage, CLI-triggered** — storage is a local SQLite file,
`.herald/herald.db` (Story 13.3). Every record (a progress entry, a
claim, a notice) is created either by an operator running an explicit
`herald` command by hand, or by CI calling the HMAC-verified webhook
handlers Story 13.4 built (`src/pyforge/herald/webhook.py`'s
`on-ship`/`on-pr-close` -- see [The webhook
endpoint](#the-webhook-endpoint-ci-calls-story-134) below). The webhook is
built, unit-tested in isolation, and not yet mounted anywhere: there is no
live HTTP listener in this package today, and no hosted scheduler either
except `herald scheduler run`'s derived-state refresh (Story 13.5, see
[How to run the scheduled
job](#how-to-run-the-scheduled-job-evidence-revalidation-and-progress-snapshot)
below), which an operator can point an optional local `cron` entry at.
Wiring the webhook into a live ASGI host and a real GitHub Actions step is
Story 13.6's job. See `docs/dreams/herald-moments-2-4-live-backend.md` for
the fuller live-backend version and why the rest of the scope was cut
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

## The webhook endpoint (CI calls, Story 13.4)

`src/pyforge/herald/webhook.py` is a second, CI-triggered path onto the
same storage `herald progress --update`/`herald success create` write:
an HMAC-verified ASGI3 callable (`webhook.create_app(repo_root, secret)`),
built and fully unit-tested in isolation, but **not mounted anywhere in
this repo today** — there is no live URL to `curl`. Mounting it into a
real ASGI host and wiring an actual GitHub Actions workflow step is Story
13.6's job; until that lands, `herald progress --update`/`herald success
create` remain the only way a record actually gets created outside a
Python test.

For when it is mounted, the shape:

- **Routes:** `POST /api/herald/webhooks/on-ship` (calls the same
  `progress.upsert` `herald progress <station> --update` calls) and
  `POST /api/herald/webhooks/on-pr-close` (calls the same `claims.create`
  `herald success create` calls, only when the payload's own `merged` and
  `gates_passed` are both `true` — any other combination is a 202 no-op,
  never an error).
- **Auth:** every request must carry an `X-Hub-Signature-256: sha256=<hex>`
  header proving the sender holds the shared secret
  (`hmac.new(secret, raw_body, hashlib.sha256)`) — a missing or mismatched
  signature is a 401 before the body is even parsed as JSON. The secret
  itself comes from the `HERALD_WEBHOOK_SECRET` env var, read once at
  mount time (`webhook.resolve_webhook_secret`) — never a literal or a
  default fallback, and never provisioned by this package (Steward's
  `keys` surface is a deployment concern, out of this story's Surface).
- **Reliability:** a storage-layer failure (`errors.HeraldError` from
  `progress.upsert`/`claims.create`) is retried up to 3 times (1s/2s/4s
  backoff) before giving up; giving up logs one structured JSON
  `ERROR`-level record (there is no email/Slack/other operator-alert
  channel in this repo to build against) and answers with a non-2xx
  status so CI's own webhook-delivery retry can re-fire the call later.

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
`crontab` entry (never a GitHub Actions workflow: `.herald/` is
gitignored, per-operator state, so a GitHub-hosted runner would run this
against an empty database every time — see this story's spec Design
Notes for the full reasoning). `cd` into `pyforge-herald`'s own package
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

The webhook handlers (`webhook.py`, [above](#the-webhook-endpoint-ci-calls-story-134))
are not mounted anywhere in this repo, so there is no live webhook to "not
fire" here yet, and no async re-validation job to fail silently either.
`herald scheduler run`
(Story 13.5, [above](#how-to-run-the-scheduled-job-evidence-revalidation-and-progress-snapshot))
is the one piece of periodic infrastructure that does exist, and it is
opt-in and operator-installed (a local `crontab` entry) — a *missed* run
of that cron entry (the machine was off, the entry was never installed)
is a real, if narrow, failure mode, distinct from "there is no automation
to miss" for everything else in this guide. If you find yourself
debugging why a PR merge didn't automatically create a progress record or
a claim, stop: it can't, today — the webhook is built and tested, but not
yet mounted into a live endpoint or wired into a real GitHub Actions
workflow (Story 13.6). Run the CLI command yourself (see
[`operator-guide.md`](operator-guide.md)'s FAQ). Once 13.6 lands, this
section will need updating along with it.

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
