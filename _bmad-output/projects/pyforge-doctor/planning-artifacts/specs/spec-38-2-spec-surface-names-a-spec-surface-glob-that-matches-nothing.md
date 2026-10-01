---
title: "38.2: `spec-surface` names a Spec surface glob that matches nothing"
type: 'feature'
created: '2026-10-01'
status: 'in-review'
baseline_revision: '5b6a82b4c7a038dbcef39d8592bb08d20719e8d1'
warnings: [oversized]
review_loop_iteration: 0
followup_review_recommended: false
flag-exempt: detector-or-gate   # a gated gate reports a silent green (spec-feature-flag-governance Q2)
context:
  - _bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-pyforge-doctor/SPEC.md
  - docs/dreams/pyforge-doctor.md
  - src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/chain.py
  - _bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-pyforge-doctor/SPEC.md
  - scripts/spec_surface_allowlist.txt
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** `spec-surface` (`sources/chain.py::_check_spec_surface`, in `detectors-ci`) reports an allowlist entry that matches no
tracked file (`stale-allowlist`) but not a Spec `surface:` glob that matches nothing, so a retired or misspelt glob stops
governing anything without a word: the asymmetry `spec-regenerable-factory`'s memlog and doctor Story 6.9 recorded. On
2026-10-01, 25 such globs sat in 7 Specs while the check reported ok (DW-OPS-2026-10-01-2).

**Approach:**

- For every Spec whose surface was read, each `surface:` glob that matches no tracked file is one `stale-surface` WARN
  naming the Spec and the glob, beside the existing `stale-allowlist` rows. A WARN never changes the exit code, so the 25
  known globs do not red the gate; fixing them is the owning Specs' work.
- A Spec whose surface could not be read is not judged (the existing unevaluable path holds).

Ledger key: `38-2-spec-surface-names-a-spec-surface-glob-that-matches-nothing`.
Ledger status (do not edit the ledger): `backlog`.
Type / Effort / Deps: feature / S / S-38.1.

### Living CAP citations

- CAP-88 (FR-21; extends `spec-regenerable-factory` CAP-2). `type: feature`, `flag-exempt: detector-or-gate`
  (`spec-feature-flag-governance` Q2).

## Acceptance Criteria

- Given a Spec with one matching and one dead glob When `spec-surface` runs Then exactly one `stale-surface` WARN names that Spec and glob
- Given a trailing-slash directory glob and a brace glob When the check runs Then each is judged by what it actually matches
- Given a Spec whose surface cannot be read When the check runs Then no `stale-surface` row is reported for it
- Given `main` When `pixi run -e pyforge-guild spec-surface-check` runs Then it lists the dead globs and exits 0
- Given the new rule is removed When the new tests run Then they fail (mutation)

## Tasks

1. Read `_check_spec_surface` and `_parse_surface` in `sources/chain.py`, and how `stale-allowlist` is built.
2. Count matches per surface glob for every readable Spec; add `stale-surface` WARN rows.
3. Tests for each matrix row; run `spec-surface-check` on `main` and record the count in the triage log.

## Boundaries & Constraints

**Always:**
- The finding is a WARN.
- Read every verdict from the exit code, never through a pipe.

**Never:**
- Do not change any Spec's `surface:` list here.
- Do not change the existing drift, coverage or `stale-allowlist` findings.
- Do not hand-edit any `SPEC.md`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| live glob | matches tracked files | no row | — |
| dead glob | matches nothing | `stale-surface` WARN | exit code unchanged |
| unreadable surface | surface parse failed | no `stale-surface` row | existing unevaluable WARN |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/chain.py` -- `_collect_surfaces` (l.2096) fills `specs[name]` with `globs` and a parallel compiled `res`; a Spec whose SPEC.md fails to parse never enters `specs`, so it is never judged. `_check_spec_surface` (l.2191) returns `(findings, presumed)`; `gather_spec_surface` emits `presumed` as WARN rows and still emits the OK verdict when `findings` is empty. `_glob_to_re` (l.1663) is the one governing matcher: no brace expansion, a trailing `/` matches no file.
- `src/shared/packages/pyforge-doctor/tests/unit/test_sources_chain_spec_surface.py` -- real tmp-git-repo fixtures (`_write_spec`, `_write_allowlist`, `_add_commit`); `test_stale_allowlist_entry_reports_fail` (l.169) is the sibling to mirror.
- `pixi.toml` l.1357 -- `spec-surface-check` runs `python -m pyforge.doctor.sources spec-surface`, so AC 4 exercises this code. `scripts/spec_surface_check.py` is the mutation-only baseline script: out of scope.

## Tasks & Acceptance

**Execution:**
- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/chain.py` -- add `_stale_surface_findings(specs, files)`: per readable Spec, each distinct glob whose compiled regex matches no tracked file is one `stale-surface` item naming Spec and glob; call it from `_check_spec_surface` and append to `presumed` -- non-gating WARN, the OK verdict and every existing finding stay unchanged.
- `src/shared/packages/pyforge-doctor/tests/unit/test_sources_chain_spec_surface.py` -- one test per matrix row and AC row (live and dead glob; trailing-slash and brace globs; unreadable SPEC.md; OK verdict kept); confirm they fail with the call removed.

**Acceptance Criteria:**
- Given the `## Acceptance Criteria` in the contract above, when the station suite and `spec-surface-check` run, then each holds and `spec-surface-check` exits 0 (read from `$?`, never a pipe).

## Spec Change Log

## Design Notes

A glob is dead exactly when `_glob_to_re` rejects every tracked path: the same regex governance uses, so the WARN never disagrees with what a Spec actually governs. A trailing-slash or brace glob therefore reports dead (it governs nothing); judging it live by directory-existence or brace expansion would be a lie.

`presumed`, not `findings`: a WARN in `findings` makes `gather_spec_surface` drop the OK row, changing an existing finding.

## Binding

Parent capability: CAP-88 (FR-21). DW-OPS-2026-10-01-2.
Dream: `docs/dreams/pyforge-doctor.md` § *Realization log*, the 2026-10-01 entry.
Ledger key: `38-2-spec-surface-names-a-spec-surface-glob-that-matches-nothing`.
Ledger status at mint: `backlog`.
Deps: S-38.1.
Minted 2026-10-01 by operator ruling: the deferral burn-down's "stop the inflow" changes run before its Phase 2.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-doctor pyforge-doctor-test` — expected: pass (the station's `verify_commands`).

## Review Triage Log

- No independent review has run yet (implementation and review stay separate).
- Implementation 2026-10-01: `pixi run -e pyforge-guild spec-surface-check` (run from this worktree, whose tracked tree equals
  `main` plus this change) lists 25 `stale-surface` WARN rows across 7 Specs (atlas, doctor, herald, marshal, pyforge-testing-charter,
  scribe, steward) beside the OK verdict and exits 0 (read from `$?`, no pipe) - the 25 globs in 7 Specs DW-OPS-2026-10-01-2 recorded.
  No Spec `surface:` list was edited. The existing `test_spec_governing_no_files_is_not_drift_blind` fixture glob is itself dead, so
  its exact check set now includes `stale-surface`; no other existing test moved. Removing the `presumed.extend(...)` call fails
  8 of the spec-surface tests (mutation confirmed).
