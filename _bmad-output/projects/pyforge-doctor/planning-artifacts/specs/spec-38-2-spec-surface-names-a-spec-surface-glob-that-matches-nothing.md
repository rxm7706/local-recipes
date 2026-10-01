---
title: "38.2: `spec-surface` names a Spec surface glob that matches nothing"
type: 'feature'
created: '2026-10-01'
status: 'backlog'
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
