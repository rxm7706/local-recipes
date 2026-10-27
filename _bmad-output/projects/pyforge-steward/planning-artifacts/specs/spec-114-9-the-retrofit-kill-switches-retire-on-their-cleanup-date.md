---
title: "114.9: the retrofit kill switches retire on their cleanup date"
type: 'feature'
created: '2026-10-26'
status: 'backlog'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
flag-exempt: flag-infrastructure   # the story retires flags (spec-feature-flag-governance Q2); read by the gate and the inventory
retires-flag:
  - pyforge.steward.budget
  - pyforge.steward.frame_upstream_check
  - pyforge.steward.workspace_clean
  - pyforge.steward.workspace_own_worktrees_only
  - pyforge.steward.deploy_perimeter
  - pyforge.steward.setup_hooks
  - pyforge.steward.workspace_full_refs
  - pyforge.steward.station_client_identity
context:
  - src/platform/config/flags.json
  - src/platform/config/flag-overlays.json
  - docs/governance/spec-feature-flag-governance/SPEC.md
  - docs/reference/story-spec-flag-block.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/epics.md
---

<intent-contract>

## Intent

**Problem:** the 8 retrofit kill switches Epic 114 minted read ON in every environment from 2026-10-26, so each carries `on_everywhere: 2026-10-26` and `cleanup_by: 2027-01-24` (Q4: a flag may live 90 days after it is ON everywhere). From 2027-01-25 the gate's `flag-clock-overdue` reds `detectors-ci` for every one still in the tree. The owning station files the removal story (Q4); this is it, minted with the switches so the clock has an owner from day one (operator ruling R5 of 2026-10-26).

**Approach:**
- On the cleanup date, for every key the operator has not turned off: remove the tree entry and its three overlay values, the read site (the verb table row or the behaviour helper) and the two-state test, and extend nothing else.
- Declare every removed key under `retires-flag:` here (the owner's declaration; another station's never counts), so a `done` Epic 114 spec naming the key reads as history and the inventory reads the row as `retired by 114-9-the-retrofit-kill-switches-retire-on-their-cleanup-date`.
- Run the gate: `flag-retired-still-read` must name no file (the checklist in `docs/reference/story-spec-flag-block.md`: no environment stand-in, no key built from parts, no reader in a class the gate never reads).
- A key the operator turned OFF in any environment stays in the tree: its capability's removal is a story of its own, and this story records which keys it left.

Ledger key: `114-9-the-retrofit-kill-switches-retire-on-their-cleanup-date`.
Type / Effort / Deps: feature / M / 114.1.

### Living CAP citations

- **`spec-feature-flag-governance` CAP-2** (the retirement path, amended 2026-10-15) and **CAP-7** (the retrofit): the flag leaves the tree only through its owner's declaration, and the inventory names the retiring story.

## Acceptance Criteria

- **AC1 — Every key gone or kept on purpose.** Each of the 8 keys is either removed (tree, overlays, reader, test) and listed under `retires-flag:`, or kept with the environment the operator turned it off in named in this spec.
- **AC2 — No reader left.** `flag-gate-check` reports no `flag-retired-still-read` and no `flag-clock-overdue`.
- **AC3 — The inventory.** `docs/governance/flag-inventory/pyforge-steward.md` reads each retired row as `retired by 114-9-the-retrofit-kill-switches-retire-on-their-cleanup-date`.
- **AC4 — The contracts.** `_SHIPPED_CLOCKS` and `_SHIPPED_BOOLEANS` lose the removed keys; the station suite passes.

## Boundaries & Constraints

**Always:**
- Declare the retirement here, on the owning station; remove the reader with the key.

**Never:**
- Never remove a key before 2027-01-24; never retire a key another station owns; never leave a reader behind.

</intent-contract>

## Binding

- Parent capability: `spec-feature-flag-governance` CAP-7 (the retrofit) and CAP-2 (the retirement path); no station CAP is minted.
- Dream: `docs/dreams/pyforge-steward.md` § *Realization log*, the 2026-10-26 (every pre-rule runtime capability sits behind a kill switch) entry.
- Epic: Epic 114, minted with the retrofit stories.
- Ledger key: `114-9-the-retrofit-kill-switches-retire-on-their-cleanup-date`.
- Ledger status at mint: `backlog` (due 2027-01-24).
- Deps: 114.1.
- Minted 2026-10-26 in one chain commit.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-guild flag-gate-check` — expected: exit 0 with no `flag-retired-still-read` and no `flag-clock-overdue` (AC2).
- `pixi run --frozen -e pyforge-guild flag-inventory` — expected: exit 0; the station report reads each retired row by this story (AC3).
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — expected: pass (AC4).

## Auto Run Result

Status: backlog (minted 2026-10-26; due 2027-01-24, operator ruling R5).

## Spec Change Log

- 2026-10-26: minted with Epic 114 from the station Dream's entry of 2026-10-26 at the operator's approval of the CAP-7 retrofit sheet (R1–R8).

## Review Triage Log

- (none yet)
