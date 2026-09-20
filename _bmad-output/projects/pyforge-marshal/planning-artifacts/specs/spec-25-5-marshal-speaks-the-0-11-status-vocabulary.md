---
title: 'Marshal speaks the 0.11 status vocabulary'
type: 'feature'
created: '2026-08-22'
status: 'done'
baseline_revision: 'f0c695758cbc926ce013a4229b0192935981f5f8'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - '_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-bmad-611-era-alignment/SPEC.md'
warnings: [oversized]
deferred: []
---

<intent-contract>

## Intent

**Problem:** bmad-loop 0.11 added status surfaces marshal cannot name (CAP-5, absorbs DW-BL011-1): the `awaiting-operator` phase (`bmad_loop/model.py` L44, terminal per `TERMINAL_PHASES` L50; park records in-commit at `.bmad-loop/operator/<key>.json`), per-task `preserve_ref` (model.py L282, projected verbatim into `status --json` per `documents.py::status_document`), and run-level `sweeps_refused` (model.py L600, dict trigger → `{not-started, failed, dirty}` slug, always present in status JSON). Today marshal's `_TERMINAL_TASK_PHASES` (core/status.py L673) omits `awaiting-operator`, so a parked run reads `running` with the parked story as "current"; `scripts/loop_stall_check.py` reads it as a 15-minute stall (DW-BL011-1); `preserve_ref`/`sweeps_refused` are invisible everywhere marshal reports.

**Approach:** mirror the installed 0.11 vocabulary — never invent field names — through the snapshot seam: extend `TaskPhaseSnapshot`/`DeferredStory`/`RunStatusSnapshot` (ports/harness.py) with `preserve_ref`/`operator`-era fields, populate them in `adapters/harness_bmadloop.py::run_status_snapshot`, teach `core/status.py` a sixth fleet state `awaiting-operator` (+ terminal-set fix + parked-story fallback for current-story), surface all three vocabularies in `cli/status.py` (fleet row + run detail, text = pure projection of JSON), name the parked state in `scripts/fleet_picture.py` and `scripts/loop_stall_check.py` as `awaiting-operator (run bmad-loop confirm)`, and add the dated 6.11 finalize note to the false-green detector's premise text (text-only).

## Boundaries & Constraints

**Always:**
- Field names mirror the installed bmad_loop 0.11.0 verbatim: phase token `"awaiting-operator"` (`Phase.AWAITING_OPERATOR`), task key `"preserve_ref"` (nullable str, reported verbatim — never re-validated against git), run key `"sweeps_refused"` (dict trigger → reason slug; reasons exactly `model.SWEEP_REFUSED_NOT_STARTED/FAILED/DIRTY` = `"not-started"/"failed"/"dirty"`). Pin with a vocabulary test against the installed package (the 25.4 enum-mirror precedent) incl. `bmad_loop.cli.STATUS_SCHEMA_VERSION == 1`.
- A parked run is NAMED `awaiting-operator (run bmad-loop confirm)` wherever run state is shown (marshal status text, fleet-picture state column/ATTENTION, stall-check) — never "stalled", "dead", "unsupervised", or "running". Machine field keeps the bare token `"awaiting-operator"`; the remedy suffix is the human projection.
- "Parked run" = ≥1 task at `awaiting-operator` AND no task in a non-terminal phase. A run actively driving another story stays `running`; a run paused on escalation stays `paused-on-escalation` (escalation outranks the park — it is run-halting; a park never blocks siblings by design).
- `_TERMINAL_TASK_PHASES` grows to mirror `bmad_loop.model.TERMINAL_PHASES` exactly ({done, deferred, escalated, awaiting-operator}); `_current_story_key` falls back to the FIRST parked story only when nothing is active (the story the operator owes), never hiding an active story.
- A present `preserve_ref` is shown as the recovery pointer wherever an escalated/deferred story is surfaced: fleet row gains `escalation_preserve_ref` (populated only for the escalated state, mirroring `escalation_reason`'s gating), run-detail `stories[*]`/`deferred[*]` gain `preserve_ref`; text renders append it when present (fleet's standing non-destructive policy, now upstream-native).
- `sweeps_refused` surfaces in `marshal status --run` detail (JSON key + text line `trigger (reason)`), `None` when run state is unreadable — never fabricated as `{}`-clean.
- All row/JSON changes are additive; text renders stay pure projections of the same envelope (NFR-12). No redaction for `preserve_ref` (a git ref, like `commit_sha`); `sweeps_refused` values are the closed slug vocabulary, not free text.
- Fixtures for adapter/stall-check tests are written by the INSTALLED writer (`bmad_loop.model.RunState(...).to_dict()` / `bmad_loop.journal.save_state`), or the existing `_write_state` dict helper extended with the exact 0.11 keys.
- Premise-text note (text-only, no behavior change), dated 2026-08-22: 6.11 build-auto finalize writes `done` only at true finalize (post-review), shrinking the dev-marks-done window — added to `pyforge.doctor.sources.marshal::gather_story_status`'s docstring area and the `story-status-check` task description in `pixi.toml`; detector behavior/containment unchanged.
- DW-BL011-1 flipped to resolved in `_bmad-output/projects/pyforge-marshal/planning-artifacts/deferred-work-ledger.md` with a dated note, same commit.
- Commit with an explicit pathspec (parent session holds unrelated staged planning changes that must not ride this commit).

**Block If:** the installed bmad_loop's field spellings differ from the ones cited above (re-read `.pixi/envs/local-recipes/lib/python3.14/site-packages/bmad_loop/model.py` / `documents.py`); or `STATUS_SCHEMA_VERSION != 1`.

**Never:** no new run-level state beyond `awaiting-operator`; no confirm-execution from marshal (naming + pointer only — `bmad-loop confirm` stays the harness's); no re-derivation of park records from `.bmad-loop/operator/` (the run snapshot is this story's source; record-drift triage stays `bmad-loop validate`'s); no changes to `supervisor/durability.py` push triggers (the `dev-commit-landed` trigger already fires on a park's commit); no retire/land behavior changes; no `--write-baseline` unscoped; no stories.yaml/folder+id adoption.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Parked-only run | tasks: 1 done + 1 awaiting-operator, not finished, supervisor alive | `derive_home_state` → `"awaiting-operator"`; `current_story` = parked key; text/fleet-picture show `awaiting-operator (run bmad-loop confirm)` | No error |
| Parked + active | tasks: 1 awaiting-operator + 1 dev-running | `"running"`, current = the active story (parked never shown as current) | No error |
| Parked + finished | finished=True, 1 awaiting-operator task | `"awaiting-operator"` (outranks `stopped` — the confirm is the next action, not a re-spin) | No error |
| Parked + dead supervisor | supervisor_alive=False, engine not alive, parked-only | `"awaiting-operator"` (never `"unsupervised"`/dead) | No error |
| Parked + escalation pause | paused_stage="escalation", parked-only, not finished | `"paused-on-escalation"` (escalation outranks) | No error |
| Stall-check parked | live quiet run, all tasks terminal, ≥1 awaiting-operator | reported distinctly as `awaiting-operator (run bmad-loop confirm)` with parked keys; NOT counted stalled; exit 0 | No error |
| Stall-check parked + active | live quiet run, awaiting-operator + dev-running tasks | still a stall (something claims to run); parked keys named in the report | exit 1 |
| preserve_ref present | escalated/deferred task carries `preserve_ref` | fleet row `escalation_preserve_ref` / detail rows' `preserve_ref` carry it verbatim; text appends it | No error |
| preserve_ref absent | task `preserve_ref: null` / pre-0.10 state.json | fields report `None`; text omits the suffix | No error |
| sweeps_refused | state `sweeps_refused: {"epic-1": "dirty"}` | detail JSON carries the dict; text line `sweeps_refused: epic-1 (dirty)` + untouched-deferred-work hint | No error |
| sweeps_refused empty/unreadable | `{}` / state unreadable | `{}` shown as none-refused; unreadable → `None`, never fabricated | No error |
| Old state.json | fixture without the 0.11 keys | `from_dict` defaults apply: no parked tasks, `preserve_ref None`, `sweeps_refused {}` — behavior identical to today | No error |

</intent-contract>

## Code Map

- `.pixi/envs/local-recipes/lib/python3.14/site-packages/bmad_loop/` — ground truth (0.11.0): `model.py` L44 `Phase.AWAITING_OPERATOR = "awaiting-operator"`, L50 `TERMINAL_PHASES` (4 members), L75-77 `SWEEP_REFUSED_*` slugs, L264 `operator_actions`, L282 `preserve_ref`, L600 `RunState.sweeps_refused`, to_dict keys L410-413/L669; `documents.py` L218 `STATUS_SCHEMA_VERSION = 1`, `status_document` per-task `"preserve_ref"` + top-level `"sweeps_refused"` (always present, `{}` when clean); `cli.py` L3048-3051 (`auto-sweep not run: {trigger} ({why})` + sweep hint), L3067-3069 (preserve_ref bracket suffix; 17-char phase column sized by `awaiting-operator`); `operatoractions.py` (`.bmad-loop/operator/<key>.json`, fields story_key/actions/spec_file/run_id/parked_at); `journal.py` L168 `save_state` (fixture writer); `sprintstatus.py` L41 board token.
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/ports/harness.py` — `TaskPhaseSnapshot` (L297): + `preserve_ref: str | None = None` (trailing default, the `branch` precedent); `DeferredStory` (L256): + `preserve_ref: str | None = None`; `RunStatusSnapshot` (L328, kw_only): + `escalated_preserve_ref: str | None = None`, `sweeps_refused: Mapping[str, str] = field(default_factory=dict)`.
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/adapters/harness_bmadloop.py` — `run_status_snapshot` (L1526): populate the new fields (`task.preserve_ref` verbatim; escalated task's `preserve_ref`; `dict(state.sweeps_refused)`), inside the existing widened guard.
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/status.py` — `_AWAITING_OPERATOR_PHASE` beside `_ESCALATED_PHASE` (L672); `_TERMINAL_TASK_PHASES` L673 (+1); `FLEET_STATES` L678 (+`"awaiting-operator"`, comment 5→6); `AWAITING_OPERATOR_REMEDY = "run bmad-loop confirm"` (single spelling for renders); `derive_home_state` L687 (parked arm per matrix; existing ladder otherwise byte-equivalent); `_current_story_key` L756 (parked fallback); `FleetHomeFacts` L768 (+`escalated_preserve_ref`); `build_fleet_row` L935 (rows gain `parked_stories` tuple + `escalation_preserve_ref`, degraded rows carry `()`/`None`); `RunDetailFacts` L1116 (+`sweeps_refused: Mapping[str,str] | None = None` — `None` = unreadable); `build_run_detail` L1172 (stories/deferred rows + `preserve_ref`; row + `"sweeps_refused"`; found=False row parity).
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/status.py` — `_gather_home_facts` L715 (thread `escalated_preserve_ref` from snapshot); `_run_detail` L1674 (thread `sweeps_refused` from snapshot, `None` when no snapshot); `_render_text_status` L1862 (state text projection with remedy suffix + `parked=` list + escalated `preserve_ref=` suffix); `_render_text_run_detail` L1935 (stories/deferred `preserve_ref=` when set; `sweeps_refused:` line).
- `scripts/fleet_picture.py` — `main()` state column branch for hstate `awaiting-operator` (+ board-count `counts["awaiting-operator"]` ATTENTION line: parked stories in the tracked ledger, run long gone); pure helper for the state naming so the CFE meta test can pin it.
- `scripts/loop_stall_check.py` — parse tasks in `live_state`/main; parked-only quiet runs report `awaiting-operator (run bmad-loop confirm)` + keys, exit 0; parked+active quiet stays stalled with keys named; module docstring notes the 0.11 park semantics.
- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/marshal.py` — `gather_story_status` docstring (L363-379): dated premise note (text-only). `pixi.toml` L654-656 `story-status-check` description: same note appended (env-export unaffected — verify by regenerating and diffing `environment.yaml`).
- `_bmad-output/projects/pyforge-marshal/planning-artifacts/deferred-work-ledger.md` L1064 — DW-BL011-1 → resolved, dated.
- Tests: `tests/unit/test_status.py` (derive/current-story/fleet-row/run-detail/render additions; existing row-shape asserts updated), `tests/unit/test_harness_bmadloop_run_status_snapshot.py` (`_task`/`_write_state` gain the 0.11 keys; new preserve_ref/sweeps_refused/awaiting-operator cases), new `tests/unit/test_bmad_loop_status_vocabulary.py` (installed-package vocabulary pin, 25.4 precedent), `.claude/skills/conda-forge-expert/tests/meta/test_loop_stall_check_awaiting_operator.py` + `test_fleet_picture_awaiting_operator.py` (importlib-loaded script tests, `test_fleet_picture_loop_home_staleness.py` convention; state.json fixtures via installed `save_state`).

## Tasks & Acceptance

**Execution:**
- `ports/harness.py` -- add the three snapshot extensions -- the seam every status consumer reads.
- `adapters/harness_bmadloop.py` -- populate them from the installed package's own state -- vocabulary mirrored at the one AD-3 import seam.
- `core/status.py` -- terminal-set fix, sixth state, parked fallback, row/detail additions -- the pure derivation layer.
- `cli/status.py` -- gather threading + text projections -- operators see all three vocabularies.
- `scripts/fleet_picture.py`, `scripts/loop_stall_check.py` -- parked-run naming (state column, ATTENTION, distinct stall-check report) -- DW-BL011-1's fix shape.
- `pyforge-doctor sources/marshal.py` + `pixi.toml` -- dated premise notes -- text-only.
- `deferred-work-ledger.md` -- DW-BL011-1 resolved, dated note.
- Tests per Code Map -- fixture-driven, installed-writer fixtures, vocabulary pin.

**Acceptance Criteria:**
- Given a state.json written by the installed 0.11 writer with a parked story, when `marshal status` (fleet + detail), fleet-picture, and stall-check each report it, then every surface names `awaiting-operator (run bmad-loop confirm)` and none says stalled/dead/unsupervised/running.
- Given tasks carrying `preserve_ref`, when an escalated/deferred story is surfaced in status output, then the ref is shown verbatim as the recovery pointer (JSON + text).
- Given `sweeps_refused` non-empty, when `marshal status --run` detail renders, then each trigger and reason slug is shown; given unreadable state, the field reports null.
- Given the marshal suite (`pixi run -e pyforge-marshal python -m pytest src/shared/packages/pyforge-marshal/tests -q`, 5187 pre-story), when run post-change, then green with the new tests added.
- Given the vocabulary test, when the installed bmad_loop's phase/slug/key spellings or STATUS_SCHEMA_VERSION move, then it reds (the drift guard).

## Spec Change Log

- 2026-08-22 (dev, hand-driven dispatch): implemented as specced, no contract deviations. Block If re-verified against the installed 0.11.0 before coding (model.py L44/L50/L75-77/L282/L600, documents.py L218/L307/L337, `bmad_loop.cli.STATUS_SCHEMA_VERSION == 1` re-export). Landed as commit `ef5b32fb91` on `marshal/25-5-status-vocabulary` (branched from this spec's own `baseline_revision`), explicit 19-path pathspec — the parent session's staged planning changes did not ride. Verification: marshal suite 5223 passed (5187 pre-story); the two new CFE meta tests + `test_no_retired_bmad_skill_ids` + `test_bmad_artifacts_in_sync` pass; `pixi project export conda-environment -e build | diff - environment.yaml` empty; `spec_surface_reconcile.py` exit 0 both in the working tree and against the bare commit (memlogs appended to spec-pyforge-marshal + the three harness_bmadloop co-governors; scoped `--write-baseline --spec` stamps for those four only). DW-BL011-1 flipped to resolved in the tracked ledger, same commit. One landing note: the pathspec commit necessarily rewrote the INDEX copy of `scripts/.spec-surface-baseline.json`; the parent's 15 staged spec-baseline additions were restored to the working file afterward but now sit UNSTAGED — re-add before committing the planning batch.

## Review Triage Log

## Design Notes

State precedence: escalation-pause > parked > finished/unsupervised — a park "must never block the stories behind it" (model.py L42) so an active run stays `running`; but once nothing is active, the confirm is the truthful next action even for a finished or supervisor-dead run (the DW's "never mislabeled dead"). Post-confirm staleness is accepted and bounded: `bmad-loop confirm` flips spec+board but not the historical state.json, so a confirmed park still reads `awaiting-operator` until the next run replaces the latest-run picture — the pointer it prints (`bmad-loop confirm`) is exactly the command that reports "not awaiting" in that case. `operator_actions` deliberately NOT threaded into snapshots this pass: CAP-5 requires naming + pointers; the actions list lives one command away (`bmad-loop confirm --list`) and threading session-authored free text would drag AD-34 redaction into every consumer for no named requirement.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass (station policy verify command; reconciled 2026-08-30 after policy drifted from this spec's original declaration).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: pass (station policy verify command; reconciled 2026-08-30 after policy drifted from this spec's original declaration).

## Auto Run Result

**Status:** done — reconstructed 2026-09-20 from git during the fleet consistency pass before the foundry cutover; no run record survived in this tracked spec.
**Summary:** landed on `main` as `88125c8c03` (2026-08-22, "Merge pull request #612 from rxm7706/marshal/25-5-status-vocabulary"). Ledger row `25-5-marshal-speaks-the-0-11-status-vocabulary: done`.
**Verification:** the station's `verify_commands` ran in the landing session; the durable record here is git only — see the landing commit(s) above.
**Files changed:** `.claude/skills/conda-forge-expert/tests/meta/test_fleet_picture_awaiting_operator.py`, `.claude/skills/conda-forge-expert/tests/meta/test_loop_stall_check_awaiting_operator.py`, `_bmad-output/projects/pyforge-marshal/planning-artifacts/deferred-work-ledger.md`, `_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-adaptive-model-tiering/.memlog.md`, `_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-bmad-loop-intent-gap-work-preservation/.memlog.md`, `_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-horizontal-run-concurrency/.memlog.md`, `_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/.memlog.md`, `pixi.toml`, `scripts/.spec-surface-baseline.json`, `scripts/fleet_picture.py`, `scripts/loop_stall_check.py`, `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/marshal.py` (+7 more)
**Residual risks:** none recorded — no run record survived to carry them.
**Follow-up review recommendation:** false

## Status reconcile 2026-09-20

- frontmatter `status` `in-review` → `done` (ledger row `25-5-marshal-speaks-the-0-11-status-vocabulary: done`).
- `## Auto Run Result` reconstructed from git (none survived).
