---
title: "PRD — pyforge-genesis (constitutive)"
status: final
created: 2026-07-28
updated: 2026-08-04
project: pyforge-genesis
currency_review: Reviewed 2026-08-04 — spec/brief timestamp bump was structural (project relocation / memlog story-completion recording), not content drift; PRD unchanged.
---

# PRD — pyforge-genesis

## This tier has nothing to require, and says so

`pyforge-genesis` is the **constitutive** project: it records the operating model — the
Charter, the Lexicon, the Guild's membership — and ships no product. A PRD states *product
requirements*; there is no product here, so there are none to state.

This file exists because the operating model admits **no size- or kind-based exemption**
(`EXEMPLAR-STANDARD.md` INV-3, § "Why no size-based exemption"): a uniform tree is
mechanically checkable, and a tasteful one is not. The sanctioned answer where a tier has
nothing to say is to **say so in one line** rather than omit the tier and force every reader
to work out whether the absence is deliberate or drift.

## Where the actual contract lives

| Concern | Artifact |
|---|---|
| Keeping the Charter true — amendment discipline, backed claims, constants in step | `specs/spec-pyforge-charter/SPEC.md` |
| The Lexicon, membership, the Dream-tier contract | `specs/spec-pyforge-genesis/SPEC.md` |
| The installer that ships this model to other repos | `pyforge-marshal` · `spec-genesis-installer` |

## If this ever gains requirements

It would mean the constitutive project had acquired a product — which is the signal to check
whether that product belongs to a Smith instead. Genesis holding buildable work is the exact
confusion the 2026-07-28 installer split resolved.
