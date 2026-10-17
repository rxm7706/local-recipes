---
title: '108.1: `estate reconcile` reds on a failed generator, and a retired CI row is never paused by the master'
type: 'fix'
created: '2026-10-17'
status: 'in-review'
baseline_revision: 'ab38be642f0f3ea30e4c7f76c318e7809beef242'
flag-exempt: detector-or-gate   # a fix needs no flag (spec-feature-flag-governance Q1); both changes sit behind their duties' existing flags (pyforge.steward.estate_refresh, pyforge.steward.ci_pause_control), and each corrects a verdict a gate or a detector reads (reconcile's exit, ci status's paused_by_master), so a flag-OFF path would keep the false green reachable (Q2's gate exemption), as 105.1, 106.1 and 107.1 recorded
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/SPEC.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/epics.md
  - docs/dreams/pyforge-steward.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/deferred-work-ledger.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-100-3-every-derived-surface-regenerates-from-the-lock-by-its-own-generator.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-103-1-steward-ci-status-reports-the-master-switch-and-every-surface-it-pauses.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-103-2-estate-reconcile-writes-the-bmad-suite-floors-from-the-batch-not-the-network.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-103-3-pyforge-ci-is-stdlib-only-as-its-tasks-say.md
  - src/shared/packages/pyforge-steward/src/pyforge/steward/estate_reconcile.py
  - src/shared/packages/pyforge-steward/src/pyforge/steward/ci.py
  - scripts/pixi_env_matrix.py
  - docs/governance/ci-surfaces.yaml
  - docs/governance/ci-surfaces.schema.json
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** two steward reports say less than what happened. Line numbers are at `ab38be642f` (main after #2253).

- **The env-matrix generator never runs (`DW-steward-103-3-2`).** `_build_generators` (`estate_reconcile.py:96`)
  gives the `env-matrix` generator `[python, "scripts/pixi_env_matrix.py", "--update",
  "docs/dreams/pyforge-unifying-strategy.md"]` (`:113`-`:122`). The script takes the Dream only as `--dream`
  (`scripts/pixi_env_matrix.py:156`) and declares no positional, so `parse_args` (`:167`) refuses the call with exit 2,
  "unrecognized arguments", before anything is read or written. The script's own usage docstring (`:13`-`:16`) shows
  the same wrong form, and Story 100.3's spec copied it (its line 51).
- **A failed generator is silent.** `run_reconcile` (`:350`) acts on a generator's exit only for
  `generate-bmad-suite` (`:371`-`:391`, which sets `generator_failed`). Every other generator goes through
  `_run_generator` (`:238`), whose exit the loop drops: the one branch that reads it, `if code != 0 and "bmad-estate"
  in …: pass` (`:394`-`:396`), is a no-op, though Story 100.3's I/O matrix says a failed scribe catalog generator
  "reds naming scribe's command, continues the remaining checks, exit non-zero". `GATING_CHECKS` (`:142`-`:151`) has
  no matrix check, so `ok` depends on the eight checks alone. The failure survives only as an unlabeled
  `{"argv", "exit": 2}` row in the journal's `generators` list (`_record_step`, `estate.py:470`), and the stale matrix
  turns up later as `detectors-ci`'s `bmad-drift` warning `pixi-env-matrix-stale`. Story 103.3's lock change hit it;
  its builder regenerated the matrix by hand. `tests/unit/test_estate_reconcile.py:120` asserts only that some argv
  contains `pixi_env_matrix.py`.
- **A retired row can read paused by the master (`DW-steward-101-1-2`).** `_row_gated_by_master` (`ci.py:500`) returns
  `False` for `kind in ("value", "retired")` or `state == "paused-manually"` (`:501`-`:503`). The registry records
  retirement in `state`; its schema's `kind` enum (`docs/governance/ci-surfaces.schema.json:44`-`:47`) has no
  `retired`, so the kind test never fires. A retired row whose workflow file still exists and reads the master
  therefore carries `paused_by_master: true`, against Story 103.1's contract ("a `value` row, a `retired` row and a
  `paused-manually` row are never gated", its AC2). Its verdict is unaffected: `_is_drift` (`:645`-`:646`) makes it
  `drift`, "retired but … still exists", and `_apply_master_overlay` (`:546`) changes only a `live` verdict. The module
  already has `_is_retired` (`:229`), which the run-list fetch (Story 103.7) uses.

**Measured at `ab38be642f`** (every exit code read directly):

- **The argv.** A scratch copy of the base tree (`git archive`), the steward env's Python, from its root:
  `python scripts/pixi_env_matrix.py --update docs/dreams/pyforge-unifying-strategy.md` exits 2, stderr
  `pixi_env_matrix.py: error: unrecognized arguments: docs/dreams/pyforge-unifying-strategy.md`, and the Dream's
  `sha1sum` is unchanged. In a second scratch tree with only the script, the lock and the Dream, and one comment line
  appended to the lock: `--check --dream <Dream>` exits 1 ("stale relative to pixi.lock"); the reconcile's argv exits
  2 and the check still exits 1 after it; `--update --dream <Dream>` exits 0, rewrites the block's
  `lock-sha256=ea1f95e75f0db54a` to `591070bc6ea1b752`, and the check then exits 0 (scratchpad `b108/argv-probe.txt`).
- **The retired row.** `b108/tools/probe_retired.py`, the real `run_status` over a fixture registry with a retired and
  a `live` row of each of `workflow`, `ci-job` and `ci-step`, every workflow file present and its job reading
  `vars.PAUSE_ALL_CI != 'true'`, the master `true`: the three retired rows read `drift` with `paused_by_master: True`,
  the three live rows `paused` with `True` (scratchpad `b108/probe-retired-base.txt`).
- **On the live registry** both are latent for `ci status`: its six retired rows (`docsite-check`,
  `linter_issue_comment`, `reusable-staged-recipes-linter-selftest`, `reusable-staged-recipes-linter`,
  `staged-recipes-linter` of kind `workflow`, `docsite-check.check` of kind `ci-job`) have no workflow file, so they
  find no job and no gate; marshal Story 101.1 skips `retired` before it reads the field. The live registry's kinds are
  `ci-job`, `ci-step`, `value` and `workflow`. The reconcile defect is live: every reconcile since Story 100.3 skipped
  the matrix.

**Approach:** run the generator as the script expects, red the run on any failed generator after everything else has
run, add the matrix check, and read retirement from `state`.

- **The argv.** `ENV_MATRIX_DREAM = "docs/dreams/pyforge-unifying-strategy.md"`, one constant; the generator runs
  `[python, "scripts/pixi_env_matrix.py", "--update", "--dream", ENV_MATRIX_DREAM]`. The script's usage docstring says
  `--update --dream …` and `--check --dream …`; its interface does not change.
- **Every generator row is labelled, and a failed one reds the run.** `_run_generator` records
  `{"label", "argv", "exit", "seconds"}` (the shape the `generate-bmad-suite` row already has), with `"error":
  "non-zero exit"` when the exit is not 0, and the loop collects each failed label. As a failed gating check does
  today, the run goes on: the remaining generators, every gating and warn check, and the spec-surface reconcile run,
  and the journal is written. Then the duty returns `ok=False` with `exit_code` `EXIT_RECONCILE_CHECKS` (1), its summary
  opening with one line per failed generator, `estate reconcile: generator <label> failed (exit <n>): <command>`, in
  run order, then the existing `estate reconcile: check <name> failed` line when a check failed too, then the summary
  it prints today. With every generator green the summary is what it was.
- **`generate-bmad-suite` keeps its early stop** (Story 103.2: a failed or unreadable report stops before the checks).
  Its summary still opens `estate reconcile: generate-bmad-suite failed (<reason>)`, and a line follows for each
  other generator that failed before it.
- **The matrix check.** `GATING_CHECKS` gains `("pixi-env-matrix-check", _guild_python("scripts/pixi_env_matrix.py",
  "--check", "--dream", ENV_MATRIX_DREAM))`, after `bmad-estate-check`, in the order the generators run. The other eight
  keep their names, argv and order.
- **A retired row is never gated.** `_row_gated_by_master` returns `False` for `kind == "value"`, for
  `_is_retired(row)`, and for `state == "paused-manually"`. The dead `kind == "retired"` test goes.
- **Pinned by a test that runs the script.** `test_estate_reconcile.py` asserts the exact argv, and runs the generator's
  argv (with the check's) as a subprocess from a scratch root that holds a copy of `scripts/pixi_env_matrix.py`, a
  fixture lock and a Dream with the script's insertion anchor, as the production runner runs it from the repository
  root. That needs no bare reconcile and touches no tracked file. The old argv run the same way exits 2. Because the
  test reads `scripts/pixi_env_matrix.py`, steward's `changes` paths in `pyforge-station-tests.yml` gain it (Story 98.1;
  `on.*.paths` already carry `scripts/**`).

**Rejected:**
- **A positional Dream argument in `pixi_env_matrix.py`.** The script's interface is `--dream`, and its other callers
  (Story 63.8's and 103.3's verification lines, `render_markdown`'s regeneration hint) use it; the caller is what is
  wrong.
- **Stop the run at the first failed generator.** Story 100.3's matrix keeps the checks running, and the operator then
  sees every failure in one run. Only `generate-bmad-suite` stops early, and it keeps doing so (Story 103.2).
- **Keep the `kind == "retired"` test beside the state test.** No registry row and no schema value has that kind, so
  the test is dead.
- **Re-run a real `estate reconcile` to prove the argv.** A bare reconcile rewrites the latest tracked journal and
  re-runs that batch's generators (`DW-steward-103-3-1`).

Ledger key: `108-1-estate-reconcile-reds-on-a-failed-generator-and-a-retired-ci-row-is-never-paused-by-the-master`.
Type / Effort / Deps: fix / S / none.

### Living CAP citations

- **Shipped behaviour.** `spec-pyforge-steward` CAP-167 (FR-40): `estate reconcile` regenerates every derived surface
  by its own generator and journals each generator's argv and exit and each check's verdict (Story 100.3), with the
  bmad-suite floors from the batch (Story 103.2). `spec-pyforge-steward` CAP-166 (FR-39): `steward ci status` judges
  every CI surface (Story 99.3) and marks the ones the master switch pauses (Story 103.1). This story makes the first
  run the generator it names and say when one fails, and the second hold 103.1's retired-row rule. It mints no CAP
  and changes no `SPEC.md`.
- **Governance.** `estate_reconcile.py` and `ci.py` are on `spec-pyforge-steward`'s surface and on
  `spec-pyforge-core`'s (every station's `src/`); `scripts/pixi_env_matrix.py` and the two test files on
  `spec-pyforge-steward`'s.
- **No flag.** Under `spec-feature-flag-governance` Q1 a `fix` needs no flag; the frontmatter records
  `flag-exempt: detector-or-gate`. Both duties keep their own flags (`pyforge.steward.estate_refresh`,
  `pyforge.steward.ci_pause_control`).
- **Origin.** `docs/dreams/pyforge-steward.md` Realization log, the 2026-10-17 (reconcile's env matrix never
  regenerates, and a retired row reads paused by the master) entry; `DW-steward-103-3-2`, `DW-steward-101-1-2`.

## Acceptance Criteria

AC1-AC6 run `_build_generators`, `GATING_CHECKS` and the real `run_reconcile` with an injected runner over a tmp
repository (Story 100.3's fixture), except AC2, which runs the script itself as a subprocess in a scratch root. AC7 runs
the real `run_status` with a fake `gh` runner over a fixture registry and workflow tree. No test runs a bare reconcile,
`pixi`, `gh`, `git commit` or the network.

- **AC1 — The argv.** `env-matrix`'s argv is exactly `[sys.executable, "scripts/pixi_env_matrix.py", "--update",
  "--dream", "docs/dreams/pyforge-unifying-strategy.md"]`; the Dream is the module's `ENV_MATRIX_DREAM`, which
  `WATCH_PATHS` holds.
- **AC2 — The script's own parser.** From a scratch root holding a copy of `scripts/pixi_env_matrix.py`, a fixture lock
  and a Dream with the `## Fleet conventions (one vocabulary)` anchor: the generator's argv exits 0 and writes a matrix
  block whose `lock-sha256` is the fixture lock's digest; the check's argv tail (`pixi_env_matrix.py --check --dream
  <Dream>`) exits 1 before the update and 0 after it; the old argv exits 2, says "unrecognized arguments" and leaves
  the Dream byte-identical.
- **AC3 — Labelled rows, unchanged green run.** With every generator green, each journal generator row carries the
  label `_build_generators` gives it, in order, and no `error`; `ok` is true and the summary is the base revision's
  text.
- **AC4 — A failed generator reds the run.** A runner that exits 2 for the `env-matrix` generator: `ok` false,
  `exit_code` 1, the summary's first line `estate reconcile: generator env-matrix failed (exit 2): <its command>`; the
  generators after it ran; every gating and warn check ran and is journaled; the journal on disk carries the failed
  row's `error`. The same holds for the scribe catalog generator (Story 100.3's I/O matrix row). Two failed generators
  are both named, in run order; a failed generator beside a failed check names both, generators first.
- **AC5 — `generate-bmad-suite` stops as before.** When it fails, no check runs, the summary opens
  `estate reconcile: generate-bmad-suite failed (non-zero exit)`, and an earlier failed generator is named after it.
- **AC6 — The matrix check.** `GATING_CHECKS` holds `pixi-env-matrix-check`, run in `pyforge-guild`, with argv
  `scripts/pixi_env_matrix.py --check --dream ENV_MATRIX_DREAM`, right after `bmad-estate-check`; the other eight keep
  their names, argv and order (pinned against the base list); when it exits 1, the run reds naming it.
- **AC7 — A retired row is never gated.** With `PAUSE_ALL_CI` `true`, a retired `workflow`, `ci-job` and `ci-step` row
  whose workflow files exist and whose job (or step) reads the master: each carries `paused_by_master` `false`, verdict
  `drift`, detail `registry row <id> is retired but <workflow> still exists`. The same three rows declared `live`
  carry `paused_by_master` `true` and read `paused` (the control, so the fixture does read the master). The
  checked-in `ci_status_master_on.json` fixture is unchanged.
- **AC8 — Mutation.** Each change below fails a named test, and the Implementation Result records which: the argv back
  to positional; `--dream` and its path dropped; a failed generator not collected; only the first failed generator
  named; the generators stopping at the first failure; the run stopping before the checks at the first failure; the
  label missing from a row; no `error` on a failed row; the check line dropped when a generator also failed; the check
  line before the generator lines; the bmad-suite stop not naming an earlier failure; the matrix check dropped; the
  check's Dream not the generator's; in `ci.py`, the base form (`kind` tested for `retired`) and no retirement test at
  all; and in the workflow, steward's `changes` paths without `scripts/pixi_env_matrix.py`.
- **AC9 — Green, the surface reconciled.** `pixi run --frozen -e pyforge-steward pyforge-steward-test`, the steward
  coverage gate and `pixi run --frozen -e pyforge-guild lint-types` exit 0; each changed governed path gets a
  surface-reconcile entry on the memlog of every Spec that governs it.

## Boundaries & Constraints

**Always:**
- Keep `generate-bmad-suite`'s early stop and report, the existing checks and their order, the warn checks, the exit
  codes and the spec-surface reconcile as they are; the journal changes only additively.
- Keep `ci status`'s envelope, verdicts and schema; no consumer changes.

**Never:**
- Never run a bare `pyforge steward estate reconcile` to test this (`DW-steward-103-3-1`).
- Never change `pixi_env_matrix.py`'s interface, `pixi.toml`, `pixi.lock` or `environment.yaml`.
- Never weaken or delete an existing assertion.

**Residual risk:**
- **A reconcile now reds where it read green.** Any generator that fails today was silent; the first reconcile after
  this lands reds on it by name. That is the point. The env-matrix generator was the only one known to fail.
- **The matrix check is a ninth gating check.** It reds a reconcile whose matrix is stale after the generator, which
  can only happen when the generator wrote somewhere else or failed (and is then named too). It runs in the Guild
  env like the others.
- **`DW-steward-103-3-1` stays open.** A bare reconcile still rewrites the latest journal; this story does not touch
  that.
- **A spec-surface refusal still comes first.** When the memlog append, the `git add`, a scoped stamp or the post-stamp
  `spec-surface-check` fails, `run_reconcile` returns that refusal (exit 3) before it reports a failed generator, as it
  already did before a failed check. The generator's row is then in neither the summary nor the journal. Unchanged
  here: the refusal is the more urgent stop, and both paths keep their order.
- **`docs/how-to/refresh-the-estate.md` does not say what a failed generator does.** Its reconcile section lists the
  generators and "gating checks (… , …)", which stays true; the page is `spec-pyforge-doctor`'s, and its `verified:`
  date already predates Story 103.2's change to `estate_reconcile.py` (doctor's `docs-currency-authored-stale`
  warning, advisory). Left as is.

## I/O & Edge-Case Matrix

| Situation | Before (`ab38be642f`) | After |
|---|---|---|
| reconcile runs the `env-matrix` generator | exit 2, "unrecognized arguments", nothing written; the run reads green | `--update --dream <Dream>`: exit 0, the matrix regenerated |
| a generator other than `generate-bmad-suite` exits non-zero | unlabeled `{"argv", "exit"}` row; `ok` from the checks alone | labelled row with `error`; the rest runs; `ok` false, exit 1, the generator named with its exit and command |
| the scribe catalog generator exits non-zero | silent (`pass`) | as above (Story 100.3's matrix row) |
| two generators fail | both silent | both named, in run order |
| a generator and a check fail | `check <name> failed` | the generator line(s), then the check line |
| `generate-bmad-suite` fails | stops before the checks, named | the same, plus any earlier failed generator |
| every generator green | the run as it was | the same summary and exit; one more check row (`pixi-env-matrix-check`) |
| the matrix is stale after the generators | no check | `pixi-env-matrix-check` exits 1; the run reds naming it |
| `ci status`, master `true`, a retired row whose workflow exists and reads the master | `drift`, `paused_by_master: true` | `drift`, `paused_by_master: false` |
| `ci status`, master `true`, a live gated row | `paused`, `true` | unchanged |
| the live registry (six retired rows, no workflow files) | `paused_by_master: false` | unchanged |

</intent-contract>

## Binding

- Parent Spec capabilities: fixes under `spec-pyforge-steward` CAP-167 (`estate reconcile`) and CAP-166
  (`steward ci status`). No CAP is minted, and no `SPEC.md` text changes.
- Dream: `docs/dreams/pyforge-steward.md` § *Realization log*, the 2026-10-17 (reconcile's env matrix never
  regenerates, and a retired row reads paused by the master) entry.
- Epic: Epic 108 (new), Story 108.1; `epic-108` and `epic-108-retrospective` are minted with it. A new epic because
  Epic 103, the last epic of CAP-166 and CAP-167 fixes, is `done`.
- Ledger key: `108-1-estate-reconcile-reds-on-a-failed-generator-and-a-retired-ci-row-is-never-paused-by-the-master`.
- Ledger status at mint: `backlog`, as 107.1's was while it was in review; `done` in the landing merge, with `epic-108`
  rolled up to `done`.
- Deps: none.
- Closes: `DW-steward-103-3-2`, `DW-steward-101-1-2` (`status: closed` on this branch, each with a `closed:` line citing
  this story and its tests).
- Surface: `marshal-policy.toml` `[epic_surfaces]."108"`.
- Flag: none — a fix (`spec-feature-flag-governance` Q1); `flag-exempt: detector-or-gate` recorded above.
- PRD and spine: re-stamped 2026-10-17, each with a `## Currency reconciliation — 2026-10-17` section and no FR or AD
  change. This story's decision and mint entries moved the Spec's memlog past the PRD's 2026-10-14 stamp, which
  `chain-currency-sweep-check` reds after its 2-day grace (`feeds spec→prd`, then `prd→arch`).

## Epic excerpt

Story 108.1 in `epics.md` § Epic 108: `estate reconcile` reds on a failed generator, and a retired CI row is never
paused by the master.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — expected: pass (the station's `verify_commands`;
  MRS-GATE-010 binding).

**Run before the push (not dispatch gates):**
- `pixi run --frozen -e pyforge-steward python -m pytest -q src/shared/packages/pyforge-steward/tests/unit/test_estate_reconcile.py src/shared/packages/pyforge-steward/tests/unit/test_ci_status.py` — expected: exit 0 (AC1-AC7).
- The AC8 mutations, one at a time on a scratch copy (never the worktree), re-running the two files — expected: each
  fails its named tests; the copy restored after each.
- `python scripts/pixi_env_matrix.py --update --dream docs/dreams/pyforge-unifying-strategy.md` in a scratch copy with
  a moved lock, then `--check --dream …` — expected: exit 0 each; the old argv exit 2.
- `pixi run --frozen -e pyforge-guild python scripts/pixi_env_matrix.py --check --dream docs/dreams/pyforge-unifying-strategy.md` in the worktree — expected: exit 0 (the live matrix is current; the check this story adds to reconcile).
- `pixi run --frozen -e pyforge-guild lint-types` — expected: exit 0.
- The steward coverage gate, `COVERAGE_GATES_STATIONS=steward pixi run --frozen -e pyforge-steward python scripts/coverage_gates_ci.py --paths-file <changed paths> --suites unit` — expected: exit 0.
- `pixi run --frozen -e pyforge-guild python scripts/ci_surface_gates.py --check` — expected: exit 0.
- `pixi run -e pyforge-guild spec-surface-check` — expected: exit 0 after the memlog entries and one scoped stamp per
  Spec (AC9).

## Spec Change Log

- 2026-10-17: minted from the Dream's 2026-10-17 entry and the two DW rows, on the orchestrating session's brief.
  `type: fix`, no flag, no CAP; bound to `spec-pyforge-steward` CAP-167 and CAP-166. Measured first: the argv in a
  scratch copy (old exit 2, new exit 0 with the check green after it) and the retired row through the real
  `run_status`. Status `in-progress` for a hand implementation on branch
  `chain-steward-108-1-reconcile-and-master-retired-2026-10-17`.
- 2026-10-17 (implementation): hand-implemented on the same branch, staged for the orchestrator to commit. The
  first trigger-map run named five script paths the AC6 base-list literal spelled out; the test now builds those argv
  strings with a join, since it never reads them. Story 108.1's memlog entries moved the Spec past the PRD's
  2026-10-14 stamp, so the PRD and the spine were re-stamped with `## Currency reconciliation — 2026-10-17` sections
  (no FR or AD change), and a memlog correction records it against the mint entry's "no PRD or spine change".
  Status `in-review`.

## Implementation Result

Hand-implemented on branch `chain-steward-108-1-reconcile-and-master-retired-2026-10-17`, from baseline `ab38be642f`.
The diff is for an independent review against this spec, not against this summary.

- **`estate_reconcile.py`:** `ENV_MATRIX_DREAM` (also the `WATCH_PATHS` entry); the `env-matrix` argv passes
  `--update --dream ENV_MATRIX_DREAM`; `GATING_CHECKS` gains `pixi-env-matrix-check` after `bmad-estate-check`;
  `_run_generator` takes the label and records `{"label", "argv", "exit", "seconds"}` plus `"error": "non-zero exit"`
  on a failure (it no longer calls `estate._record_step`, whose import goes); `_generator_failure_lines` builds one line
  per failed generator; `run_reconcile` collects the failed rows, names them after `generate-bmad-suite`'s own line
  when that one stops the run, and otherwise reds the run after the checks and the spec-surface reconcile, the
  generator lines first, then the existing check line. The `pass` branch is gone.
- **`ci.py`:** `_row_gated_by_master` tests `_is_retired(row)` in place of `kind == "retired"`, with a docstring.
- **`scripts/pixi_env_matrix.py`:** the two usage lines of the module docstring (also the `--help` description).
- **Tests:** `tests/unit/test_estate_reconcile.py` (`test_ac1_generators_order_and_conditional` asserts the exact argv;
  14 new `test_108_1_*` cases, AC1-AC6); `tests/unit/test_ci_status.py` (3 new cases, AC7).
- **Workflow:** `pyforge-station-tests.yml`'s `steward_paths` gains `scripts/pixi_env_matrix.py`, which the AC2 test
  copies; `on.*.paths` already carry `scripts/**`. The trigger map's first run after the new tests also named five
  script paths the AC6 base-list literal spelled out; the test builds those argv strings with a join, as
  `test_docs_map_is_a_watched_path` does, because it never reads them.
- **Against the base.** The two test files run with `ab38be642f`'s `pyforge.steward` on `PYTHONPATH`:
  `test_ci_status.py` 3 failed (the three AC7 cases, each on `paused_by_master` `True`), 32 passed;
  `test_estate_reconcile.py` stops at collection (`ENV_MATRIX_DREAM` does not exist there). The green-run and
  failed-check summaries of Story 100.3's fixture (scratchpad `b108/tools/probe_green_summary.py`) are byte-identical
  at the base and after (`diff` exit 0).
- **AC8, each mutation on a scratch copy of the staged tree (`git write-tree` then `git archive`), the copy restored and
  byte-compared after each** (scratchpad `b108/tools/mutate.py`, `b108/mutations.txt`): the control passed 64 (the two
  files and the trigger map's read-to-trigger test) before and after.

  | Mutation | Failed |
  |---|---|
  | M1 the argv positional again | 3: AC1, AC2, `test_ac1_generators_order_and_conditional` |
  | M2 `--dream` and its path dropped | 2: AC1, `test_ac1_generators_order_and_conditional` |
  | M3 a failed generator not collected | 8: the six AC4 cases, the two-failures test, AC5 |
  | M4 only the first failed generator named | 1: the two-failures test |
  | M5a the generators stop at the first failure | 7: five AC4 cases (not `docs-pixi-tasks`, the last), the two-failures test, AC5 |
  | M5b the run stops before the checks at the first failure | 7: the six AC4 cases, the two-failures test |
  | M6 the label missing from a row | 9: AC3, the six AC4 cases, the two-failures test, AC5 |
  | M7 the check line dropped when a generator also failed | 1: the two-failures test |
  | M8 the bmad-suite stop names no earlier failure | 1: AC5 |
  | M9 the matrix check dropped | 3: AC2, both AC6 tests |
  | M10 the check's Dream not the generator's | 2: AC2, the AC6 order test |
  | M11 no `error` on a failed row | 6: the six AC4 cases |
  | M12 the check line before the generator lines | 1: the two-failures test |
  | C1 `ci.py`: the base form (`kind` tested for `retired`) | 3: the three AC7 cases |
  | C2 `ci.py`: no retirement test at all | 3: the three AC7 cases |
  | W1 the workflow without `scripts/pixi_env_matrix.py` | 1: `test_every_read_and_declared_glob_fires_its_job` |

  The trigger map's `test_every_declared_glob_has_a_tracked_representative` was left out of the scratch runs: the
  scratch copy's index comes from `git init` and `git add -A`, which honours `.gitignore`'s `.cursor/` rule, so the
  `.cursor/**` files the real index force-tracks are missing there and the test fails for that reason alone; it passes
  in the worktree.

## Verification run (2026-10-17, before the review)

On the 16-core host, at the branch's staged tree (base `ab38be642f` plus this story); every exit code read directly,
never through a pipe.

- The two changed test files, `pixi run --frozen -e pyforge-steward python -m pytest -q` on them: exit 0, 63 passed
  (28 in `test_estate_reconcile.py`, 35 in `test_ci_status.py`; 14 and 3 of them `test_108_1_*`).
- `test_station_tests_trigger_map.py` with the two files: exit 0, 108 passed.
- The AC8 mutations (Implementation Result): each of the 16 failed its named tests; the scratch copy passed 64 before
  and after.
- The argv in a scratch copy of the base with the lock moved (`b108/argv-probe.txt`): the old argv exit 2 and
  `--check --dream` exit 1 after it; `--update --dream` exit 0 and the check exit 0 after it. The retired-row probe on
  the staged code (`b108/probe-retired-after.txt`): the three retired rows `drift` with `paused_by_master: False`, the
  three live rows `paused` with `True`.
- `pixi run --frozen -e pyforge-guild python scripts/pixi_env_matrix.py --check --dream docs/dreams/pyforge-unifying-strategy.md`
  in the worktree: exit 0 (the live matrix is current).
- `pixi run --frozen -e pyforge-steward pyforge-steward-test`: exit 0, 2899 passed, 2 skipped, 1 warning, in 420 s
  (run last, after the stamps).
- The steward coverage gate, `COVERAGE_GATES_STATIONS=steward pixi run --frozen -e pyforge-steward python
  scripts/coverage_gates_ci.py --paths-file <the staged paths> --suites unit`: exit 0; `estate_reconcile.py` 91%,
  `ci.py` 87% (floor 80%).
- `pixi run --frozen -e pyforge-guild lint-types`: exit 0.
- Planning detectors, each `pixi run --frozen -e pyforge-guild <task>` on the staged tree: chain-completeness,
  dream-chain, dreams-hygiene (warnings only, the same 121 as at the base), deferred-work, ledger-regression,
  story-status, flag-gate, chain-currency-sweep (exit 1 before the PRD and spine re-stamp, `feeds spec→prd`; exit 0
  after), tea-playwright-check, ad-citation, frontmatter-duplicate-keys, governance-currency and llms-full-check, each
  exit 0; `python scripts/ci_surface_gates.py --check` exit 0. `bmad_tea_playwright.py --project pyforge-steward`
  exit 0 (388 stories, 140 test files).
- `sprint-ledger-sync -- --project steward` from a worktree-local feed seeded from the tracked twin: exit 0, `wrote
  steward (604)`; `story-status-check` exit 0 after it.
- `spec-surface-check`: exit 0, last, after the memlog entries on `spec-pyforge-steward` and `spec-pyforge-core` (the
  two Specs whose surfaces hold the changed paths) and one scoped stamp each; the baseline moves only those Specs'
  memlog hashes and the five changed paths. `pixi run --frozen -e pyforge-guild detectors-ci`: exit 0, 49 detectors
  pass.
- `pixi run --frozen -e pyforge-guild python -m pytest -q tests/scripts/test_pixi_env_matrix.py`: exit 0, 3 passed
  (the script's own tests; it changes only in its docstring). `pixi run --frozen -e pyforge-core pyforge-core-test`
  (its meta tests scan every station's `src/`): exit 0, 2484 passed, 1 skipped.
- Not run here: the full `pr-preflight` (left to the orchestrator before the push), and the station suites other than
  steward's and core's; no other station's tests read a changed line.
