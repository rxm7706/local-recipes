---
title: "105.1: Every marshal PRD FR arrow names the Spec capability that realizes it"
type: 'chore'
created: '2026-10-25'
status: 'in-review'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/prds/prd-pyforge-marshal-2026-07-25/prd.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/.memlog.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md
  - docs/dreams/pyforge-marshal.md
  - docs/governance/spec-one-chain-per-station/SPEC.md
  - docs/governance/fr-baseline.json
  - src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/one_chain.py
deferred:
  - summary: >-
      Marshal PRD FR-144..FR-147 (section 16.5, detector self-verification) have no realizing capability: they keep the fold's counted arrows CAP-102..CAP-105 until the operator picks their source.
    evidence: |-
      Story 105.1 (2026-10-25) re-mapped the fold's counted FR arrows from evidence, and the operator ruled to leave these four unchanged pending a source-capability decision. Their PRD section names spec-dream-to-code-model-self-verification, whose status is absorbed and whose CAP-1..CAP-3 now describe the verify_scope primitive, not fixture meta-tests, a detector-incident log or the --dreams mode. Their current arrows point at spec-pyforge-marshal CAP-102..CAP-105, which are fleet-chain-completeness capabilities. Options: re-point them at the Spec or station that now owns detector self-verification (doctor is the likely owner), mint a marshal CAP for them, or retire the FRs.
    location: >-
      _bmad-output/projects/pyforge-marshal/planning-artifacts/prds/prd-pyforge-marshal-2026-07-25/prd.md (FR-144..FR-147)
    severity: low
---

<intent-contract>

## Intent

**Problem:** most of the marshal PRD's `FR-n ← CAP-m` arrows name the wrong capability. Line numbers are at
`d287eceb0a`.

- **Where the arrows came from.** Before the 2026-09-16 fold the PRD's FR headings carried no arrows. The fold commit
  `1e845b55fc` ("land marshal fold (CAP-8 pilot)") appended them by counting: FR-128..FR-195 read CAP-(FR−42), and
  FR-59..FR-65 read CAP-9 and CAP-19..CAP-23. At the fold, `spec-pyforge-marshal` CAP-111 was already "The declared
  Python floor equals the tested floor", so FR-153 "One governed surface ← CAP-111" never matched. Arrows written
  later by Spec renders (FR-196 onward) are right.
- **Why nothing noticed.** Doctor's `fr-without-cap` (`pyforge/doctor/sources/one_chain.py:326-388`) is the only
  reader. It checks that an FR minted after `docs/governance/fr-baseline.json` (209 marshal FRs exempt) cites a CAP some
  open Spec declares, never that the citation is the right one.
- **What was found when it mattered.** Stories 103.1 and 104.1 bind to CAP-21/22 and CAP-133, whose FRs (FR-153/154,
  FR-134) point elsewhere; both chain reviews flagged it.

**Approach:**
- **The table is the contract.** `spec-pyforge-marshal`'s memlog carries the approved re-map (the 2026-10-25 decision
  entry "the approved re-map for Story 105.1"): 71 headings, each `FR-n ← <new> (was CAP-k)`. It was derived from the
  source Spec's own `CAP-k → FR-n` lines, the FR body naming its source and CAP range, stories that cite an FR and a
  source CAP together, and the source CAP headline matching the FR title by position, each mapped through the Spec's
  `← spec-<old> CAP-k` provenance.
- **The rewrite.** Each of the 71 headings' arrow is replaced, nothing else on the line. Cross-Spec arrows use the PRD's
  existing form, `← spec-pyforge-core CAP-n` (as FR-209/210/226 already do) and `← spec-pyforge-testing-charter CAP-n`.
- **FR-144..FR-147 stay.** Their source Spec is absorbed and no capability carries them. Per the ruling they keep
  their arrows, the PRD's currency section names them as awaiting a source-capability decision, and the `deferred:`
  item above becomes a deferred-work ledger row.
- **The record.** A PRD `## 44. Currency reconciliation — 2026-10-25 (Story 105.1)` section lists the re-map by
  block; the PRD, spine and epics `updated:` stamps move with notes (no FR, AD or story text changes).
- **`type: chore`, no flag.** A traceability correction to a planning artifact; under `spec-feature-flag-governance`
  Q1 a chore carries no flag. Planning files only, so it is built in its own chain PR, not dispatched.

Ledger key: `105-1-every-marshal-prd-fr-arrow-names-the-spec-capability-that-realizes-it`.
Type / Effort / Deps: chore / S / —.

### Living CAP citations

- **`spec-one-chain-per-station` CAP-5** (FRs derive from CAPs): every FR names the capability it derives from; this
  story makes marshal's names true.
- **`spec-one-chain-per-station` CAP-8** (the marshal pilot): the fold this story corrects.
- No `spec-pyforge-marshal` CAP is minted, and no `SPEC.md` text changes.
- **Origin.** `docs/dreams/pyforge-marshal.md` Realization log, the 2026-10-25 (the PRD's FR arrows were numbered, not
  traced) entry; the operator's ruling of 2026-10-25.

## Acceptance Criteria

- **AC1 — The 71 arrows.** Every heading in the memlog table carries exactly its new arrow, and no other FR heading's
  arrow changed (a diff of the PRD's `#### FR-` lines against `d287eceb0a` shows exactly 71 changed lines).
- **AC2 — Every cited capability exists.** Each `CAP-n` in a changed arrow without a `spec-` prefix is declared in
  `spec-pyforge-marshal/SPEC.md`; each cross-Spec arrow names a CAP its Spec declares.
- **AC3 — FR-144..FR-147.** Their arrows are unchanged; PRD § 44 names them as awaiting a source-capability decision;
  the deferred-work ledger carries the row ingested from this spec's `deferred:` list.
- **AC4 — Gates.** `fr-without-cap`, `chain-currency`, `chain-completeness`, `ad-citation-check` and `detectors-ci`
  stay green.

## Boundaries & Constraints

**Always:**
- Change only the arrow text of the 71 headings, and re-stamp what chain currency requires in the same commit.

**Never:**
- Never change an FR's number, title or body, `SPEC.md`, or a detector.
- Never re-point FR-144..FR-147 without an operator decision.

## I/O & Edge-Case Matrix

| Heading block | Before | After |
|---|---|---|
| FR-1..FR-58 | marshal capability families CAP-1..CAP-8 | unchanged |
| FR-59..FR-65, FR-128..FR-143, FR-148..FR-195 | counted by the fold | the table's arrows |
| FR-144..FR-147 | CAP-102..CAP-105 (counted) | unchanged, flagged |
| FR-196..FR-239 | written by Spec renders | unchanged |

</intent-contract>

## Binding

- Parent capabilities: `spec-one-chain-per-station` CAP-5 and CAP-8. No CAP is minted, and no `SPEC.md` text changes.
- Dream: `docs/dreams/pyforge-marshal.md` § *Realization log*, the 2026-10-25 (the PRD's FR arrows were numbered, not
  traced) entry.
- Epic: Epic 105 (new), minted with this story. `epic-105` and `epic-105-retrospective` are minted with it.
- Ledger key: `105-1-every-marshal-prd-fr-arrow-names-the-spec-capability-that-realizes-it`.
- Deps: —.
- Surface: `marshal-policy.toml` `[epic_surfaces]."105"`, added with this mint.
- Minted 2026-10-25 in one chain commit; built in the same PR.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).

**Run before the push (not dispatch gates):**
- `git diff d287eceb0a -- _bmad-output/projects/pyforge-marshal/planning-artifacts/prds/prd-pyforge-marshal-2026-07-25/prd.md | grep -c '^+#### FR-'` — expected: `71` (AC1).
- `pixi run -e pyforge-guild python -m pyforge.doctor.sources fr-without-cap` — expected: OK (AC4).
- `pixi run -e pyforge-guild python scripts/chain_currency_sweep_check.py --json --project pyforge-marshal` — expected: no errors (AC4).
- `pixi run -e pyforge-guild detectors-ci` — expected: exit 0 (AC4).

## Auto Run Result

Status: in-review (hand-built in the chain PR; promoted to `done` by `dispatch_land_finalize` after the merge)
Implementation: the 71 PRD FR heading arrows rewritten from the memlog table (`#### FR-` lines changed: 71); PRD
§ 44 and the spine's Currency reconciliation 2026-10-25 (Story 105.1) added; PRD, spine and epics re-stamped;
`DW-marshal-105-1` ingested for FR-144..FR-147.

## Spec Change Log

- 2026-10-25: minted from the Dream entry of 2026-10-25 (the PRD's FR arrows were numbered, not traced) at the
  operator's ruling "Apply the PRD FR→CAP re-map as proposed: 71 headings through a chore story chain, and leave
  FR-144..FR-147 unchanged with a note that they need a source-capability decision." `type: chore`, no flag, no CAP.

## Review Triage Log

- No review has run yet.
