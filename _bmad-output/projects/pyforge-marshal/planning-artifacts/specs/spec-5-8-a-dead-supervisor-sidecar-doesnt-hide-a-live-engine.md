---
title: 'A dead supervisor sidecar does not hide a live engine'
type: 'bugfix'
created: '2026-08-12'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: true
context: ['{project-root}/_bmad-output/projects/pyforge-marshal/planning-artifacts/architecture/architecture-pyforge-marshal-2026-07-25/ARCHITECTURE-SPINE.md']
warnings: []
baseline_revision: 'f6b3e8f2b32efdedb498c47fa2352f5e17bb4594'
final_revision: '96d8407ad23d03ef406fc48d0b40b6a089fd20e3'
---

<intent-contract>

## Intent

**Problem:** `core/status.py::derive_home_state`'s first branch (`if not finished and
supervisor_alive is False: return "unsupervised"`) fires before checking whether the harness
engine itself has any in-flight task, so a run whose supervisor sidecar died (crash,
`--foreground`, a bare `bmad-loop resume` that never spawns a fresh one) but whose engine is
still working reads identically to one that actually needs a re-spin (2026-08-11 incident: 5
live stations misreported for a full session).

**Approach:** thread the engine's own already-recovered pid (`cli/status.py`'s
`_RunJournalFacts.launch_pid`, journaled by every `run-launch`/`run-resume` outcome entry and
already read today, currently discarded after computing `elapsed_seconds`) through as a new
`engine_alive` signal, probed with the same `ProcessPort.is_alive` call already used for the
supervisor. `derive_home_state` only returns `"unsupervised"` when the engine is NOT confirmed
alive; a confirmed-alive engine falls through to the normal state derivation instead.

## Boundaries & Constraints

**Always:**
- `FLEET_STATES`'s 5-value vocabulary is unchanged.
- `engine_alive` is derived from `launch_pid`, the SAME journaled pid `cli/status.py` already
  recovers per run -- no new file read, no new subprocess, no hand-maintained flag (AD-5).
- `derive_home_state` gains `engine_alive: bool | None = None`, keyword-only with a default
  that reproduces today's exact behavior -- every existing call site that does not pass it
  keeps its current result unchanged.
- Only `engine_alive is True` (a confirmed-alive probe) may soften the first branch;
  `False` or `None` (dead, or unprobed/unknown) must still return `"unsupervised"` -- narrows
  a false positive, never softens a real one.
- A dead-or-unprobed engine behind a dead supervisor still returns `"unsupervised"` exactly as
  today, including when the run has genuinely stalled.

**Block If:** none identified -- the fallback signal, its source, and the one-directional
softening rule are all fully determined by AD-5 and the already-shipped journal fields (see
Design Notes); nothing here requires human adjudication.

**Never:**
- Do not touch `is_run_live`/`cli/land.py`'s branch-retirement predicate. Its own docstring
  already documents why it deliberately never calls `derive_home_state`; extending it to
  consult engine liveness is a separate, unscoped change this story does not make.
- Do not add a 6th `FLEET_STATES` value, a new `Finding`, or a new row field to announce
  "supervisor dead, engine alive" -- the two failure shapes are already distinguishable via
  `state` alone (one of the 4 healthy values vs. `"unsupervised"`); no new surfacing mechanism.
- Do not use `HarnessPort.run_status_snapshot`'s `finished`/`tasks` fields as the fallback
  signal -- `derive_home_state`'s own existing docstring names those as exactly the STALE
  signal a crashed supervisor leaves behind; they cannot corroborate engine liveness.
- Do not reuse Story 3.5's `evaluate_idle`/tmux-pane-content machinery here -- it answers "is
  the engine producing NEW output," a stronger and costlier question than "is its pid alive,"
  and pulls in a second port (`SessionObserverPort`) this fix does not need.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Dead supervisor, engine alive, task in flight | `supervisor_alive=False`, `engine_alive=True`, task phase `dev-running` | `state == "running"` | No finding |
| Dead supervisor, engine alive, no in-flight task | `supervisor_alive=False`, `engine_alive=True`, `tasks=()` | `state == "idle"` | No finding |
| Dead supervisor, engine alive, paused on escalation | `supervisor_alive=False`, `engine_alive=True`, `paused_stage="escalation"` | `state == "paused-on-escalation"` | No finding |
| Dead supervisor, engine also dead | `supervisor_alive=False`, `engine_alive=False` | `state == "unsupervised"` | No finding (unchanged) |
| Dead supervisor, engine liveness unprobed | `supervisor_alive=False`, `engine_alive=None` | `state == "unsupervised"` | No finding (unchanged, safe default) |
| Supervisor never attached (2026-08-11 reproduction), engine alive | `supervisor_pid=None -> supervisor_alive=False`, `engine_alive=True` | State derives normally, never `"unsupervised"` | No finding |
| Finished run, supervisor already exited | `finished=True` | `state == "stopped"`; `engine_alive` never consulted | No finding (unchanged) |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/status.py` -- EDIT.
  `derive_home_state` gains keyword-only `engine_alive: bool | None = None`; first branch
  consults it; docstring updated (no longer "the ONLY unsupervised trigger" unconditionally).
  `FleetHomeFacts` gains `engine_alive: bool | None = None`. `build_fleet_row` threads
  `facts.engine_alive` into its `derive_home_state(...)` call.
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/status.py` -- EDIT.
  `_gather_home_facts` computes `engine_alive = process.is_alive(journal_facts.launch_pid)`
  (`launch_pid` is guaranteed non-`None` at that point -- the earlier `journal_unreadable`
  return already excludes the `None` case) and threads it into the `FleetHomeFacts(...)` call.
- `src/shared/packages/pyforge-marshal/tests/unit/test_status.py` -- EDIT. Update
  `test_home_with_dead_supervisor_is_unsupervised` (currently asserts `"unsupervised"` for a
  scenario -- launch pid alive, supervisor pid dead -- that is exactly this story's target
  behavior change) and add new coverage per the I/O matrix.

## Tasks & Acceptance

**Execution:**
- [x] `core/status.py` -- add `engine_alive` param to `derive_home_state`, gate the first
  branch on it, update the docstring -- implements the fallback check itself.
- [x] `core/status.py` -- add `engine_alive` field to `FleetHomeFacts`; thread it through
  `build_fleet_row`'s `derive_home_state(...)` call -- carries the new signal from the impure
  shell into the pure core (AD-4).
- [x] `cli/status.py` -- compute `engine_alive` from the already-recovered
  `journal_facts.launch_pid` in `_gather_home_facts`; thread into `FleetHomeFacts(...)` -- no
  new I/O, reuses an existing journaled fact (AD-5).
- [x] `tests/unit/test_status.py` -- fix `test_home_with_dead_supervisor_is_unsupervised`'s now
  wrong scenario (make both pids dead, or add a distinctly-named counterpart) and add unit
  coverage for the I/O matrix rows above, both at the pure `derive_home_state` level and one
  end-to-end `run_status` reproduction of the 2026-08-11 scenario.

**Acceptance Criteria:**
- Given a run resumed via bare `bmad-loop resume` (no supervisor pid ever journaled) whose
  engine process is still alive, when `marshal status` runs, then the row's state derives from
  the run's actual task/pause state and is never `"unsupervised"`.
- Given the identical scenario except the engine process has also exited, when `marshal
  status` runs, then the row still reports `"unsupervised"`.
- Given a dead-supervisor-alive-engine row, when rendered under both `--format text` and
  `--format json`, then both projections carry the same derived state (AD-14 parity, matching
  every other field's existing convention).

## Design Notes

- **Why `launch_pid`, not tmux/idle detection:** `launch_pid` is already recovered per run at
  zero extra I/O cost -- the cheapest signal that directly answers "is the engine's own
  process alive," which is what CAP-1 asks. Story 3.5's idle-strand machinery answers a
  stronger, costlier question ("is it producing new output right now") this fix does not need.
- **Why the softening is one-directional:** mirrors this module's own repeated "unproven is
  reported as the cautious state, never silently softened" discipline -- the same precedent
  `supervisor_alive is None` (never triggers unsupervised on its own, but never counts as
  "alive" either) and `is_run_live`'s `journal_unreadable` handling (treated as live, the safe
  direction for its own purpose) already establish elsewhere in this file.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` -- expected: full suite green,
  including the updated and new `test_status.py` coverage.
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` -- expected: clean, no dependency drift.
- `pixi run --frozen -e pyforge-marshal lint-imports --config src/shared/packages/pyforge-marshal/pyproject.toml --no-cache` -- expected: clean, no import-boundary violation (AD-4 pure-core/impure-shell split preserved).

## Spec Change Log

## Review Triage Log

### 2026-08-12 — Review pass 1 (Blind Hunter + Edge Case Hunter, parallel)

- intent_gap: 0
- bad_spec: 0
- patch: 2 (high 1, medium 0, low 1)
- defer: 2 (high 1, medium 1, low 0)
- reject: 2 (high 0, medium 0, low 2)
- addressed_findings:
  - `[high]` `[patch]` **`_gather_run_journal_facts`'s `launch_pid` resolution preferred the FIRST `_LAUNCH_KIND` OUTCOME entry and never even looked at `_RESUME_KIND` once one was found, so `launch_pid` stayed pinned to a run's ORIGINAL launch pid forever, across any later `bmad-loop resume` -- silently defeating this story's own fix for exactly the scenario that motivates it (a resumed run whose original launch pid has exited).** Found by the Blind Hunter, independently corroborated by direct source inspection. Fixed: the loop now selects the MOST RECENT OUTCOME entry by timestamp across both kinds, mirroring `supervisor_pid`'s own already-correct identical pattern a few lines below. New test: `test_engine_alive_reflects_the_resumed_pid_not_the_original_launch_pid` (a `run-launch` entry with a dead pid, followed by a `run-resume` entry with a different, alive pid -- proves the resumed pid is the one consulted).
  - `[low]` `[patch]` **The comment justifying the new `engine_alive` probe undersold its cost as "no new I/O, no new subprocess" without noting it is a new `is_alive` syscall per home per sweep.** Found by the Blind Hunter, matching this file's own convention of precisely quantifying cost claims elsewhere (e.g. `_UNPUSHED_WORK_TIMEOUT_S`). Fixed: comment reworded to name the extra liveness check explicitly.
- deferred (not fixed in this pass, appended to `deferred-work.md` as NEW entries):
  - `[high]` `DW-FU-5-8`: `is_run_live` (the landing-safety predicate `cli/land.py` uses to refuse retiring a branch out from under a live run) still reads only `facts.supervisor_alive`, never the new `facts.engine_alive` -- in this story's own motivating scenario, `marshal land` could treat a dead-sidecar-alive-engine branch as safe to retire. Out of this story's own Boundaries-scoped surface (`derive_home_state`/`FleetHomeFacts` only); needs a dedicated follow-up story.
  - `[medium]` `DW-FU-5-8-2`: `ProcessPort.is_alive`'s bare pid-existence probe has no identity/start-time corroboration and admits a degenerate `pid: 0` journal entry as "alive" -- a pre-existing characteristic of the primitive (already true for `supervisor_alive` since Story 3.4/5.1), now given a second, verdict-flipping consumer. Cross-cutting hardening of `ProcessPort.is_alive` itself is out of this story's surface.
- rejected:
  - **No new row field or `Finding` announces "supervisor dead, engine alive" -- the row reads identically to a fully-supervised healthy row.** Judged: the literal contract (SPEC.md CAP-2 and the epics.md AC) requires only that the two FAILURE shapes -- engine-alive vs. engine-dead -- be distinguishable from each other via the report, which `state` already satisfies (`unsupervised` vs. one of the 4 healthy values). Further surfacing (a WARN, a new field) is an explicit Non-goal in both the SPEC ("left to the downstream story's design") and this story's own Boundaries; not a gap against this story's actual contract.
  - **`derive_home_state`'s `engine_alive: bool | None = None` default is unexercised speculative generality.** Judged: required, not speculative -- 9+ pre-existing pure-level tests call `derive_home_state` without `engine_alive` and must keep passing unchanged (this story's own explicit Boundaries: "every existing call site that does not pass it keeps its current result unchanged"); removing the default would force touching unrelated, already-passing tests.

### 2026-08-12 — Repair pass (deterministic verification failure; Blind Hunter + Edge Case Hunter, parallel)

Pass 1's finalize committed `d9f7691c97` and the harness's own deterministic `## Verification` gate (external to this workflow's review) then ran the spec's three commands and found `pixi run --frozen -e pyforge-ci pyforge-deps-test` red -- `pyforge-steward`'s `dashboard/apps.py`/`cache.py` (Story 9.1, unrelated, already-merged) import `django` unconditionally while it is declared only as an optional extra. Confirmed reproducible identically on the repo's real `main`, i.e. pre-existing and unrelated to this story's own diff (`core/status.py`/`cli/status.py`/`test_status.py` only). Repaired using this repo's own established precedent (commit `20ad57a62f`, an identical repair for marshal Story 4.11) by adding a `BASELINE_UNDECLARED_IMPORTS["pyforge-steward"]["django"]` ratchet entry to `tests/packaging/test_dependency_completeness.py`, mirroring that dict's existing `_http` entry for the same package. No `<intent-contract>` content touched; `baseline_revision`/the story's own 3-file diff untouched.

- intent_gap: 0
- bad_spec: 0
- patch: 2 (high 0, medium 0, low 2)
- defer: 1 (high 0, medium 1, low 0)
- reject: 2 (high 0, medium 0, low 2)
- addressed_findings:
  - `[low]` `[patch]` **The new baseline entry's rationale overstated what actually gates `cache.py`'s reachability as "Django's own app-loading/cache-backend wiring" -- `cache.py` is an ordinary module with no such framework-level gate.** Found independently by the Blind Hunter. Fixed: reworded to cite the real guard, `tests/meta/test_invariants.py::test_no_module_outside_dashboard_imports_dashboard_django_or_channels`.
  - `[low]` `[patch]` **The `BASELINE_UNDECLARED_IMPORTS` dict's header comment frames every entry as predating the gate's 2026-07-29 landing date, which this new entry (from Story 9.1, merged 2026-08-11) contradicts -- already inaccurate since precedent commit `20ad57a62f`'s Aug-9 entries, not newly introduced by this pass.** Found by the Edge Case Hunter. Fixed: reworded to describe the ratchet as accruing later entries from other stories over time, citing `20ad57a62f`.
- deferred (not fixed in this pass, appended to `deferred-work.md` as a NEW entry):
  - `[medium]` `DW-FU-5-8-3`: `BASELINE_UNDECLARED_IMPORTS` is a single shared repo-wide dict with no cross-worktree land convention (unlike `pixi.toml`, which `CLAUDE.md` already instructs to fix on `main` directly) -- every other concurrent bmad-loop worktree hitting the same pre-existing `pyforge-steward: django` failure is likely to mint a colliding entry independently. Repo-tooling/process decision outside this story's surface.
- rejected:
  - **The baseline entry names no story/ledger owner for the actual fix (teaching the scanner to recognize framework-plugin modules) and doesn't anticipate the sibling `channels` import named in the same package's own docstring.** Judged: matches the existing `_http` sibling entry's identical shape exactly (also owner-less, also names only its own module) -- established convention, not a gap this pass introduced.
  - **The diff itself carries no embedded proof that the gate was rerun.** Judged: normal diff shape; verification was performed directly (`pyforge-deps-test`: 67 passed; `pyforge-marshal-test`: 3499 passed; `lint-imports`: 3 kept, 0 broken) and is recorded in this entry and the Auto Run Result below, not expected inside the diff.


## Auto Run Result

Status: done

**Summary.** Implementation (pass 1) was already complete on entry to this session: `derive_home_state` gained the keyword-only `engine_alive` signal, `FleetHomeFacts`/`build_fleet_row` thread it through, and `cli/status.py::_gather_home_facts` derives it from the journal's most-recently-resumed `launch_pid`. This session was a targeted repair: the bmad-loop harness's own deterministic `## Verification` gate found `pixi run --frozen -e pyforge-ci pyforge-deps-test` red after pass 1's commit. Root cause was confirmed pre-existing and unrelated to this story (reproduces identically on the repo's real `main`): `pyforge-steward`'s `dashboard/apps.py`/`cache.py` (Story 9.1) import `django` unconditionally while it's declared only as an optional extra. Repaired using this repo's own established precedent (commit `20ad57a62f`) rather than touching pyforge-steward's design or this story's `<intent-contract>`.

**Files changed this pass:**
- `tests/packaging/test_dependency_completeness.py` -- added a `BASELINE_UNDECLARED_IMPORTS["pyforge-steward"]["django"]` ratchet entry (mirrors the existing `_http` entry for the same package), plus a header-comment wording fix.

**Review findings breakdown (this pass):** patch 2 (low 2, both applied -- an imprecise "cache-backend wiring" claim corrected to cite the real guard test, and a stale ratchet-header date claim reworded), defer 1 (medium, `DW-FU-5-8-3` -- the shared baseline dict has no cross-worktree land convention, unlike `pixi.toml`), reject 2 (both matched established precedent / not actionable).

**Verification performed:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` -- 3499 passed, 9 deselected.
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` -- 67 passed (previously 1 failed / 66 passed).
- `pixi run --frozen -e pyforge-marshal lint-imports --config src/shared/packages/pyforge-marshal/pyproject.toml --no-cache` -- 3 contracts kept, 0 broken.

**Residual risks:** `DW-FU-5-8-3` (this pass) and the two carried-over deferrals from pass 1 (`DW-FU-5-8`: `is_run_live` still ignores `engine_alive`; `DW-FU-5-8-2`: `ProcessPort.is_alive` has no pid-reuse/identity guard) remain open, all explicitly out of this story's scoped surface. `followup_review_recommended` stays `true`, carried from pass 1's substantive code fix (the `launch_pid` resolution bug), not reset by this cosmetic repair pass.
