---
title: '62.1: The kill switch writes the flag tree whole and reports its reason'
type: 'fix'
created: '2026-11-25'
status: 'in-review'
story: 62-1-the-kill-switch-writes-the-flag-tree-whole-and-reports-its-reason
spec: spec-pyforge-doctor
difficulty: 'easy'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
surface:
  - 'src/shared/packages/pyforge-doctor/src/pyforge/doctor/actuators/flag_kill_switch.py'
  - 'src/shared/packages/pyforge-doctor/src/pyforge/doctor/__main__.py'
  - 'src/shared/packages/pyforge-doctor/tests/unit/test_flag_kill_switch.py'
  - 'src/shared/packages/pyforge-doctor/tests/unit/test_live_flag_kill_switch.py'
  - 'src/shared/packages/pyforge-doctor/tests/meta/test_read_only_guard.py'
  - '_bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-pyforge-doctor/contract.md'
context:
  - _bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-pyforge-doctor/SPEC.md
  - _bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-pyforge-doctor/contract.md
  - _bmad-output/projects/pyforge-doctor/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-doctor/planning-artifacts/deferred-work-ledger.md
  - docs/dreams/pyforge-doctor.md
  - src/shared/packages/pyforge-core/src/pyforge/core/atomic_write.py
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** `DW-doctor-61-1-2` reports two defects in `doctor flags kill-switch`, both reviewer-reported and not re-traced. `disable_flag` (`actuators/flag_kill_switch.py`) rewrites `flags.json` with `Path.write_text`, which truncates the file before writing it, so a reader that opens the tree during the write can see a partial file and fall back to the flag's default, which for a kill switch is on. And the operator's `--reason` is recorded only as a label on `pyforge_doctor_flag_kill_switch_total`, an in-process counter in a command that exits before anything scrapes it; the result line the command prints names the flag, the path and the state change, not the reason.

**Approach:** Reproduce each defect against the tree first, with a test that fails at the story's baseline. Then write the tree through `pyforge.core.atomic_write` (`atomic_write_text`, passing the existing file's own mode so the replacement keeps it), and add the reason to the result line `_run_flags` prints, on one line whatever the reason holds, so the operator's terminal or the job log carries it after the process is gone. The replace lands on the tree's resolved path, so a symlinked tree stays a symlink and the file its readers open is the one replaced. Replacing needs a new file in the tree's directory, which the in-place write did not: where the process cannot create one, the command is a named refusal at exit 2 with the tree byte-identical, not an internal error. The `--reason` help text and the station's `contract.md` say where the reason goes, and `contract.md` § Bridges and import closure gains the row for `pyforge.core.atomic_write`. The counter stays as CAP-96 states it. The read-only guard's non-vacuous proof (`test_flag_kill_switch_itself_writes_somewhere`) counts the kernel's atomic write as a write call site, in the exempt module and in every other. A defect the tree does not reproduce is not fixed: it is recorded here and in the row as not a defect, with the command that showed it.

Ledger key: `62-1-the-kill-switch-writes-the-flag-tree-whole-and-reports-its-reason`.

### Living CAP citations

- spec-pyforge-doctor CAP-96 (realized, no text change); no AD moves.

## Boundaries & Constraints

**Always:**
- Reproduce a defect before fixing it, and record the reproducing command and its exit code in the Spec Change Log.
- Read every verdict from its exit code, never through a pipe.
- Keep an unknown key at exit 2 with the file byte-identical.
- Replace the tree at its resolved path, so a symlinked tree stays a symlink and its target is the file written.
- Print the result on one line: a whitespace run in the reason, a newline included, folds to one space.
- Refuse by name at exit 2 (`doctor flags kill-switch: cannot replace <path>: <error>`), the tree byte-identical, when the tree's directory cannot take the replacement.
- Keep `contract.md` true by hand where this story moves it: the `pyforge.core.atomic_write` row and the module count of § Bridges and import closure, and the `--reason` and verb rows (`contract.md` is a Spec companion, edited by hand; lead's ruling of 2026-11-25).
- Close `DW-doctor-61-1-2` with the commit that resolves it.

**Never:**
- Never add a second file the actuator writes (a journal, a textfile metric): the flag tree is its one write under CAP-96 and NFR-1, and a third sanctioned write is a Spec change this story does not carry.
- Never add an environment variable, a flag, an option or an exit code, and never remove the counter. The named refusal is exit 2, the code `contract.md` already gives a refused actuator.
- Never hand-edit a `SPEC.md`, a generated page or `sprint-status-ledger.yaml`.

## Acceptance Criteria

**Given** `disable_flag` writes `flags.json` with `Path.write_text`, which truncates the file before it writes, and `record_kill_switch_metric` increments a counter that no scrape reads before the one-shot command exits
**When** each of the two defects of `DW-doctor-61-1-2` is first reproduced against the tree, and then the tree is written through `pyforge.core.atomic_write` with the file's own mode kept, and the command's result line names the reason
**Then** a failure during the write leaves `flags.json` byte-identical and no temporary file beside it, a symlinked tree is still a symlink and its target reads DISABLED, a tree whose directory the process cannot write is a named refusal at exit 2 with the file byte-identical, the one result line of a successful run carries the flag, the path, the state change and the reason, and the read-only guard still proves the actuator module writes and still fails when a third module does
**And** a defect the tree does not reproduce is recorded as not a defect in the story spec and in the row, and `DW-doctor-61-1-2` reads resolved in doctor's ledger with the commit that closed it

- **AC1 — The tree is replaced in one step (defect 1, the non-atomic write).** The test makes the write fail part-way and asserts `flags.json` is byte-identical and its directory holds no other file, and asserts the file's mode is unchanged after a successful run; it fails at the story's baseline. Expected: exit 0. If the baseline does not reproduce the defect, this AC is met by the Spec Change Log entry that records it as not a defect.

  ```bash
  pixi run --frozen -e pyforge-doctor pytest "src/shared/packages/pyforge-doctor/tests/unit/test_flag_kill_switch.py::test_disable_flag_replaces_the_tree_in_one_step" -q
  ```

- **AC2 — The reason is on the result line (defect 2, the lost metric).** The test runs `main(["flags", "kill-switch", "--flag", ..., "--reason", ..., "--flags-path", ...])` on its own tree and asserts exit 0 and that stdout carries the reason beside the flag, the path and the state change; it fails at the story's baseline. Expected: exit 0. If the baseline does not reproduce the defect, this AC is met by the Spec Change Log entry that records it as not a defect.

  ```bash
  pixi run --frozen -e pyforge-doctor pytest "src/shared/packages/pyforge-doctor/tests/unit/test_flag_kill_switch.py::test_kill_switch_result_line_names_the_reason" -q
  ```

- **AC2a — The review's three cases hold.** A symlinked tree is written through (the link stays a link, its target reads DISABLED with its mode kept); a reason with a newline, a tab and a carriage return prints as one line; a tree in a directory the process cannot write exits 2 with `doctor flags kill-switch: cannot replace <path>` on stderr, no traceback, and the file byte-identical. Each failed on the first implementation. Expected: exit 0.

  ```bash
  pixi run --frozen -e pyforge-doctor pytest "src/shared/packages/pyforge-doctor/tests/unit/test_flag_kill_switch.py::test_disable_flag_writes_through_a_symlinked_tree" "src/shared/packages/pyforge-doctor/tests/unit/test_flag_kill_switch.py::test_kill_switch_prints_a_multi_line_reason_on_one_line" "src/shared/packages/pyforge-doctor/tests/unit/test_flag_kill_switch.py::test_kill_switch_refuses_a_tree_in_a_directory_it_cannot_write" -q
  ```

- **AC3 — CAP-96's own success check holds, and the contract names the new kernel import.** Expected: exit 0.

  ```bash
  pixi run --frozen -e pyforge-doctor pytest src/shared/packages/pyforge-doctor/tests/unit/test_flag_kill_switch.py src/shared/packages/pyforge-doctor/tests/meta/test_read_only_guard.py src/shared/packages/pyforge-doctor/tests/meta/test_public_contract.py -q
  ```

- **AC4 — Both doctor lanes pass.** Expected: exit 0.

  ```bash
  pixi run --frozen -e pyforge-doctor pyforge-doctor-test && pixi run --frozen -e pyforge-doctor pyforge-doctor-live-test
  ```

</intent-contract>

## Binding

- Capabilities: spec-pyforge-doctor CAP-96 (realized, no text change); no AD moves.
- Dream: `docs/dreams/pyforge-doctor.md`, the 2026-11-25 entry (the kill switch writes the flag tree whole); operator ruling of 2026-11-25.
- Epic: Epic 62, minted with this story.
- Ledger key: `62-1-the-kill-switch-writes-the-flag-tree-whole-and-reports-its-reason`.
- Surface: `marshal-policy.toml` `[epic_surfaces]."62"`.
- Deferred work: closes `DW-doctor-61-1-2`.

## Verification

**Commands:** the Acceptance Criteria above, each read from its exit code.

## Spec Change Log

- 2026-11-25: minted from the station Dream's 2026-11-25 entry and the operator's ruling of the same date.
- 2026-11-25: defect 1: reproduced and fixed - `pixi run --frozen -e pyforge-doctor pytest "src/shared/packages/pyforge-doctor/tests/unit/test_flag_kill_switch.py::test_disable_flag_replaces_the_tree_in_one_step" -q` exited 1 on the unchanged tree (`Path.write_text` failing part-way left `flags.json` truncated); `disable_flag` now replaces the tree through `pyforge.core.atomic_write.atomic_write_text` with the file's own mode, and the test exits 0.
- 2026-11-25: defect 2: reproduced and fixed - `pixi run --frozen -e pyforge-doctor pytest "src/shared/packages/pyforge-doctor/tests/unit/test_flag_kill_switch.py::test_kill_switch_result_line_names_the_reason" -q` exited 1 on the unchanged tree (stdout was `disabled <flag> in <path> (ENABLED -> DISABLED)`, no reason); the result line now ends `; reason: <reason>`, and the test exits 0.
- 2026-11-25: review of the first implementation, lead's rulings applied. Each case below exited 1 before its fix (the three AC2a tests, 3 failed) and exits 0 after: the replace lands on the resolved path, so a symlinked tree is written through instead of being swapped for a regular file while its target stayed ENABLED; the reason is printed on one line (whitespace runs fold to one space); an `OSError` from the replace (a directory the process cannot write) is the named refusal `doctor flags kill-switch: cannot replace <path>: <error>` at exit 2 with the tree byte-identical, where it was the last-resort net's internal error. The `--reason` and verb help texts name the result line. `contract.md` moved by hand under the lead's ruling, which retires this story's "never hand-edit `contract.md`": the `pyforge.core.atomic_write` row and "Nine `pyforge.core` modules" in § Bridges and import closure, and the `--reason` and `doctor flags kill-switch` rows; `contract.md` joined the surface. No environment variable, flag, option, exit code or verb was added.
- 2026-11-25: the story is implemented and in review. Not this story's to write, left with the lead: the row's closure in the deferred-work ledger, the ledger key, the memlog and spec-surface stamp for `contract.md`, and the epics and Dream wording.
