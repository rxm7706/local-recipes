---
title: Every capability is classified — rebuild, retire, or dated A-only
type: dream
owner: steward
status: specified
---

# Every capability is classified — rebuild, retire, or dated A-only

## The Dream

A stays the oracle by **policy and a PIN**, not by a check that every
capability was transferred, retired, or scheduled. Today a new `CAP-N`
or a path after the pin SHA can sit unclassified forever. Story 44.1’s
move-list over the tracked tree stays **blocked**; that is not this
Dream.

The Dream is a **capability ledger** — the strangler routing table.
Each capability has one mode: `rebuild` (B re-derives from Frame/Spec;
A is oracle until `verified-in-foundry`), `retire` (must not appear on
B), `A-only` (expiry: story or date), or `B-only` (named on a Spec
before `done`). Never `move`. Never a long-lived B branch that
mirrors A. A detector in `detectors-ci` refuses unclassified `CAP-N`,
refuses `A-only` without expiry, and refuses `verified-in-foundry`
without a case-list id. New paths and Specs after the PIN SHA queue
`--append` until classified.

Inventory is an **extract**, not a novel. Walk `CAP-N` headings plus
`intent` / `success` — the same trunc-avoiding flow Scribe already
uses for planning pointers and the library catalog. Do not load
wholesale `SPEC.md` bodies. Do not keep the first 20k characters and
drop the Capabilities section.

> A pin without a classified list is a feeling that A is complete.

## Why now

Operator 2026-09-13: A is oracle by PIN, not by a transfer proof.
Do not flip 44.1. Add this as the default operating check. Kinships
to regenerate-not-fold (`fnr:CAP-5`), the thin case list (54.1), and
Scribe’s extract surfaces (13.1 / 14.1).

## What it looks like when real

- `docs/foundry/capability-ledger.yaml` is tracked and complete
  against every live `CAP-N` extract.
- `A-only` rows carry an expiry date.
- A row that claims `verified-in-foundry` cites a case-list id.
- `detectors-ci` HARD-fails unclassified or undated rows.
- 44.1 remains `blocked`. No `move` mode.

## Kinships

- `docs/dreams/foundry-regenerate-not-fold.md` /
  `spec-foundry-regenerate-not-fold` (`fnr:CAP-1..5`)
- `docs/dreams/pyforge-unifying-strategy.md` /
  `spec-python-foundry-cutover` (44.1 stays blocked)
- `docs/dreams/scribe-planning-pointers.md` /
  `spec-scribe-planning-pointers` (heading extract, never wholesale)
- `docs/dreams/scribe-named-docs.md` /
  `spec-scribe-named-docs` (catalog `##` extract, never 20k truncate)
- `docs/dreams/capability-effect-check.md` (effect is a later doctor
  criterion; this Dream classifies destiny, not callers)

## Constraints / Non-goals

- Do not flip 44.1 or any other Epic 44 `blocked` key.
- No `move` mode. Rebuild or retire; do not invent a fold path.
- Do not rsync `_bmad-output` or package trees onto foundry.
- Do not treat Frame preflight as classification.
- Do not compile wholesale SPEC prose into the detector input.

## Realization log

- **2026-09-13** — Dreamt and specified the same day. Operator: mint
  Dream + Spec; trunc-based extract is the inventory flow. Epic 55.
