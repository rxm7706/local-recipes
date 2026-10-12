---
title: "43.1: bmad-drift knows every file marshal dispatch writes into Tier-3"
type: 'fix'
created: '2026-10-12'
status: 'in-progress'
baseline_revision: '70975ae790'
review_loop_iteration: 4
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-pyforge-doctor/SPEC.md
  - _bmad-output/projects/pyforge-doctor/planning-artifacts/epics.md
  - docs/dreams/bmad-drift-new-artifact-shape.md
  - src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/factory.py
  - src/shared/packages/pyforge-doctor/tests/unit/test_sources_factory.py
  - src/shared/packages/pyforge-doctor/tests/meta/test_source_independence.py
  - scripts/bmad_drift_check.py
  - _bmad-output/projects/pyforge-marshal/SYNC-RUNBOOK.md
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/recall_feedback.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/adapters/harness_bmadloop.py
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** bmad-drift fails files that marshal dispatch writes into its own gitignored Tier-3 store.

- **Where the verdict lives.** `pixi run -e pyforge-guild bmad-drift-check` runs `python -m pyforge.doctor.sources
  bmad-drift`. Its `check_coverage` (`sources/factory.py`, Story 6.8) walks `_bmad-output/projects/pyforge-marshal/`,
  and any file `classify()` cannot name is an `uncovered` HARD finding. The tree includes the gitignored
  `implementation-artifacts/`. `detectors-ci` runs this source.
- **The defect.** Marshal Story 47.1 (with 47.2 and 93.1) writes a recall-feedback pair into a dispatch worktree's
  Tier-3 store: `recall-feedback__<story>__<run_id>.md`
  (`core/recall_feedback.py::recall_feedback_output_relpath`) and the marker `recall-feedback__<story>__<run_id>.md.query-ran`
  (`adapters/harness_bmadloop.py::_recall_query_marker_path`). `classify()` has no rule for either. In that worktree
  `detectors-ci` exits 1, while CI's fresh clone, which has no Tier-3 files, is green.
- **Found on 2026-10-12, on marshal Story 97.2.** Its dispatch worktree's `pyforge-marshal/implementation-artifacts/`
  holds exactly `recall-feedback__97.2__pyforge-marshal-20261012T103206150Z-210a0f06.md` and its `.md.query-ran`.
  Marshal 94.1's worktree holds the same pair.
- **Reproduced at `70975ae790`.** `test_sources_factory.py`'s own `_bootstrap` fixture gives one OK row. Planting the
  files below gives one `uncovered` FAIL each. A control file under `dispatch-runs/<run>/` stays covered.

**Every Tier-3 shape marshal writes, measured at `70975ae790`.** The source was read without importing marshal. The
`bmad-build-auto` row comes from the skill marshal dispatch launches.

| Shape under `implementation-artifacts/` | Writer | bmad-drift today |
|---|---|---|
| `recall-feedback__<story>__<run>.md` | marshal `core/recall_feedback.py::recall_feedback_output_relpath`, through `adapters/harness_bmadloop.py::inject_recall_feedback` | `uncovered` |
| `recall-feedback__<story>__<run>.md.query-ran` | marshal `adapters/harness_bmadloop.py::_recall_query_marker_path` | `uncovered` |
| `epic-<N>-continuity.md` | marshal `core/derived_context.py::continuity_output_relpath` (written while the continuity layer is on) | `uncovered` |
| `session-advisories/<run>/…` | marshal `cli/context.py::_session_advisory_runs_dir` (`marshal context advisory`, the session-close ritual) | `uncovered` |
| `dispatch-runs-quarantine/<run>/…`, `dispatch-runs-quarantine/README*` | the location marshal's stale-run remedy names (`core/dispatch_stale.py`); the operator moves a run there | `uncovered` (145 files on the primary checkout) |
| `token-economy-benchmark-<stamp>.json`, `token-economy-benchmark-per-layer-<stamp>.json` | marshal `cli/benchmark.py::default_artifact_path`, `_default_per_layer_artifact_path` | `uncovered` |
| `bmad-build-auto-result-<slug>.md` | the `bmad-build-auto` session marshal dispatch launches (`.claude/skills/bmad-build-auto/workflow.md`, when there is no spec file to write to) | `uncovered` |
| `<…>attempted-change<…>.patch` at the Tier-3 root | the dispatched session's blocked-halt patch. Marshal's supervisor leaves the Tier-3 copy in place (`dispatch_supervisor/__main__.py::_attempted_change_patch_paths`) | `stray-file` HARD, with the remedy "already in git history — remove". That is untrue: it is the only copy. `scripts/bmad_drift_check.py --fix` deletes it |
| `sessions/<id>/gate-records/<story>/gate-record.json` (added by review iteration 2) | marshal `cli/gate.py::_write_gate_record` (`marshal gate evaluate` without `--run-id`), through the twice-defined `_tier3_path` | `uncovered` |
| `dispatch-runs/<run>/failed/<story>/changes.patch` (added by review iteration 2) | the dispatch supervisor's `dispatch_supervisor/__main__.py::_journal_dispatch_preserve`, at the path `core/dispatch_preserve.py::failed_patch_path` builds: a failed dispatch's only copy of its uncommitted work | `stray-file` HARD, with the same untrue remedy (57 files on the primary checkout) |
| `fleet-drain-runs/campaign.lock` (added by review iteration 3) | marshal `core/dispatch_fleet.py::fleet_cycle_lock_path`; the advisory lock adds `.lock` (`adapters/fs_local.py`) | `uncovered` |
| `dispatch-runs/`, `runs/`, `fleet-drain-runs/`, `sprint-status*.yaml`, `epic-<N>-context.md`, `worktree-verdicts-<date>.json`, `deferred-work.md`, `spec-*.md`, `retros/` | marshal and the BMAD skills | covered |

**Approach:**
- **One declared list.** `sources/factory.py` gains `TIER3_RUN_ARTIFACTS`, a tuple of `(pattern, classification,
  writer)` rows, one per shape marshal or its dispatched session writes into Tier-3. `writer` names the source file
  and symbol, or the skill file.
  - The existing Tier-3 run rules move into it unchanged, with the same class strings: `runs/`, `dispatch-runs/`,
    `fleet-drain-runs/`, `epic-<N>-context.md`, `sprint-status*.yaml` and `worktree-verdicts-<date>.json`.
  - `classify()` reads the list at the point where those rules sat. The `coverage-summary` buckets for today's files
    do not change, except that a failed attempt's `changes.patch` moves from `local:run-journal` to
    `local:failed-attempt` (review iteration 2).
- **The new rows:**
  - the recall-feedback pair, `local:recall-feedback`;
  - `epic-<N>-continuity.md`, `local:sprint-feed` (the class `epic-<N>-context.md` has);
  - `session-advisories/<run>/…` and `dispatch-runs-quarantine/…`, `local:run-journal`;
  - both benchmark defaults, `local:benchmark`;
  - `bmad-build-auto-result-<slug>.md`, `local:run-result`;
  - the Tier-3-root attempted-change patch, `local:attempted-change`;
  - `sessions/<id>/…` gate records, `local:run-journal` (review iteration 2);
  - a failed attempt's `dispatch-runs/<run>/failed/<story>/changes.patch`, a new class `local:failed-attempt`, listed
    before the `dispatch-runs/` row (review iteration 2);
  - `fleet-drain-runs/campaign.lock`, `local:run-journal` (review iteration 3).
- **The patch is kept.** `check_archive_hygiene` does not report the attempted-change patch as a `stray-file`, and
  `scripts/bmad_drift_check.py`'s `do_fix` does not delete it. Every other stray suffix (`.patch`, `.diff`, `.bak`,
  `.orig`, `.tmp`, `.rej`) is reported and removed as today. Since review iteration 2 the failed-attempt patch is kept
  too, and the keep is derived from the row's class (`TIER3_KEPT_CLASSES`), never from a second hand-coded shape.
- **The reference copy agrees.** `scripts/bmad_drift_check.py` keeps an unused reference `classify()` copy, documented
  as hand-synced. It gains the same rows, and a test fails if the two copies disagree on any sample path.
- **A meta-test keeps the list in step with marshal.** A new doctor meta-test reads
  `src/shared/packages/pyforge-marshal/src/**/*.py` with `ast`. It never imports `pyforge.marshal`: the classifier
  never imports the station it judges.
  - It collects every path segment marshal builds directly under `implementation-artifacts`, resolving module-level
    string constants. Such a segment comes from a `/` join after the segment `"implementation-artifacts"`, an f-string
    tail on `implementation_artifacts_relpath(...)`, or a literal holding `implementation-artifacts/<segment>`.
  - A table in the test maps each collected segment to a sample path. The test fails, naming `file:line`, for a
    collected segment with no row, and for a row whose sample classifies `UNKNOWN`.
  - For each row it checks that the writer token is still in the cited source, for example `".query-ran"` in
    `_recall_query_marker_path` and `bmad-build-auto-result-` in the skill's `workflow.md`. A renamed writer then
    fails the test; it does not leave a dead row behind.
  - A prototype of the scan at `70975ae790` collects `deferred-work.md`, `dispatch-runs`, `dispatch-runs-quarantine`,
    `epic-{}-context.md`, `epic-{}-continuity.md`, `fleet-drain-runs`, the recall-feedback stem, `runs`,
    `session-advisories`, `sprint-status.yaml`, `token-economy-benchmark-{}.json` and
    `token-economy-benchmark-per-layer-{}.json`.
  - Doctor's station-tests job triggers on any `src/` change (`.github/workflows/pyforge-station-tests.yml`
    `doctor_paths`), so a marshal PR that adds a shape runs this test.
- **The runbook says so.** `_bmad-output/projects/pyforge-marshal/SYNC-RUNBOOK.md`'s `stray-file` row (`--fix`) and
  `uncovered` row point at the declared list and say that the attempted-change patch is kept.

Ledger key: `43-1-bmad-drift-knows-every-file-marshal-dispatch-writes-into-tier-3`.
Type / Effort / Deps: fix / S / —.

### Living CAP citations

- **Capability.** `spec-pyforge-doctor` CAP-12: the fix ships as classification rules in `classify()`, and
  `check_coverage`'s fail-closed default holds for any file no rule names. With CAP-11 (`classify()` recognizes a
  legitimate, writer-mandated artifact shape). FR-15 (Story 6.8, the port) and FR-16 (Story 6.11). A defect of shipped
  behaviour, so no CAP is minted and no `SPEC.md` text changes.
- **No flag.** `type: fix` (`spec-feature-flag-governance` Q1): a fix restores intended behaviour.
- **Origin.** `docs/dreams/pyforge-doctor.md` § *Realization log*, the 2026-10-12 (bmad-drift knows dispatch run
  artifacts) entry. Operator ask 2026-10-12, verbatim: "Do this task here: Teach bmad-drift about dispatch
  recall-feedback files".

## Acceptance Criteria

Fixtures build on `test_sources_factory.py`'s `_bootstrap`, a clean, committed `pyforge-marshal` tree whose `gather`
gives one OK row. Planted Tier-3 files stay uncommitted, as that helper's docstring describes.

- **AC1 — The recall-feedback pair is not uncovered.** Plant
  `implementation-artifacts/recall-feedback__97.2__pyforge-marshal-20261012T103206150Z-210a0f06.md` and the same name
  plus `.query-ran`. `factory.gather` gives the single OK row, and `classify()` returns `local:recall-feedback` for
  both.
- **AC2 — An unknown file still fails.** Plant `implementation-artifacts/randomfile.txt`: exactly one FAIL
  `uncovered` naming it. Each of these look-alikes is also one `uncovered` FAIL:
  - `recall-feedback.md` and `recall-feedback__97.2.md` (no run segment);
  - `recall-feedback__a__b.txt`;
  - `notes.query-ran` (no recall-feedback stem);
  - `session-advisories.md` at the root;
  - `token-economy-benchmark.json` (no stamp);
  - `epic-x-continuity.md`;
  - `bmad-build-auto-result.md` (no slug).
- **AC3 — Every shape in the Intent table is covered.** Plant one file of each shape in the table:
  - `epic-97-continuity.md`;
  - `session-advisories/<run>/journal.jsonl`;
  - `dispatch-runs-quarantine/<run>/journal.jsonl` and `dispatch-runs-quarantine/README.md`;
  - `token-economy-benchmark-2026-10-12T103206Z.json` and `token-economy-benchmark-per-layer-2026-10-12T103206Z.json`;
  - `bmad-build-auto-result-97-2-some-story.md`;
  - `97-2-x-attempted-change.patch`;
  - the AC1 pair.

  `gather` gives the single OK row, and `classify()` returns a class declared in `TIER3_RUN_ARTIFACTS` for every
  planted file. `scratch.bak` and `review-diff.patch` at the Tier-3 root are each still one `stray-file` FAIL. Against a
  tmp tree, `scripts/bmad_drift_check.py`'s `do_fix` removes those two and keeps the attempted-change patch.
- **AC4 — The list stays in step with marshal.** The meta-test passes on the tree. It fails, naming the file and line,
  when it scans a fixture copy of a marshal module with an added line `run_dir = root / "implementation-artifacts" /
  "new-kind"`. It fails when a table row's writer token is missing from its cited source. Neither
  `sources/factory.py` nor the meta-test imports `pyforge.marshal`: `tests/meta/test_source_independence.py` still
  passes, and the meta-test has no `pyforge.marshal` import.
- **AC5 — The reference copy agrees.** For every sample path in the meta-test's table and in AC2, the reference
  `classify()` in `scripts/bmad_drift_check.py` returns the same class as `sources/factory.py`'s.
- **AC6 — Mutation.** Each change fails the test named:
  - Remove the recall-feedback rows: AC1.
  - Remove the attempted-change exemption from `check_archive_hygiene`: AC3.
  - Let `do_fix` delete the patch again: AC3's `do_fix` assertion.
  - Remove the `session-advisories` row: AC3, and the AC4 meta-test, naming `cli/context.py`.
  - Widen the recall-feedback pattern to `recall-feedback.*`: AC2.
- **AC7 — A worktree holding these files reads clean.** In the dispatch worktree that runs this story,
  `_bmad-output/projects/pyforge-marshal/implementation-artifacts/` is absent. A marshal dispatch worktree has it as a
  real directory holding only its recall-feedback pair. Create it as a real directory, never a symlink to the primary
  checkout, and plant the AC1 pair and one file of each AC3 shape. `pixi run -e pyforge-guild bmad-drift-check` reports
  no `uncovered` and no `stray-file`, and `pixi run -e pyforge-guild detectors-ci` exits 0. Remove the directory
  afterwards.
- **AC8 — Nothing else moves.** Every existing `test_sources_factory.py` test passes unchanged. Every existing class
  string and finding kind is as before. The `coverage-summary` buckets for a tree without the new shapes are as
  before.

## Boundaries & Constraints

**Always:**
- Keep `check_coverage`'s fail-closed default: a file no rule names is `uncovered` (HARD).
- Keep each moved rule's class string.
- Read marshal's source as text or `ast`, never by import.
- Read every verdict from the exit code, never through a pipe.
- Reconcile every governed path the change touches on the memlog of each Spec that governs it, then stamp those Specs
  scoped: `spec-pyforge-doctor`, and every co-governor `spec-surface-check` names (`spec-pyforge-core` co-governs
  station `src/`; `_bmad-output/projects/pyforge-marshal/SYNC-RUNBOOK.md` and `scripts/bmad_drift_check.py` may have
  their own governors) (AGENTS.md pre-PR item 5).

**Never:**
- Never import `pyforge.marshal`, or any station package, from `sources/factory.py` or the meta-test.
- Never skip gitignored Tier-3 files wholesale in `check_coverage`, and never add a catch-all rule. Each shape gets its
  own row.
- Never change marshal's writers. This story teaches the classifier; marshal's paths stay as they are.
- Never hand-edit a `SPEC.md` or a `sprint-status-ledger.yaml`.

**Residual risk:**
- The meta-test sees a path marshal builds in a form it recognizes: a `/` join, an f-string tail, or a literal under
  `implementation-artifacts`. A path built some other way, such as a `with_name` suffix like `.query-ran`, is covered
  by its table row and writer token, not by the scan. A future writer in a new form shows up as `uncovered` in a dispatch
  worktree, as today.
- `bmad-drift` scans `pyforge-marshal` only. Other stations' dispatch worktrees hold the same recall-feedback files,
  but no bmad-drift scan reads them.

## I/O & Edge-Case Matrix

| File under `pyforge-marshal/implementation-artifacts/` | `classify()` | Finding |
|---|---|---|
| `recall-feedback__97.2__<run>.md` | `local:recall-feedback` | none |
| `recall-feedback__97.2__<run>.md.query-ran` | `local:recall-feedback` | none |
| `recall-feedback.md`, `recall-feedback__97.2.md`, `recall-feedback__a__b.txt` | `UNKNOWN` | `uncovered` FAIL |
| `epic-97-continuity.md` | `local:sprint-feed` | none |
| `session-advisories/<run>/journal.jsonl` | `local:run-journal` | none |
| `dispatch-runs-quarantine/<run>/session.log`, `dispatch-runs-quarantine/README.md` | `local:run-journal` | none |
| `token-economy-benchmark-<stamp>.json`, `token-economy-benchmark-per-layer-<stamp>.json` | `local:benchmark` | none |
| `bmad-build-auto-result-<slug>.md` | `local:run-result` | none |
| `<…>attempted-change<…>.patch` at the root | `local:attempted-change` | none; `--fix` keeps it |
| `review-diff.patch`, `scratch.bak` at the root | `UNKNOWN` (stray suffix) | `stray-file` FAIL; `--fix` removes it |
| `randomfile.txt` | `UNKNOWN` | `uncovered` FAIL |
| `dispatch-runs/<run>/journal.jsonl` | `local:run-journal` | none (unchanged) |
| `sessions/<id>/gate-records/97-2/gate-record.json` | `local:run-journal` | none |
| `dispatch-runs/<run>/failed/<story>/changes.patch` | `local:failed-attempt` | none; kept, never `stray-file` |
| `dispatch-runs/<run>/failed/<story>/other.patch`, `runs/<run>/failed/<story>/changes.patch` | `local:run-journal` (stray suffix) | `stray-file` FAIL |
| `fleet-drain-runs/campaign.lock` | `local:run-journal` | none |
| `fleet-drain-runs/other.lock`, `fleet-drain-runs/campaign` | `UNKNOWN` | `uncovered` FAIL |
| `fleet-drain-runs/campaign.lock.bak` | `UNKNOWN` (stray suffix) | `stray-file` FAIL |

</intent-contract>

## Binding

- Parent Spec capabilities: `spec-pyforge-doctor` CAP-12, with CAP-11; FR-15 (Story 6.8), FR-16 (Story 6.11). No CAP is
  minted, and no `SPEC.md` text changes.
- Dream: `docs/dreams/pyforge-doctor.md` § *Realization log*, the 2026-10-12 (bmad-drift knows dispatch run
  artifacts) entry.
- Epic: Epic 43 (new), on the operator's numbering. Epic 6, which shipped the classifier, is `done`. Under the
  2026-10-04 ruling a fix may reopen its own epic; this one opens Epic 43 instead. `epic-43` and
  `epic-43-retrospective` are minted with it.
- Ledger key: `43-1-bmad-drift-knows-every-file-marshal-dispatch-writes-into-tier-3`.
- Ledger status at mint: `backlog`.
- Deps: —.
- Precedent: Story 6.11 (a `classify()` rule, with a look-alike that still fails); Story 6.12 (a bmad-drift fix in both
  `sources/factory.py` and `scripts/bmad_drift_check.py`).
- Surface: `marshal-policy.toml` `[epic_surfaces]."43"`, added with this mint. It holds the default surface,
  `scripts/bmad_drift_check.py`, `tests/scripts/**`, marshal's `SYNC-RUNBOOK.md`, and every Spec memlog.
- Spec: the `spec-pyforge-doctor` memlog records the ask verbatim, the design and this mint.
- Minted 2026-10-12 in one chain commit.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-doctor pyforge-doctor-test` — expected: pass, with the AC1-AC6 and AC8 tests (the station's `verify_commands`; MRS-GATE-010 binding).

**Run before the push (not dispatch gates):**
- `pixi run --frozen -e pyforge-ci pyforge-doctor-scripts-test` — expected: pass (the `tests/scripts/` side of AC3 and AC5).
- `pixi run -e pyforge-guild bmad-drift-check` and `pixi run -e pyforge-guild detectors-ci` in the dispatch worktree, with the AC7 files planted — expected: no `uncovered` or `stray-file` finding, and exit 0.
- `pixi run --frozen -e pyforge-guild lint-types` — expected: exit 0.
- `python scripts/spec_surface_reconcile.py` and `pixi run --frozen -e pyforge-guild spec-surface-check` — expected: exit 0 after the memlogs and scoped stamps.
- The five AC6 mutations — expected: each fails its named test. Restore each.

## Named, not fixed here

- **Operator-made patches.** `parked-diffs/<…>.patch` and `saved-patches/<…>.patch` under marshal's Tier-3 store on the
  primary checkout are operator-made, and no code writes them. They stay `stray-file`. The operator decides whether to
  keep them.
- **Other stations' Tier-3.** bmad-drift scans `pyforge-marshal` only (`PROJ_REL`). Widening it is a separate change.

## Spec Change Log

- 2026-10-12 — The independent reviews widened the declared shapes, within the operator's "keep the wider scope".
  Iteration 2 added `sessions/<id>/…` gate records (`local:run-journal`) and a failed attempt's
  `dispatch-runs/<run>/failed/<story>/changes.patch` under a new class, `local:failed-attempt`, kept like the
  attempted-change patch; the keep is now derived from the class (`TIER3_KEPT_CLASSES`). Iteration 3 added
  `fleet-drain-runs/campaign.lock` (`local:run-journal`) and corrected the failed-attempt writer to
  `core/dispatch_preserve.py::failed_patch_path`; the iteration-2 record named `supervisor/intent_gap_preserve.py`,
  which writes only the loop home's `.bmad-loop/runs/`. The Intent table, the Approach's new rows and the I/O matrix
  now carry these shapes.

- 2026-10-12 — Scope confirmed by the operator: asked whether to keep the wider scope (all seven dispatch-written kinds plus the attempted-change patch exemption) or narrow to the recall-feedback pair, the operator answered "keep the wider scope, keep going".

- 2026-10-12: minted from the operator's ask "Do this task here: Teach bmad-drift about dispatch recall-feedback files",
  found on marshal Story 97.2's dispatch worktree.

## Review Triage Log

### 2026-10-12 — Fix pass for iteration 3 (implementer)

Separate implementer session on `dispatch/pyforge-doctor/43.1` at `691611ffd0`, uncommitted. F1, F3, F4 and the nit are fixed; F2 is appended to `DW-doctor-43-1-2`, and its cheap cases are fixed now. Mutations ran in the scratch repo copy, restored from the worktree after each run; the worktree's `git status` and `git diff` were identical before and after. Line numbers are at this pass's working tree.

- F1 — the failed-attempt row now cites `core/dispatch_preserve.py::failed_patch_path` (`factory.py:332`). Its comment names the real caller, `dispatch_supervisor/__main__.py::_journal_dispatch_preserve`, and says why the look-alike `supervisor/intent_gap_preserve.py::_write_failed_patch` (loop home only) is not the writer.
  - The meta table row (`test_bmad_drift_tier3_marshal_shapes.py:218`, token `"changes.patch"`) and `_WRITER_TOKENS` both cite it. `_WRITER_TOKENS` now accepts several required literals per row (`:236`, checked at `:711`). This row needs `"changes.patch"` plus `return run_dir / "failed"`: `"changes.patch"` alone also sits in `_write_failed_patch`, so the iteration-2 mis-cite would have passed on it.
  - Memlog: a correction event on `spec-pyforge-doctor` (`.memlog.md:716`) names the iteration-2 entry and the story's iteration-2 fix-pass entry as wrong, and states the real writer.
  - Mutations:
    - Decisive: rename `"changes.patch"` in `failed_patch_path` in a scratch marshal copy → red (`test_every_tier3_rule_names_a_real_writer`, `test_writer_tokens_still_present_in_cited_sources`).
    - The same rename in `supervisor/intent_gap_preserve.py` → green, as it should be now that the file isn't cited.
    - Point the row back at `_write_failed_patch` → red, because `return run_dir / "failed"` is missing there.
- F3 — a new row, `^implementation-artifacts/fleet-drain-runs/campaign\.lock$` → `local:run-journal`, with writer `core/dispatch_fleet.py::fleet_cycle_lock_path` (`factory.py:359-361`, script `:137`).
  - Its comment notes the `.lock` suffix comes from the advisory lock (`adapters/fs_local.py`). The token is `/ "campaign"`, in 1 marshal symbol.
  - Meta table row: `:225`. AC3 plant: `test_sources_factory.py:1805`.
  - Look-alikes: `fleet-drain-runs/other.lock` and `fleet-drain-runs/campaign` stay `uncovered` (`:1950`), and `campaign.lock.bak` is `stray-file` (`:1963`). Script agreement samples cover all three (`tests/scripts/…:70-72`).
  - Mutations:
    - Remove factory's row → 4 tests red.
    - Remove the script's row → the equality and agreement tests red.
    - Widen the row to any root `.lock` → the `other.lock` look-alike test red, and the writer test red (its pattern key changed).
    - Rename `"campaign"` in `fleet_cycle_lock_path` in a marshal copy → the writer and token tests red.
- F4 — the spec now records the iteration-2 and iteration-3 shapes:
  - a new Spec Change Log entry, which also notes the writer correction;
  - three Intent-table rows (`sessions/<id>/…`, the failed-attempt patch, `campaign.lock`), each marked with the review iteration that added it;
  - the Approach's new-rows list gains the three shapes and the class `local:failed-attempt`. The moved-rules bullet now says the failed patches change bucket, and "The patch is kept" now covers the failed-attempt patch and the derived exemption;
  - six I/O-matrix rows, covering the shapes and their look-alikes.
- F2 — appended to `DW-doctor-43-1-2`, with fresh cited `verified:` lines. The cheap cases are fixed now:
  - the `sessions/` token is `/ "sessions" / session_id` (1 symbol, was `"sessions"` in 2). Mutation: pointing the row at `core/layer_savings_sources.py::read_dispatch_idle_timing`, which also holds `"sessions"`, → red;
  - the failed-attempt pair (F1) is the other.
  - Still generic and deferred: `"runs"` (30 symbols) and `"sprint-status.yaml"` (6). No single literal pins their writers, and the tuple form now makes a second literal possible.
  - `DW-doctor-43-1-1`'s location and `verified:` line are refreshed for the moved rows.
- Nit — the Auto Run Result now says the iteration-2 pass is committed (`9554d68795`) and this pass is uncommitted.

AC8, with the primary checkout's 3020 `pyforge-marshal` files: HEAD's factory and this pass's give identical classes (0 changed; the checkout holds no `campaign.lock` today). `main`'s factory against this pass's changes exactly 202 files: 145 quarantine files go from `UNKNOWN` to `local:run-journal`, and 57 failed patches go from `local:run-journal` to `local:failed-attempt`. That matches the iteration-3 review's count.

8 mutations this pass, all as expected: 7 red, and the `intent_gap_preserve.py` rename green.

AC7: a real `implementation-artifacts/` (not a symlink) holding the AC1 pair, every AC3 shape, a `sessions/<id>/…` gate record, a failed-attempt `changes.patch` and `fleet-drain-runs/campaign.lock` (15 files) gives `bmad-drift-check` 0, with no `uncovered` and no `stray-file`. Adding `fleet-drain-runs/other.lock` gives 2 (`uncovered`). `detectors-ci` gives 0 (46 of 46). The directory was removed.

Gates, exit codes read from files:

| Gate | Exit | Notes |
|---|---|---|
| `pixi run --frozen -e pyforge-doctor pyforge-doctor-test` | 0 | 3596 passed, 1 skipped; the speed-budget test 1 passed |
| `pixi run --frozen -e pyforge-ci pyforge-doctor-scripts-test` | 0 | 1494 passed, 31 skipped |
| `pixi run -e pyforge-guild lint-types` | 0 | pyforge-doctor ruff, ruff-format and mypy ok |
| `spec-surface-check` | 0 | after memlog reconciles and scoped stamps on `pyforge-doctor/spec-pyforge-doctor` and `pyforge-marshal/spec-pyforge-core` |
| `scripts/spec_surface_reconcile.py` | 0 | |
| `bmad-drift-check` | 0 | |
| `deferred-work-check` | 0 | |
| `frontmatter-duplicate-keys-check` | 0 | |
| `detectors-ci` | 0 | 46 of 46, re-run after this entry and the Auto Run Result were written |

### 2026-10-12 — Independent review, iteration 3: sent back (1 medium, 2 low patch; 1 low defer)

Fresh separate agent, review at 9554d68795. N1, N2, N5, N6 closed and N3 partly (27 mutations; resolver give-up restored → `sessions` lost; sessions/failed-attempt rows and kept classes removed or reordered → red; wrong writer symbols → red; tightened kept rows → exemption follows). Live scan: 16 segments; cross-checked against every Tier-3-returning helper and every `implementation-artifacts` grep hit — the only writers outside the scan are `.query-ran` (covered), `fleet-drain-runs/campaign.lock` (F3) and transient atomic-write temp files. `--fix` touches only root-level files and skips kept classes. AC7 by hand (13 planted files incl. a sessions gate record and a failed-attempt patch): `bmad-drift-check` 0, `detectors-ci` 46/46; root `review-diff.patch`, `failed/97.2/other.patch` and `randomfile.txt` controls each exit 2. AC8 on the primary checkout's 3020 marshal files: only 145 quarantine files (UNKNOWN → `local:run-journal`) and 57 failed patches (`local:run-journal` → `local:failed-attempt`, their `stray-file` findings gone) change. Gates all 0.

- `[medium]` `[patch]` F1 `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/factory.py:328`, meta-test `tests/meta/test_bmad_drift_tier3_marshal_shapes.py:217` cite `supervisor/intent_gap_preserve.py::_write_failed_patch`, which writes the loop home's `.bmad-loop/runs/<id>/failed/<story>/changes.patch`, not Tier-3; the Tier-3 `dispatch-runs/<run>/failed/<story>/changes.patch` is written by `core/dispatch_preserve.py::failed_patch_path` (`:47-49`, called from `dispatch_supervisor/__main__.py::_journal_dispatch_preserve` `:349`). Renaming `"changes.patch"` in the real writer leaves every test green. Fix: cite `core/dispatch_preserve.py::failed_patch_path` (token `"changes.patch"`) in both places; correct the record with a memlog entry (the iteration-2 entry and `spec-pyforge-doctor/.memlog.md:715` name the wrong writer).
- `[low]` `[patch]` F3 `fleet-drain-runs/campaign.lock` (marshal `cli/dispatch.py:6427` via `core/dispatch_fleet.py::fleet_cycle_lock_path` `:442-450`, `.lock` from `adapters/fs_local.py:469`) is `uncovered`: the moved row needs a subdirectory. Fix: a `^implementation-artifacts/fleet-drain-runs/campaign\.lock$` → `local:run-journal` row (writer `fleet_cycle_lock_path`) in both copies, with a look-alike test.
- `[low]` `[patch]` F4 the spec's Intent table, Approach and I/O matrix do not record the two iteration-2 shapes (`sessions/<id>/…`, the failed-attempt patch and its new class `local:failed-attempt`). Fix: a Spec Change Log entry (and the table/matrix rows).
- `[low]` `[defer]` F2 three writer tokens are generic (`'"runs"'` in 30 marshal symbols, `'"sprint-status.yaml"'` in 6, `'"sessions"'` in 2), so a wrong symbol holding the same literal passes; append to DW-doctor-43-1-2.
- Nit: the Auto Run Result still calls the iteration-2 pass uncommitted (refreshed at landing).

Send-back: F1, F3, F4 in one pass; F2 appended to DW-doctor-43-1-2. The iteration-3 reviewer named the decisive check: renaming `"changes.patch"` in `core/dispatch_preserve.py::failed_patch_path` must go red — the orchestrator re-runs it on the delta before landing.

### 2026-10-12 — Fix pass for iteration 2 (implementer)

Separate implementer session on `dispatch/pyforge-doctor/43.1` at `a17efcc91e`, uncommitted. N1, N2, N3, N5, N6 and the nit are fixed; N4 is appended to `DW-doctor-43-1-2`. Mutations ran in a scratch copy of the repo's relevant files (doctor package, marshal `src/`, the script, `tests/scripts/`, the two skill files), restored from the worktree after each run. The worktree's `git status` and `git diff` were identical before and after. Line numbers are at this pass's working tree.

- N1 — meta-test `test_bmad_drift_tier3_marshal_shapes.py`:
  - The index records each module's `from … import` (relative, or absolute under `pyforge.marshal`; `_import_base` `:322`, `_build_index` `:340`) and its top-level functions.
  - A call resolves to its definition in this order: the calling module's own function; then the function its import names, followed through re-exports (`_function` `:463`); then `module.helper(...)` through an imported submodule (`_resolve_call` `:486`).
  - Failing those, it accepts several same-named definitions only when they all render the same template (`:509`); `_tier3_path` is duplicated verbatim in `cli/spin.py:1039` and `supervisor/__main__.py:722`.
  - Imported module constants resolve too (`_resolve_name` `:449`).
  - Live marshal now gives 16 segments: the 15 from iteration 1 plus `sessions` (`cli/gate.py:1222`). `"sessions"` is in `_EXPECTED_MARSHAL_SEGMENTS` (`:43`), with a `_SHAPE_TABLE` row (`:205`).
  - `factory.py:412` and `scripts/bmad_drift_check.py:150` carry `^implementation-artifacts/sessions/[A-Za-z0-9._-]+/.*` → `local:run-journal`. Its writer is `cli/gate.py::_write_gate_record` (verified at `cli/gate.py:1162`); the class is the same as `runs/<run>/gate-records/`.
  - New `test_fixture_helper_defined_twice_still_resolves` (`:774`) covers three cases, each red naming `c.py:<line>`: imported-one-of-two-different-definitions, two-identical-definitions-not-imported, and a submodule attribute call.
  - Mutations:
    - The old give-up resolution → meta-test red, "scan no longer sees: ['sessions']", and all 3 fixture cases red.
    - Import following off → 2 fixture cases red.
    - Render-same acceptance off → 1 fixture case red.
    - Remove factory's sessions row → AC3 and the meta-test red, naming `cli/gate.py:1222`.
    - Remove the script's sessions row → the agreement tests red.
    - A new kind built through `gate.py`'s `_tier3_path` in a marshal copy → red, naming `cli/gate.py:1419`.
- N2 — new row `^implementation-artifacts/dispatch-runs/[A-Za-z0-9._-]+/failed/[A-Za-z0-9._-]+/changes\.patch` → `local:failed-attempt`, writer `supervisor/intent_gap_preserve.py::_write_failed_patch` (`factory.py:326`, script `:128`).
  - It is listed before the `dispatch-runs/` row, which would otherwise claim it.
  - Its class is kept (N5), so `check_archive_hygiene` no longer reports it. All 57 such files on the primary checkout sit under `dispatch-runs/<run>/failed/<story>/`.
  - Tests:
    - `test_failed_attempt_patch_is_kept_and_its_look_alikes_are_not` (`test_sources_factory.py:1902`) keeps it, and four look-alikes (`failed/<story>/other.patch`, a run-root `changes.patch`, `failed/changes.patch`, the same shape under `runs/`) stay `stray-file`.
    - The AC3 plant includes it (`:1804`).
    - Agreement samples cover it, plus three `local:run-journal` look-alikes (`tests/scripts/…:67`).
  - `--fix`: `do_fix` removes root-level strays only (`IMPL.iterdir()`), so it never reached this nested file. Its keep is derived all the same, and `test_do_fix_never_reaches_a_failed_attempt_patch` (`tests/scripts/…:161`) asserts `_is_kept_tier3_artifact` holds and the file survives.
  - Mutations, each red in the hygiene test and AC3: drop `local:failed-attempt` from `TIER3_KEPT_CLASSES`; remove the row; move it after `dispatch-runs/`. Dropping it from the script's kept classes reds the equality test and the do_fix test.
- N3 — `_WRITER_TOKENS` (`:226`) gives each `TIER3_RUN_ARTIFACTS` row, keyed by pattern, a token that must sit inside the cited symbol's own source (`_symbol_source` `:662`: `ast.get_source_segment`; the module docstring for `::__doc__`; the whole file for a skill file).
  - The token set must equal the row set (`test_every_tier3_rule_names_a_real_writer` `:677`). The attempted-change token is the code's `rglob("*attempted-change*.patch")`, not the docstring copy.
  - The worktree-verdicts writer is now `scripts/worktree_sweep.py::__doc__` (`factory.py:377`), the documented `--format json` redirect; `main` never names the file.
  - Mutations, each red:
    - Recall `.md` row pointed at `format_recall_feedback_for_injection`.
    - Session-advisories row pointed at `core/derived_context.py::continuity_output_relpath`.
    - Attempted-change row pointed at its caller `_commit_and_journal_blocked_halt` (same file).
    - Sessions row pointed at `cli/gate.py::run_evaluate`.
    - In marshal copies: the `rglob` glob renamed in code only; `"changes.patch"` renamed in `_write_failed_patch`.
- N5 — `TIER3_KEPT_CLASSES = {local:attempted-change, local:failed-attempt}` and `_is_kept_tier3_artifact(rel)` = `_classify_tier3_run_artifact(rel) in TIER3_KEPT_CLASSES` (`factory.py:463-467`, used at `:1026`; script `:174-178`, used in `do_fix` at `:508`). The hand-coded `_is_attempted_change_patch_rel` is gone from both.
  - `test_kept_exemption_follows_the_table_class` (`test_sources_factory.py:1926`) narrows the row and sees the patch go `stray-file`.
  - `test_reference_rows_and_kept_classes_equal_factorys` (`tests/scripts/…:108`) pins the script's rows (order included) and kept classes to factory's.
  - `test_do_fix_keep_follows_the_reference_table` (`:147`) narrows the script row and sees `--fix` remove the patch.
  - Mutations: tighten factory's attempted-change row with the derivation untouched → AC3 red (the patch is `stray-file`); tighten the script's row → `test_do_fix_keeps_attempted_change_patch` red, plus the equality and agreement tests.
- N6 — the Auto Run Result block now reads `Status: in-progress` and states the send-back history, the open iteration-3 review and the current change. The stale iteration-1 line is marked superseded. Frontmatter `status: 'in-progress'` and `review_loop_iteration` are untouched.
- Nit — the `# noqa: E402` at `tests/scripts/test_bmad_drift_check_tier3_classify.py:34` is removed (`ruff check --isolated` clean).
- N4 — appended to `DW-doctor-43-1-2` (`planning-artifacts/deferred-work-ledger.md:2989`), with a fresh cited `verified:` line. Since N3, a code-only rename of the glob already reds the factory-side writer test; what remains is the meta table's file-wide token. `DW-doctor-43-1-1`'s location and verified line are refreshed for the moved rows.
- Also updated: `SYNC-RUNBOOK.md:83` (`stray-file` / `--fix`) now names `TIER3_KEPT_CLASSES` and both kept shapes. A comment on the `TIER3_RUN_ARTIFACTS` docstring now records first-match ordering.

AC8 note: the 57 `dispatch-runs/<run>/failed/<story>/changes.patch` files on the primary checkout move from `local:run-journal` to `local:failed-attempt`, and their `stray-file` findings go away; this is the N2 fix. No other existing file changes class.

18 mutations this pass, all red as expected. In the scratch copy's baseline, the mutated nodes were green; three unrelated `test_sources_factory.py` tests failed there because they read `pixi.toml` and `scripts/pixi_env_matrix.py`, which the copy omits.

AC7: a real `implementation-artifacts/` (not a symlink) holding the AC1 pair, every AC3 shape, a `sessions/<id>/gate-records/97-2/gate-record.json` and a `dispatch-runs/<run>/failed/28.9/changes.patch` (14 files) gives `bmad-drift-check` 0 with no `uncovered` and no `stray-file`. Adding `dispatch-runs/<run>/failed/28.9/other.patch` gives 2 (`stray-file`). `detectors-ci` gives 0 (46 of 46). The directory was removed.

Gates, exit codes read from files: `pixi run --frozen -e pyforge-doctor pyforge-doctor-test` 0 (3593 passed, 1 skipped; the speed-budget test 1 passed); `pixi run --frozen -e pyforge-ci pyforge-doctor-scripts-test` 0 (1490 passed, 31 skipped); `pixi run -e pyforge-guild lint-types` 0 (pyforge-doctor ruff, ruff-format and mypy ok); `spec-surface-check` 0 after memlog reconciles and scoped stamps on `pyforge-doctor/spec-pyforge-doctor` and `pyforge-marshal/spec-pyforge-core`; `scripts/spec_surface_reconcile.py` 0; `bmad-drift-check` 0; `deferred-work-check` 0; `frontmatter-duplicate-keys-check` 0; `detectors-ci` 0 (46 of 46, re-run after this entry and the Auto Run Result were written). The AC8 comparison of HEAD's factory and this pass's over all 3020 files of the primary checkout's `pyforge-marshal` tree differs in exactly those 57 files.

### 2026-10-12 — Independent review, iteration 2: sent back (2 medium, 3 low patch; 1 low defer)

Fresh separate agent, review at c7759791e9. AC1-AC8 hold and R1-R9/R12 are closed (38 mutations caught: the script's reference classify, every factory row, the five marshal idioms naming path:lineno, nine blinding mutations). AC7 by hand: every AC1/AC3 shape gives `bmad-drift-check` 0 and `detectors-ci` 46/46; a `review-diff.patch` or `randomfile.txt` control reds it. AC8: classifying all 3727 files of the primary and worktree `pyforge-marshal` trees with main's factory and HEAD's differs only in 145 quarantine files moving UNKNOWN -> `local:run-journal`. Gates all 0 (`pyforge-doctor-test` 3588 passed, scripts 1482, lint-types, spec-surface, bmad-drift, deferred-work, frontmatter-duplicate-keys, detectors-ci 46/46, coverage-gate).

- `[medium]` `[patch]` N1 `src/shared/packages/pyforge-doctor/tests/meta/test_bmad_drift_tier3_marshal_shapes.py:378-388` `_resolve_call` gives up on a helper defined in more than one module: `_tier3_path` (`cli/spin.py:1039`, `supervisor/__main__.py:722`) never resolves at `cli/gate.py:1222`, which writes `implementation-artifacts/sessions/<id>/gate-records/<story>/gate-record.json` (`marshal gate evaluate` without `--run-id`); neither the scan nor `TIER3_RUN_ARTIFACTS` knows `sessions/` (planting it makes `bmad-drift-check` exit 2 `uncovered`). In scope under the operator's "keep the wider scope" (every dispatch-written kind). Fix: follow the module's `from .spin import _tier3_path` (or accept several definitions that render the same); a `^implementation-artifacts/sessions/[A-Za-z0-9._-]+/.*` row in `factory.py` and `scripts/bmad_drift_check.py` (writer `cli/gate.py::_write_gate_record`); a `_SHAPE_TABLE` row; `"sessions"` in `_EXPECTED_MARSHAL_SEGMENTS`; a fixture case for a twice-defined helper.
- `[medium]` `[patch]` N2 `factory.py` `check_archive_hygiene` reports `dispatch-runs/<run>/failed/<story>/changes.patch` — the preserved failed attempt written by `supervisor/intent_gap_preserve.py:178` — as `stray-file` HARD with the false remedy "already in git history — remove" (57 on the primary checkout). Same defect class as the attempted-change patch, so in scope. Fix: extend the keep-exemption (and `--fix`) to it, with a test and a writer reference.
- `[low]` `[patch]` N3 meta-test `:536` `test_every_tier3_rule_names_a_real_writer` only checks the cited symbol exists; a wrong but existing symbol or file passes. Fix: require a row-specific token inside that symbol's source.
- `[low]` `[patch]` N5 `factory.py` `_is_attempted_change_patch_rel` and its script copy hand-code the shape a second time. Fix: derive the exemption from the table class (`_classify_tier3_run_artifact(rel)` in the exempt set).
- `[low]` `[patch]` N6 the spec's Auto Run Result "Status: done" and the stale iteration-1 line contradict the send-back. Fix: refresh at landing.
- `[low]` `[defer]` N4 the attempted-change writer token also appears in a docstring (`dispatch_supervisor/__main__.py:892`), so renaming the real glob (`:903`) stays green; append to DW-doctor-43-1-2.
- Nit: unused `# noqa: E402` at `tests/scripts/test_bmad_drift_check_tier3_classify.py:34`.

Send-back: N1, N2, N3, N5, N6 and the nit in one pass; N4 appended to DW-doctor-43-1-2; a fresh independent review (iteration 3) gates the landing.

### 2026-10-12 — Fix pass for iteration 1 (implementer)

Separate implementer session on `dispatch/pyforge-doctor/43.1` at `69d61f9386`, uncommitted. R1-R9 and R12 fixed; R10 and R11 deferred as ledger rows. Every mutation ran in a scratch copy (doctor `src/` through `PYTHONPATH`, the script through a scratch repo root, marshal through a copied tree); the worktree's `git status` and `git diff` were identical before and after. Line numbers are at this pass's working tree.

- R1 — `tests/scripts/test_bmad_drift_check_tier3_classify.py:47-105`: every sample is planted under `factory._impl(repo_root)` (the test asserts `factory._rel(...)` equals the sample). The samples are the meta-test's `_SHAPE_TABLE`, read from that file (`:47`), plus the real recall-feedback pair, the quarantine README, a dotted mixed-case result slug, a `sprint-status-<x>.yaml` control, the AC2 look-alikes and two stray suffixes. Each asserts that both classifiers return the declared class, so an `UNKNOWN`-for-everything pair cannot pass. Mutations: drop the script's session-advisories row → 2 failed; make its `_classify_tier3_run_artifact` return `None` → 23 failed.
- R2 — meta-test `test_bmad_drift_tier3_marshal_shapes.py:206-469` renders an expression to a path template, with `{}` for anything unresolved. `/` chains are flattened (`_flatten` `:321`). A `Name` resolves through the enclosing function's single binding, then the module's single top-level binding (`_resolve_name` `:361`): `_SESSION_ADVISORIES_DIRNAME`, `_DISPATCH_RUNS_DIRNAME`, `_FLEET_RUNS_DIRNAME`, `_SMOKE_SPEC_FILENAME`. A call resolves through a top-level function's single `return` anywhere in the scanned tree, with `implementation_artifacts_relpath` as the named fallback (`_resolve_call` `:371`). `<placeholder>` text becomes `{}`; docstrings and f-string or `+` fragments are skipped (`_fragment_ids` `:401`). The final assertion is `_EXPECTED_MARSHAL_SEGMENTS <= collected` (`:558`), with no union.
  - Live marshal, this HEAD: 15 segments. The prototype's 12 — `deferred-work.md`, `dispatch-runs`, `dispatch-runs-quarantine`, `epic-{}-context.md`, `epic-{}-continuity.md`, `fleet-drain-runs`, `recall-feedback__{}__{}.md`, `runs`, `session-advisories`, `sprint-status.yaml`, `token-economy-benchmark-{}.json`, `token-economy-benchmark-per-layer-{}.json` — plus three story-spec names: `spec-{}-{}{}.md` (`cli/spin.py:532`), `spec-{}-{}{}-recovered.md` (`cli/deploy.py:1421`) and `spec-1-1-marshal-conformance-smoke.md` (`cli/adapters.py:1534`). All three classify `tracked:spec` and share one table row.
  - Mutations in scratch marshal copies, each red naming the added line: the real idiom `run_dir = root / "_bmad-output" / "projects" / slug / "implementation-artifacts" / "new-kind"` in `core/dispatch.py` → `core/dispatch.py:686`; the multi-line `canonical_repo_root(...) / ... / "new-kind"` form in `core/dispatch_fleet.py` → `:1230`; a module constant `_NEW_KIND_DIRNAME` in `cli/context.py` → `:1025`; an f-string tail on the imported `implementation_artifacts_relpath(...)` in `core/recall_feedback.py` → `:120`; the same through a local `stem` in `core/derived_context.py` → `:469`.
  - Blinding, each red: skip `cli/context.py` and `cli/benchmark.py` → "scan no longer sees" 3 segments; `_scan` returns `[]` → all 12; no call resolution → 3 missing plus a spec template with no row; no module-name resolution → `fleet-drain-runs`, `session-advisories`; no `/` flattening → 4 missing; one extra expected segment → red, proving there is no union.
- R3 — `_Hit(segment, path, lineno)` (`:220`); `where` is `path:lineno` (`:226`). Each `_assert_scan_covered` (`:480`) message leads with every `path:lineno` that builds the segment, both for a segment with no row and for a row whose sample, or the collected template instantiated (`_instantiate` `:472`), classifies other than the row's declared class. AC6's fourth bullet now holds: removing factory's session-advisories row reds the meta-test naming `cli/context.py:899`, and AC3.
- R4 — `pytest` is used (`pytest.raises`, parametrize); there is no unused `proj`; `sources/factory.py` is `ruff format` clean (two blank lines before `NONTERMINAL_STATUS`). `lint-types` exit 0, with pyforge-doctor ruff, ruff-format and mypy ok.
- R5 — `test_sources_factory.py:1792-1878`: `_TIER3_DISPATCH_SHAPES` maps each planted file to its class. The AC3 test asserts each planted file's class equals it and is a `TIER3_RUN_ARTIFACTS` class, and that the stray set is exactly the two controls. Mutation: remove the attempted-change row → AC3 red, naming `97-2-x-attempted-change.patch`.
- R6 — scan-and-assert is `_assert_scan_covered` (`:480`). `test_fixture_new_kind_fails_naming_file_and_line` (`:580`) runs it under `pytest.raises(..., match=r"fake_marshal_module\.py:1: builds implementation-artifacts/new-kind")` for five forms: a `/` literal, a `/` chain after a variable, a module constant, an f-string tail and a plain literal. A known segment passes (`:590`). Mutation: make `_assert_scan_covered` a no-op → "DID NOT RAISE".
- R7 — `factory.py:302-426`: each writer is a repo-relative `file::symbol` (prefix `_MARSHAL_SRC_REL`, `:302`) or the skill file. The recall-feedback row splits into a `.md` row (`core/recall_feedback.py::recall_feedback_output_relpath`) and a `.md.query-ran` row (`adapters/harness_bmadloop.py::_recall_query_marker_path`), same class. New `test_every_tier3_rule_names_a_real_writer` (`:536`) parses each writer file and requires the top-level symbol. The meta table gains the attempted-change row (`dispatch_supervisor/__main__.py`, token `*attempted-change*.patch`, `:192`) and the worktree-verdicts row (`scripts/worktree_sweep.py`, `:199`). Mutations: a renamed writer symbol in factory → red; `.query-ran` renamed in a copy of `harness_bmadloop.py` → token test red.
- R8 — the incident comments sit beside the moved rows (`factory.py:311-363`; the sweep-verdicts text whole at `:351`). `classify()` keeps a pointer where sweep-verdicts sat (`:1486`) and a section comment at the lookup (`:1462`); the stray blank line is gone.
- R9 — `bmad-build-auto-result-[A-Za-z0-9._-]+\.md` in `factory.py:414` and `scripts/bmad_drift_check.py:149`. `test_bmad_build_auto_result_takes_the_writers_slug_or_timestamp` (`test_sources_factory.py:1888`) covers `...-2026-10-12T103206Z.md` and `...-97.2-Some_Story.md`. Mutations: narrow either copy back → red.
- R12 — `SYNC-RUNBOOK.md:94`, the `uncovered` row: the script keeps an unused reference copy of `classify()` only; a new Tier-3 row is mirrored into `_TIER3_RUN_ARTIFACT_PATTERNS`; the row names the meta-test and the agreement test. `scripts/bmad_drift_check.py:39`'s docstring no longer says nothing enforces agreement.
- R10, R11 — deferred as `DW-doctor-43-1-1` and `DW-doctor-43-1-2` (`planning-artifacts/deferred-work-ledger.md:2976`, `:2988`).

AC6, re-run in scratch: remove the recall rows → AC1 red; remove the hygiene exemption → AC3 red; let `do_fix` delete the patch → AC3's `do_fix` test red; remove the session-advisories row → AC3 and the meta-test red, naming `cli/context.py:899`; widen the recall pattern → AC2 red on 3 look-alikes. 24 mutations in all this pass; 24 red.

AC7: a real `implementation-artifacts/` (not a symlink) holding the AC1 pair and every AC3 shape gives `bmad-drift-check` 0, with no `uncovered` and no `stray-file`; adding `review-diff.patch` gives 2 (`stray-file`); `detectors-ci` 0 (46 of 46). The directory was removed.

Gates, exit codes read from files: `pixi run --frozen -e pyforge-doctor pyforge-doctor-test` 0 (3588 passed, 1 skipped; the speed-budget test 1 passed); `pixi run --frozen -e pyforge-ci pyforge-doctor-scripts-test` 0 (1482 passed, 31 skipped); `pixi run -e pyforge-guild lint-types` 0; `spec-surface-check` 0 after memlog reconciles and scoped stamps on `pyforge-doctor/spec-pyforge-doctor` and `pyforge-marshal/spec-pyforge-core`; `scripts/spec_surface_reconcile.py` 0; `bmad-drift-check` 0; `deferred-work-check` 0; `frontmatter-duplicate-keys-check` 0; `detectors-ci` 0 (46 of 46, re-run after this entry was written).

### 2026-10-12 — Independent review, iteration 1: sent back (4 high, 2 medium, 4 low patch; 2 low defer)

Separate agent, review of `git diff origin/main...HEAD` (merge-base 6bbfff6dd6, HEAD 1997f1344e). The classifier change is sound: rows correct, moved rules' class strings unchanged (no reader besides tests/docs), `--fix` keeps the attempted-change patch, an unknown file and every look-alike stay failing; AC7 by hand: a real `implementation-artifacts/` holding every AC1/AC3 shape gives `bmad-drift-check` 0, and a stray `review-diff.patch` control turns it red. But the AC4/AC5 guards pass vacuously and `lint-types` is red, so the earlier "AC1-AC8 verified" line did not hold. 14 mutations, 8 caught.

- `[high]` `[patch]` R1 `tests/scripts/test_bmad_drift_check_tier3_classify.py:67` plants samples at the project root, not under `implementation-artifacts/`, so both classifiers return UNKNOWN for all 20 and the AC5 agreement test checks nothing (breaking the script's reference `classify()` survives). Fix: plant under `factory._impl(repo_root)`; add the meta-test table's samples.
- `[high]` `[patch]` R2 `src/shared/packages/pyforge-doctor/tests/meta/test_bmad_drift_tier3_marshal_shapes.py:126-140, 221-239` the ast scan is near-blind: `_path_join_string` stops at the first non-constant operand, so marshal's usual `root / ... / slug / "implementation-artifacts" / X` is never collected; module constants and the `implementation_artifacts_relpath(...)` f-string tail are not resolved (3 segments found live vs 12 in the prototype); the final assertion `_EXPECTED_MARSHAL_SEGMENTS <= normalized | _table_segment_keys()` always holds. Fix: flatten the Div chain, take the operand after `"implementation-artifacts"`, resolve Names through module-level str assignments, handle the `JoinedStr` tail, assert `_EXPECTED_MARSHAL_SEGMENTS <= normalized` without the union.
- `[high]` `[patch]` R3 same file `:170-184, 238` failures never name `file:line` (AC4, AC6 bullet 4). Fix: collect `(segment, path, lineno)`; put `path:lineno` in the message.
- `[high]` `[patch]` R4 `lint-types` red: F401 unused `pytest` (`:10`), F841 unused `proj` (`:201`) in the meta-test; `ruff format` on `sources/factory.py` (~:394).
- `[medium]` `[patch]` R5 `tests/unit/test_sources_factory.py:1866-1872` the AC3 loop cannot fail (removing the attempted-change row passes everything). Fix: assert each planted file's class is in the TIER3 classes, stray controls excluded.
- `[medium]` `[patch]` R6 meta-test `:242-250` the AC4 fixture test never runs the coverage assertion. Fix: factor scan-and-assert into a helper, run it on the fixture under `pytest.raises` matching `fake_marshal_module.py:1`.
- `[low]` `[patch]` R7 `factory.py:305-375` several `writer` values are prose, not `file::symbol`/skill paths; the attempted-change and worktree-verdicts rows have no writer-token row in the meta-test. Fix: real `file::symbol` values and the two missing rows.
- `[low]` `[patch]` R8 `factory.py:1431-1442` an orphaned sweep-verdicts comment; a stray blank line inside the benchmark comment; the moved rules' incident comments deleted although `classify()`'s docstring calls them load-bearing. Fix: restore them beside the rows.
- `[low]` `[patch]` R9 `factory.py:369`, `scripts/bmad_drift_check.py:135` `bmad-build-auto-result-[a-z0-9-]+` misses the writer's `<slug-or-timestamp>` form (uppercase T/Z, dots; `.claude/skills/bmad-build-auto/workflow.md:32`). Fix: `[A-Za-z0-9._-]+`.
- `[low]` `[patch]` R12 `_bmad-output/projects/pyforge-marshal/SYNC-RUNBOOK.md` the `uncovered` row lost that the script holds only an unused reference copy of `classify()`. Fix: reword.
- `[low]` `[defer]` R10 the plain benchmark row shadows the per-layer row and accepts any suffix; `dispatch-runs-quarantine/.*` accepts any depth (neither hides a stray-suffix file) — optional tightening.
- `[low]` `[defer]` R11 some writer tokens are formatting-fragile or name a reader (`cli/status.py`'s literal token; `dispatch-runs` cited from `layer_savings_sources.py`, writer `core/dispatch.py`).

Send-back: R1-R9 and R12 in one pass; R10/R11 as doctor deferred-work rows; a fresh independent review (iteration 2) gates the landing.

- 2026-10-12 iteration 1 (superseded): the first implementation pass recorded "AC1–AC8 verified locally, no blocking findings" here. The independent review above found that claim did not hold (the AC4/AC5 guards passed vacuously and `lint-types` was red). The current state is the newest fix-pass entry at the top of this log.

## Auto Run Result

Status: in-progress

The independent review sent the story back three times (iteration 1: R1-R12; iteration 2: N1-N6; iteration 3: F1-F4). Fix passes 1 and 2 are committed on `dispatch/pyforge-doctor/43.1` (`c7759791e9`, `9554d68795`); the iteration-3 fix pass is uncommitted at the time of writing. A fresh independent review, iteration 4, gates the landing; this block is refreshed again at landing.

- Change: `sources/factory.py` declares `TIER3_RUN_ARTIFACTS` (pattern, class, writer `file::symbol`), one row per Tier-3 shape marshal or its dispatched session writes. The rows include:
  - `sessions/<id>/…` gate records;
  - a failed attempt's `dispatch-runs/<run>/failed/<story>/changes.patch` (`local:failed-attempt`, writer `core/dispatch_preserve.py::failed_patch_path`);
  - `fleet-drain-runs/campaign.lock`.

  The keep-exemption in `check_archive_hygiene` and in `scripts/bmad_drift_check.py --fix` is derived from the row's class (`TIER3_KEPT_CLASSES`). The script keeps a hand-synced, test-checked reference copy.
- Guards: the doctor meta-test reads marshal with `ast` (never imported), resolving `/` chains, names, and imported or twice-defined helpers. It fails naming `path:lineno` for a segment with no row. Every row's writer must carry its literal(s) inside the cited symbol.
- Deferred: `DW-doctor-43-1-1` (R10) and `DW-doctor-43-1-2` (R11, with N4 and F2 appended) in the doctor deferred-work ledger.
- Follow-up review: required. The iteration-4 independent review has not run.

Verification: `pixi run --frozen -e pyforge-doctor pyforge-doctor-test`; `pixi run --frozen -e pyforge-ci pyforge-doctor-scripts-test`; `pixi run -e pyforge-guild lint-types`; `pixi run -e pyforge-guild spec-surface-check` after memlog reconciles and scoped stamps on `pyforge-doctor/spec-pyforge-doctor` and `pyforge-marshal/spec-pyforge-core` (never a bare global stamp); `bmad-drift-check` and `detectors-ci` with the AC7 Tier-3 tree planted; `deferred-work-check`; `frontmatter-duplicate-keys-check`. Exit codes per pass are in the Review Triage Log's fix-pass entries.
