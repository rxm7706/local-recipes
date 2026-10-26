---
title: "41.2: The satellite PRDs' FR ids leave the kernel's id space"
type: 'chore'
created: '2026-10-26'
status: 'backlog'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/prds/prd-pyforge-atlas-2026-07-17/prd.md
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-pyforge-atlas/SPEC.md
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-pyforge-atlas/.memlog.md
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/architecture/architecture-pyforge-atlas-2026-07-17/ARCHITECTURE-SPINE.md
  - docs/dreams/pyforge-atlas.md
  - docs/governance/spec-one-chain-per-station/CHAIN-STANDARD.md
  - src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/one_chain.py
  - docs/governance/fr-baseline.json
  - scripts/fr_baseline.py
---

<intent-contract>

## Intent

**Problem:** Two satellite PRDs carried verbatim into the atlas PRD (Unity Data Stack FR-1..FR-60, Wasm Analytics Stack FR-1..FR-17) reuse the kernel's FR-1..FR-22 ids and carry no arrows, so a bare `FR-10` names three requirements and the detector's first-definition-wins parser reads the Unity ids as duplicates (39 entries baselined on 2026-10-26 under `fr-duplicate-id`).

**Approach:**
- **Renumber from FR-78.** Unity FR-1..FR-60 → FR-78..FR-137; Wasm FR-1..FR-17 → FR-138..FR-154 (the next free id after FR-77), marshal's 2026-08-08 precedent.
- **Trace the arrows by subsection.** Each satellite subsection realizes one of CAP-18..CAP-26 (Unity) or CAP-27..CAP-31 (Wasm); every heading gains `← CAP-m` read from that CAP's intent and success, never counted.
- **The re-key map.** `planning-artifacts/rekey-<date>.md`, one line per old → new id; every reference in `epics.md`, the spine, the story specs and the Spec is read one by one (146 `FR-1..FR-22` mentions in `epics.md` are ambiguous between kernel and satellite) and re-pointed only where it names the satellite.
- **The baseline shrinks.** `scripts/fr_baseline.py --prune` removes every atlas `fr-duplicate-id` entry once no duplicate fires.
- Operator ruling (d) of 2026-10-26: minted `backlog`, not built in the one-PR effort.

Ledger key: `41-2-the-satellite-prds-fr-ids-leave-the-kernel-s-id-space`.
Type / Effort / Deps: chore / M / 41.1.

### Living CAP citations

- **`spec-pyforge-atlas` CAP-18..CAP-31**: the capabilities the renumbered requirements will cite.
- **`spec-one-chain-per-station` CAP-5** (amended) and **CAP-6**; CHAIN-STANDARD § 6 (one id family, defined once per PRD).

## Acceptance Criteria

- **AC1 — Unique ids.** No FR id is defined twice in the atlas PRD; the satellite headings read FR-78..FR-154 in document order.
- **AC2 — Traced arrows.** Every satellite heading carries `← CAP-m` with m in 18..31, and the independent review reads each subsection against its CAP's intent and success.
- **AC3 — The re-key map.** `planning-artifacts/rekey-<date>.md` lists every old → new id; `grep` finds no remaining reference to a satellite id by its old number in `epics.md`, the spine or the story specs.
- **AC4 — The baseline.** `docs/governance/fr-baseline.json` carries no atlas `fr-duplicate-id` entry; `fr-without-cap` is green.

## Boundaries & Constraints

**Always:**
- Read every ambiguous reference before re-pointing it; keep the kernel's FR-1..FR-77 untouched.

**Never:**
- Never renumber a kernel FR; never count an arrow; never hand-edit `SPEC.md`.

## I/O & Edge-Case Matrix

| Section | Before | After |
|---|---|---|
| Unity FR-1..FR-60 | collide with the kernel; no arrows | FR-78..FR-137 ← CAP-18..CAP-26 |
| Wasm FR-1..FR-17 | collide; no arrows | FR-138..FR-154 ← CAP-27..CAP-31 |
| baseline `fr-duplicate-id` (atlas) | 39 entries | 0 |

</intent-contract>

## Binding

- Parent capabilities: `spec-pyforge-atlas` CAP-18..CAP-31; `spec-one-chain-per-station` CAP-5 and CAP-6.
- Dream: `docs/dreams/pyforge-atlas.md` § *Realization log*, the 2026-10-26 entry.
- Epic: Epic 41, minted with Story 41.1.
- Ledger key: `41-2-the-satellite-prds-fr-ids-leave-the-kernel-s-id-space`.
- Deps: 41.1.
- Minted 2026-10-26 in one chain commit; built in the same PR (the one-PR "every requirement derives from a capability" effort: atlas 41.1, doctor 50.1, herald 47.1, marshal 108.1, mason 33.1, scribe 27.1, steward 111.1, warden 20.1).

## Verification

**Commands:**
- `pixi run -e pyforge-guild python -m pyforge.doctor.sources fr-without-cap` — expected: OK, no atlas `fr-duplicate-id` (AC4).
- `pixi run -e pyforge-guild detectors-ci` — expected: exit 0.

## Auto Run Result

Status: backlog (minted 2026-10-26, operator ruling (d): not built in the one-PR effort).

## Spec Change Log

- 2026-10-26: minted from the station Dream's entry of 2026-10-26 (every requirement derives from a capability) at the operator's rulings of 2026-10-26 ("yes forbid it"; the ruling sheet accepted in full).

## Review Triage Log

- (none yet)
