---
title: "38.1: A `verified:` line written from now on cites what it read"
type: 'fix'
created: '2026-10-01'
status: 'in-progress'
baseline_revision: '731f299611bd290e1d3d7040e7a30d864b00b6b1'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-pyforge-doctor/SPEC.md
  - docs/dreams/pyforge-doctor.md
  - src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/chain.py
  - _bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-pyforge-doctor/SPEC.md
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** CAP-29's success clause says every `verified:` line on a deferred-work entry cites a `file:line` or a reproduced or
measured fact, but the deferred-work check reads `verified:` lines only for their date (`_VERIFIED_RE`,
`_parse_verified_date`), so nothing enforces it. Re-verification passes wrote "still open" after the fix had landed
(DW-FU-42-3-9, DW-FU-46-1-6) and checked the wrong file (DW-10-3-1) (DW-OPS-2026-10-01-4).

**Approach:**

- In the deferred-work gather, a `verified:` line dated on or after a cutoff (this story's landing date, a module
  constant) must contain a `path:line` reference (`<path>.<ext>:<n>` or `:<n>-<m>`) or a backtick-quoted command followed by
  its exit code; one that has neither is a FAIL finding naming the project and entry id.
- Lines dated before the cutoff are never failed: the OK finding's detail counts them. No ledger line is rewritten.

Ledger key: `38-1-a-verified-line-written-from-now-on-cites-what-it-read`.
Ledger status (do not edit the ledger): `backlog`.
Type / Effort / Deps: fix / S / —.

### Living CAP citations

- CAP-29 (`spec-deferred-work-resolution-sweep` CAP-4: evidence-grounded verdict recording), in progress; this story
  enforces its success clause. No new CAP; `spec-feature-flag-governance` Q1: a `fix` needs no flag.

## Acceptance Criteria

- Given a `verified:` line dated on or after the cutoff that cites `chain.py:4344` When the check runs Then no finding
- Given a `verified:` line dated on or after the cutoff with no `path:line` and no command-with-exit-code When the check runs Then one FAIL naming the entry
- Given a bare `verified:` line dated before the cutoff When the check runs Then no FAIL, and the OK detail counts it
- Given a line citing only a backtick-quoted command and its exit code When the check runs Then no finding
- Given a `path:120-140` range When the check runs Then it counts as a citation
- Given `main` When `deferred-work-check` runs Then it exits 0
- Given the rule is removed When the new tests run Then they fail (mutation)

## Tasks

1. Read the deferred-work gather in `sources/chain.py` (`_VERIFIED_RE`, `_parse_verified_date`, `gather_deferred_work`).
2. Add the citation predicate and the cutoff constant; FAIL only post-cutoff bare lines.
3. Tests for each matrix row; run the mutation by hand; run `deferred-work-check` on `main`.

## Boundaries & Constraints

**Always:**
- Old lines are grandfathered by date.
- Read every verdict from the exit code, never through a pipe.

**Never:**
- Do not rewrite any ledger line.
- Do not fail a line dated before the cutoff.
- Do not hand-edit any `SPEC.md`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| cited | post-cutoff, `path:line` | no finding | — |
| bare | post-cutoff, no citation | FAIL naming the entry | — |
| grandfathered | pre-cutoff, bare | counted in OK detail | — |
| command | post-cutoff, command + exit code | no finding | — |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/chain.py` -- `_VERIFIED_RE` and `_parse_verified_date` (reuse; the line regex and the date parse stay unmodified), `_deferred_work_findings` (per-project loop: the new check joins it), `_gather_deferred_work` (OK finding: carries the grandfathered count), `_deferred_work_message` (one new kind branch).
- `src/shared/packages/pyforge-doctor/tests/unit/test_sources_chain_deferred_work.py` -- the matrix rows; two OK-shape pins (`evidence == {"projects_scanned": N}`) gain the new key. `_check_project_deferred_work` keeps its four-argument signature (a monkeypatch test wraps it).
- Read-only evidence: `scripts/deferred_work_check.py` delegates to `python -m pyforge.doctor.sources deferred-work`; the `deferred-work-check` pixi task is the exit-code verdict.

## Design Notes

- **Cutoff is 2026-10-02, not the landing day.** Measured 2026-10-01 over the eight tracked ledgers: 937 `verified:` lines are dated 2026-10-01 (the burn-down's bulk pass) and 373 of them carry no citation. A cutoff of 2026-10-01 would red `main` and break the AC "`main` exits 0" and "no ledger line is rewritten". The first day after the burn-down is the earliest cutoff that satisfies all three; "from now on" starts there.
- One FAIL per entry (not per line) with an `uncited_lines` count; every `verified:` line in an entry is judged, since reconciliation appends rather than replaces.
- A line whose leading token is not a `YYYY-MM-DD` date is neither failed nor counted (it already reads as never-verified in 11.1).

## Binding

Parent capability: CAP-29 (realizes its success clause; no new CAP). DW-OPS-2026-10-01-4.
Dream: `docs/dreams/pyforge-doctor.md` § *Realization log*, the 2026-10-01 entry.
Ledger key: `38-1-a-verified-line-written-from-now-on-cites-what-it-read`.
Ledger status at mint: `backlog`.
Deps: —.
Minted 2026-10-01 by operator ruling: the deferral burn-down's "stop the inflow" changes run before its Phase 2.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-doctor pyforge-doctor-test` — expected: pass (the station's `verify_commands`).

## Review Triage Log

- No independent review has run yet (implementation and review stay separate).
