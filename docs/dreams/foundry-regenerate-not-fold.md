---
title: Foundry is regenerated from Frames, not folded from last year's tree
type: dream
owner: steward
status: specified
---

# Foundry is regenerated from Frames, not folded from last year's tree

## The Dream

`python-foundry` is the lasting git root. It should be born from contracts —
Dreams, memlogs, Frames, the suite register, public CLI and MCP — not from a
path-rename of `src/shared/packages/`. A year of incremental build left
Containerfile `COPY` of package source, `five_tier` hardcoded on
`src/shared/packages`, django packages without `pixi.toml`, and a host that
imports `pyforge.steward.keys`. Folding that tree into `src/packages/` would
pay that year again under a new directory name.

The Dream is **regenerate, do not fold**. Invent and refine in
`local-recipes`. Foundry receives proven capability as **new packages**,
empty `src/packages/` filled when a station is born. Launch is **CLI + MCP**:
`pyforge-core`, then steward, then marshal, proven against a thin archived
test oracle. Portals and `/console/` stay here until a later UX Dream. Public
verbs stay (`pyforge steward`, `pyforge marshal`, `warden scan`).

> A lasting root that only exists because we copied the brownfield is not a
> foundry. It is a second checkout.

## Campaign — four verbs

**Launch the Foundry. Adopt Frames. Build the Intelligence Hub. Wire every
component of the BMAD-suite.**

Operating model: **strangler fig**. Facade is the public CLI (later
`cutover_root`). Each `rebuild` row is a new vine on B from Frame+Spec.
A long-lived git mirror of A is out of contract. The capability ledger
is the routing table (`docs/dreams/foundry-capability-ledger.md`).

| Mode | Meaning |
|---|---|
| `rebuild` | B re-derives from Frame/Spec; A is oracle until `verified-in-foundry` |
| `retire` | Must not appear on B; A may keep history |
| `A-only` | Allowed on A; expiry (story id or `YYYY-MM-DD`) |
| `B-only` | Named on a Spec before `done` |

Never `move`. `verified-in-foundry` is a claim on a `rebuild` row (needs
a 54.1 case-list id), not a fifth mode. Frame preflight is not the oracle.

- **Launch** — B exists *and* a regenerated kernel runs there. Not “A’s
  tree arrived.” Factory island (44.7) and the cutover flag (44.12)
  landed. 54.1 case-list is the thin oracle. 54.2–54.4 rebuild core /
  steward / marshal on B. 44.4–44.6 stay parked (file-move, not dispatch).
- **Adopt Frames** — Company + eight station `.frame.md` as Frame Spec
  **v0.3 working draft** (53.2 + 53.5; Apache-2.0; `openteams-ai/frame-spec#28`).
  B is the Frame writer. Frames are spec, not a copy list.
- **Build the Hub** — Charter map, Frames, `track.json`, Guards (53.1–53.4).
  Do not invent Hub objects first in foundry. No Community Frame / registry
  until that later-cap is named.
- **Wire the suite** — re-provision in foundry from the register. Not
  `apply --phase 1b` as a tree copy. Chrome / mybmad stay on A until UX
  exists. Drain is not unlocked by 28.29.

## Why now

Operator 2026-09-13: invent in local-recipes; foundry receives proven
capability; Frames + Charter + suite as spec; willing to break import paths
but **CLI names stay**. Adversarial review the same day: fold is worse than
rewrite; “debt-free after two stations” is false; wait-for-44.14 stalls
Launch; Frame-schema-only misses `MRS-DISP-*`. Chosen: **A + thin oracle** —
start the kernel now; Story 1 archives about 20–40 existing
core/steward/marshal tests as the gate.

## What it looks like when real

- Foundry `src/packages/` has no fold of `src/shared/packages/`.
- `pyforge core` / station_port, `pyforge steward`, `pyforge marshal` run
  there and pass the thin oracle.
- One marshal dispatch against the foundry remote is green.
- `steward cutover apply --phase 1a` is not how packages appear.
- `pyforge.cutover_root` is still `local-recipes` until the kernel is
  verified (attended, no loop running).
- Host and `django-*` are absent from foundry Launch.

## Kinships

- `docs/dreams/pyforge-unifying-strategy.md` § Cutover /
  `spec-python-foundry-cutover` (`fnd:CAP-1..10`; new `fnd:CAP-11` kernel)
- `docs/dreams/intelligence-hub.md` / `spec-intelligence-hub` (Frames, Track, Guards)
- `docs/dreams/bmad-suite-lifecycle.md` / `spec-bmad-suite-lifecycle` (register, provision)
- `docs/dreams/regenerable-factory.md` (archive as oracle, not as source copy)
- `docs/dreams/pyforge-steward.md`, `docs/dreams/pyforge-marshal.md`
- Company Frame `docs/foundry/frames/pyforge.frame.md` (no lasting `src/shared/packages/`)
- `docs/dreams/foundry-capability-ledger.md` / `spec-foundry-capability-ledger` (modes / Epic 55)

## Constraints / Non-goals

- No `apply --phase 1a` as realization of packages.
- No host / seven portals in Launch.
- Do not rename public CLI verbs.
- Do not flip `cutover_root` in this Dream’s first epic.
- Do not flip 44.9, 44.10, or archive local-recipes.
- Do not copy the recipe universe (44.8).
- Do not move the CFE cell (44.6). Rebuild from Specs; local-recipes is the oracle.
- Full 44.14 oracle later; thin slice now.

## Realization log

- **2026-09-13** — Dreamt and specified the same day. Operator accepted
  regenerate-not-fold, A + thin oracle, CLI+MCP Launch. Epic 54 mints the
  kernel Stories. 44.4 / 44.5 / 44.6 parked as file-move. Ledger keys stay
  `backlog`; they are not dispatched. CFE is rebuild-from-spec, not cargo.
- **2026-09-13** — A/B lock: one starting contract (Dream + Frame + Spec
  five-fields); A/B the behavior. `fnr:CAP-5` + `ab-sync.md`. Story 54.5
  lands the protocol on foundry. BMAD-on-B is slim; do not copy A's trees.
- **2026-09-13** — Strangler kit merged (A #1343 / B #3): Frames v0.3,
  case-list, Epic 55 Spec. Mode contract memorialized on B
  (`docs/foundry/modes.md` + `estate-smoke`).
