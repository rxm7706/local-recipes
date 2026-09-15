---
name: marshal-run-watch
description: Reusable ops-manager status check for marshal-supervised BMAD work — one pinned run, a whole station (project), or the entire fleet (all projects). Covers both the multi-story bmad-loop orchestrator pattern and the one-shot bmad-build-auto dispatch pattern. Gathers ground truth, diffs against last-known persisted state, surfaces a structured report only when something changed or a :00/:30 boundary is due, and recommends the next poll delay for /loop dynamic mode. Use when invoked by name, or via a /loop session watching a run, a station, or the fleet.
---

# Marshal Run Watch

Parameterized, repeatable status check for marshal-supervised BMAD work, at
three scopes. Built so a `/loop` dynamic-mode session can call it every tick
without the operator re-pasting the "operations manager" prompt each time,
and so it works unchanged for the NEXT run, a different station, or a
fleet-wide sweep.

Two run patterns exist within a station and this skill handles both:

- **`bmad-loop`** — a multi-story orchestrator run living in
  `~/.bmad-loops/<slug>/`, driven by the `bmad-loop` CLI. Ground truth is
  `bmad-loop status <run_id> --json` + `bmad-loop list --json`.
- **`bmad-build-auto`** — a single-story detached dispatch launched via
  `marshal factory dispatch`. There is no separate orchestrator run; ground
  truth is entirely `marshal status --project <slug>`'s `dispatch_*` fields.

## Arguments

Parsed from the trailing `ARGUMENTS:` line, whitespace-separated. The first
token selects scope:

1. **`fleet`** — watch every BMAD project at once (discovered live from
   `_bmad-output/projects/*/` — never a hardcoded list). No further args.
   Produces a compact per-project snapshot (Step 4b), not the full 5-section
   report. Use for a wide "is anything stuck" sweep.
2. **`station <slug>`** — watch a station's most-recent/active run,
   auto-detecting pattern and run_id (Step 0). Full single-run report.
3. **`<slug> [run_id] [pattern]`** (bare slug, no `fleet`/`station` keyword)
   — shorthand for `station <slug>` when `run_id`/`pattern` are omitted, or a
   fully pinned run when given. This is the backward-compatible form; a
   `/loop` already running this shorthand keeps working unchanged.
   - `run_id` (optional): `bmad-loop` pattern: the harness run id
     (`YYYYMMDD-HHMMSS-xxxx`). `bmad-build-auto` pattern: the marshal-tracked
     dispatch run id (`<slug>-YYYYMMDDTHHMMSSmmmZ-xxxxxxxx`). Omit to
     auto-detect (Step 0).
   - `pattern` (optional): `bmad-loop` or `bmad-build-auto`. Omit to infer.

If the first token is empty entirely (no arguments at all), stop and ask
whether to watch `fleet`, a specific station, or a specific run — never guess.

Example invocations:
- `fleet` — sweep all projects
- `station pyforge-warden` — watch pyforge-warden's current run, whatever it is
- `pyforge-herald 20260914-201759-bd47 bmad-loop` — pin an exact run
- `pyforge-warden` — bare-slug shorthand, same as `station pyforge-warden`

## Step 0 — auto-detect run_id / pattern when omitted (station/pinned scope only)

Not applicable to `fleet` scope — see Step 1's fleet branch instead.

If `pattern` is omitted: check whether `~/.bmad-loops/<slug>/.bmad-loop/runs/`
exists and `cd ~/.bmad-loops/<slug> && pixi run -e local-recipes bmad-loop list --json`
has any row with `status` in `running`/`paused`. If so, pattern is `bmad-loop`.
Otherwise, pattern is `bmad-build-auto`.

If `run_id` is omitted:
- `bmad-loop` pattern: take the **last** entry in `bmad-loop list --json`'s
  `runs` array (chronologically newest) whose `status` is `running` or
  `paused`; if none, take the newest entry overall and note it is not live.
- `bmad-build-auto` pattern: read `dispatch_run_id` from
  `marshal status --project <slug> --format json`'s `data.homes[0]`.

State the resolved `run_id`/`pattern` explicitly in the report so the operator
can pin it next time.

## Step 1 — gather ground truth

**`fleet` scope:** discover every project slug live —
`ls _bmad-output/projects/` (repo root) — never reuse a hardcoded list, a
project gets added/retired. For EACH slug, run the same auto-detection as
Step 0 (pattern, then run_id) and the matching per-pattern ground-truth call
below, but skip the landed-work/journal/epics deep-dives — fleet scope reports
state and current story only, not full detail (that's what `station <slug>`
is for). Also skip a slug entirely (note it as "idle, no active run") when
Step 0 finds no `running`/`paused` row and no live `dispatch_run_id`.

**`bmad-loop` pattern:**
```
cd ~/.bmad-loops/<slug> && pixi run -e local-recipes bmad-loop status <run_id> --json
pixi run -e local-recipes bmad-loop list --json
```
(same directory) — confirms overall run state and catches a status the
per-run call doesn't surface (e.g. `stopped`).

**`bmad-build-auto` pattern:**
```
pixi run -e pyforge-marshal marshal status --project <slug> --format json
```
This pattern's ground truth IS this command's `dispatch_*` fields:
`dispatch_run_id`, `dispatch_baseline_revision`, `dispatch_final_revision`,
`dispatch_completion_verdict`, `dispatch_verification_verdict`,
`dispatch_verification_failed_gate`, `dispatch_supervisor_alive`,
`dispatch_story_started_at`/`_ended_at`, `current_story`, `escalation_reason`.
There is no separate orchestrator-run status call for this pattern.

**Both patterns, always also run:**
```
pixi run -e pyforge-marshal marshal status --project <slug> --format json
```
For the `bmad-loop` pattern this call's `dispatch_*` fields can be a **stale,
unrelated** one-shot dispatch record left over from a prior attempt — use it
ONLY for `data.homes[0].state` (supervisor liveness), never as this run's
per-story ground truth. `bmad-loop status` is always the source of truth for
`bmad-loop`-pattern per-story detail.

If a story reads `escalated`/paused, or you need the blocking reason, also
read the tail of `.bmad-loop/runs/<run_id>/journal.jsonl` (bmad-loop pattern)
for the latest `story-escalated`/`dev-decision` entries.

**Both patterns, landed-work check** (run from the main repo root):
```
git fetch origin --quiet
git rev-parse origin/loop/<slug>
gh pr list --repo rxm7706/local-recipes --state all --json number,title,headRefName,state,updatedAt --limit 30
```
Filter the PR list to rows whose `headRefName` contains `<slug>` — branch
naming for landing PRs has drifted before (`loop/<slug>` vs `land/<slug>-<story>`
seen historically), so match loosely on the slug rather than one exact prefix.

## Step 2 — load/update persisted state

**Station/pinned scope:** state file
`.claude/data/marshal-run-watch/<slug>__<run_id>.json` (repo-root relative;
`.claude/data/` is gitignored — create the directory if missing).

Read it if present. Compute `changed = true` when any of the following
differs from the loaded state:
- any story's `phase` or `commit_sha` (bmad-loop), or `dispatch_completion_verdict`
  / `dispatch_verification_verdict` (bmad-build-auto)
- the run/dispatch's overall `status` (e.g. `in-progress` → `paused` → `finished`)
- a new `paused_reason`/`escalation_reason` appears
- `origin/loop/<slug>`'s SHA advanced
- the filtered PR list gained a row or any row's `state`/`updatedAt` changed

**Fleet scope:** one state file for the whole sweep,
`.claude/data/marshal-run-watch/__fleet__.json`, keyed by slug. Compute
`changed = true` if ANY slug's `{pattern, run_id, status, current_story_or_phase}`
tuple differs from the loaded state, or a slug appears/disappears (project
added/retired) — same "first observation, not a delta" rule when the file is
absent.

After computing the delta, **overwrite** the state file with the fresh
snapshot (full gathered data + `last_report_at`: now, UTC ISO8601).

## Step 3 — decide whether to surface a report this tick

Compute `now` (UTC). A **boundary tick** is when `now`'s minute-of-hour falls
in `{0,1,2,3,4,30,31,32,33,34}` (a few minutes of slack for firing jitter —
the enclosing loop polls on a computed delay, not to the exact second).

Surface the full report (Step 4/4b) when ANY of:
- `changed` is true (Step 2),
- this is a boundary tick,
- no prior state existed (first run),
- (station/pinned) the run/dispatch just reached `paused`/`escalated` or
  `finished`/terminal; (fleet) any slug just reached `paused`/`escalated`.

Otherwise: this is a quiet tick. Do not print the report — just note in one
line that nothing changed and it's not yet a reporting boundary, then go
straight to Step 5.

## Step 4 — report format (station/pinned scope, when surfacing)

```
## <slug> — Run `<run_id>` (<pattern>) Status Report
*(checked <UTC timestamp>)*

**Session Completions:** stories driven to done/completed since this run/dispatch
started (or since it was last resumed, if that's known) — check phase +
commit_sha / dispatch_completion_verdict directly, never the sprint-status
ledger alone (it lags a live run).

**Delta Since Last Update:** what changed since the last persisted check —
phase transitions, new commits on the loop/landing branch, a new or updated
PR, a new escalation. If this is the first check, say so instead of "none."

**Currently Running:** active story key (bmad-loop) or the dispatch's current
story (bmad-build-auto), phase/verdict, attempt number, token consumption.

**Up Next & Full Queue:** for `bmad-loop`, derive LIVE from
`_bmad-output/projects/<slug>/planning-artifacts/epics.md` (full story
sequence) cross-checked against that project's `sprint-status-ledger.yaml`
(which remain `backlog`) — never reuse a hardcoded sequence from a prior
report, epics get added/rescoped. For `bmad-build-auto` (single story), state
there is no further queue unless the operator names one.

**User Action Required:** explicitly check for a paused/escalated status. If
found, summarize the blocking condition and flag it. Otherwise state "None."
Always add one line noting any stale/unrelated `dispatch_*` record spotted in
Step 1 so it isn't mistaken for this run's state.
```

## Step 4b — report format (fleet scope, when surfacing)

```
## Fleet Watch — <N> projects
*(checked <UTC timestamp>)*

**Delta Since Last Update:** which slugs changed status/current-story/phase,
or gained/lost an escalation, since the last persisted sweep. First sweep:
say so instead of "none."

**Per-Project Snapshot:** one line per slug — `<slug> — <pattern> — <run_id
or "idle"> — <status/phase> — <ESCALATED, if applicable>`. Sort escalated/
paused projects first.

**User Action Required:** for each slug currently paused/escalated, its
blocking condition in one line (pull from that project's own
`bmad-loop status <run_id> --json` `paused_reason`, or `marshal status`'s
`escalation_reason` for bmad-build-auto). "None" if nothing is paused
fleet-wide. Point to `station <slug>` (or a pinned run) for deep-dive detail
on any one project instead of expanding it here.
```

## Step 5 — recommend the next poll delay

State this explicitly so the enclosing `/loop` turn can act on it:

**Station/pinned scope:**
- **Run/dispatch reached a terminal state** (`finished`, or a
  `bmad-build-auto` dispatch with a completion verdict and no further story):
  recommend the loop **stop** (`ScheduleWakeup(stop: true)`), not reschedule.
- **Paused/escalated:** nothing will change faster than a human resolving it.
  Recommend `delaySeconds` = seconds until the next `:00`/`:30` boundary
  (cap at 1800) — keep the visible cadence, but there's no reason to poll
  faster while blocked.
- **Actively in-progress:** recommend
  `delaySeconds = min(300, seconds-to-next-:00/:30-boundary)` — a ~5-minute
  cadence catches a story completing or a PR landing promptly without
  spamming the terminal (Step 3 suppresses the report on quiet 5-minute
  ticks), while never skipping past a half-hour boundary.

**Fleet scope:**
- **At least one slug is actively `running`/`dev-running`/`review-running`:**
  same `min(300, seconds-to-next-boundary)` 5-minute cadence as station scope
  — something fleet-wide could complete or escalate between boundaries.
- **Every slug is idle/finished/paused, nothing actively running:** recommend
  `delaySeconds` = seconds to next `:00`/`:30` boundary only (no 5-minute
  cadence) — polling faster than that buys nothing when nothing is moving.
  Never recommend stopping the fleet loop outright (unlike station scope) —
  a new run can start on any station at any time without this loop knowing.

Always give a one-sentence `reason` reflecting which case applied and the
computed boundary math.

## What this skill does NOT do

- Does not call `ScheduleWakeup` itself — that's the enclosing `/loop` turn's
  job; this skill only recommends the delay and reason.
- Does not resolve escalations, resume runs, or touch any state other than
  its own cache file under `.claude/data/marshal-run-watch/`.
- Does not fabricate a queue or delta when the underlying commands fail —
  report the failure plainly instead.
