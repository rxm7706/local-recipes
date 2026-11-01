---
title: "14.4: The default solver shares the manifest edit path and is bounded"
type: 'fix'
created: '2026-11-01'
status: 'backlog'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
context:
  - _bmad-output/projects/pyforge-warden/planning-artifacts/specs/spec-pyforge-warden/SPEC.md
  - _bmad-output/projects/pyforge-warden/planning-artifacts/specs/spec-pyforge-warden/.memlog.md
  - _bmad-output/projects/pyforge-warden/planning-artifacts/research/egm-audit-2026-11-01.md
  - _bmad-output/projects/pyforge-warden/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-warden/planning-artifacts/specs/spec-14-1-the-actuator-resolves-the-lowest-osv-fixed-release-the-estate-s-solver-accepts.md
  - _bmad-output/projects/pyforge-warden/planning-artifacts/specs/spec-14-2-the-actuator-edits-the-manifest-and-re-solves-the-lock-in-a-throwaway-copy.md
  - _bmad-output/projects/pyforge-warden/planning-artifacts/deferred-work-ledger.md
  - src/shared/packages/pyforge-warden/src/pyforge/warden/fix_solver.py
  - src/shared/packages/pyforge-warden/src/pyforge/warden/manifest_edit.py
deferred: []
---

<intent-contract>

## Intent

**Problem:** CAP-24's real `--open-fix-prs` path resolves a target by asking the default pixi-lock solver to accept each
OSV-fixed candidate, and that solver fails on the estate's own manifests and runs unbounded (line numbers at
`03a7aff5d9`):
- `default_pixi_lock_solver` probes through its own two regexes (`_probe_pixi_toml_floor`, `src/shared/packages/pyforge-warden/src/pyforge/warden/fix_solver.py` about
  :152-171), which match only a double-quoted key or a single-quoted bare key. The bare-key form the repo uses,
  `pkg = ">=1.0"`, is never probed, and `pyproject.toml` and recipe dependencies are always rejected. The edit path the
  fix itself takes (`manifest_edit.edit_requirement_to_floor`, through `manifest_fixup.prepare_manifest_fix`) handles
  bare keys, so the two paths disagree (WAR-D-C2).
- `_edit_pixi_toml`'s last pattern (`src/shared/packages/pyforge-warden/src/pyforge/warden/manifest_edit.py` about :49-56) matches `pkg = ">=1.0"  # note` with the quoted
  value as its group and writes the floor back unquoted, which is invalid TOML.
- `resolve_fix_target`'s candidate loop (`fix_solver.py` about :121-131) has no cap and no total budget, each candidate
  copies the whole scanned tree (`.pixi/` and `.git` included, about :176-178), and each `pixi lock` may take
  `PIXI_LOCK_TIMEOUT_SECONDS = 600.0` (`src/shared/packages/pyforge-warden/src/pyforge/warden/engines.py:177`) (WAR-M-D5).
- `PIXI_VERSION_RANGE = SpecifierSet(">=0.80.0,<0.81")` (`engines.py:174`) excludes the installed pixi 0.81.0, so the
  real path refuses on the workspace's own pixi, and nothing ties the range to `pixi.toml`'s `requires-pixi`.
- `DW-warden-14-1` (`_bmad-output/projects/pyforge-warden/planning-artifacts/deferred-work-ledger.md`, about :816) records that the default solver has never run end to
  end; the unit tests inject the seam only (WAR-D-R1).

EGM audit 2026-11-01, cluster WAR-CL-7; findings WAR-D-C2, WAR-D-R1, WAR-M-D5, accepted by the operator on 2026-11-01;
residue `_bmad-output/projects/pyforge-warden/planning-artifacts/research/egm-audit-2026-11-01.md`.

**Approach:**
- The default solver probes a candidate by editing its copy through `manifest_edit.edit_requirement_to_floor`, the one
  edit path `prepare_manifest_fix` uses, so `pixi.toml` bare keys, `pyproject.toml` and recipe requirement lines are all
  probed. `_probe_pixi_toml_floor` goes.
- `_edit_pixi_toml` keeps a quoted value quoted before a trailing comment and preserves the file's final newline, or
  its absence.
- `resolve_fix_target` caps the candidate list and bounds the loop with a total solve budget; an overrun is a `failed`
  actuation outcome. `PIXI_LOCK_TIMEOUT_SECONDS` becomes configurable (the Spec's Resource-bounds constraint). The
  per-candidate `copytree` ignores `.pixi/` and `.git`.
- `PIXI_VERSION_RANGE` is retested and widened to admit the workspace pixi, and tied to `requires-pixi`: an entry in
  `scripts/pixi_version_registry.py`, or a test that reads `pixi.toml`.
- `tests/unit/test_fix_solver_seam.py` gains the bare-key, trailing-comment and last-line-without-newline cases with
  `run_pixi_lock` stubbed, and an opt-in integration test runs the real `pixi lock` on a hermetic fixture repo.
  `DW-warden-14-1` closes.
- A memlog decision on `spec-pyforge-warden` records the shared edit path, the cap, the budget and the configurable
  timeout; CAP-24 success names the bound through a `bmad-spec` re-derive.

Ledger key: `14-4-the-default-solver-shares-the-manifest-edit-path-and-is-bounded`.
Type / Effort / Deps: fix / M / —.

### Living CAP citations

- `spec-pyforge-warden` CAP-24 (FR-41) — the fix-PR actuator finishes the fix on the estate's repos. A `fix`, so no
  new CAP; `spec-feature-flag-governance` Q1: a `fix` needs no flag (the 14.1 and 14.2 flags keep gating the path).

## Acceptance Criteria

- **AC1 — Every declaration form is probed.** Given fixture repos that declare the vulnerable package as a `pixi.toml`
  bare key (`pkg = ">=1.0"`), a quoted key, a `pyproject.toml` dependency and a recipe requirement line, with
  `run_pixi_lock` stubbed to accept, When the default solver probes a candidate, Then each probe edits the copy through
  `edit_requirement_to_floor` and returns `accepted`; no form is rejected for its syntax.
- **AC2 — The edit writes valid TOML.** Given `pkg = ">=1.0"  # pinned` and, separately, a declaration on the file's
  last line with no final newline, When `edit_requirement_to_floor` sets the floor, Then the value stays quoted, the
  comment survives, the final-newline state is unchanged, and `tomllib` parses the result.
- **AC3 — The loop is bounded.** Given more candidates than the cap, or a stubbed solver slower than the total budget,
  When `resolve_fix_target` runs, Then it stops at the cap or the budget and returns a `failed` resolution naming the
  bound; the status and exit code are unchanged.
- **AC4 — The copy is lean.** Given a scan target with `.pixi/` and `.git` directories, When a candidate is probed, Then
  the copy holds neither, and the scanned tree is byte-identical after the run.
- **AC5 — The workspace pixi is in range.** Given the workspace's pixi (0.81.0 at mint), When the real path checks
  `PIXI_VERSION_RANGE`, Then it is admitted; and a test (or a `scripts/pixi_version_registry.py` entry checked by
  `pixi-version-check`) fails when the range and `pixi.toml`'s `requires-pixi` drift apart.
- **AC6 — The real path runs once.** Given an opt-in marker (excluded from the default loop), When the integration test
  runs, Then the real `pixi lock` re-solves a hermetic fixture repo's copy at a candidate floor.
- **AC7 — The records close.** `DW-warden-14-1` carries a `resolution:` naming this story and a `verified:` line citing
  the `path:line` of the new test; a memlog decision records the bound, and CAP-24 success names it through a
  `bmad-spec` re-derive.
- **AC8 — Green.** `pixi run --frozen -e pyforge-warden pyforge-warden-test` passes.

## Boundaries & Constraints

**Always:** one manifest edit path for the probe and the fix; the scanned tree is never written; every failure is a
`failed` actuation outcome, never a rung, a status or an exit code; pixi runs only on the real `--open-fix-prs` path,
through `_engine_env()`.

**Never:** add a second regex set for the probe; run a real `pixi lock` in the default test loop; widen the version
range without a test against the installed pixi; hand-edit `SPEC.md`.

</intent-contract>

## Binding

- Parent capability: `spec-pyforge-warden` CAP-24 (FR-41) — the fix-PR actuator finishes the fix on the estate's repos;
  a fix, no new CAP.

Parent: CAP-24

- EGM audit findings carried: WAR-D-C2, WAR-D-R1, WAR-M-D5 (cluster WAR-CL-7; accepted 2026-11-01; one memlog event
  each on `spec-pyforge-warden/.memlog.md`); residue `_bmad-output/projects/pyforge-warden/planning-artifacts/research/egm-audit-2026-11-01.md`.
- Deferred work: closes `DW-warden-14-1`.
- Epic: Epic 14 — a fix story joins its done epic (operator rule 2026-10-04; doctor Story 41.5 lets the epic key roll up
  to `in-progress`).
- Ledger key: `14-4-the-default-solver-shares-the-manifest-edit-path-and-is-bounded`.
- Ledger status at mint: `backlog`.
- Deps: —.
- Surface: `src/shared/packages/pyforge-warden/src/pyforge/warden/fix_solver.py`, `src/shared/packages/pyforge-warden/src/pyforge/warden/manifest_edit.py`, `src/shared/packages/pyforge-warden/src/pyforge/warden/manifest_fixup.py`, `src/shared/packages/pyforge-warden/src/pyforge/warden/engines.py`,
  `src/shared/packages/pyforge-warden/tests/unit/test_fix_solver_seam.py`, `src/shared/packages/pyforge-warden/tests/unit/test_manifest_edit.py`, `scripts/pixi_version_registry.py`,
  `_bmad-output/projects/pyforge-warden/planning-artifacts/deferred-work-ledger.md`.
- Dream: `docs/dreams/pyforge-warden.md` § *Realization log*, the 2026-11-01 (the EGM fleet audit) entry.
- Minted 2026-11-01 by the EGM audit landing (marshal Story 113.7, spec-pyforge-marshal:CAP-302); mode in-PR: built in the audit's landing PR.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-warden pyforge-warden-test` — expected: pass (the station's `verify_commands`).
- `pixi run --frozen -e pyforge-warden pytest src/shared/packages/pyforge-warden/tests/unit/test_fix_solver_seam.py src/shared/packages/pyforge-warden/tests/unit/test_manifest_edit.py src/shared/packages/pyforge-warden/tests/unit/test_manifest_fixup.py src/shared/packages/pyforge-warden/tests/unit/test_fix_target_resolution.py -q` — expected: pass.
- `pixi run --frozen -e pyforge-guild lint-types` — expected: exit 0.

**Run before the push:**
- The opt-in real-`pixi lock` integration test, by its marker, on a machine with the workspace pixi — expected: pass.
- `pixi run -e pyforge-guild pixi-version-check` when the registry gains an entry — expected: exit 0.

## Auto Run Result

Status: backlog

Summary: not yet dispatched.

## Spec Change Log

- 2026-11-01: minted `backlog` from the EGM fleet audit (marshal Story 113.7): cluster WAR-CL-7, findings WAR-D-C2,
  WAR-D-R1 and WAR-M-D5, accepted by the operator; mode in-PR.

## Review Triage Log

- (none yet)
