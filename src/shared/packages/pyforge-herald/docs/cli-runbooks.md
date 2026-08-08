# Herald CLI Runbooks & Troubleshooting

Story 12.1. Practical, copy-pasteable walkthroughs for the two most common
operator tasks — authoring a notice and publishing a success claim — plus a
troubleshooting section for the failure modes that actually exist in this
codebase today.

**Scope note.** Herald's Moments 2-4 (Progress/Success/Operations) are
**local-storage, CLI-triggered** — there is no webhook server, no database,
no cron scheduler anywhere in this package. Every record (a progress entry,
a claim, a notice) is created by an operator running an explicit `herald`
command by hand. See `docs/dreams/herald-moments-2-4-live-backend.md` for
the deferred live-backend version and why the scope was cut down. This
runbook documents the system as it exists, not that Dream.

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

`herald success` manages Moment 3. `create` makes a draft (the
CLI-triggered stand-in for what would have been a PR-close webhook
payload); `review` shows it read-only; `publish` requires the operator
role and validates every evidence link before writing anything.

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

Every Moment's storage is a single JSON file under `.herald/` in the
repo root (`progress.json`, `claims.json`, `notices-index.json`). A
hand-edited or corrupted file fails loud, not silently:

```
$ herald success list
herald: HeraldError: claims file /path/to/.herald/claims.json could not be read: Expecting property name enclosed in double quotes: line 1 column 2 (char 1)
```

Exit code 1. Fix: restore the file from git history / a backup, or hand-fix
the JSON syntax error the message points at. There is no repair tool.

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
herald: error: unknown command 'bogus'; valid subcommands: 'deck', 'progress', 'success', 'notice'
See --help for available options.
```

Running `herald` with no arguments at all is a slightly different case —
not an argparse usage error, exit code 1:

```
$ herald
usage: herald [-h] [--version] command ...
herald: error: no command given; valid subcommands: deck, progress, success, notice
```

### What is *not* a failure mode here

There is no webhook to "not fire," no cron job to "miss," and no
async re-validation job to fail silently — none of that infrastructure
exists in this codebase. If you find yourself debugging why a PR merge
didn't automatically create a progress record or a claim, stop: it can't,
by design, today. Run the CLI command yourself (see
[`operator-guide.md`](operator-guide.md)'s FAQ). The live-automation
version is tracked as a Dream, not a bug:
`docs/dreams/herald-moments-2-4-live-backend.md`.

## Escalation path

1. Check this file and [`automation-troubleshooting.md`](automation-troubleshooting.md)
   for the specific error text you're seeing.
2. If the failure looks like it should have been automatic (a webhook, a
   cron job, an email/in-app alert), read
   `docs/dreams/herald-moments-2-4-live-backend.md` first — it is very
   likely the gap you're hitting is the documented, intentional scope cut,
   not a bug.
3. Otherwise, file an issue against `rxm7706/local-recipes` describing the
   exact command, flags, and error text (or JSON, if `--json` was used).
   There is no separate Herald issue tracker or team inbox — this repo's
   GitHub issues are it.
