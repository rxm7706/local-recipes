---
title: "14.2: The actuator edits the manifest and re-solves the lock in a throwaway copy"
type: 'feature'
created: '2026-09-28'
status: 'backlog'
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
