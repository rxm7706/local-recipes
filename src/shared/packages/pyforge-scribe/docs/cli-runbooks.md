# Scribe CLI Runbooks & Troubleshooting

Story 3.3. Practical, copy-pasteable walkthrough for the one operator task
this package deliberately does not automate for you — scheduling the
nightly knowledge-graph compile — plus a troubleshooting section for the
failure modes that actually exist in this codebase today. Format follows
`pyforge-herald`'s `docs/cli-runbooks.md` (its Story 13.5 scheduler
runbook is the direct precedent this one mirrors).

**Scope note.** Everything `scribe graph compile` reads and writes is
**operator-local**: the checked-in `.claude/memory/` tree of *your*
checkout, *your* per-user session transcripts
(`~/.claude/projects/<encoded-repo-path>/*.jsonl`), and the gitignored
derived graph store (`.claude/data/pyforge-scribe/graph.json`). That is
why the documented trigger below is an opt-in, operator-installed local
`crontab` entry and **never a GitHub Actions workflow** — a GitHub-hosted
runner has none of those three surfaces, so a scheduled workflow would
faithfully compile an empty machine every night and prove nothing (the
same reasoning `pyforge-herald`'s scheduler runbook records for its
gitignored `.herald/herald.db`). The CLI verb itself is the schedulable
unit; no scheduler dependency (APScheduler, Celery, or similar) is added
for one nightly invocation, and Scribe's compile does **not** couple into
`herald scheduler run` — two stations, two schedules, two databases.

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
behavior — it exists for scheduling clarity in cron lines and logs.

```
$ cd /path/to/local-recipes
$ pixi run -e pyforge-scribe scribe graph compile --nightly
compiled 812 node(s), 1 invalidated -> /path/to/local-recipes/.claude/data/pyforge-scribe/graph.json
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
   the lock ...` to stderr and **exits 0** — an overlapping cron firing is
   never a corrupted double-write and never red cron mail.
2. **In the cron line below**: `flock -n` skips the firing before pixi
   even starts, saving the environment-activation cost when the previous
   night's run is somehow still going.

### Installing the nightly trigger

Install with `crontab -e`, adjusting `/path/to/local-recipes` for your
own checkout — there is no packaged default location this can assume.
Logs append to `~/.cache/scribe-nightly-compile.log` (stdout and stderr,
including every `warning:` line), so `tail` that file to see what last
night's run did:

```cron
# Nightly 02:30 -- scribe knowledge-graph compile (Story 3.3). Runs from
# the repo checkout whose .claude/memory/ and .claude/data/ this machine
# actually uses; session transcripts are per-user, so a different
# checkout (or a CI runner) has nothing real to compile. flock -n skips
# this firing outright if the previous run is still going, rather than
# overlapping two rebuilds of the same graph store.
30 2 * * *  cd /path/to/local-recipes && \
    flock -n /tmp/scribe-nightly-compile.lock \
    pixi run -e pyforge-scribe scribe graph compile --nightly \
        >> ~/.cache/scribe-nightly-compile.log 2>&1
```

This entry is **opt-in** — nothing in this repo installs it for you, and
a checkout without it simply has a staler compiled graph (every `scribe
recall` answer still cites whatever the last compile saw). PRD SM-4
("completes unattended across at least 4 consecutive scheduled runs")
is validated against this entry's log on the operator machine that
installs it.

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

Exit 2. The cron line's `cd` points at the wrong directory, or the
checkout was moved. Fix the path in `crontab -e`.

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
