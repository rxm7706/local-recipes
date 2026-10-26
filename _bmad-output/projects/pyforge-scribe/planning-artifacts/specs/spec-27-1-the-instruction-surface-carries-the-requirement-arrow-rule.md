---
title: "27.1: The instruction surface carries the requirement-arrow rule"
type: 'chore'
created: '2026-10-26'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: true
context:
  - AGENTS.md
  - docs/reference/agent-instruction-notes.md
  - .claude/memory/MEMORY.md
  - _bmad-output/projects/pyforge-scribe/planning-artifacts/specs/spec-pyforge-scribe/SPEC.md
  - _bmad-output/projects/pyforge-scribe/planning-artifacts/specs/spec-pyforge-scribe/.memlog.md
  - _bmad-output/projects/pyforge-scribe/planning-artifacts/epics.md
  - docs/dreams/pyforge-scribe.md
  - src/shared/packages/pyforge-scribe/tests/meta/test_instruction_surface_parity.py
  - docs/governance/spec-one-chain-per-station/CHAIN-STANDARD.md
  - .claude/skills/bmad-project-context/SKILL.md
---

<intent-contract>

## Intent

**Problem:** The rule the Guild amended on 2026-10-26 (a requirement cites defined capabilities only) and the multi-station-PR shape #2240 and #2319 set reach a harness only through the instruction surface scribe owns; AGENTS.md said nothing about either, the managed block did not point at CHAIN-STANDARD, no pitfall recorded the shared scribe Postgres that failed a parallel preflight, and team memory held neither the rule nor the ruling.

**Approach:**
- **Pointers outside the block** (CAP-27, point-don't-copy): Pre-PR checklist item 6 gains the requirement-arrow bullet and item 7 the multi-station-PR bullet, both verbatim from the 2026-10-25 audit's proposed text; each names CHAIN-STANDARD § 2 and `fr-without-cap` rather than restating them.
- **Inside the block, through the skill.** `bmad-project-context` (record): the Governance line under *Where things are* names `docs/governance/spec-one-chain-per-station/CHAIN-STANDARD.md`; *Known pitfalls* gains the shared-Postgres line (one full preflight at a time; the scribe lane on `127.0.0.1:5433`; re-run the lane alone before reading a red as real); the provenance line is re-verified against `92fa3edbbd`; the path and the port are checked against the tree (`pixi.toml`).
- **The incident** in `docs/reference/agent-instruction-notes.md` § *Moved from AGENTS.md*, so the AGENTS.md line stays a pointer.
- **Team memory.** `scribe capture --type feedback` ("trace, never count") and `--type project` (the 2026-10-26 ruling and the ruling sheet).
- **`type: chore`, no flag.**

Ledger key: `27-1-the-instruction-surface-carries-the-requirement-arrow-rule`.
Type / Effort / Deps: chore / S / —.

### Living CAP citations

- **`spec-pyforge-scribe` CAP-27** (one `AGENTS.md`, pointers elsewhere) and **CAP-29** (no duplicated section): the surface this story edits, within its rules.
- **`spec-one-chain-per-station` CAP-5** (amended): the rule the pointers carry.
- **Origin.** `docs/dreams/pyforge-scribe.md` Realization log, the 2026-10-26 entry; the operator's ask of 2026-10-26.

## Acceptance Criteria

- **AC1 — The bullets.** AGENTS.md item 6 contains the sentence "A PRD requirement names the capability that realizes it" and item 7 contains "One PR may carry stories from several stations"; both sit outside the `bmad:context` markers.
- **AC2 — The block.** Between the markers, the Governance line names `docs/governance/spec-one-chain-per-station/CHAIN-STANDARD.md` and a *Known pitfalls* line names `127.0.0.1:5433`; the provenance comment reads `Verified 2026-10-26 against 92fa3edbbd`.
- **AC3 — The notes and the memory.** `docs/reference/agent-instruction-notes.md` has the heading "Pre-PR checklist items 6 and 7: the FR-arrow incident"; `.claude/memory/feedback/` and `.claude/memory/project/` each gained one 2026-10-26 file and `MEMORY.md` two lines.
- **AC4 — Gates.** `pixi run --frozen -e pyforge-scribe pyforge-scribe-test` passes (the parity meta-test included); `pixi run -e pyforge-guild governance-currency` exits 0; `detectors-ci` exits 0.

## Boundaries & Constraints

**Always:**
- Point, never copy: every AGENTS.md line names where the rule lives; block edits go through the skill with path-checked claims.

**Never:**
- Never hand-edit the `bmad:context` block outside the skill's record/refresh shape; never duplicate an AGENTS.md section into a per-tool file.

## I/O & Edge-Case Matrix

| Surface | Before | After |
|---|---|---|
| AGENTS.md item 6 | no arrow rule | the requirement-arrow bullet (pointer) |
| AGENTS.md item 7 | no multi-station shape | the one-PR bullet (pointer) |
| block, Governance line | `docs/governance/` only | + CHAIN-STANDARD path |
| block, Known pitfalls | no Postgres pitfall | the shared-cluster line |
| notes § Moved from AGENTS.md | — | the FR-arrow incident |
| `.claude/memory/` | — | two captures |

</intent-contract>

## Binding

- Parent capabilities: `spec-pyforge-scribe` CAP-27 and CAP-29; `spec-one-chain-per-station` CAP-5 (amended). No scribe CAP is minted.
- Dream: `docs/dreams/pyforge-scribe.md` § *Realization log*, the 2026-10-26 entry.
- Epic: Epic 27 (new), minted with this story. `epic-27` and `epic-27-retrospective` are minted with it.
- Ledger key: `27-1-the-instruction-surface-carries-the-requirement-arrow-rule`.
- Deps: —.
- Minted 2026-10-26 in one chain commit; built in the same PR (the one-PR "every requirement derives from a capability" effort: atlas 41.1, doctor 50.1, herald 47.1, marshal 108.1, mason 33.1, scribe 27.1, steward 111.1, warden 20.1).

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-scribe pyforge-scribe-test` — expected: pass (parity meta-test included; needs the scribe Postgres up, `scribe-pg-up` first) (AC4).

**Run before the push (not dispatch gates):**
- `grep -c 'A PRD requirement names the capability that realizes it' AGENTS.md` — expected: `1` (AC1).
- `grep -c 'Verified 2026-10-26 against 92fa3edbbd' AGENTS.md` — expected: `1` (AC2).
- `pixi run -e pyforge-guild governance-currency` — expected: exit 0 (AC4).
- `pixi run -e pyforge-guild detectors-ci` — expected: exit 0 (AC4).

## Auto Run Result

Status: done (hand-built in the chain PR; promoted after the independent reviews, inside the PR)
Implementation: the two AGENTS.md bullets; the block's pointer, pitfall and provenance line through `bmad-project-context` (record); the notes incident; two `scribe capture` entries; PRD, spine and epics re-stamped with § Currency reconciliation — 2026-10-26 (Story 27.1).

## Spec Change Log

- 2026-10-26: minted from the station Dream's entry of 2026-10-26 (every requirement derives from a capability) at the operator's rulings of 2026-10-26 ("yes forbid it"; the ruling sheet accepted in full).

- 2026-10-26: promoted to `done` inside the chain PR after the independent reviews of 2026-10-26 (planning tables: FAIL then PASS on the amendments; detector diff: FAIL then PASS on round 2), every finding applied in the chain PR.

## Review Triage Log

- 2026-10-26: the independent reviews of 2026-10-26 (planning tables: FAIL then PASS on the amendments; detector diff: FAIL then PASS on round 2), every finding applied in the chain PR; no blocker open at promotion.
