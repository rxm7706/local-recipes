---
title: Marshal-driven landings are provably Marshal-driven
type: dream
owner: marshal
status: archived
archived-reason: folded-into-station-dream
---

> **Consolidated into [[pyforge-marshal]]** on 2026-09-16 (one-chain-per-station CAP-8 pilot; folded from `marshal-land-merge-subject`).

# marshal land renders a detectable merge subject

## The Dream

Every landing route Marshal itself drives — `bmad-loop`, `deploy land-story`,
`marshal land` — is detectable from its merge-subject shape alone, the same
way `deploy land-story` already renders `identity.render_merge_subject`'s
templated form. No Marshal-driven merge is ever mistaken for a human's plain
GitHub PR merge again.

## What is real (the core)

- `deploy land-story` already renders the templated subject
  (`identity.render_merge_subject`), confirmed live — `core/promotion.py`'s
  `marshal_native_merged_keys` classifies it correctly.
- `core.promotion.merged_story_keys` / `marshal_native_merged_keys` already
  classify merge subjects into templated / bmad-loop-native / generic
  GitHub-PR patterns — the classification machinery exists and is correct;
  only one of Marshal's own landing routes fails to render a subject it can
  recognize.

## The frontier

- **`marshal land` (`cli/land.py::run_land`)** defaults to
  `landing_merge_strategy: "merge"` (`core/policy.py:335`) and calls
  `forge.merge_pr`, letting GitHub write its own auto-generated subject —
  byte-identical in shape to a human's plain PR merge. Discovered
  2026-08-12 during [[pyforge-marshal]] Story 5.9's review pass: of the keys
  `merged_story_keys` finds outside the templated/native patterns, the
  large majority are `marshal land` landings, not genuine `bmad-quick-dev`
  sessions — every consumer of this classification (fleet-picture,
  `marshal status`, `dashboard-drift-check`, and 5.9's own
  `reconcile-completions`) currently mislabels them.
- Fix: change `marshal land` to render the templated subject via
  `identity.render_merge_subject`, matching `land-story`. Once landed,
  `marshal_native_merged_keys` classifies `marshal land` merges correctly
  going forward with no further change needed anywhere downstream —
  including 5.9's own `not-loop-native` bucket, which narrows back toward
  genuine quick-dev sessions automatically.
- Not a prerequisite for 5.9, which ships today with the coarser
  `not-loop-native` label (git alone cannot currently tell `marshal land`
  and `bmad-quick-dev` apart, so 5.9 reports the honest, joint fact).

## Realization log

- **2026-08-12** — Dream seeded from [[pyforge-marshal]] Story 5.9's review
  pass 2 escalation (intent-gap finding 1): `marshal_native_merged_keys`'s
  own detection is correct, but `marshal land`'s merge strategy defeats it
  for its own landings.
- **2026-08-14** — Realized — Story 5.10 (FR-187) shipped: `cli/land.py` renders the AD-24 templated subject through `ForgePort.merge_pr`. Status flipped and FR-187 backfilled into the PRD by the 2026-08-14 audit.
