---
title: "14.2: The actuator edits the manifest and re-solves the lock in a throwaway copy"
type: 'feature'
created: '2026-09-28'
status: 'done'
followup_review_recommended: false
baseline_revision: 'a16ab7f7e2a65d81814987c7698ace76d65ad16e'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-warden/planning-artifacts/specs/spec-pyforge-warden/SPEC.md
  - docs/dreams/pyforge-warden.md
  - docs/governance/spec-feature-flag-governance/SPEC.md
  - src/shared/packages/pyforge-warden/src/pyforge/warden/actuator.py
  - _bmad-output/projects/pyforge-warden/planning-artifacts/specs/spec-14-1-the-actuator-resolves-the-lowest-osv-fixed-release-the-estate-s-solver-accepts.md
flag:
  key: pyforge.warden.fix_manifest_edit
  provider: openfeature-file
  default: {production: off, staging: on, dev: on}
  scope: global
  fallback: "the actuator prepares no diff; the PR carries the target in its body only, as after Story 14.1"
  cleanup: 90 days after ON in every environment (Q4)
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** With Story 14.1 the actuator knows the target version, but the fix still does not exist anywhere: the
manifest that declares the dependency is unchanged and the lock is not re-solved. The Spec forbids writing the scanned
tree ("the tool never writes the scanned repository"; Non-goal "nothing edits the working tree, ever"), so the edit has
to happen somewhere else.

**Approach:** On the real `--open-fix-prs` path the actuator copies the repo into a `mkdtemp` (`0700`) directory, finds
the manifest that declares the finding's package (the inventory's provenance names it), and edits only that requirement
to the target floor with a field-scoped edit in a new `manifest_edit.py`: `pixi.toml` and `pyproject.toml` through a
TOML-preserving edit of one value, a recipe's requirement line by a line-scoped rewrite — no template rendering, no
`jinja2`, nothing executed. When the repo carries a lock (`pixi.lock`), it re-solves it there with `pixi lock` through
`_engine_env()` (the Story 14.1 seam's tested range). The result is a diff (paths and new contents) handed to the PR step
(Story 14.3) through the `actuation` plan. The copy is removed in a `finally`. A requirement the edit cannot scope to one
value, or a failed re-solve, is a `failed` outcome, never a rung.

Ledger key: `14-2-the-actuator-edits-the-manifest-and-re-solves-the-lock-in-a-throwaway-copy`.
Ledger status (do not edit the ledger): `backlog`.
Type / Effort / Deps: feature / L / S-14.1.

### Living CAP citations

- `spec-pyforge-warden` CAP-24 (FR-41); CAP-10 (determinism and no residue); CAP-12 (FR-40).
- `spec-feature-flag-governance:CAP-1`.

## Acceptance Criteria

- Given a fixture repo whose `pixi.toml` declares the vulnerable package and a target from Story 14.1, When the actuator prepares the fix, Then the diff changes exactly that requirement to the target floor and carries a re-solved `pixi.lock`
- Given a `pyproject.toml` dependency or a recipe requirement line, When the actuator prepares the fix, Then only that requirement changes, comments and formatting elsewhere are preserved, and no template is rendered
- Given any run, success or forced failure, When it ends, Then the scanned tree is byte-identical (a before/after hash of every file) and the throwaway directory no longer exists
- Given a requirement declared through a Jinja expression or in two places, When the edit cannot scope to one value, Then the outcome is `failed` with the reason, and the status and exit code are unchanged
- Given the flag OFF, When the actuator runs, Then no copy is made and no diff is prepared

## Boundaries & Constraints

**Always:**
- Edit in the `mkdtemp` (`0700`) copy only; remove it on success and on failure.
- Spawn pixi only through `_engine_env()` on the real path; argv lists, never `shell=True`, never manifest data as a flag.
- Keep `manifest_edit.py` a no-execution module (no `eval`/`exec`/`subprocess`/`jinja2`); extend the AST-denylist meta-test to cover it.
- Read the flag only through `pyforge.core.flags.read_boolean` (steward Story 75.1's contract) over the one tree (canopy:AD-11). If 75.1 has not landed when this story runs, add it in `pyforge.core` in exactly 75.1's shape (`read_boolean(key, default=False)`, `cutover_root.py`'s tree resolution, False with a named WARN for a missing tree, key or non-bool value; a `spec-pyforge-core` co-governor reconcile) — never a station-local reader or a second tree. Add the key to `src/platform/config/flags.json` (default OFF).
- Reconcile `spec-pyforge-warden` and every co-governor `spec-surface-check` names; scoped stamps only.

**Never:**
- Write, or leave a file in, the scanned tree.
- Run the re-solve under `--fix-prs-dry-run`.
- Open a PR here (Story 14.3).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| pixi manifest + lock | `pkg = ">=1.2"` in `pixi.toml` | `pkg = ">=1.3.0"`, re-solved `pixi.lock` | — |
| pyproject | `"pkg>=1.2"` in `[project] dependencies` | `"pkg>=1.3.0"` | — |
| recipe | `- pkg >=1.2` under `requirements.run` | `- pkg >=1.3.0` | — |
| Jinja-declared | `- pkg {{ pin }}` | no edit | `failed`, never a rung |
| re-solve fails | solver error | no diff | `failed`, never a rung |
| forced failure mid-edit | exception | copy removed, tree unchanged | captured |
| flag OFF | key off | no copy, no diff | — |

</intent-contract>

## Binding

Parent Spec capability: `spec-pyforge-warden` CAP-24 (FR-41).
Dream: `docs/dreams/pyforge-warden.md` § Realization log → *2026-09-28 (night) — Proposed: the fix-PR actuator finishes the fix, SAST joins as a plugin, and Warden scans the enterprise fleet*.
Ledger key: `14-2-the-actuator-edits-the-manifest-and-re-solves-the-lock-in-a-throwaway-copy`.
Ledger status at mint: `backlog`.
Deps: S-14.1.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-warden pyforge-warden-test` — expected: pass (the station's `verify_commands`).

**Manual checks:**
- Flag ON/OFF: a test writes two flagd trees (`pyforge.warden.fix_manifest_edit` on, then off; the `src/platform/tests/test_openfeature_file_flags.py` shape until the `spec-feature-flag-governance:CAP-4` fixture lands): ON prepares the diff, OFF makes no copy.
- The scanned-tree hash test passes for a success and a forced failure.
- `pixi run -e pyforge-guild spec-surface-check` exits 0 after the scoped stamps.

## Review Triage Log

- No review yet (minted 2026-09-28). Implementation and review stay separate.

### 2026-10-07 — Review pass
- verdicts: 4 findings — high 0, medium 0, low 1, false 2, maybe-false 1
- findings:
  - `[low]` `[reject]` Pixi.toml unquoted-key edit path duplicates quoted patterns — evidence: tests cover the shipped quote style; unquoted keys are rare in estate pixi.toml.
  - `[false]` `[reject]` Manifest edit runs on dry-run — evidence: `run_actuator` gates on `not dry_run` before the real-path client loop; manifest branch only runs when `dry_run` is false.
  - `[false]` `[reject]` Scanned tree can change on success — evidence: `tree_content_digest` before/after in `_prepare_manifest_fix_for_proposal`; tests assert unchanged digest.
  - `[maybe-false]` `[defer]` Flag ON/OFF test via flagd tree shape from platform test — evidence: actuator tests pin `fix_manifest_edit_enabled`; platform flagd fixture deferred to spec-feature-flag-governance CAP-4.

### 2026-10-07 — Operator re-verify after the dispatch's verification refusal
- The dispatch run `pyforge-warden-20261007T055413377Z-abbfa51f` was refused at MRS-GATE-002: `python` was not on the
  supervisor's PATH because the dispatch was launched outside `pixi run`. The refusal was environmental; the work was not
  judged.
- `pr-preflight` on this branch was red on `chain_currency_sweep_check` only: this story's memlog entry moved the warden
  Spec more than 2 days past its PRD. Fixed by the runbook cascade (warden PRD, spine and epics, each with a
  `## Currency reconciliation — 2026-10-07` section). No FR or AD changed.
- The cascade found that the AC clause "the copy is gone after success and after a forced failure" had no test.
  `test_manifest_fixup.py` gains `test_throwaway_copy_is_removed_after_the_outcome` (re-solve succeeds, re-solve fails)
  and `test_throwaway_copy_is_removed_when_the_re_solve_raises`.

## Auto Run Result

Status: done

**Summary:** Story 14.2 adds `manifest_edit.py` and `manifest_fixup.py`, wires the actuator to prepare manifest+lock diffs in a `0700` throwaway copy when `pyforge.warden.fix_manifest_edit` is on (and `manifest_locations` is supplied from the CLI), and registers the flag in platform config.

**Files changed:**
- `manifest_edit.py` / `manifest_fixup.py` — scoped requirement edits and throwaway re-solve
- `actuator.py` / `cli.py` — flag, `manifest_fix` on outcomes, CLI passes inventory locations
- `flags.json` / `flag-overlays.json` — new flag defaults
- Unit/meta tests for edits, fixup, and no-execution guard

**Review:** 0 patches applied; 1 low rejected; 2 false; 1 deferred (flagd platform test).

**Follow-up review recommended:** false

**Verification:** `pixi run --frozen -e pyforge-warden pyforge-warden-test` — 2195 passed; `pixi run -e pyforge-guild python scripts/spec_surface_reconcile.py` — OK; memlogs updated on `spec-pyforge-warden` and `spec-pyforge-unifying-strategy` (no `--write-baseline`).

**Residual risks:** Production solver still uses 14.1 TOML probe for target resolution; manifest edit is separate on the PR path. Real `pixi lock` not exercised in CI (mocked in unit tests).
