---
title: 'Story 17.3 — The recurring campaigns have a home and a record'
type: 'docs'
created: '2026-09-14'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
context: []
warnings: []
deferred: []
declared_low_risk: true
updated: '2026-09-18'
---

<intent-contract>

## Intent

**Problem:** Bulk feedstock work (refresh Track A/B, platform expansion, red-PR
remediation) is a continuous practice that must run as named, repeatable campaigns
with recorded evidence — not ad-hoc sweeps. `spec-fleet-stewardship` CAP-3 adopted
three legacy Tier-1 workflow specs as companions but had no Story, so the shipped
Spec looked undecomposed.

**Approach:** Retroactively bind CAP-3 to those three companions. Each campaign
lands evidence in its own Worked Examples / Current State. Dormancy between waves
is a currency fact the specs self-document, not a defect. No new implementation
and no new stories.

## Boundaries & Constraints

**Always:**
- Adopted companions stay authoritative where they live (legacy `docs/specs/`,
  in force during the transition):
  - `docs/specs/feedstock-refresh.md` (Track A/B bulk refresh)
  - `docs/specs/feedstock-platform-expansion.md` (per-feedstock dual-goal workflow)
  - `docs/specs/feedstock-failure-remediation.md` (red-PR loop)
- When a wave runs, evidence lands in that spec's Worked Examples / Current State.
- CLAUDE.md Rules 1 and 2 apply to every campaign wave.
- Record CAP-3 dormancy honestly: engine specs last-touched 2026-06/07; Track A
  Wave H remaining and Track B unstarted as of the 2026-09-09 realization-gate.

**Never:**
- Never absorb the three workflow procedures into a new mason-owned rewrite.
- Never author a new file under `docs/specs/`.
- Never mint `.claude/skills/pyforge-mason/`.
- Never edit `recipes/**` as part of this promotion.
- Never hand-edit `sprint-status-ledger.yaml`.
- Never read dormancy as a failed capability — the success criterion is "evidence
  lands when a wave runs."

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Wave running | Named campaign in progress | Evidence appended to the owning companion's Worked Examples / Current State | Ad-hoc sweep without a named spec is out of contract |
| Wave dormant | No refresh/expansion/remediation commits | Companion dates stay; dormancy note remains accurate | Not a red finding |
| Companion last-touch | Realization-gate 2026-09-11 | `1aeaf12cee` (refresh + remediation, 2026-07-02); `1bdd5a2f02` (platform-expansion, 2026-06-28) | Date drift would update the currency note, not fail CAP-3 |
| Foundry 44.8 | Recipes archive / move | Consult steward S-44.8; this story does not relocate campaigns | Out of scope |

</intent-contract>

## Code Map

- `docs/specs/feedstock-refresh.md` — Track A/B; Waves B–F evidence; Wave H remaining.
- `docs/specs/feedstock-platform-expansion.md` — dual-goal per-feedstock workflow.
- `docs/specs/feedstock-failure-remediation.md` — FLAKE / REAL_FIX / BLOCKED loop.
- `_bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-fleet-stewardship/` — CAP-3 pointer + `.memlog.md`.
- `docs/dreams/fleet-stewardship.md` — archived practice Dream.

## Tasks & Acceptance

**Execution:**
- `docs` — bind CAP-3 to Story 17.3 (already in `epics.md`).
- `docs` — this file is the tracked story-spec promotion.

**Acceptance Criteria:**
- Given bulk feedstock work could be ad-hoc, when this practice is in force, then each campaign has a named workflow spec and lands its evidence in that spec's own Worked Examples / Current State.
- And dormancy between waves is a currency fact the specs self-document, not a defect.
- Status: done — re-verified 2026-09-11 (historical; dormant today, matching the Spec's 2026-09-09 realization-gate note): companion last-touch commits still match documented dates; the criterion held when waves ran (Track A Waves B–F).

## Spec Change Log

- 2026-09-18: Promoted tracked `spec-<ledger-key>.md` from `epics.md` + CAP-3 verified line. No new implementation.

## Review Triage Log

None — retroactive contract-spec for a `done` practice story.

## Design Notes

Deps: S-17.1. CAP-3 is the dormant arm of a still-`shipped` Spec: the engines exist
and already recorded their waves; they are not currently executing. Fold 2026-09-17
kept the three companions on the absorbed pointer (`surface-drift: exempt` restored
so `recipes/**` stays coverage-only).

## Verification

**Commands:**
- `git log -1 --format='%h %ci' -- docs/specs/feedstock-refresh.md docs/specs/feedstock-failure-remediation.md docs/specs/feedstock-platform-expansion.md`

**Landing evidence:**
- Epic mint `92c419b052` (2026-09-14).
- CAP-3 verified line at HEAD `b36c8be118` (2026-09-11).

## Auto Run Result

Status: done

**Summary:** Practice already in force (historically evidenced, dormant today).
This file is the missing tracked story spec for ledger key
`17-3-the-recurring-campaigns-have-a-home-and-a-record`.
