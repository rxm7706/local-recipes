---
title: "38.3: The fleet hygiene sweep runs with the other detectors, warn-only"
type: 'fix'
created: '2026-10-01'
status: 'backlog'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-pyforge-doctor/SPEC.md
  - docs/dreams/pyforge-doctor.md
  - src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/hygiene.py
  - src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/__main__.py
  - src/shared/packages/pyforge-doctor/src/pyforge/doctor/models.py
  - scripts/detectors.py
  - pixi.toml
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** Story 9.2 built `sources/hygiene.py`, the fleet hygiene sweep (CAP-42), and registered `Source.BMAD_OUTPUT_HYGIENE`
(`bmad-output-hygiene`), but it is absent from `sources/__main__.py`'s `DISPATCH`, from `scripts/detectors.py` and from
`pixi.toml`, so `gather()` runs only in its own tests and its four deferrals (DW-FU-9-2, DW-FU-9-2-2, DW-FU-9-2-3,
DW-FU-9-3) describe code nothing runs (DW-OPS-2026-10-01-1). Run once by hand on 2026-10-01 it reports 5 orphan-file
warnings. Operator ruling 2026-10-01: wire it in, warn-only.

**Approach:**

- Add `Source.BMAD_OUTPUT_HYGIENE.value: hygiene.gather` to `DISPATCH`, a `guild-tasks` pixi task running
  `python -m pyforge.doctor.sources bmad-output-hygiene`, and a row in `scripts/detectors.py`.
- Its findings stay WARN (CAP-43: reported, never auto-applied); a WARN never changes an exit code.
- Re-check the four hygiene deferrals against the running source and close or update each with evidence.

Ledger key: `38-3-the-fleet-hygiene-sweep-runs-with-the-other-detectors-warn-only`.
Ledger status (do not edit the ledger): `backlog`.
Type / Effort / Deps: fix / S / —.

### Living CAP citations

- CAP-42, CAP-43 (`spec-deferred-work-visibility` CAP-8, CAP-9), in progress; operator ruling 2026-10-01. No new CAP;
  `spec-feature-flag-governance` Q1: a `fix` needs no flag.

## Acceptance Criteria

- Given the module When `python -m pyforge.doctor.sources bmad-output-hygiene` runs Then `hygiene.gather` runs and prints its findings
- Given the detector aggregate When it runs Then it includes the hygiene source
- Given the hygiene source reports WARN findings When the aggregate's exit code is read Then it is unchanged by them
- Given the four hygiene deferrals When the story lands Then each is closed or updated with evidence from the running source
- Given the `DISPATCH` row is removed When the new tests run Then they fail (mutation)

## Tasks

1. Read `sources/hygiene.py`, `sources/__main__.py` (`DISPATCH`), `scripts/detectors.py` and an existing guild-tasks detector task in `pixi.toml`.
2. Wire the source in the three places; keep it warn-only.
3. Tests: dispatch reaches `gather`, the aggregate lists it, a WARN leaves the exit code; re-check the four deferrals.

## Boundaries & Constraints

**Always:**
- The sweep stays advisory (CAP-43).
- Read every verdict from the exit code, never through a pipe.

**Never:**
- Do not make a hygiene finding FAIL.
- Do not reimplement any `hygiene_definitions` predicate.
- Do not hand-edit any `SPEC.md`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| dispatch | `bmad-output-hygiene` | runs `gather` | — |
| aggregate | detectors run | hygiene included | — |
| warn only | orphan-file WARNs | exit code unchanged | — |

</intent-contract>

## Binding

Parent capabilities: CAP-42, CAP-43 (realizes Story 9.2's promise; no new CAP). DW-OPS-2026-10-01-1.
Dream: `docs/dreams/pyforge-doctor.md` § *Realization log*, the 2026-10-01 entry.
Ledger key: `38-3-the-fleet-hygiene-sweep-runs-with-the-other-detectors-warn-only`.
Ledger status at mint: `backlog`.
Deps: —.
Minted 2026-10-01 by operator ruling: the deferral burn-down's "stop the inflow" changes run before its Phase 2.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-doctor pyforge-doctor-test` — expected: pass (the station's `verify_commands`).

## Review Triage Log

- No independent review has run yet (implementation and review stay separate).
