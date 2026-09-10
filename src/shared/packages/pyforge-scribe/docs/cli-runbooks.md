# Scribe CLI Runbooks & Troubleshooting

Story 3.3 (compile itself) + Story 8.1 (its trigger). Practical,
copy-pasteable walkthrough for scheduling the nightly knowledge-graph
compile — installed by one repeatable command rather than a hand-typed
`crontab -e` — plus a troubleshooting section for the failure modes that
actually exist in this codebase today. Format follows `pyforge-herald`'s
`docs/cli-runbooks.md` (its Story 13.5 scheduler runbook is the direct
precedent this one mirrors).

**Scope note.** Everything `scribe graph compile` reads and writes is
**operator-local**: the checked-in `.claude/memory/` tree of *your*
checkout, *your* per-user session transcripts
(`~/.claude/projects/<encoded-repo-path>/*.jsonl`), and the gitignored
derived graph store (`.claude/data/pyforge-scribe/graph.json`). That is
why the documented trigger below is a **checked-in systemd-user timer,
installed by a documented, repeatable act** (`scribe-install-nightly-
trigger` — Story 8.1, replacing the hand-typed `crontab -e` line this
section used to document) and **never a GitHub Actions workflow** — see
"Scope note" under "Installing the nightly trigger" below for the full
reasoning. The CLI verb itself is the schedulable unit; no scheduler
dependency (APScheduler, Celery, or similar) is added for one nightly
invocation, and Scribe's compile does **not** couple into `herald
scheduler run` — two stations, two schedules, two databases.

`scribe` is not on `PATH` in a bare shell — run it through the pixi env
(`pixi run -e pyforge-scribe scribe ...`) from the **repo root**: the CLI
resolves `.claude/memory/` and `.claude/data/` relative to the current
working directory (unlike `herald`, which wants its own package
directory).

## How to run the nightly compile

`scribe graph compile --nightly` rebuilds the compiled knowledge graph
from scratch on every run — the six named surfaces (`.claude/memory/`,
`.memlog.md` files, git history, retros, CHANGELOGs, raw session
transcripts) in, one atomic store write out. It never prompts (FR-11),
performs zero network calls (AD-6), and `--nightly` itself changes no
behavior — it exists for scheduling clarity in the trigger and its logs.

```
$ cd /path/to/local-recipes
$ pixi run -e pyforge-scribe scribe graph compile --nightly
compiled 812 node(s), 1 invalidated, 3 stale -> /path/to/local-recipes/.claude/data/pyforge-scribe/graph.json
```

A degraded surface (no `git` on PATH, a malformed memory entry, a missing
transcript root) prints a `warning:` line to stderr and is skipped — the
compile still exits 0. Only a missing `.claude/memory/` tree (running
from the wrong directory) exits 2.

### What keeps an unattended run bounded (Story 3.3)

The transcript surface is per-user and unbounded in principle (the live
measurement that motivated this: 27 files / 631MB, growing). Three bounds
apply on every compile, as a precondition of scheduling it:

- **File-count cap and byte budget** — at most 256 files, at most 1 GiB
  total, allocated newest-first (recent sessions are where not-yet-curated
  decisions live). Both defaults comfortably cover the live surface; when
  the surface outgrows them, one `warning: transcript scan capped: ...`
  line names how many files were skipped.
- **Per-file timeout** — 30s per file (matching the `git log` surface's
  own timeout); a pathological file keeps its partial results with a
  warning instead of hanging the night's run.
- **mtime-incremental scan cache** —
  `.claude/data/pyforge-scribe/transcript-scan-cache.json` (beside the
  graph store, gitignored, disposable). Unchanged transcript files are
  not re-read on the next run, so the nightly re-run is cheap; a changed
  or new file is re-scanned automatically. Deleting the cache file is
  always safe — the next compile rebuilds it.

### Overlap protection

Two layers, both skip-not-queue (two concurrent compiles of the same
derived store are pure waste):

1. **In the CLI**: `scribe graph compile` takes a non-blocking lock keyed
   to the graph store's path (a lock file under the OS temp dir — never
   inside the repo tree). If another compile already holds it, the second
   run prints `skipped: another `` `scribe graph compile` `` already holds
   the lock ...` to stderr and **exits 0** — an overlapping firing is
   never a corrupted double-write and never a red scheduled run.
2. **In the systemd unit**: a `Type=oneshot` service systemd already
   considers active refuses a second `start` outright (systemd's own
   "already running" skip — logged, not an error) if a previous night's
   run is somehow still going by the time the timer fires again.

### Installing the nightly trigger

Story 8.1 replaced the former hand-typed `crontab -e` line with a
**checked-in, reviewable trigger definition** — a systemd-user timer
rendered from
`src/shared/packages/pyforge-scribe/ops/systemd/pyforge-scribe-nightly-
compile.service.tmpl` + `.timer` — installed by one documented,
repeatable pixi task rather than an operator hand-editing their own
crontab:

```
$ cd /path/to/local-recipes
$ pixi run -e pyforge-scribe scribe-install-nightly-trigger
scribe-install-nightly-trigger: installed and enabled pyforge-scribe-nightly-compile.timer
  status:     systemctl --user status pyforge-scribe-nightly-compile.timer
  next run:   systemctl --user list-timers pyforge-scribe-nightly-compile.timer
  unit files: /home/you/.config/systemd/user
```

This renders the checked-in template with this checkout's absolute path
and the resolved `pixi` binary substituted, copies both units into
`~/.config/systemd/user/`, then runs `systemctl --user daemon-reload` and
`enable --now` — idempotent, safe to re-run any time (after moving the
checkout, for example). The rendered `.service` unit runs
`pyforge-scribe-nightly-compile` (`scripts/scribe_nightly_trigger.py`),
which invokes `scribe graph compile --nightly` and propagates its exit
code unchanged; the `.timer` unit fires it at 02:30 daily
(`Persistent=true` catches up a firing missed while the machine was off).
Logs append to `~/.cache/scribe-nightly-compile.log` (stdout and stderr,
including every `warning:` line — the unit's own `StandardOutput`/
`StandardError=append:...` directives, mirroring the former cron line's
redirection), so `tail` that file, or `journalctl --user -u
pyforge-scribe-nightly-compile.service`, to see what recent runs did.

To validate a fresh install without waiting for the next 02:30 firing, run
the service once by hand:

```
$ systemctl --user start pyforge-scribe-nightly-compile.service
```

then check `tail ~/.cache/scribe-nightly-compile.log` or run `pixi run -e
local-recipes scribe-graph-freshness-check` to confirm the graph store's
mtime just advanced.

To disable/uninstall the trigger, stop and disable the timer:

```
$ systemctl --user disable --now pyforge-scribe-nightly-compile.timer
```

**Linger requirement.** A systemd-user timer only fires on its own while
the invoking user has an active login session; `Persistent=true` (below)
catches up a firing missed while the machine was briefly off, but it does
**not** fire while the user is fully logged out for an extended period. If
this machine is not kept continuously logged in, run `loginctl
enable-linger $USER` once so the timer keeps firing regardless — the
installer checks this (best-effort) and prints an advisory to stderr when
linger is off.

This installation act is still **opt-in** — nothing forces an operator to
run it, and a checkout without it simply has a staler compiled graph
(every `scribe recall` answer still cites whatever the last compile saw)
— but it is no longer a hand-typed, undocumented line living only in one
operator's own crontab: the trigger's definition is checked into git,
reviewable in a PR, and installed by running one named command. PRD SM-4
("completes unattended across at least 4 consecutive scheduled runs") is
validated against the log above, or against `graph.json`'s own mtime
series (`pixi run -e local-recipes scribe-graph-freshness-check`), on the
operator machine that installs it.

If the configured `GraphStore` driver is PostgreSQL
(`PYFORGE_GRAPHSTORE_OWNER=steward` — Story 28.1), the trigger first
ensures the local cluster is up (`pixi run -e pyforge-scribe-pg
scribe-pg-up`, the same idempotent command an operator runs by hand — see
`scripts/scribe_pg.py`) before compiling; if that fails for any reason
(the cluster's binaries are not installed on this machine, `pixi` cannot
be found, ...) it refuses cleanly — a message to stderr and exit 0 —
rather than ever reporting a red scheduled run for a driver this machine
cannot confirm live. The default `FlatFileGraphStore` path needs none of
this and is unaffected.

A systemd-user unit does not inherit an operator's own interactive shell
environment, so `PYFORGE_GRAPHSTORE_OWNER` must be baked into the rendered
`.service` file at install time (exactly like `PIXI_BIN` already is) for
the scheduled run to ever see it — **re-run `pixi run -e pyforge-scribe
scribe-install-nightly-trigger` any time you set or change
`PYFORGE_GRAPHSTORE_OWNER`**, or the nightly run keeps silently compiling
against the default `FlatFileGraphStore` regardless of what you configured
for interactive use.

#### Scope note: why not a GitHub Actions workflow

Everything the nightly compile reads lives on the **operator's own
machine**: the checked-in `.claude/memory/` tree of *that* checkout,
*that* operator's per-user session transcripts
(`~/.claude/projects/<encoded-repo-path>/*.jsonl`), and the gitignored
derived graph store (`.claude/data/pyforge-scribe/graph.json`). A
GitHub-hosted Actions runner has **none** of these three surfaces — it
checks out a fresh, transcript-free clone and throws it away when the job
ends — so a scheduled `.github/workflows/` job would faithfully "compile"
an empty machine every night and prove nothing about whether the real
knowledge graph is current (the same reasoning `pyforge-herald`'s own
scheduler runbook records for its gitignored `.herald/herald.db`). This
is a **HARD boundary for Epic 8** — a future pass finding the trigger
unreliable should diagnose systemd-timer/PATH issues on the operator
machine, not re-litigate GitHub Actions as an alternative host for it.

## Troubleshooting

### `skipped: another scribe graph compile already holds the lock ...`

Not an error (exit 0). Another compile against the same graph store was
still running — usually last night's run overrunning into a manual one.
If it persists, look for a wedged `scribe` process; killing it releases
the lock automatically (advisory locks die with their process — there is
no stale-lock file to clean up).

### `warning: transcript scan capped: skipped N of M file(s) ...`

The transcript surface outgrew the file-count or byte budget; the newest
files were scanned, the oldest skipped. Old sessions' decisions that were
never curated are the content at risk — run `scribe capture --transcripts`
interactively to review what the older files hold, or prune ancient
`*.jsonl` files you no longer care about from
`~/.claude/projects/<encoded-repo-path>/`.

### `warning: transcript scan timed out after 30s in <file> ...`

One pathological file exceeded the per-file processing budget; its
partial results were kept and it was left uncached (the next run retries
it). Recurring timeouts on the same file usually mean an enormous
single-session transcript — prune it or accept the partial scan.

### `warning: transcript surface unavailable (... does not exist) ...`

Expected on any machine that has never run a Claude Code session against
this repo — the transcript surface simply contributes zero nodes. The
other five surfaces still compile.

### `.claude/memory does not exist -- run `scribe graph compile` from the repo root`

Exit 2. The rendered unit's `WorkingDirectory=` points at the wrong
directory, or the checkout was moved. Re-run `pixi run -e pyforge-scribe
scribe-install-nightly-trigger` from the checkout's new location to
re-render it.

### `scribe-graph-freshness-check` reports a missing or stale graph store

Advisory only (never a PR gate) — run `pixi run -e local-recipes
scribe-graph-freshness-check` for the age report. A missing store means
the trigger has never fired on this machine (run
`scribe-install-nightly-trigger`, or check `systemctl --user status
pyforge-scribe-nightly-compile.timer`); a stale one (older than 24h)
usually means the timer stopped firing — check `journalctl --user -u
pyforge-scribe-nightly-compile.service` for the last run's output.

### Stale or corrupt derived state

Both files under `.claude/data/pyforge-scribe/` (`graph.json`,
`transcript-scan-cache.json`) are derived and disposable (AD-1). Delete
either or both and re-run the compile — nothing durable lives there;
durable content is the checked-in `.claude/memory/` tree and your
transcripts, which the compile only reads.

## Escalation path

1. Check this file for the specific warning/error text you're seeing —
   most of what looks like a failure above is a documented, bounded
   degradation.
2. Read `src/pyforge/scribe/compile.py`'s module docstring (the
   scheduling/bounding rationale lives there) before concluding the
   scheduler machinery is missing — the absence of a GitHub Actions
   workflow is the documented, intentional scope.
3. Otherwise, file an issue against `rxm7706/local-recipes` with the
   exact command and log lines from `~/.cache/scribe-nightly-compile.log`.
   There is no separate Scribe issue tracker — this repo's GitHub issues
   are it.
