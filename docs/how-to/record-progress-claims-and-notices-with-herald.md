---
sources:
  - src/shared/packages/pyforge-herald/src/pyforge/herald/cli.py
  - src/shared/packages/pyforge-herald/src/pyforge/herald/auth.py
  - src/shared/packages/pyforge-herald/src/pyforge/herald/scheduler.py
  - src/shared/packages/pyforge-herald/scripts
  - src/shared/packages/pyforge-herald/web/package.json
verified: 2026-11-24
---

# How to record progress, claims and notices with Herald

Use the `herald progress`, `herald success` and `herald notice` commands to record a station's progress, publish a success claim, and author an operations notice. What these records are and where they are stored is in [Herald's Four Moments](../explanation/herald-four-moments.md).

## When to use this

- A station shipped something and you want today's Progress record written.
- You are publishing a success claim with evidence links.
- You are announcing a deprecation, fix or end-of-life.
- The web dashboard must show what you just wrote.
- You want evidence revalidated on a schedule.

:::note
**Prerequisites.** `herald` is not on `PATH` in a bare shell: it is a console script inside the `pyforge-herald` pixi environment (the `pyforge-guild` environment carries it too). Run every command from the repo root as `pixi run --frozen -e pyforge-herald herald <subcommand> ...`, or open `pixi shell -e pyforge-herald` for a whole session. A bare `herald` that returns "command not found" is almost always this.
:::

The example output below was captured by running the built `herald` binary in a scratch directory on 2026-08-08.

## Steps

### 1. Satisfy the operator-role gate

Every write subcommand (`progress <station> --update`, `success publish`, `notice author`/`publish`/`close`/`archive`) calls the same gate (`auth.require_operator_role`) before doing anything else. Reads are always public. The gate resolves an auth context from, in order:

1. **`HERALD_TOKEN` env var**, format `<role>:<opaque-token>` (a single `:` splits the two), e.g. `export HERALD_TOKEN=operator:x`. Any non-empty opaque token works today: this is a role-presence stub, not real credential verification (see the `auth.py` module docstring). A value with no `:` is ignored.
2. **`~/.herald/config`** — a JSON file `{"role": "operator"}`.

`success publish` and `notice author`/`publish`/`close` also prompt `Continue? [Y/n]` before writing, and `notice archive` asks you to confirm the redirect (`Redirect 'OLD' -> 'NEW'? [Y/n]`). Answering anything but blank/`y`/`yes` aborts with no write and exit 0 (e.g. `aborted: publish not confirmed`). `progress <station> --update` has no confirmation prompt; it asks only for the unblock narrative, and only when `--unblock-narrative` is omitted.

### 2. Record progress

```
$ export HERALD_TOKEN=operator:x
$ herald progress warden --update \
    --shipped "Harness Policy" --compute-hours 3.5 \
    --token-spend 42000 --wall-clock-hours 6
Unblock narrative for warden on 2026-08-08 (blank for none): none
Progress updated for warden
```

`--unblock-narrative` can be given on the command line instead of prompted interactively; `--shipped` is repeatable for multiple shipped capabilities in one update.

Read it back, or list everything:

```
$ herald progress warden
station: warden
date: 2026-08-08
shipped_capabilities: Harness Policy
compute_hours: 3.5
token_spend: 42000
wall_clock_hours: 6.0
unblock_narrative: none

$ herald progress
2026-08-08  warden  1 capabilities  compute=3.5h  token_spend=42000  wall_clock=6.0h
```

Filter with `--station`/`--date-range`, or get NDJSON with `--json`.

### 3. Create, review and publish a success claim

`create` makes a draft: the same `claims.create` call the `on-pr-close` webhook handler makes. `review` shows it read-only; `publish` requires the operator role and validates every evidence link before writing anything.

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

`--thesis` is required the first time a claim is published (a claim with no thesis yet). Evidence links are optional per-type flags on `create`: `--evidence-test-results`, `--evidence-metrics`, `--evidence-adoption`, each a URL, and `--evidence-notice`, the component name of an operations notice that already exists. `--shipped-date` defaults to today.

Other read commands: `herald success list [--status draft|published|closed]` and `herald success get <claim-id>` (full detail, including edit history). To re-check a published claim's evidence later, run `herald success validate <claim-id>` or `herald success validate --all`.

### 4. Author an operations notice

`herald notice` manages deprecations, fixes and EOL announcements. Listing and `get` are read-only and require no auth; `author`/`publish`/`close`/`archive` write local storage and require the operator role.

Draft, then publish:

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

Add `--publish` to `author` to skip the draft stage. Any flag you omit (`--type`, `--component`, `--what`, `--why`, `--migration`; `--deadline` and `--reason-link` are optional) is prompted for interactively. `--type` must be one of `deprecation`, `fix`, `eol`.

Read it back:

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

`herald notice` (bare, no subcommand) is equivalent to `herald notice list`. Draft notices are excluded from listings by default: pass `--status draft` or `--status all` to see them.

Close and archive:

```
$ herald notice close auth-api-v1 --reason "migration complete"
$ herald notice archive --rename auth-api-v1 auth-api-v2
```

`archive --rename` is bookkeeping only (a redirect record in local storage; the new name must already have a notice). There is no HTTP server to serve an actual redirect from.

### 5. Refresh the web dashboard's snapshot

No `herald` write touches the dashboard. Re-run the exporter for whichever Moment changed, from the repo root:

| Moment | Command |
|---|---|
| Progress | `npm run sync-progress` (from `src/shared/packages/pyforge-herald/web/`) |
| Success | `pixi run -e pyforge-herald python src/shared/packages/pyforge-herald/scripts/export_web_snapshot.py --repo-root .` |
| Operations | `pixi run -e pyforge-herald python src/shared/packages/pyforge-herald/scripts/export_notices_snapshot.py --repo-root .` |

Then reload the page. Defaults and the dashboard's states are in the [web dashboard reference](../reference/herald-web-dashboard.md).

### 6. Run the scheduled job

`herald scheduler run` (Story 13.5) composes two operations into one invocation: it revalidates every claim's evidence (the same `claims.revalidate_all` call `herald success validate --all` makes) and rewrites the Progress tab's `progress.json` snapshot. It never requires the operator role: it only refreshes derived state, never claim or progress content.

```
$ herald scheduler run --repo-root /path/to/repo
progress: 1 record(s) aggregated -> /path/to/repo/web/public/progress.json
evidence: 1 claim(s) revalidated, 1 with broken evidence: 8e90b277-0190-4742-bda3-713ccc0bd486
```

A claim with broken evidence is named, never raised (exit code 0 either way). With `--json`:

```
$ herald scheduler run --repo-root /path/to/repo --json
{"claims_checked": 1, "broken_evidence_claim_ids": ["8e90b277-0190-4742-bda3-713ccc0bd486"], "records_aggregated": 1, "snapshot_path": "/path/to/repo/web/public/progress.json"}
```

`--out-dir` overrides where `progress.json` is written. Its default is `<repo-root>/web/public`, which is not the dashboard's directory when `--repo-root` is the repository root, so pass the dashboard's `public/` directory explicitly.

### 7. Install the weekly trigger (optional)

Both jobs run unconditionally on every invocation: the ~weekly evidence-staleness window (`evidence.STALE_AFTER`, seven days) is enforced by how often you run this command, not by anything inside it. Install a local `crontab` entry for your own real, durable `.herald/herald.db`, never a GitHub Actions workflow: `.herald/` is gitignored, per-operator state.

Run it from the same checkout root you run `herald` from, so `--repo-root` names the store your writes go to. The `flock -n` wrapper skips a run outright rather than overlapping with one still in progress (evidence revalidation makes one real HTTP request per link, unbounded by claim count):

```cron
# Weekly Sunday 03:00 -- evidence revalidation + progress snapshot refresh (Story 13.5).
0 3 * * 0  cd /path/to/repo && \
    flock -n /tmp/herald-scheduler.lock \
    pixi run -e pyforge-herald herald scheduler run --repo-root /path/to/repo \
        --out-dir /path/to/repo/src/shared/packages/pyforge-herald/web/public \
        >> ~/.cache/herald-scheduler.log 2>&1
```

Install with `crontab -e`. Adjust the path for your own checkout; there is no packaged default location this can assume. [Run Herald's live backend locally](run-herald-live-backend-locally.md) carries the variant that writes the snapshot beside the primary checkout's store instead.

## What you get

- Progress, claim and notice rows in `.herald/herald.db`, plus a git-tracked markdown file per notice under `notices/`.
- Refreshed `progress.json`, `success.json` and `notices.json` snapshots under the dashboard's `public/` directory, once the exporters have run.

When a command refuses or the dashboard looks wrong, see [How to troubleshoot Herald's progress, claims and notices](troubleshoot-herald-moments.md).
