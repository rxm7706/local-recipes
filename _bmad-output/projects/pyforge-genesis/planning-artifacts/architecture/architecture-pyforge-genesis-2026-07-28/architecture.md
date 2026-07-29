---
name: pyforge-genesis
type: architecture
status: final
created: 2026-07-28
updated: 2026-07-28
---

# Architecture — pyforge-genesis (constitutive)

## There is no build substrate here

An architecture describes how something is built. `pyforge-genesis` builds nothing: it
records the operating model. The Charter is the unit of *legitimacy* and does no work
(Charter § The Lexicon §1), so there is no substrate to describe.

Present for the same reason as the PRD beside it — INV-3 admits no exemption, and a tier
that states its emptiness is auditable where an absent one is ambiguous.

## The one structural rule that does apply

**This project holds no station's work.** A chain filed here that is owned by a Smith is a
filing error, not an exception — enforced by `dream_chain_check.py` INV-2, which routes
`owner: guild` here and every other owner to `pyforge-<station>`.

`guild` is closed at two Dreams: the Charter, and Genesis itself. A third is an unassigned
Dream hiding behind a collective noun (`bmad_drift_check.py` → `dream-unowned`).

## Where architecture that matters lives

The installer's architecture — the write guard, the managed-region engine, detect-and-plan —
moved with it to `pyforge-marshal` as
`architecture/architecture-genesis-installer-2026-07-25/`.
