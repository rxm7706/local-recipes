---
id: SPEC-pyforge-charter
spec: pyforge-charter
status: in-progress
owner-dream: docs/dreams/pyforge-charter.md
surface:
  - docs/dreams/pyforge-charter.md
sources:
  - ../../../../../../docs/dreams/pyforge-charter.md
open_questions: []
---

> **Canonical contract.** This SPEC is the complete contract for what to build, test and
> validate. Source documents in frontmatter are traceability only.

# The Charter — keeping the constitution true

## Why

The Charter is the unit of *legitimacy*: it authorizes the workers and does no work itself.
That makes a Spec for it look circular — and the circularity is the point. **A charter that
no one keeps current is not a constitution, it is a wall poster.**

This Spec governs the one thing the Charter cannot do for itself: **stay true.** Every claim
it makes about enforcement must be backed by something that fails; every amendment must be
legible as a dated decision; and every constant it names must match the code that reads it.
Three defects on 2026-07-28 alone prove the need — §5 contradicted its own detector for
weeks, §7 claimed a gate that printed and exited clean, and `GUILD_DREAMS` was duplicated
across two files that disagreed.

The Charter governs the *workers*; this Spec governs *the Charter*.

## Capabilities

- **CAP-1 — amendment, never silent edit.** *Intent:* a constitutional change is auditable.
  *Success:* every substantive change lands as a dated **Realization log** entry naming what
  it superseded and why; the superseded text is quoted, not deleted.
- **CAP-2 — claims are backed.** *Intent:* the Charter never asserts enforcement that does
  not exist. *Success:* each "enforced, not merely asserted" claim names a detector, and that
  detector fails when the claim is violated.
- **CAP-3 — constants match their readers.** *Intent:* a value the Charter fixes (the eight
  stations, the two `guild` Dreams) equals what the code enforcing it holds. *Success:*
  `STATIONS` and `GUILD_DREAMS` agree across `bmad_drift_check.py` and `generate.py`.
- **CAP-4 — the Lexicon stays exhaustive.** *Intent:* every noun does one job, every job has
  one noun. *Success:* a new organizational concept either maps to one of the seven or the
  Lexicon gains an entry — never a synonym smuggled into prose.

## Constraints

- **Tier 0 outranks everything.** No Spec, PRD, architecture or detector may contradict the
  Charter. Where one does, the Charter is right *or* it is amended — never quietly diverged
  from. §5 was contradicted by `pyforge-genesis.md` frontmatter and by `GUILD_DREAMS` for
  weeks, and nothing flagged it because the two drifted *compatibly*.
- **The amendment must move the artifacts with it.** An amendment that changes a constant
  and leaves a mirror stale is half-applied. The §5 amendment required edits in the Dream,
  two detectors and the board.
- **Duplicated constitutional constants are a standing hazard.** `GUILD_DREAMS` lives in two
  files by necessity (one runs in bare CI). Any change touches both, in the same commit.
- **The Charter does not prescribe craft.** It names who is accountable, never how a craft
  works — that is each station's Spec.

## Non-goals

- **Rewriting the Charter into a Spec.** The two are different nouns; this governs the
  document's integrity, not its content.
- **Gating amendments on tooling.** A constitutional change may precede its enforcement —
  but the gap is recorded, not left implicit.
- **Extending `guild` beyond two Dreams.** Closed by §5.

## Success signal

A reader can reconstruct every constitutional change from the Realization log alone —
what it said before, what it says now, and why — and every enforcement claim in the document
maps to a detector that actually fails. As of 2026-07-28: three amendments recorded (§5
owning-is-becoming, §6 Doctor's verdict, §7 accountability-made-real), each with its
superseded text quoted and its detector updated in the same pass.
