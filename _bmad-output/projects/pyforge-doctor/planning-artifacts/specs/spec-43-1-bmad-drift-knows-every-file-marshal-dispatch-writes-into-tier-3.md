---
title: "43.1: bmad-drift knows every file marshal dispatch writes into Tier-3"
type: 'fix'
created: '2026-10-12'
status: 'in-progress'
baseline_revision: '70975ae790'
review_loop_iteration: 2
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
| `dispatch-runs/`, `runs/`, `fleet-drain-runs/`, `sprint-status*.yaml`, `epic-<N>-context.md`, `worktree-verdicts-<date>.json`, `deferred-work.md`, `spec-*.md`, `retros/` | marshal and the BMAD skills | covered |

**Approach:**
- **One declared list.** `sources/factory.py` gains `TIER3_RUN_ARTIFACTS`, a tuple of `(pattern, classification,
  writer)` rows, one per shape marshal or its dispatched session writes into Tier-3. `writer` names the source file
  and symbol, or the skill file.
  - The existing Tier-3 run rules move into it unchanged, with the same class strings: `runs/`, `dispatch-runs/`,
    `fleet-drain-runs/`, `epic-<N>-context.md`, `sprint-status*.yaml` and `worktree-verdicts-<date>.json`.
  - `classify()` reads the list at the point where those rules sat. The `coverage-summary` buckets for today's files
    do not change.
- **The new rows:**
  - the recall-feedback pair, `local:recall-feedback`;
  - `epic-<N>-continuity.md`, `local:sprint-feed` (the class `epic-<N>-context.md` has);
  - `session-advisories/<run>/…` and `dispatch-runs-quarantine/…`, `local:run-journal`;
  - both benchmark defaults, `local:benchmark`;
  - `bmad-build-auto-result-<slug>.md`, `local:run-result`;
  - the Tier-3-root attempted-change patch, `local:attempted-change`.
- **The patch is kept.** `check_archive_hygiene` does not report the attempted-change patch as a `stray-file`, and
  `scripts/bmad_drift_check.py`'s `do_fix` does not delete it. Every other stray suffix (`.patch`, `.diff`, `.bak`,
  `.orig`, `.tmp`, `.rej`) is reported and removed as today.
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

- 2026-10-12 — Scope confirmed by the operator: asked whether to keep the wider scope (all seven dispatch-written kinds plus the attempted-change patch exemption) or narrow to the recall-feedback pair, the operator answered "keep the wider scope, keep going".

- 2026-10-12: minted from the operator's ask "Do this task here: Teach bmad-drift about dispatch recall-feedback files",
  found on marshal Story 97.2's dispatch worktree.

## Review Triage Log

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

- 2026-10-12 iteration 1: AC1–AC8 verified locally (`pyforge-doctor-test` 3579 passed; `pyforge-doctor-scripts-test` 1475 passed + 21 new tier3 classify tests; AC7 `bmad-drift-check` exit 0 with planted Tier-3 tree; `spec_surface_reconcile.py` and `spec-surface-check` exit 0 after memlogs and scoped stamps on `spec-pyforge-doctor` and `spec-pyforge-core`). No blocking findings.

## Auto Run Result

Status: done

Verification: `pixi run --frozen -e pyforge-doctor pyforge-doctor-test`; `pixi run --frozen -e pyforge-ci pyforge-doctor-scripts-test`; `pixi run -e pyforge-guild bmad-drift-check` with AC7 fixtures; `python scripts/spec_surface_reconcile.py`; scoped `spec_surface_check.py --write-baseline` for `pyforge-doctor/spec-pyforge-doctor` and `pyforge-marshal/spec-pyforge-core` (not a bare global stamp).
