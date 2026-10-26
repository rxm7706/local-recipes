---
title: "106.1: Every marshal seed-installer FR names the capability that realizes it"
type: 'chore'
created: '2026-10-25'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/prds/prd-pyforge-marshal-2026-07-25/prd.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/.memlog.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md
  - docs/dreams/pyforge-marshal.md
  - docs/governance/spec-one-chain-per-station/SPEC.md
  - src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/one_chain.py
---

<intent-contract>

## Intent

**Problem:** the marshal PRD's § 15 (the seed installer, FR-66..FR-127) carries no `← CAP-n` arrow on any of its 62
requirement bullets. Line numbers are at `fd06415e4d`.

- **Why they have none.** § 15 was the genesis installer's satellite PRD (`FR1..FR62`), renumbered into this FR space as
  FR-66..FR-127 on 2026-08-08. Its Spec's nine capabilities were folded into `spec-pyforge-marshal` on 2026-08-02 as
  CAP-10..CAP-18 (verbatim, renumbered). The 2026-09-16 pilot fold (`1e845b55fc`) appended arrows to FR headings only,
  so these bullets got none.
- **Why nothing noticed.** Doctor's `fr-without-cap` (`pyforge/doctor/sources/one_chain.py`) reads only FRs absent from
  `docs/governance/fr-baseline.json`, and all 62 are in it.
- **What found it.** The fleet audit of 2026-10-25, after Story 105.1 (#2314). The audit matched § 15 to CAP-10..CAP-16
  by title only; tracing each requirement shows CAP-17 (the state file), CAP-18 (templates and air-gap) and CAP-8 (the
  distribution) realize parts of it too, and four requirements derive only from Spec constraints (a fifth, FR-101, from CAP-15 and a constraint).

**Approach:**
- **The table is the contract.** `spec-pyforge-marshal`'s memlog carries the approved table (the 2026-10-25 decision
  entry "the approved table for Story 106.1"): 62 bullets, each `FR-n ← <arrow>`. Evidence: each subsection's verb
  against the capability whose success states it (CAP-10..CAP-18 at `1e845b55fc^`, the full pre-fold text), the
  `epics.md` stories that realized each FR (Epics 7..12), and, for FR-122, the 2026-08-10 correct-course that put the
  seed inside `pyforge-marshal` (CAP-8).
- **The constraint form.** FR-120, FR-121, FR-125 and FR-126 are stated by no capability, only by the Spec's
  Constraints. Per the operator's ruling they read `← Constraint "<the bullet's lead phrase>"`. FR-101 reads
  `← CAP-15, Constraint "Copier is a dependency, not a framework"` (the review ruling): its flag is the update verb's,
  and only the constraint states its `run_recopy` mapping.
- **The addition.** Each bullet gains ` ← <arrow>` after its bold id, in the shape `- **FR-66** ← CAP-10 — …`;
  nothing else on the line changes.

- **The record.** A PRD `## Currency reconciliation — 2026-10-25 (Story 106.1)` section lists the change; the PRD,
  spine and epics `updated:` stamps move with notes.
- **`type: chore`, no flag.** A traceability correction to a planning artifact; under `spec-feature-flag-governance`
  Q1 a chore carries no flag. Planning files only, so it is built in its own chain PR, not dispatched.

Ledger key: `106-1-every-marshal-seed-installer-fr-names-the-capability-that-realizes-it`.
Type / Effort / Deps: chore / M / —.

### Living CAP citations

- **`spec-one-chain-per-station` CAP-5** (FRs derive from CAPs): every FR names the capability it derives from; this
  story makes § 15's names exist.
- **`spec-one-chain-per-station` CAP-8** (the marshal pilot): the fold that left § 15 without arrows.
- No `spec-pyforge-marshal` CAP is minted, and no `SPEC.md` text changes.
- **Origin.** `docs/dreams/pyforge-marshal.md` Realization log, the 2026-10-25 (the seed installer's FRs never got their arrows) entry; the operator's rulings of 2026-10-25 "Do rows 1-5 in one PR" and "Cite the constraint (Recommended)".

## Acceptance Criteria

- **AC1 — The 62 arrows.** FR-66..FR-127 each carry exactly their arrow from the table, and no other FR line
  changed (a diff of the PRD against `fd06415e4d` shows exactly 62 changed FR-66..FR-127 bullets and no changed
  `#### FR-` heading).
- **AC2 — Every cited capability exists.** Each `CAP-n` in a changed arrow without a `spec-` prefix is declared in
  `spec-pyforge-marshal/SPEC.md`.
- **AC3 — Every cited constraint exists.** Each `Constraint "…"` arrow quotes the lead phrase of a bullet under
  `spec-pyforge-marshal/SPEC.md` § Constraints.
- **AC4 — Gates.** `fr-without-cap`, `chain-currency`, `chain-completeness` and `detectors-ci` stay green.

## Boundaries & Constraints

**Always:**
- Change only the arrow text of the lines in the table, and re-stamp what chain currency requires in the same commit.

**Never:**
- Never change an FR's number, title or body, `SPEC.md`, or a detector.

## I/O & Edge-Case Matrix

| Subsection | FRs | After |
|---|---|---|
| Model manifest & classification | FR-66..FR-71 | CAP-10 (FR-70 + CAP-17, FR-71 + CAP-15) |
| `marshal seed init` | FR-72..FR-78 | CAP-14 (FR-77 + CAP-17) |
| `marshal seed adopt` | FR-79..FR-87 | CAP-12 (FR-86 + CAP-11) |
| `marshal seed check` | FR-88..FR-93 | CAP-13 |
| `marshal seed update` + migrations | FR-94..FR-101 | CAP-15 (FR-95 + CAP-13; FR-96 + CAP-17; FR-99 CAP-11, CAP-15); FR-101 CAP-15 and the Copier constraint |
| State file | FR-102..FR-107 | CAP-17 (FR-106 + CAP-11) |
| Managed regions | FR-108..FR-113 | CAP-11 |
| Agent adapter fan-out | FR-114..FR-117 | CAP-16 (FR-116 + CAP-17, CAP-12) |
| Templates, distribution & CLI | FR-118..FR-127 | FR-118/119 CAP-18; FR-120/121 the Copier constraint; FR-122 CAP-8; FR-123 CAP-12, CAP-13; FR-124 CAP-12, CAP-15; FR-125 "Two clocks"; FR-126 the finding-enum constraint; FR-127 CAP-10 |
| Every other FR | — | unchanged |

</intent-contract>

## Binding

- Parent capabilities: `spec-one-chain-per-station` CAP-5 and CAP-8. No CAP is minted, and no `SPEC.md` text changes.
- Dream: `docs/dreams/pyforge-marshal.md` § *Realization log*, the 2026-10-25 (the seed installer's FRs never got their arrows) entry.
- Epic: Epic 106 (new), minted with this story. `epic-106` and `epic-106-retrospective` are minted with it; Story
  106.2 joins it.
- Ledger key: `106-1-every-marshal-seed-installer-fr-names-the-capability-that-realizes-it`.
- Deps: —.
- Minted 2026-10-25 in one chain commit; built in the same PR (the five-station FR-arrow PR: herald 46.1, mason 32.1,
  warden 19.1, steward 110.1, marshal 106.1 and 106.2, atlas 40.1).

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass (the station's `verify_commands`).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: pass (the station's `verify_commands`).

**Run before the push (not dispatch gates):**
- `git diff fd06415e4d -- _bmad-output/projects/pyforge-marshal/planning-artifacts/prds/prd-pyforge-marshal-2026-07-25/prd.md | grep -cE '^\+- \*\*FR-(6[6-9]|[7-9][0-9]|1[01][0-9]|12[0-7])\*\*'` — expected: `62` (AC1).
- `pixi run -e pyforge-guild python -m pyforge.doctor.sources fr-without-cap` — expected: OK.
- `pixi run -e pyforge-guild python scripts/chain_currency_sweep_check.py --json --project pyforge-marshal` — expected: no errors.
- `pixi run -e pyforge-guild detectors-ci` — expected: exit 0.

## Auto Run Result

Status: done (hand-built and promoted to `done` in the chain PR, as #2240 did; the merge subject names marshal 106.1's key, the others land through their ledgers at `main` reading `done`)
Implementation: the PRD FR arrows rewritten from the memlog table; PRD and spine § Currency reconciliation —
2026-10-25 (Story 106.1) added; PRD, spine and epics re-stamped.

## Spec Change Log

- 2026-10-25: minted from the Dream entry of 2026-10-25 (the seed installer's FRs never got their arrows) at the operator's rulings of 2026-10-25 "Do rows 1-5 in one PR" and "Cite the constraint (Recommended)". `type: chore`, no flag.
- 2026-10-25: implemented in the chain PR; moved to `in-review`.
- 2026-10-25: round-1 review amendments applied on the operator's rulings: FR-116 ← CAP-16, CAP-17, CAP-12; FR-96 ← CAP-15,
  CAP-17; FR-101 ← CAP-15 and the Copier constraint.
- 2026-10-25: promoted to `done` in the chain PR after the independent review and its round-1 amendments: this spec, its `epics.md` Status line and its ledger keys.

## Review Triage Log

- **Round 1, 2026-10-25 (an independent reviewer over `fd06415e4d..efc10887a7`, reading the diff against the
  Specs and the pre-fold text): PASS, 0 blockers, 5 should-fix, 9 nits across the seven stories.**
  Marshal 106.1: CAP-8 and CAP-10..CAP-18 match their pre-fold text, and every row is confirmed except three.
  Should-fix: FR-116 also needs CAP-17 (adapters recorded in state) and CAP-12 (`seed adopt --agents`); FR-101's
  constraint-only arrow extended the operator's ruling beyond its list. Nits: FR-96 also CAP-17
  (`migrations_applied[]`); the spec's effort read S against the epics' M; the memlog named the constraints' heading
  wrongly. Applied on the operator's rulings "Apply all (Recommended)" and, for FR-101, "CAP-15 + constraint
  (Recommended)", with a memlog amendment; still 62 bullets, four citing a constraint alone.
