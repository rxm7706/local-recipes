---
title: "41.3: Every atlas NFR names the capabilities it bounds"
type: 'chore'
created: '2026-10-26'
status: 'blocked'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: true
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
---

> **Retired 2026-11-10 — never dispatch.** Operator rulings of 2026-11-10
> (`docs/dreams/pyforge-unifying-strategy.md` § Realization log, the second addendum, ruling 6): the ten NFR lines
> are the Unity satellite's (`prd.md` § Satellite: Unity Data Stack), which is retired, never built, and kept on A as
> history; Story 41.2 turns that section into a dated `Fold provenance` record section. Tracing ten Unity NFRs to
> retired capabilities would promote history into the live requirement space. A record section stops only the
> duplicate findings: doctor's parser (`sources/one_chain.py` `_fr_definitions`) still reads a first definition there,
> so the ten NFRs and the Unity satellite's FR-23..FR-60, the 48 baseline `projects` ids this story owned, stay
> arrowless and baselined for good, and doctor Story 58.4's `--prune` keeps them. That gap is DW-atlas-46-1-9, which
> Story 46.1 writes (owner: none; retired satellite history held in the baseline). The ledger key is `blocked`; an
> operator flip does not revive it. Text kept as history.

<intent-contract>

## Intent

**Problem:** CHAIN-STANDARD § 6 says every NFR cites a CAP; none of the atlas PRD's ten NFR lines does, so they are baselined as the pre-rule arrowless population (ruling (c) of 2026-10-26).

**Approach:**
- Trace each NFR against the Spec's capability successes and write `← CAP-m` on its defining line; a bound that tightens several capabilities cites each.
- Prune the baseline (`scripts/fr_baseline.py --prune`) so the atlas `projects` entry empties; the ratchet never re-adds an id.
- Minted `backlog` by ruling (c); built in its own chain PR.

Ledger key: `41-3-every-atlas-nfr-names-the-capabilities-it-bounds`.
Type / Effort / Deps: chore / S / 41.1.

### Living CAP citations

- **`spec-one-chain-per-station` CAP-5** (amended): an NFR cites the CAP(s) it bounds. The atlas CAPs cited are named in the memlog table the story will carry.

## Acceptance Criteria

- **AC1 — Ten arrows.** Every `NFR-n` line (n = 1..10) carries `← CAP-m`; a diff against the pre-story PRD shows exactly 10 changed NFR lines.
- **AC2 — Defined cites.** Each cited CAP is a definition line in `spec-pyforge-atlas/SPEC.md`; `fr-cap-unresolved` reports nothing for atlas.
- **AC3 — The baseline.** `docs/governance/fr-baseline.json` `projects.pyforge-atlas` carries no NFR id after `--prune`.

## Boundaries & Constraints

**Always:**
- Trace from the CAP's success text; record the table in the station memlog before editing the PRD.

**Never:**
- Never count arrows; never change an NFR's text; never hand-edit `SPEC.md`.

## I/O & Edge-Case Matrix

| Line | Before | After |
|---|---|---|
| NFR-1..NFR-10 | no arrow (baselined) | `← CAP-m` traced |
| baseline `projects.pyforge-atlas` | 10 NFR ids (+ satellite ids until 41.2) | pruned |

</intent-contract>

## Binding

- Parent capability: `spec-one-chain-per-station` CAP-5 (amended 2026-10-26).
- Dream: `docs/dreams/pyforge-atlas.md` § *Realization log*, the 2026-10-26 entry.
- Epic: Epic 41, minted with Story 41.1.
- Ledger key: `41-3-every-atlas-nfr-names-the-capabilities-it-bounds`.
- Deps: 41.1.
- Minted 2026-10-26 in one chain commit; built in the same PR (the one-PR "every requirement derives from a capability" effort: atlas 41.1, doctor 50.1, herald 47.1, marshal 108.1, mason 33.1, scribe 27.1, steward 111.1, warden 20.1).

## Verification

**Commands:**
- `pixi run -e pyforge-guild python -m pyforge.doctor.sources fr-without-cap` — expected: OK (AC2).
- `pixi run -e pyforge-guild detectors-ci` — expected: exit 0.

## Auto Run Result

Status: blocked (retired 2026-11-10, never dispatched; minted 2026-10-26, operator ruling (c): the NFR backfill is its own story per station).

## Spec Change Log

- 2026-10-26: minted from the station Dream's entry of 2026-10-26 (every requirement derives from a capability) at the operator's rulings of 2026-10-26 ("yes forbid it"; the ruling sheet accepted in full).

- 2026-11-10: retired at the cutover readiness mint (operator rulings of 2026-11-10, the second addendum, ruling 6), as steward Stories 44.4 to 44.6 were: the key moves from `backlog` to `blocked` and the story is never dispatched.

- 2026-11-10 (second review of the mint): the retired note names what happens to the 48 baseline ids this story owned. Story 41.2's record section does not remove them (it suppresses duplicates only), so they stay baselined as retired history, the gap DW-atlas-46-1-9 that Story 46.1 writes (rule R4).

## Review Triage Log

- (none yet)
