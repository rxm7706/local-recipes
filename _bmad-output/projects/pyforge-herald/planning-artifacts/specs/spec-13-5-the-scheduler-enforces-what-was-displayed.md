---
title: 'The scheduler enforces what was displayed'
type: 'feature'
created: '2026-08-13'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
context: []
warnings: ['oversized']
baseline_revision: '488105bdc1b812d849ae7317bac1dcbe3e32bbac'
final_revision: 'fce8d5ba044fb452de6c552b79583d75eff9e9e3'
---

<intent-contract>

## Intent

**Problem:** Evidence staleness (`evidence.STALE_AFTER = 7 days`) is only ever computed
on read, never enforced, and the progress web-tab snapshot only refreshes when an
operator remembers to run `herald success validate --all` / re-export it by hand.
`docs/operator-guide.md`/`docs/automation-troubleshooting.md` both admit today: "There's
no weekly job doing this automatically."

**Approach:** Add a `scheduler.py` module composing the two operations Story 8.2/9.5
already scaled down to operator-run CLI verbs — evidence revalidation
(`claims.revalidate_all`) and the progress snapshot export — behind one new
`herald scheduler run` CLI verb, then wire a *real* recurring trigger for it: a
documented local `cron` entry, not a GitHub Actions workflow (`.herald/` is gitignored,
operator-local state — a fresh CI checkout would run the job against nothing real,
unlike `dashboard.yml`'s git-history-derived data).

## Boundaries & Constraints

**Always:**
- Evidence revalidation reuses `claims.revalidate_all` unchanged (same behavior as
  `herald success validate --all`: never raises on a broken link, updates
  `validated`/`validated_at`, returns the updated claims).
- Progress aggregation reuses `progress.list_records`, writing the same
  `web/public/progress.json` shape `scripts/export_progress_snapshot.py` already
  produces — refactor that script to delegate to a new `progress.write_snapshot`
  function instead of duplicating the write logic a third time (cli.py's `--json`
  listing is the second).
- The new `herald scheduler run` verb follows the existing dispatcher conventions:
  added to `TOP_LEVEL_COMMANDS`, routed via `_route`, wrapped in `dispatch`.
- Both jobs run unconditionally on every invocation — the 7-day window is enforced by
  the trigger's cadence (~weekly cron), not by in-code filtering.
- Neither job requires the operator role: mirrors `success validate`'s existing ungated
  behavior (revalidation/export never create or modify claim/progress content, only
  refresh derived state).
- Document the real trigger (a copy-pasteable `crontab` line invoking
  `pixi run -e pyforge-herald herald scheduler run`) in `docs/cli-runbooks.md`, and
  replace the "no weekly job"/"no scheduled job" language in `operator-guide.md` and
  `automation-troubleshooting.md` now that the mechanism exists.

**Never:**
- No new scheduler dependency (APScheduler/Celery/etc.) — `evidence.py`'s own docstring
  already settled this ("adding a scheduler dependency for one weekly re-check is
  exactly the kind of speculative weight this repo's lean-dependency doctrine argues
  against").
- No operator-alert delivery (email/Slack/etc.) — named under LB-2 (the webhook,
  Story 13.4), not LB-3; out of scope here.
- No GitHub Actions workflow — would silently run against an empty `.herald/herald.db`
  on every fresh checkout, which is worse than not building it (false confidence).
- No changes to Story 13.4 (webhook, still blocked) or its cross-station dependency.
- No change to the shape of any existing CLI command or the web-tab contract.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Happy path | `.herald/herald.db` has progress records and claims with evidence | `herald scheduler run` revalidates every claim's evidence, writes `progress.json`, prints a summary (records aggregated, claims revalidated) | No error expected |
| Empty DB | fresh `.herald/herald.db`, no records/claims | Job completes; summary reports zero counts | No error — not a failure |
| Broken evidence link | a claim's evidence link now 404s | That claim's evidence entry is marked `validated: false`; summary names the claim id; exit code 0 (matches `validate --all`'s never-raise contract) | Surfaced in output text/JSON, never raised |
| `--json` output | `herald scheduler run --json` | One JSON object: counts + list of claim ids with newly-broken evidence | No error expected |

</intent-contract>

## Code Map

- `src/pyforge/herald/scheduler.py` -- NEW. `run_evidence_revalidation(claims_path, *, validate=None, now=...)` (thin wrapper over `claims.revalidate_all`, returns a summary), `run_progress_aggregation(progress_path, out_dir, ...)` (calls `progress.write_snapshot`), `run_scheduled_jobs(...)` composing both into one result dataclass.
- `src/pyforge/herald/progress.py` -- add `write_snapshot(progress_path: Path, out_dir: Path) -> Path`, moved from `scripts/export_progress_snapshot.py`'s `export_progress_snapshot` body (same output shape: `out_dir/progress.json`, newest-first, `json.dumps(..., indent=2)`).
- `scripts/export_progress_snapshot.py` -- refactor `export_progress_snapshot()` to call `progress.write_snapshot`; CLI wrapper (`main`) unchanged.
- `src/pyforge/herald/cli.py` -- add `"scheduler"` to `TOP_LEVEL_COMMANDS`; a `scheduler` subparser with a `run` subcommand (`--repo-root`, `--out-dir`, `--json`); `_run_scheduler_run`; a `_route` branch.
- `tests/test_scheduler.py` -- NEW unit tests for the module (empty DB, populated DB, broken-link case, injected clock).
- `tests/test_cli_epic13.py` -- NEW CLI-level tests for `herald scheduler run` (mirrors `tests/test_cli_success.py`'s `--repo-root tmp_path` isolation pattern and the `_stub_evidence_validation` autouse fixture).
- `tests/test_export_progress_snapshot.py` -- re-verify unchanged behavior post-refactor (no new tests required, existing ones must still pass).
- `docs/cli-runbooks.md`, `docs/operator-guide.md`, `docs/automation-troubleshooting.md` -- document `herald scheduler run` and the crontab trigger; remove the now-false "no weekly job" claims.

## Tasks & Acceptance

**Execution:**
- [x] `src/pyforge/herald/progress.py` -- add `write_snapshot(progress_path, out_dir) -> Path` -- gives `scheduler.py` a package-internal call target (scripts/ is unpackaged, can't be imported back into src/pyforge)
- [x] `scripts/export_progress_snapshot.py` -- delegate `export_progress_snapshot()` to `progress.write_snapshot` -- removes the now-duplicated write logic
- [x] `src/pyforge/herald/scheduler.py` -- implement `run_evidence_revalidation`, `run_progress_aggregation`, `run_scheduled_jobs` -- the scheduled-job module (this story's named Surface)
- [x] `src/pyforge/herald/cli.py` -- add `scheduler run` subcommand + `_run_scheduler_run` + `_route` branch -- the operator/cron-facing entry point
- [x] `tests/test_scheduler.py` -- unit-test the I/O matrix above -- proves the module's behavior independent of the CLI
- [x] `tests/test_cli_epic13.py` -- CLI-level tests for `scheduler run` (`--json` and plain output, exit code 0 on broken links) -- proves the wiring
- [x] `docs/cli-runbooks.md` -- add `herald scheduler run` + the crontab install line (weekly, e.g. `0 3 * * 0`) -- the "+ config" half of this story's Surface
- [x] `docs/operator-guide.md`, `docs/automation-troubleshooting.md` -- replace "no weekly job"/"no scheduled job" language with the new command + cron pointer -- keeps docs truthful post-implementation

**Acceptance Criteria:**
- Given a `.herald/herald.db` with claims carrying evidence and progress records, when `herald scheduler run` executes, then every claim's evidence is revalidated (`claims.revalidate_all` semantics) and `progress.json` is rewritten from the current DB state, both in one invocation.
- Given a claim whose evidence link now returns 404, when `herald scheduler run` executes, then the claim's evidence is marked unvalidated and named in the summary output, and the command still exits 0.
- Given the documented crontab line is installed, when the scheduled time arrives, then `herald scheduler run` executes without any operator action — the mechanism this story delivers, verified by manual/CLI inspection since no server exists yet to observe end-to-end (Story 13.6's job).
- Given no `--json` flag, when `herald scheduler run` completes, then human-readable summary lines are printed (record count aggregated, claims revalidated, any broken-evidence claim ids).

## Spec Change Log

## Review Triage Log

### 2026-08-13 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 5 (high 0, medium 2, low 3)
- defer: 1 (high 0, medium 1, low 0)
- reject: 6 (high 0, medium 0, low 6)
- addressed_findings:
  - `[medium]` `[patch]` `run_scheduled_jobs` chained the two jobs — a `HeraldError` from evidence revalidation silently skipped progress aggregation for that invocation. Fixed: both jobs now always run; the error re-raises after both are attempted.
  - `[medium]` `[patch]` An `OSError` from `progress.write_snapshot` (disk full, unwritable `--out-dir`) escaped `dispatch`'s `HeraldError`-only catch as a raw traceback instead of the CLI's structured error contract. Fixed: `_run_scheduler_run` now wraps `OSError` as a `HeraldError`.
  - `[low]` `[patch]` `broken_evidence_claim_ids` could misname a claim `claims.revalidate_all` left untouched (its own discard-stale-on-conflict rule) as "broken," since such a claim can still carry pre-existing `validated=False` evidence. Fixed: only evidence stamped with this run's own shared timestamp counts.
  - `[low]` `[patch]` The documented weekly crontab had no overlap guard despite evidence revalidation's unbounded-by-claim-count runtime. Fixed: added an `flock -n` wrapper to the recipe in `docs/cli-runbooks.md`.
  - `[low]` `[patch]` `--out-dir`'s default docstring implied unconditional equivalence to `export_progress_snapshot.py`'s package-anchored default without stating the "only when `--repo-root` is this package's own checkout" condition plainly, or that the two commands' `--repo-root` conventions differ from `deck`'s portable one. Fixed: clarified the docstring and `cli-runbooks.md`'s trigger section.

**Deferred:** `DW-FU-13-5` (medium) — `claims.revalidate_all`'s sequential, unbounded-by-claim-count HTTP evidence checks are pre-existing (Story 9.5) but now reachable unattended via cron instead of only under an operator's eye; latent at today's claims-store scale. See `_bmad-output/implementation-artifacts/deferred-work.md`.

**Rejected (noise, not this story's problem):** `herald scheduler run --json`'s structured error output "inconsistent" with `success validate --json` — pre-existing gap in `success validate` (never implemented `--json` output at all), not a regression in the new command, which implements it correctly · a claim that no Story 13.5 spec file exists anywhere in the repo — false; it exists at `_bmad-output/implementation-artifacts/spec-13-5-the-scheduler-enforces-what-was-displayed.md`, readable via the Tier-3 backlink, just outside a plain `git`-tracked search · `evidence.schedule_async_validation` left unused — a pre-existing (Story 6.4), already-dead lower-level utility; `claims.revalidate_all` (which the spec explicitly mandates reusing) is the correct, DB-aware integration point, not a gap · a second unsynchronized `list_records` read for the `records_aggregated` count vs. `write_snapshot`'s own read — a real but purely cosmetic race (an informational count) with a multi-microsecond window in a single-writer local cron job · no CLI/doc callout that the ungated write-refresh command now runs off cron as well as interactively — the ungated design is an explicit, spec-mandated reuse of `success validate`'s established precedent, not a new exposure · a challenge to "both jobs run unconditionally" (no in-code staleness filtering) as possibly under-specified by `epics.md` — already a reasoned, explicit Design Notes decision made during planning, not an oversight.

## Design Notes

**Why a local cron entry, not GitHub Actions.** `dashboard.yml`'s cron works because it
regenerates data from git history on every fresh checkout — a durable source. Herald's
`.herald/herald.db` is gitignored, per-operator-local state (Story 1.4, AD-5); a
GitHub-hosted runner would never have populated it, so the job would silently do
nothing every run — worse than today's "operator remembers," since it would look
automated while doing nothing. A local `cron` entry runs on the same filesystem as the
real DB, so it actually enforces the window — matching `evidence.py`'s own docstring:
"whatever already triggers periodic work in this repo (a cron entry, a pixi task) can
invoke it directly."

**Why `progress.write_snapshot` moves into the package.** `pyproject.toml` only
packages `src/pyforge`; `scripts/` is an unpackaged dev convenience `scheduler.py`
cannot import back into `src/`. Moving the write logic in once, and having the script
delegate to it, avoids a third copy of the same four lines.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-herald pyforge-herald-test` — expected: pass (station policy verify command; reconciled 2026-08-30 after policy drifted from this spec's original declaration).

**Manual checks (if no CLI):**
- Confirm `docs/cli-runbooks.md`'s crontab line is copy-pasteable and matches the actual `herald scheduler run` invocation added to `cli.py`.

## Auto Run Result

Status: done

**Summary.** Story 13.5 adds `herald scheduler run`: a new CLI verb composing evidence
revalidation (`claims.revalidate_all`, unchanged from Story 9.5) and a progress-snapshot
export into one operator/cron-facing invocation, so the 7-day evidence-staleness window
and the web dashboard's Progress tab are actually enforced on a schedule instead of
operator-remembered. The trigger is a documented local `crontab` entry with an `flock -n`
overlap guard -- not GitHub Actions, since `.herald/herald.db` is gitignored,
per-operator-local state a GitHub-hosted runner would never have populated.

**Files changed:**
- `src/pyforge/herald/scheduler.py` (new) -- the scheduled-job module: `run_evidence_revalidation`, `run_progress_aggregation`, `run_scheduled_jobs`.
- `src/pyforge/herald/progress.py` -- new `write_snapshot()`, moved from the export script so `scheduler.py` (unpackaged `scripts/` can't be imported back into `src/`) can call it too.
- `scripts/export_progress_snapshot.py` -- delegates to `progress.write_snapshot`; CLI wrapper unchanged.
- `src/pyforge/herald/cli.py` -- `scheduler run` subcommand, `_run_scheduler_run`, `_route` branch; wraps `OSError` as a structured `HeraldError`.
- `tests/test_scheduler.py` (new), `tests/test_cli_epic13.py` (new) -- unit + CLI-level coverage of the full I/O matrix plus the review-pass fixes.
- `tests/test_bridge.py` -- classifies `scheduler.py` in the bridge-core module sweep (required by an existing meta-test).
- `docs/cli-runbooks.md`, `docs/operator-guide.md`, `docs/automation-troubleshooting.md` -- document the new command and the crontab trigger; retire the now-false "no weekly job" language.

**Review findings breakdown:** 5 patches applied (job isolation between the two composed
jobs so a claims-store failure no longer silently skips the progress snapshot; an `OSError`
from an unwritable `--out-dir` now surfaces as a structured `HeraldError` instead of a raw
traceback; `broken_evidence_claim_ids` no longer misnames a claim `revalidate_all` left
untouched by a concurrent write; the documented crontab gained an `flock -n` overlap guard;
the `--out-dir` default's docstring now states its "only when `--repo-root` is this
package's own checkout" condition plainly) -- all committed with dedicated regression
tests. 1 item deferred (`DW-FU-13-5`: `claims.revalidate_all`'s sequential, unbounded HTTP
evidence checks are pre-existing from Story 9.5 but now reachable unattended via cron
instead of only under an operator's eye; latent at today's claims-store scale). 6 items
rejected as noise (a false claim that no Story 13.5 spec exists in the repo; a pre-existing
`success validate --json` gap mistaken for a scheduler regression; flagging the unused,
already-dead `evidence.schedule_async_validation` as if this story should have wired it in
over the correct, spec-mandated `claims.revalidate_all`; a cosmetic microsecond-window
double-read race on an informational count; a soft "should this be documented as wider
auth exposure" note against an explicit, spec-mandated ungated design; a re-litigation of
an already-reasoned Design Notes decision).

**Follow-up review recommendation:** false. The five patches are localized to two source
files (`scheduler.py`, `cli.py`) plus one doc, each independently covered by a new
regression test, with the full suite green throughout -- matches the "a few localized
low-consequence fixes" case the workflow's own guidance says does not warrant an
independent follow-up pass.

**Verification performed:**
- `pixi run -e pyforge-herald pyforge-herald-test`: 851 passed, 2 skipped (848 baseline +
  3 new regression tests from the review pass).
- Manual: `herald scheduler run --repo-root <scratch dir> --json` produces a valid JSON
  summary at exit 0 against a fresh `.herald/` directory.
- `git status`/`git diff` inspected directly (not just the implementation subagent's
  self-report) before and after the review pass; confirmed no changes outside this
  story's intended files (no `pixi.toml`, no `.github/workflows/`, no `recipes/`).

**Residual risks:** `DW-FU-13-5` (deferred, medium) -- evidence revalidation's sequential
HTTP checks have no batching/cap and are now cron-reachable; latent, not active, at
today's small claims-store scale. This is a Herald `local-recipes` monorepo PR touching
files outside `recipes/` (docs, scripts, `src/`) -- per `CLAUDE.md`'s PR CI gate rule, the
PR needs the `maintenance` label at open/update time; `pixi.toml` was not touched, so the
`environment.yaml` sync gate does not apply.
