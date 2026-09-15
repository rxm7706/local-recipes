---
title: '44.1: marshal watch ports the operator''s ritual into a real CLI verb'
type: 'feature' # feature | bugfix | refactor | chore
created: '2026-09-15'
status: 'ready-for-dev' # draft | ready-for-dev | in-progress | in-review | done | blocked
baseline_revision: 'c717dfaca05'
review_loop_iteration: 0 # incremented by step-04 before each review loopback
followup_review_recommended: false # set by step-04 on status: done; step-01 READS this — false HALTs, true allows one follow-up then forces false
context: ['{project-root}/.claude/skills/marshal-run-watch/SKILL.md'] # the Claude skill whose validated logic this story ports
deferred: [] # append-only machine-readable deferred review findings; each item carries summary/evidence and optional location/severity
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** Watching a live `bmad-loop` run or `bmad-build-auto` dispatch today means an
operator hand-driving a ritual through a chat session: `bmad-loop status <run_id> --json`,
`bmad-loop list --json`, `marshal status --project <slug>`, diffing the result against what was
true minutes ago, and deciding how long to wait before checking again. That ritual was worked
out live (2026-09-15, pyforge-herald run `20260914-201759-bd47`, Epic 21) and captured as a
Claude-only project skill (`.claude/skills/marshal-run-watch/SKILL.md`) — proven correct, but
invisible to marshal's own CLI, its unified `pyforge marshal` grammar, its MCP face, its persona,
and its portal.

**Approach:** Add a `marshal watch` subcommand (new `cli/watch.py`, registered in `cli/main.py`
alongside `status`/`homes`/`check`) that ports the skill's validated ground-truth-gathering +
delta-vs-last-observation + boundary-aware poll-delay-recommendation logic into real, tested
Python. Three scopes: a pinned run (`--project SLUG --run RUN_ID`), a station's current run
(`--project SLUG` alone, auto-detecting pattern and run_id), or the whole fleet (`--fleet`,
discovering every project under `_bmad-output/projects/*/` live). Reuses the SAME ground truth
`bmad-loop status`/`list` and `marshal status` already read — no new data source, no second
status engine.

## Boundaries & Constraints

**Always:**
- Register `watch` as a new top-level subcommand in `cli/main.py`'s `_build_parser`, calling
  `watch_cli.add_watch_subparser(subparsers)` — the exact pattern every existing verb uses
  (`status_cli.add_status_subparser(subparsers)` et al., `cli/main.py:264` and neighbors).
- Return the shared `Envelope` shape every marshal command returns
  (`core/model.py::build_envelope` — `schema_version`, `command`, `status`, `verdict`, `data`,
  `data_version`, `findings`, `assumptions`). `marshal watch`'s `data` carries the report; do not
  invent a parallel response shape.
- For the `bmad-loop` pattern (a project with a live/paused row in
  `~/.bmad-loops/<slug>/.bmad-loop/runs/` via `bmad-loop list --json`), ground truth is `bmad-loop
  status <run_id> --json` for per-story detail, `bmad-loop list --json` for overall run status.
  `marshal status --project <slug>`'s `dispatch_*` fields are consulted ONLY for supervisor
  liveness (`data.homes[0].state`), never as this pattern's per-story ground truth — they can
  describe a stale, unrelated prior `bmad-build-auto` dispatch for the same slug.
- For the `bmad-build-auto` pattern (no live/paused `bmad-loop` row for the slug), ground truth is
  entirely `marshal status --project <slug>`'s `dispatch_*` fields
  (`dispatch_run_id`/`dispatch_completion_verdict`/`dispatch_verification_verdict`/
  `dispatch_supervisor_alive`/`current_story`/`escalation_reason`).
- Auto-detect pattern and run_id when `--run` is omitted: check for a `running`/`paused` row in
  `bmad-loop list --json` first (bmad-loop pattern wins if present), else fall back to
  `marshal status`'s `dispatch_run_id` (bmad-build-auto pattern).
- Persist the last observation as a small local JSON cache (one file per pinned
  slug+run_id, one shared file for `--fleet`), under
  `.claude/data/marshal-run-watch/<slug>__<run_id>.json` / `.claude/data/marshal-run-watch/__fleet__.json`
  — mirroring the skill's own cache convention. Missing or unreadable cache means "first
  observation," never a fabricated delta.
- Compute `changed` from: any story's `phase`/`commit_sha` (bmad-loop) or
  `dispatch_completion_verdict`/`dispatch_verification_verdict` (bmad-build-auto); the run's
  overall status; a new `paused_reason`/`escalation_reason`; the loop branch's SHA (`git
  rev-parse origin/loop/<slug>`, best-effort — a `git` failure is a finding, not a crash).
- Recommend a next-check delay in the report: `min(300, seconds_to_next_half_hour_boundary)`
  while a run is actively progressing (any story `dev-running`/`review-running`, or `--fleet`
  with at least one project in that state); boundary-only (no 300s floor) while
  paused/escalated; omit the recommendation once the run/dispatch is finished/terminal.
- Discover fleet-scope projects live via `_bmad-output/projects/*/` — never a hardcoded slug
  list.

**Never:**
- Never resolve escalations, resume runs, dispatch new work, or write to any sprint ledger.
  `marshal watch` is read-only, full stop.
- Never treat `marshal watch` as a second fleet-summary verdict competing with `marshal status`
  — it is a report *shape* over the same ground truth, not a new source of truth.
- Never fabricate a delta or a queue when an underlying `bmad-loop`/`git`/`gh` command fails —
  report the failure as a `Finding`, do not guess.
- Never require network access for the core diff+report logic to be testable — tests drive it
  against fixture journals/state, not a live `bmad-loop` process or GitHub API.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Pinned bmad-loop run, first check | `--project X --run R`, no prior cache | First-observation report (all five sections), cache written | No error expected |
| Pinned bmad-loop run, no change | Same run, unchanged since last cache | Report states "nothing changed" explicitly (not a full repeated report), delay recommendation given | No error expected |
| Pinned bmad-loop run, story completed | A story's `phase`/`commit_sha` changed since cache | Full report surfaces the completion under Session Completions / Delta | No error expected |
| Stale unrelated dispatch record present | `marshal status --project X`'s `dispatch_*` describes a different, older run than live `bmad-loop status` | Report uses only the `bmad-loop` result for per-story detail and states the stale record was ignored | No error expected |
| Station scope, no run given | `--project X` alone, live bmad-loop row exists | Auto-detects bmad-loop pattern + that run's id, proceeds as pinned | No error expected |
| Station scope, no run given | `--project X` alone, no bmad-loop row, dispatch record exists | Auto-detects bmad-build-auto pattern from `marshal status`'s `dispatch_run_id` | No error expected |
| Fleet scope | `--fleet` | Compact per-project snapshot, escalated/paused sorted first, discovered live from `_bmad-output/projects/*/` | No error expected |
| Run paused/escalated | `bmad-loop status`'s `paused_stage == "escalation"` | User Action Required section states the blocking condition; delay recommendation is boundary-only | No error expected |
| Run finished | `bmad-loop status`'s `finished: true` | Report states completion; no next-check delay recommended | No error expected |
| No prior cache, cache directory missing | First invocation ever for this cache key | Cache directory created, first-observation report produced | No error expected |
| `bmad-loop` CLI unavailable / errors | `bmad-loop status`/`list` exits non-zero | A `Finding` names the failed command; no delta fabricated | Exit non-zero, `verdict: error` |
| Neither `--run` nor `--fleet` resolvable | `--project X` with no live bmad-loop row and no `dispatch_run_id` | A `Finding` states no active run found for the slug | Exit non-zero, `verdict: error` |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/main.py:243-276` (`_build_parser`)
  — add `watch_cli.add_watch_subparser(subparsers)` alongside the existing
  `status_cli`/`check_cli`/`init_cli` registrations, same import-and-call pattern.
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/status.py:361-` (`add_status_subparser`)
  — the argparse subparser registration pattern to mirror exactly for `add_watch_subparser`
  (parser help/description text, `--project`/`--format` flag conventions).
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/model.py:48-` (`Verdict`, `Status`,
  `Severity`, `Finding`, `Envelope`, `build_envelope`) — the shared response envelope every
  marshal command returns; `marshal watch` must return this shape, not a bespoke one.
- `.claude/skills/marshal-run-watch/SKILL.md` (whole file) — the validated ground-truth-gathering,
  delta-predicate, boundary/backoff-pacing, and report-shape logic this story ports. Treat its
  Step 1 (ground truth per pattern), Step 2 (state diff), Step 3 (surface-or-quiet decision), and
  Step 5 (next-delay recommendation) as the algorithm; do not redesign them.
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/status.py` (`run_status`,
  supervisor/engine liveness distinction) — the existing `UNSUPERVISED`-vs-dead-engine handling
  `marshal watch`'s fleet-scope liveness read should reuse rather than re-derive.
- `src/shared/packages/pyforge-marshal/tests/` (existing test module layout for `status`/`homes`/
  `check`) — the fixture-journal/fixture-state testing convention to extend for `watch`'s tests
  (no live `bmad-loop` process required).

## Tasks & Acceptance

**Execution:**
- `cli/watch.py` (new) -- argparse subparser (`--project`, `--run`, `--fleet`, `--format`),
  pattern auto-detection, ground-truth gathering per pattern, the local JSON cache read/write,
  the delta predicate, the report renderer (pinned/station five-section shape; fleet compact
  snapshot), and the next-delay recommendation -- the story's entire surface
- `cli/main.py` -- wire `add_watch_subparser` into `_build_parser`
- `tests/` -- new test module covering every I/O matrix row above via fixture journals/state,
  no live `bmad-loop` process or network call

**Acceptance Criteria:**
- Given a pinned `bmad-loop`-pattern run with no prior cache, when `marshal watch --project
  <slug> --run <run_id>` runs, then the report's five sections (Session Completions / Delta
  Since Last Update / Currently Running / Up Next & Full Queue / User Action Required) are
  populated from `bmad-loop status`/`list` alone, and a cache file is written.
- Given the same run with no intervening change, when `marshal watch` runs again, then the
  report states plainly that nothing changed rather than repeating the full report verbatim.
- Given `marshal status --project <slug>`'s `dispatch_*` fields describe a different, older run
  than the live `bmad-loop status` result, when `marshal watch --project <slug>` runs, then the
  report's per-story detail comes only from `bmad-loop status`, and the report states a stale
  unrelated dispatch record was present and ignored.
- Given `--fleet`, when `marshal watch` runs, then every project under `_bmad-output/projects/*/`
  is discovered live (not from a hardcoded list) and reported in a compact per-project snapshot
  with escalated/paused projects sorted first.
- Given any run in any scenario, `marshal watch` never writes to a sprint ledger, never calls
  `bmad-loop resolve`/`resume`/`dispatch`, and its own persisted cache is the only file it writes
  outside of `.claude/data/marshal-run-watch/`.

## Spec Change Log

## Review Triage Log

## Design Notes

**Pattern auto-detection.** Reuse the skill's own Step 0 logic verbatim: check
`~/.bmad-loops/<slug>/.bmad-loop/runs/` existence and `bmad-loop list --json` for a
`running`/`paused` row first; only fall back to the `bmad-build-auto`/`dispatch_run_id` reading
when no such row exists. This ordering matters — a station can have BOTH a live `bmad-loop` run
and a stale `dispatch_*` record simultaneously (observed live 2026-09-15 on pyforge-herald), and
the `bmad-loop` row must win.

**Cache key shape.** One cache file per `(slug, run_id)` pair for pinned/station scope, one
shared `__fleet__.json` for fleet scope — mirroring the skill's own two-file convention so a
fleet watch and a pinned watch on the same slug never clobber each other's state.

**Boundary math.** "Next `:00`/`:30` boundary" means the next wall-clock minute divisible by 30;
compute it in UTC from `datetime.now(timezone.utc)`, matching the skill's own convention (avoids
local-timezone drift between the CLI and whatever `/loop` session recommends a delay from it).

## Verification

**Commands:**
- `pixi run -e pyforge-marshal pyforge-marshal-test -k watch` -- expected: all new tests pass,
  covering every I/O matrix row above
- `pixi run -e pyforge-marshal marshal watch --project pyforge-marshal` (manual smoke, read-only,
  matching this repo's own dogfood-on-a-real-station convention) -- expected: a real report
  against this very story's own dispatch run, no crash, no ledger/file write outside the cache

## Auto Run Result
