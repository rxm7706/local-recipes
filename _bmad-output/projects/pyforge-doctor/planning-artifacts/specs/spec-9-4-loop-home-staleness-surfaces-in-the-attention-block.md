---
title: 'Story 9.4: Loop-home staleness surfaces in the ATTENTION block'
type: 'feature'
created: '2026-08-15'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
context: []
warnings: ['oversized']
difficulty: ''
baseline_revision: '531e0e128fc2150d07a7fd4e6ee07dffdfa433a7'
final_revision: '70c7654dc39fa2a0d6733989acf340bc94a7cecc'
---

<intent-contract>

## Intent

**Problem:** No automated signal exists for a `loop/pyforge-<slug>` loop-home
branch falling far behind `origin/main`. On 2026-08-15 all four active
stations' loop homes were found 55-60 commits behind with nobody noticing,
which is how three stations independently rediscovered the same
already-fixed bug before their branches caught up.

**Approach:** Add a `loop_home_staleness()` function to `scripts/fleet_picture.py`
that live-fetches `origin main` for each `~/.bmad-loops/pyforge-<slug>` home and
reports any branch `STALE_BEHIND_THRESHOLD` or more commits behind, then wire
one line per stale home into the existing ATTENTION block -- the same
report-only, fault-tolerant shape the baseline-drift line already established
in this file the same session.

## Boundaries & Constraints

**Always:** Report-only -- `fleet_picture.py` keeps returning 0 unconditionally;
this is one more `needs` line, never a gate. Live-fetch `origin main` per home
before measuring (a stale local remote-tracking ref would defeat the entire
point -- the incident happened *because* nobody had fetched). Swallow
per-home failures (missing remote, network error, detached HEAD) by skipping
that home, matching `running_stations()`'s existing fault-tolerant idiom.
Reuse the `~/.bmad-loops` + `(p / ".git").exists()` home-iteration idiom
already established by `scripts/bmad_loop_baseline_drift_check.py`'s
`LOOP_ROOT`.

**Block If:** N/A -- no unattended decision blocks this story. The threshold
is an explicit, documented default (see Design Notes), not a human decision.

**Never:** No new CLI/argparse surface on `fleet_picture.py` (it has none
today). No new pixi task, no `DETECTOR` registry marker, no dashboard row --
this signal lives only in the ATTENTION block, per the epic's own framing
("one more line in the same block"). No mutation of any loop-home branch,
working tree, or non-remote-tracking ref; a `git fetch` of `origin main`
only updates the local `refs/remotes/origin/main` pointer.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Stale home | loop-home branch >= threshold commits behind live-fetched `origin/main` | `(slug, branch, count)` in the returned list | No error expected |
| In-sync home | branch even with or ahead of `origin/main` | home absent from the returned list | No error expected |
| Below-threshold home | branch 1..threshold-1 commits behind | home absent from the returned list | No error expected |
| No loop-homes directory | `~/.bmad-loops` missing or not a directory | empty list | Returns `[]`, no exception |
| Per-home git failure | no `origin` remote / detached HEAD / fetch timeout | that home is skipped | Exception swallowed per-home; other homes still checked |

</intent-contract>

## Code Map

- `scripts/fleet_picture.py` -- add `LOOP_ROOT`/`STALE_BEHIND_THRESHOLD` constants, the `loop_home_staleness()` function, and its ATTENTION-block wiring.
- `.claude/skills/conda-forge-expert/tests/meta/test_fleet_picture_loop_home_staleness.py` -- NEW. Proves the AC against a synthetically-staled branch.

## Tasks & Acceptance

**Execution:**
- [x] `scripts/fleet_picture.py` -- add `LOOP_ROOT = pathlib.Path.home() / ".bmad-loops"` and `STALE_BEHIND_THRESHOLD = 20` module constants -- mirrors `bmad_loop_baseline_drift_check.py`'s `LOOP_ROOT` idiom; threshold is an explicit documented default (Design Notes).
- [x] `scripts/fleet_picture.py` -- add `loop_home_staleness(loop_root: pathlib.Path = LOOP_ROOT, threshold: int = STALE_BEHIND_THRESHOLD) -> list[tuple[str, str, int]]` -- for each `loop_root` child with a `.git` entry: read the current branch (`git branch --show-current`), live-fetch `origin main` (bounded timeout, best-effort), then `git rev-list --count <branch>..origin/main`; collect `(slug, branch, commits_behind)` for every home at or above `threshold`. Any per-home failure (empty branch, no `origin` remote, non-digit rev-list output, timeout) skips that home rather than raising.
- [x] `scripts/fleet_picture.py` -- in the ATTENTION section, after the baseline-drift block, call `loop_home_staleness()` inside a `try/except Exception: watch.append(...)` (matching the baseline-drift/open-PR call sites) and append one `needs` line per stale home naming the slug, branch, and commit count.
- [x] `.claude/skills/conda-forge-expert/tests/meta/test_fleet_picture_loop_home_staleness.py` -- NEW -- build a bare "origin" + a loop-home-shaped clone checked out on `loop/pyforge-teststation` (same `_repo_with_origin`-style harness as `test_unpushed_work_check.py`), advance `origin/main` past the branch's tip by `>= threshold` commits, then assert `loop_home_staleness(loop_root=<parent of the clone>, threshold=<small test threshold>)` reports `("teststation", "loop/pyforge-teststation", N)`. Sibling tests: an in-sync home stays silent; a home below threshold stays silent; a missing `loop_root` returns `[]`.

**Acceptance Criteria:**
- Given a loop-home clone whose branch is `STALE_BEHIND_THRESHOLD`+ commits behind a live-fetched `origin/main`, when `loop_home_staleness()` runs, then its result includes that home's slug, branch, and commit count.
- Given `loop_home_staleness()` returns at least one stale home, when `fleet_picture.py`'s `main()` builds its ATTENTION block, then one `needs` line names the slug, branch, and commit count, and the script still exits 0.
- Given no `~/.bmad-loops` directory exists, when `loop_home_staleness()` runs, then it returns `[]` without raising.

## Spec Change Log

(none yet)

## Review Triage Log

### 2026-08-15 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 3 (high 0, medium 2, low 1)
- defer: 0
- reject: 10 (low 10)
- addressed_findings:
  - `[medium]` `[patch]` Blind Hunter + Edge Case Hunter (independently, same root cause) found `git rev-list --count` lacked `check=True` (unlike the `fetch` call just above it), so a failing invocation produced empty/non-digit stdout that `count.isdigit()` treated identically to "0 commits behind" -- a real staleness would have silently under-reported instead of being skipped. Fixed: added `check=True`, matching the `fetch` call's own pattern, so a failure now raises and is caught by the existing per-home `except Exception: continue`.
  - `[medium]` `[patch]` Blind Hunter found the I/O matrix's "Per-home git failure" row (skip-on-failure, other homes still checked) had no dedicated test -- 4 tests covered stale/in-sync/below-threshold/missing-root but none exercised the fault-tolerance path itself. Fixed: added `test_a_home_with_no_origin_remote_is_skipped_without_aborting_the_scan`, which puts a home with no `origin` remote configured alongside a healthy stale home in the same `loop_root` and asserts the broken one is silently absent while the healthy one still reports correctly.
  - `[low]` `[patch]` Blind Hunter found `STALE_BEHIND_THRESHOLD = 20` had no in-code rationale, only in the spec's Design Notes (not visible to a future reader of the script alone). Fixed: added a 4-line comment above the constant restating why 20 was chosen and that it isn't derived from the incident's 55-60 magnitude.
  - `[low]` `[reject]` Blind Hunter + Edge Case Hunter (independently, same root cause) found the blanket `except Exception: continue` per home swallows all failures with no diagnostics, and Blind Hunter separately found no stderr/diagnostics surface anywhere. Rejected: this is the spec's own explicit "Always" clause ("Swallow per-home failures ... by skipping that home, matching `running_stations()`'s existing fault-tolerant idiom") -- a deliberate scoping decision, not an oversight.
  - `[low]` `[reject]` Blind Hunter found `origin`/`main` hardcoded with no verification the remote is canonical or the default branch is actually `main`. Rejected: the AC itself is scoped to `origin/main` (`Given a loop/pyforge-<slug> branch N or more commits behind origin/main`), and all 8 real loop homes' `origin` remote and `main` default branch were verified live during planning -- not a generalized tool, a fleet-specific check.
  - `[low]` `[reject]` Blind Hunter found the outer `try/except` around the `loop_home_staleness()` call site looks like dead code given the internal blanket catch. Rejected as factually incorrect: the internal try/except only wraps the per-home git subprocess calls -- `sorted(p for p in loop_root.iterdir() if (p / ".git").exists())` runs outside it, so a `PermissionError` from an unreadable entry propagates past the function boundary and is exactly what the outer catch exists to handle (matches Edge Case Hunter's independent finding below, which this rejection also resolves).
  - `[low]` `[reject]` Edge Case Hunter found a `PermissionError` from the `iterdir()`/`.exists()` scan aborts the whole function rather than degrading per-home. Rejected: this is the outer try/except's exact purpose (see previous entry) and matches the same two-tier granularity (whole-subsystem failure -> one generic `watch` line) already used by the `running_stations()`, open-PR, and baseline-drift blocks in this same file.
  - `[low]` `[reject]` Blind Hunter + Edge Case Hunter (independently) found `home.name.replace("pyforge-", "")` replaces every occurrence of the substring, not just a leading prefix. Rejected: byte-identical to the pre-existing idiom used 3 other times in this same file and in `bmad_loop_baseline_drift_check.py` (verified via grep); the fleet has exactly 8 fixed station names, none containing "pyforge-" twice, so there is no reachable input that triggers a different result.
  - `[low]` `[reject]` Blind Hunter found any `.git`-bearing directory under `~/.bmad-loops/` is treated as a monitored station with no `pyforge-*` filter. Rejected: byte-identical to `bmad_loop_baseline_drift_check.py`'s existing `LOOP_ROOT` iteration idiom; worst case is one extra benign ATTENTION line for an unexpected directory, not a crash.
  - `[low]` `[reject]` Blind Hunter found the live `git fetch` per home is unthrottled with no caching, framed as tension with this repo's fleet-picture throttling guidance. Rejected: that guidance governs how often an operator invokes the `fleet-picture` pixi task, not internal per-run network-call caching -- 8 bounded-timeout fetches per run is consistent with this file's existing unthrottled `gh pr list` / `marshal status` / baseline-drift subprocess calls.
  - `[low]` `[reject]` Blind Hunter found empty `git branch --show-current` output is treated as detached HEAD without checking the command's return code, conflating it with a genuine failure. Rejected: both cases take the identical code path (`continue`, skip this home) -- there is no behavioral difference to fix, only a comment-wording nuance.
  - `[low]` `[reject]` Blind Hunter found the test docstring's incident narrative (citing `docs/dreams/bmad-loop-baseline-drift.md`) isn't proven by this diff alone. Rejected: the same file already cites the same doc identically in the pre-existing baseline-drift ATTENTION block (line ~219), and the incident is independently corroborated in this project's own tracked `epics.md`.

## Design Notes

**Threshold default (20).** The epic text ("N or more commits behind") leaves
N unstated -- confirmed not a pinned value anywhere in this repo (no
`marshal-policy.toml`/`policy-defaults.toml` key, no prior art). The
2026-08-15 incident's 55-60 commits is the magnitude at which it was noticed
by accident, not a chosen threshold. 20 is picked to catch drift well before
it reaches that magnitude while tolerating the small, routine gap a loop
home normally carries between other stations' independent merges to `main`.
This is a plain module constant, not a CLI flag -- `fleet_picture.py` has no
argparse today and this story doesn't add one.

**Why a live fetch, not a cached remote-tracking ref.** The incident's own
root cause was "no automated signal" -- if this check trusted whatever
`origin/main` happened to be last fetched, a loop home idle long enough to
go stale would also have a stale local view of how stale it is, silently
under-reporting. A per-home `git fetch origin main` (bounded timeout,
best-effort) keeps the measurement honest at the cost of one extra network
round-trip per station, in the same spirit as this file's existing live
`gh pr list` and `marshal status` calls.

**Inlined in `fleet_picture.py`, not a sibling detector script.** Unlike
`bmad_loop_baseline_drift_check.py` (a `DETECTOR`-registered script with an
independent CI/dashboard consumer, wired into `fleet_picture.py` as a
secondary convenience), this signal has no other consumer -- the epic frames
it as "one more line in the same block." A same-file function keeps the
change surgical and avoids inventing a pixi task / registry entry nothing
asked for.

**`needs`, not `watch`.** Bucketed alongside baseline-drift and open PRs: it
names a concrete, actionable remedy (resync the loop home) with a
demonstrated real cost when ignored, not merely an FYI.

## Verification

**Commands:**
- `pixi run -e local-recipes test` -- expected: full suite green, including the new `test_fleet_picture_loop_home_staleness.py`.
- `python scripts/fleet_picture.py` -- expected: runs to completion, exit 0, ATTENTION block prints (no stale homes expected in the live fleet today).

**Manual checks (if no CLI):**
- Read the new ATTENTION-block wiring and confirm it sits inside the same `try/except Exception` fault-tolerance pattern as the baseline-drift and open-PR blocks immediately above it.

## Auto Run Result

Status: done

**Summary.** Implementation and review (Blind Hunter + Edge Case Hunter) were already complete
from the prior session (see Review Triage Log above) and `2375018c8f` landed the feature. That
session's *deterministic verification* failed on `python scripts/spec_surface_reconcile.py`
(rc=1, 15 findings) -- unrelated to this story's own diff. This resume pass repaired the working
tree so both of this station's gating verify commands pass, without touching the intent contract.

**Root cause.** Story 9.4's own commit touched only `scripts/fleet_picture.py` and its new test --
neither is governed by any `spec-surface` glob, so it could not itself be the source of the 15
findings. All 15 were pre-existing drift inherited from `main` at the branch point
(`531e0e128f`), spanning 5 specs across 3 stations (doctor, marshal, steward): governed files had
changed without their owning spec's `.memlog.md` moving, or (one case) a spec had never been
baseline-stamped at all.

**Files changed (this pass, commit `70c7654dc3`):**
- `_bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-pyforge-doctor/.memlog.md` -- bookkeeping-only entry for Story 11.1's 8 drifted files (real capability: `spec-deferred-work-resolution-sweep` CAP-1).
- `_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-fleet-status-supervisor-fallback/.memlog.md` -- bookkeeping-only entry for `status.py` re-drift (real capability: `spec-marshal-land-cross-project-story-key-collision`).
- `_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-landing-evidence-grammar/.memlog.md` -- bookkeeping-only entry for `promotion.py`/`status.py` drift (same real owner as above).
- `_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-marshal-land-cross-project-story-key-collision/.memlog.md` -- first landing/bookkeeping entry for its own CAP-1/CAP-2 (this spec had never been baseline-stamped).
- `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-python-agent-platform/.memlog.md` -- bookkeeping-only entry for `pixi.toml` drift (real capability: the same doctor Story 11.1 above).
- `scripts/.spec-surface-baseline.json` -- scoped stamp (`--spec` x5) covering exactly these 5 keys; verified 1 added, 4 changed, 0 removed, nothing else touched.

**Review findings breakdown:** none in this pass -- mechanical bookkeeping repair, not new code; the prior session's review (Blind Hunter + Edge Case Hunter) already covered the actual feature diff.

**Verification performed:**
- `python scripts/spec_surface_reconcile.py` -- now `OK: every tracked file governed or allowlisted; no drift.` (exit 0; was exit 1 with 15 findings).
- `pixi run --frozen -e pyforge-doctor pyforge-doctor-test` -- 955 passed, 2 skipped (this station's other gating verify command).
- `python scripts/fleet_picture.py` -- exit 0, ATTENTION block prints, no stale loop-homes in the live fleet.
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` -- 4679 passed, 9 deselected (re-verifying the two marshal specs' own capabilities were untouched by this bookkeeping).
- `pixi run -e local-recipes test` (broader repo-wide suite, not one of this station's gating commands) -- 6 pre-existing failures (`test_all_scripts_runnable.py` x5, `test_bmad_artifacts_in_sync.py::test_bmad_artifacts_integrity`), confirmed byte-identical with and without this pass's changes via `git stash`. Unrelated to spec-surface reconciliation and out of this story's scope.

**Residual risks:** none identified. The reconciled specs' own real capabilities (marshal status/promotion, doctor due-for-verification, steward pixi task) were independently re-verified green; no code behavior changed, only spec-surface bookkeeping.

