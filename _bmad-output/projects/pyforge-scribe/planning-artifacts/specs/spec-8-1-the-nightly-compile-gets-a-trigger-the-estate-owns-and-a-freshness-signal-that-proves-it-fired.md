---
title: 'The nightly compile gets a trigger the estate owns, and a freshness signal that proves it fired'
type: 'feature'
created: '2026-09-10'
status: 'ready-for-dev'
review_loop_iteration: 0
followup_review_recommended: false
context: []
warnings: []
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** `scribe graph compile --nightly` is prompt-free, `flock -n`-safe, and exits 0 on an
overlapping firing (`cli.py:285-299`) — Story 3.3 already shipped the bounds, the lock, and the
unattended mode — but nothing triggers it. The only documented trigger is an opt-in operator
`crontab` line (`cli.py:290-291`, `docs/cli-runbooks.md` § *Installing the nightly trigger*) that
nobody installed. `.claude/data/pyforge-scribe/graph.json` was last written 2026-08-27, and
`spec-pyforge-scribe`'s own CAP-2 success signal — "nightly compile completes unattended across
at least 4 consecutive scheduled runs" — is unverifiable today because there are no scheduled
runs. This is a realization-gate gap (`spec-pyforge-unifying-strategy` batch row C6): a
capability that is built but not in effect.

**Approach:** Define a checked-in, repeatable trigger — a `pixi.toml` task plus the estate-side
hook that invokes it (a marshal dispatch hook, or a versioned systemd-user/`launchd` unit the
bootstrap installs) — and install it by a documented, repeatable act rather than a hand-typed
`crontab -e`. Document the installation in `cli-runbooks.md` § *Installing the nightly trigger*,
and add an advisory freshness/staleness check (the age of `graph.json` against the schedule's own
period) reachable from the detector set. No new compile capability is built here; this story only
gets the already-shipped Story 3.3 capability into effect and makes it provable.

## Boundaries & Constraints

**Always:**
- The trigger definition (the `pixi.toml` task and the hook/unit that invokes it) is checked into
  git and reviewable — installed by a documented, repeatable act, never a hand-typed `crontab -e`.
- The freshness/staleness check surfaces as an **advisory** finding only — never a PR gate, never
  a second verdict alongside the detector set's existing gates.
- The runbook records explicitly **why** this is not a GitHub Actions workflow (§ *Scope note*),
  so a future pass does not re-propose one.
- If a scheduled run is ever pointed at the PostgreSQL `GraphStore` driver, the trigger either
  starts the local cluster (`scribe-pg-up`) or refuses cleanly — it must never fail red on a
  machine that doesn't have the cluster up.
- The default `FlatFileGraphStore` path needs no service and is unaffected by the PostgreSQL
  handling above.

**Never:**
- Never implement the trigger as a `.github/workflows/` GitHub Actions workflow (Epic 8 HARD
  boundary) — a GitHub-hosted runner has none of the three surfaces the compile needs (this
  checkout's `.claude/memory/`, the per-user `~/.claude/projects/<encoded-repo>/*.jsonl`
  transcripts, and the gitignored graph store), so a scheduled workflow would faithfully compile
  an empty machine every night and prove nothing.
- Never build new compile capability, bounding logic, locking, or unattended-mode behavior —
  Story 3.3 already shipped all of that (`cli.py:285-299`); this story only triggers it.
- Never treat the graph store as a source of record — `graph.json` stays a derived, gitignored
  artifact; the freshness check reads its mtime, it does not promote or duplicate its content.
- Never require the durable/PostgreSQL driver path silently as a precondition for the trigger to
  succeed on the default configuration.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Trigger fires on schedule | Trigger installed on the machine holding the three surfaces (`.claude/memory/`, per-user transcripts, graph store) | Compile fires on schedule; four consecutive scheduled runs are recorded (run log or `graph.json` mtime series); the trigger's definition is reviewable in git | N/A — success path, compile exits 0 per Story 3.3's existing contract |
| Freshness check runs | `.claude/data/pyforge-scribe/graph.json` age is compared against the schedule's own period | Age is reportable; a store older than the schedule's period surfaces as a finding | Finding is **advisory only** — never a PR gate, never a second verdict |
| GitHub Actions considered as the trigger mechanism | A future contributor or reviewer proposes `.github/workflows/` | Runbook § *Scope note* explains why not (hosted runner lacks all three surfaces) | Boundary is documented explicitly; no workflow file is added |
| Scheduled run configured against the PostgreSQL `GraphStore` driver | Trigger fires while the local Postgres cluster is not running | Trigger starts `scribe-pg-up`, or refuses cleanly with a clear message | Must never fail red on a machine without the cluster; default `FlatFileGraphStore` runs unaffected |

</intent-contract>

## Code Map

- `pixi.toml` (root) — add the nightly-compile trigger task (mirrors the existing
  `pyforge-scribe` feature/task block conventions)
- estate-side hook that invokes the task — a marshal dispatch hook (under
  `src/shared/packages/pyforge-marshal/`), or a versioned systemd-user/`launchd` unit installed by
  the bootstrap — exact home is an implementation choice within the story's Surface note
- `src/shared/packages/pyforge-scribe/docs/cli-runbooks.md` § *Installing the nightly trigger* —
  replace the "opt-in operator crontab entry" framing with the new documented, repeatable
  installation act; add a § *Scope note* recording why this is not a GitHub Actions workflow
- `src/shared/packages/pyforge-scribe/src/pyforge/scribe/cli.py` (~L285-301) — read-only reference:
  the existing `graph compile --nightly` entrypoint (`flock -n`-safe, exits 0 on overlap) this
  story triggers, not modifies
- a freshness/staleness check reachable from the detector set (advisory finding only) — likely a
  new detector source or an addition to an existing one
- `.claude/data/pyforge-scribe/graph.json` — read only; the freshness check inspects its mtime;
  stays gitignored and derived

## Tasks & Acceptance

**Execution:**
- feature: define a checked-in trigger — a `pixi.toml` task plus the estate-side hook that invokes
  it (marshal dispatch hook, or a versioned systemd-user/`launchd` unit the bootstrap installs) —
  never `.github/workflows/`
- docs: rewrite `cli-runbooks.md` § *Installing the nightly trigger* to document the new
  repeatable installation act, replacing the hand-typed-`crontab` framing
- docs: add `cli-runbooks.md` § *Scope note* recording why this is not a GitHub Actions workflow
- feature: add an advisory freshness/staleness check (age of `graph.json` vs. the schedule's own
  period) reachable from the detector set — never a PR gate, never a second verdict
- feature: make the trigger either start `scribe-pg-up` or refuse cleanly when the configured
  `GraphStore` driver is PostgreSQL and the local cluster is not up; leave the default
  `FlatFileGraphStore` path unaffected

**Acceptance Criteria:**
- Given `scribe graph compile --nightly` is prompt-free, `flock -n`-safe and exits 0 on an
  overlapping firing (`cli.py:285-299`), and the only documented trigger is "an opt-in operator
  crontab entry" (`cli.py:290-291`, `docs/cli-runbooks.md` § *Installing the nightly trigger*)
  that is not installed — the store's last write is 2026-08-27 — when the trigger is defined in
  the repo and installed by a documented, repeatable act rather than a hand-typed `crontab -e`,
  then the compile fires on schedule on the machine that holds the three surfaces, four
  consecutive scheduled runs are recorded (run log or graph mtime series), and the trigger's
  definition is reviewable in git.
- And a freshness signal exists and is checkable: the age of `.claude/data/pyforge-scribe/graph.json`
  is reportable, and a store older than the schedule's own period surfaces as an **advisory**
  finding — never a PR gate and never a second verdict.
- And the boundary is honoured explicitly: the story records **why** this is not a GitHub Actions
  workflow (runbook § *Scope note*), so the next pass does not re-propose one.
- And the durable-driver path is not silently required — the default `FlatFileGraphStore` needs no
  service; if a scheduled run is ever pointed at the PostgreSQL driver it needs the local cluster
  up (`scribe-pg-up`), which the trigger must either start or refuse cleanly, never fail red on a
  machine without it.

## Spec Change Log

## Review Triage Log
