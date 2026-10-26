---
title: "108.2: Every marshal NFR names the capabilities it bounds"
type: 'chore'
created: '2026-10-26'
status: 'backlog'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: true
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/prds/prd-pyforge-marshal-2026-07-25/prd.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/.memlog.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md
  - docs/governance/spec-one-chain-per-station/CHAIN-STANDARD.md
  - docs/governance/fr-baseline.json
---

<intent-contract>

## Intent

**Problem:** CHAIN-STANDARD § 6 says every NFR cites a CAP; none of the marshal PRD's 33 lettered NFR lines does, so they are baselined as the pre-rule arrowless population (ruling (c) of 2026-10-26).

**Approach:**
- Trace each NFR against the Spec's capability successes and write `← CAP-m` on its defining line, keeping the lettered id (§ 6 sanctions the family; the detector reads it).
- Record the 33-row table in the station memlog before editing the PRD; the independent review reads it.
- Prune the baseline so the marshal `projects` entry empties. Minted `backlog` by ruling (c); built in its own chain PR.

Ledger key: `108-2-every-marshal-nfr-names-the-capabilities-it-bounds`.
Type / Effort / Deps: chore / M / 108.1.

### Living CAP citations

- **`spec-one-chain-per-station` CAP-5** (amended): an NFR cites the CAP(s) it bounds; the lettered family is one grammar. The marshal CAPs cited are named in the memlog table the story will carry.

## Acceptance Criteria

- **AC1 — 33 arrows.** Every lettered NFR line carries `← CAP-m`; a diff against the pre-story PRD shows exactly 33 changed NFR lines.
- **AC2 — Defined cites.** Each cited CAP is a definition line in `spec-pyforge-marshal/SPEC.md`; `fr-cap-unresolved` reports nothing for marshal.
- **AC3 — The baseline.** `docs/governance/fr-baseline.json` `projects.pyforge-marshal` is empty after `--prune`.

## Boundaries & Constraints

**Always:**
- Trace from the CAP's success text; keep the lettered ids.

**Never:**
- Never count arrows; never renumber an NFR; never change an NFR's text; never hand-edit `SPEC.md`.

## I/O & Edge-Case Matrix

| Line | Before | After |
|---|---|---|
| 33 lettered NFR lines | no arrow (baselined) | `← CAP-m` traced |
| baseline `projects.pyforge-marshal` | 33 ids | pruned |

</intent-contract>

## Binding

- Parent capability: `spec-one-chain-per-station` CAP-5 (amended 2026-10-26).
- Dream: `docs/dreams/pyforge-marshal.md` § *Realization log*, the 2026-10-26 entry.
- Epic: Epic 108, minted with Story 108.1.
- Ledger key: `108-2-every-marshal-nfr-names-the-capabilities-it-bounds`.
- Deps: 108.1.
- Minted 2026-10-26 in one chain commit; built in the same PR (the one-PR "every requirement derives from a capability" effort: atlas 41.1, doctor 50.1, herald 47.1, marshal 108.1, mason 33.1, scribe 27.1, steward 111.1, warden 20.1).

## Verification

**Commands:**
- `pixi run -e pyforge-guild python -m pyforge.doctor.sources fr-without-cap` — expected: OK (AC2).
- `pixi run -e pyforge-guild detectors-ci` — expected: exit 0.

## Auto Run Result

Status: backlog (minted 2026-10-26, operator ruling (c): the NFR backfill is its own story per station).

## Spec Change Log

- 2026-10-26: minted from the station Dream's entry of 2026-10-26 (every requirement derives from a capability) at the operator's rulings of 2026-10-26 ("yes forbid it"; the ruling sheet accepted in full).

## Review Triage Log

- (none yet)
