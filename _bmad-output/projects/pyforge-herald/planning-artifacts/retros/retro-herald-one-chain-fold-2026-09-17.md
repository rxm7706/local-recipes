---
title: Herald one-chain fold
date: 2026-09-17
verdict: accepted
trigger: chain-currency code→retro after 2026-09-16 code motion
---

# Retrospective — Herald one-chain fold (2026-09-17)

Folds the herald station into one chain per `spec-one-chain-per-station` CAP-3
and CHAIN-STANDARD § 7. This retro clears the `code→retro` feeds edge
(code last-touch 2026-09-16, prior retro 2026-09-13).

## What landed

- 11 Dreams (owner herald) on one station Dream; 10 satellite Dreams archived
  with `Consolidated into [[pyforge-herald]]`.
- 10 Spec folders: `spec-pyforge-herald` is `ready` with sequential CAP-1..47;
  nine absorbed pointers keep memlog + companions (record).
- Feed remint through `_bmad-output/projects/pyforge-herald/planning-artifacts/rekey-2026-09-17.md`
  (21 keys). Epic 23.5–23.8 became 23.3–23.6. `blocked` keys unchanged.
- FR←CAP on the station PRD; `pixi.lock` stays on doctor.

## What we would do differently

- Classify reminted `pyforge-herald:CAP-n` rows in `docs/foundry/capability-ledger.yaml`
  in the same commit as the remint (scribe lesson 4).
- Re-point DW `source_spec` through the map in the same commit as the story-spec remint
  (lesson 16); never `--fix`.
