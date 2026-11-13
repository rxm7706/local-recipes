---
title: '121.5: The host, platform and portals get their foundry contract'
type: 'docs'
created: '2026-11-10'
status: 'blocked'
flag-exempt: docs-only
difficulty: easy
story: 121.5
spec: foundry-capability-ledger
surface:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-121-5-the-host-platform-and-portals-get-their-foundry-contract.md
context:
  - docs/dreams/pyforge-unifying-strategy.md
  - docs/dreams/pyforge-steward.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-foundry-capability-ledger/SPEC.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-foundry-capability-ledger/modes.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-foundry-capability-ledger/extract.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/epics.md
warnings: []
deferred: []
declared_low_risk: false
---

> **Minted blocked 2026-11-10 — never dispatch until the operator flips it.** Blocking condition: the operator's
> ruling on the host after Launch (the second addendum of `docs/dreams/pyforge-unifying-strategy.md` § Realization log,
> ruling 3). This Story is the expiry anchor `"steward:121.5"`; an agent never flips its ledger key.

<intent-contract>

## Intent

**Problem:** Ruling 3: host, platform and portal capabilities are A-only with a Story as their expiry, and no such Story existed. This is the expiry anchor ("steward:121.5") of about 90 ledger rows and of case `k-no-host`. Minted `blocked`; nothing is built.

**Approach:** None until the operator flips the key. When flipped: a dated Dream entry and a Spec decide per group whether B rebuilds it or A keeps it, and every ledger row that expires on "steward:121.5" is re-decided in that change.

Ledger key: `121-5-the-host-platform-and-portals-get-their-foundry-contract`. Type / Effort / Deps: docs / S / —.

### Living CAP citations

- **`spec-foundry-capability-ledger`** — fcl:CAP-1 (schema v1 and the written rules) and fcl:CAP-2 (the refusals and the expiry clock), amended 2026-11-10 and re-derived at mint.

## Boundaries & Constraints

**Always:**
- Blocking condition: the operator's ruling on the host after Launch.

**Never:**
- Never flip the ledger key off `blocked`: Epic 44 minted its stories blocked the same way, and only the operator flips one.
- Never dispatch this story.

## Acceptance Criteria

- **AC1 — the key exists and is blocked.** Expected: 1.
  ```bash
  grep -c '^  121-5-the-host-platform-and-portals-get-their-foundry-contract: blocked$' _bmad-output/projects/pyforge-steward/planning-artifacts/sprint-status-ledger.yaml
  ```
- **AC2 — the story spec says why it waits and declares its type.** Expected: 3.
  ```bash
  grep -c "^status: 'blocked'$\|^type: 'docs'$\|^flag-exempt: docs-only$" _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-121-5-the-host-platform-and-portals-get-their-foundry-contract.md
  ```
- **AC3 — ledger hygiene and the flag gate.** Expected: exit 0.
  ```bash
  pixi run -e pyforge-guild story-status-check && pixi run -e pyforge-guild ledger-regression-check && pixi run -e pyforge-guild flag-gate-check
  ```

</intent-contract>

## Binding

Parent: `spec-foundry-capability-ledger` fcl:CAP-1

- Dream: `docs/dreams/pyforge-unifying-strategy.md` § Realization log (the 2026-11-10 entry, its addendum, its second addendum and the mint entry) and `docs/dreams/pyforge-steward.md` § *2026-11-10 — Cutover readiness: the steward Spec, suite and shared surfaces tell the truth*.
- Epic: Epic 121.
- Ledger key: `121-5-the-host-platform-and-portals-get-their-foundry-contract` (`blocked` at mint).
- Deps: —.
- Surface: `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-121-5-the-host-platform-and-portals-get-their-foundry-contract.md`.
- Minted 2026-11-10 by the cutover-readiness mint (control-plane unit), one PR from branch `cutover-readiness-2026-11-10`.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-guild story-status-check` — expected: exit 0.

## Notes

- Mint-only in the 2026-11-10 PR: its epics.md block, its `blocked` ledger key and this spec; no build wave runs it.
