---
title: "14.1: The actuator resolves the lowest OSV-fixed release the estate's solver accepts"
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
  - src/shared/packages/pyforge-warden/src/pyforge/warden/vuln.py
flag:
  key: pyforge.warden.fix_target_resolution
  provider: openfeature-file
  default: {production: off, staging: on, dev: on}
  scope: global
  fallback: "the upgrade proposal cites the advisory and the current vulnerable version with no target, as today"
  cleanup: 90 days after ON in every environment (Q4)
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** The fix-PR actuator's upgrade proposal is a pointer, not a fix. `actuator.py:21-23` says it "does NOT
compute a target version" and that "precise target resolution + manifest editing are deferred". The OSV data is
already read: `vuln.py::_extract_fixed_version` takes the **first** `ECOSYSTEM`/`SEMVER` `fixed` event of the matching
`affected[]` entry into `EngineResult.fixed_versions`, and `cli.py` threads it to `render_text` only, never to the
actuator. The first event is not the lowest acceptable one, and nothing asks the estate's solver whether a candidate
resolves. The operator ruled on 2026-09-28 that the actuator finishes the fix on the estate's repos.

**Approach:** `vuln.py` surfaces every `fixed` candidate of the matching `affected[]` entry (the same tolerant,
package-matched, `GIT`-range-skipping walk), additive and defaulted on `EngineResult`. `cli.py` threads the candidates
into `run_actuator` with the findings. The actuator keeps the candidates at or above the current version, sorts them
with `packaging.version`, and asks a solver seam, in order, whether the repo solves with that floor; the first that
solves is the target. The default seam runs `pixi lock` in a throwaway copy through `engines.py`'s `_engine_env()`
helper, under a tested pixi version range; it runs only on the real `--open-fix-prs` path. Under `--fix-prs-dry-run`
the seam never runs: the payload names the lowest candidate and `solver: not-run`. The target, the candidates tried and
the solver's verdict ride the open `actuation` object. The flag is read through `pyforge.core.flags.read_boolean` (steward Story 75.1's contract); with it
OFF the proposal is exactly today's.

Ledger key: `14-1-the-actuator-resolves-the-lowest-osv-fixed-release-the-estate-s-solver-accepts`.
Ledger status (do not edit the ledger): `backlog`.
Type / Effort / Deps: feature / M / —.

### Living CAP citations

- `spec-pyforge-warden` CAP-24 (FR-41); CAP-12 (FR-40, the actuator); CAP-11 (no silent egress).
- `spec-feature-flag-governance:CAP-1` (the flag block).

## Acceptance Criteria

- Given an advisory with `fixed` events 1.2.3 and 1.3.0 for a package at 1.2.0, and a fixture solver that refuses 1.2.3, When the actuator plans on the real path, Then the target is 1.3.0 and the payload lists both candidates with the solver's answer for each
- Given the same finding, When the run is `--fix-prs-dry-run`, Then no solver runs, no socket opens (socket-guard green), and the payload names 1.2.3 with `solver: not-run`
- Given a `GIT`-typed range, a `fixed` event below the current version, or an `affected[]` entry for a different package, When candidates are collected, Then none of them is a candidate
- Given no candidate the solver accepts, When the actuator plans, Then the outcome is `failed` with the reason in `actuation`, and the status and exit code equal the same run without `--open-fix-prs`
- Given the flag OFF (a flagd tree with the key's `defaultVariant` off), When the actuator plans, Then the proposal and payload are byte-identical to today's

## Boundaries & Constraints

**Always:**
- Keep the actuator post-verdict: nothing here feeds a rung, the status or the exit code (`test_verdict_sole_ownership.py` stays green).
- Spawn pixi only through `_engine_env()`, only on the real path, with a declared tested version range that fails loud out of range.
- Keep `EngineResult` changes additive and defaulted; keep the `ComplianceReport` at 1.1.0 (`actuation` is an open object).
- Read the flag only through `pyforge.core.flags.read_boolean` (steward Story 75.1's contract) over the one tree (canopy:AD-11). If 75.1 has not landed when this story runs, add it in `pyforge.core` in exactly 75.1's shape (`read_boolean(key, default=False)`, `cutover_root.py`'s tree resolution, False with a named WARN for a missing tree, key or non-bool value; a `spec-pyforge-core` co-governor reconcile) — never a station-local reader or a second tree. Add the key to `src/platform/config/flags.json` (default OFF).
- Add the key to `src/platform/config/flags.json` with the tree default OFF.
- Reconcile `spec-pyforge-warden` and every co-governor `spec-surface-check` names, then stamp each scoped with `--spec`.

**Never:**
- Edit a manifest or open a PR here (Stories 14.2 and 14.3).
- Run the solver under `--fix-prs-dry-run`, or open a socket in the scan's own process.
- Change `Finding` (schema-frozen) or add a finding family.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| lowest accepted | fixed 1.2.3, 1.3.0; solver refuses 1.2.3 | target 1.3.0 | — |
| dry-run | same | lowest candidate 1.2.3, `solver: not-run` | no socket |
| below current | fixed 1.1.0, current 1.2.0 | 1.1.0 dropped | — |
| GIT range | a commit-hash `fixed` | not a candidate | — |
| nothing solves | every candidate refused | `failed` outcome | never a rung |
| pixi out of range | pixi version outside the tested range | `failed` outcome naming the range | never a rung |
| flag OFF | key off in the tree | today's proposal | — |

</intent-contract>

## Binding

Parent Spec capability: `spec-pyforge-warden` CAP-24 (FR-41).
Dream: `docs/dreams/pyforge-warden.md` § Realization log → *2026-09-28 (night) — Proposed: the fix-PR actuator finishes the fix, SAST joins as a plugin, and Warden scans the enterprise fleet*.
Ledger key: `14-1-the-actuator-resolves-the-lowest-osv-fixed-release-the-estate-s-solver-accepts`.
Ledger status at mint: `backlog`.
Deps: —.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-warden pyforge-warden-test` — expected: pass (the station's `verify_commands`).

**Manual checks:**
- Flag ON/OFF: a test writes two flagd trees (`pyforge.warden.fix_target_resolution` with `defaultVariant` on, then off — the `src/platform/tests/test_openfeature_file_flags.py` shape, until the testing-kit fixture of `spec-feature-flag-governance:CAP-4` lands) and runs the actuator under each: ON resolves the target, OFF yields today's proposal byte for byte.
- The socket-guard test passes under `--fix-prs-dry-run` with the flag ON.
- `pixi run -e pyforge-guild spec-surface-check` exits 0 after the scoped stamps.

## Review Triage Log

- No review yet (minted 2026-09-28). Implementation and review stay separate: the reviewer reads the diff against this spec and CAP-24.
