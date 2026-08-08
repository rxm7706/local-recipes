---
id: SPEC-pyforge-charter
spec: pyforge-charter
status: in-progress
owner-dream: docs/dreams/pyforge-charter.md
covers-dreams:
  # Absorbed 2026-08-08 as CAP-5..CAP-8 + the Dream's § Satellite: The Seed.
  # `owner: guild` closed at one; this Spec is the whole constitutive chain.
  - docs/dreams/pyforge-genesis.md
surface:
  - docs/dreams/pyforge-charter.md
  - docs/dreams/README.md          # the Tier-0 frontmatter contract (absorbed: was spec-pyforge-genesis's surface)
sources:
  - ../../../docs/dreams/pyforge-charter.md
  - ../../../archive/docs/dreams/pyforge-genesis.md   # absorbed 2026-08-08; archived, not deleted
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
- **CAP-5 — membership is legible.** *(Absorbed 2026-08-08 from `spec-pyforge-genesis`.)*
  *Intent:* a reader can answer "who are the Smiths, and what does each own?" without reading
  code. *Success:* the roster, each station's mandate, motto and craft, and the `owner:`
  through-line are readable from the Charter alone.
- **CAP-6 — the Dream tier is self-describing.** *(Absorbed 2026-08-08.)* *Intent:* the
  frontmatter contract (`type` · `owner` · `status`) and the Dream lifecycle are documented
  where Dreams live. *Success:* `docs/dreams/README.md` states the vocabulary, the lifecycle
  order, and the practice/dream distinction, and matches what the detectors enforce.
- **CAP-7 — constitutive claims are enforced, not asserted.** *(Absorbed 2026-08-08.)*
  *Intent:* the Charter's own enforcement claims are real. *Success:* `dream-unowned` fires on
  a Dream with no station, a station outside the eight, or a `guild` that is not this Charter;
  the Guildhall refuses to publish an unattributable row (§7); and `GUILD_DREAMS` in **both**
  detectors matches the one Dream §5 names.
- **CAP-8 — the seed is recorded, and distinguished from its installer.** *(Absorbed
  2026-08-08.)* *Intent:* the operating model is legible as something installable elsewhere,
  without that record drifting into the buildable installer the Marshal owns. *Success:* the
  Charter's § *Satellite: The Seed* states the master idea, the alignment instrument and the
  greenfield/brownfield seed, and names the installer as Marshal-owned buildable work rather
  than describing its verbs; no constitutive document specifies installer behaviour.

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
- **Constitutive ≠ homeless, and ≠ buildable.** *(Absorbed 2026-08-08.)* This chain lives in
  `docs/governance/`, not under `_bmad-output/projects/` — no Smith may own the document that
  constitutes the Smiths. Nothing here ships as code.
- **This chain holds no station's work.** *(Absorbed 2026-08-08.)* If a chain lands in
  `docs/governance/` that is owned by a Smith, that is a filing error, not an exception.

## Non-goals

- **Rewriting the Charter into a Spec.** The two are different nouns; this governs the
  document's integrity, not its content.
- **Gating amendments on tooling.** A constitutional change may precede its enforcement —
  but the gap is recorded, not left implicit.
- **Extending `guild` beyond this one Dream.** Closed by §5 as amended 2026-08-08; a second
  `guild` is an unassigned Dream hiding behind a collective noun.
- **The installer.** *(Absorbed 2026-08-08.)* Standing up a greenfield or brownfield repo is
  buildable work owned by the Marshal. This Spec records the seed; it never specifies the
  machine that plants it.
- **A ninth station.** *(Absorbed 2026-08-08.)* `guild` marks a Dream above the roster, never
  beside it.

## Success signal

A reader can reconstruct every constitutional change from the Realization log alone —
what it said before, what it says now, and why — and every enforcement claim in the document
maps to a detector that actually fails. A newcomer reads the Charter and can name the eight
Smiths, what each is accountable for, and how a Dream becomes code, without reading a line of
source.

As of 2026-08-08: five amendments recorded (§5 owning-is-becoming, §6 Doctor's verdict, §7
accountability-made-real, §5 `guild` closed at one, §5 outcome-and-mechanism), each with its
superseded text quoted and its detectors updated in the same pass. Concretely: **8 stations ·
1 constitutive Dream · 8 projects** — plus the `dream-unowned` check live in
`bmad_drift_check.py` and the Guildhall gating on attribution.
