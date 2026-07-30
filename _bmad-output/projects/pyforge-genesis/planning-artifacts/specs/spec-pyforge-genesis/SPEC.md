---
id: SPEC-pyforge-genesis
spec: pyforge-genesis
status: in-progress
owner-dream: docs/dreams/pyforge-genesis.md
surface:
  - docs/dreams/README.md          # the Dream-tier contract; the Charter itself is spec-pyforge-charter
sources:
  - ../../../../../../docs/dreams/pyforge-genesis.md
  - ../../../../../../docs/dreams/pyforge-charter.md
  - ../../../../../../docs/dreams/genesis-installer.md
open_questions: []
---

> **Canonical contract.** This SPEC and the files in `companions:` are the complete,
> preservation-validated contract for what to build, test, and validate. Source documents
> listed in frontmatter are for traceability only.

# Genesis — the operating model, recorded

## Why

Genesis is the **constitutive** half of the operating model: the master idea, the umbrella
narrative, and the records that make the Guild legible — the Charter, the Lexicon, the
membership. It is one of exactly two Dreams that **precede the stations** (Charter §5), and
its project is the one not named for a Smith, because the Dreams it holds existed before
there were Smiths to own them.

It is not the installer. `genesis init` / `genesis adopt` — the machine that installs this
model into any repository — is buildable work owned by the **Marshal**
([[genesis-installer]], `spec-genesis-installer`). This Dream is *what gets installed*;
that Dream is *what installs it*. Conflating the two is what produced a Dream doing two
jobs, an `owner:` that flipped twice, and a Charter clause that contradicted its own
detector for weeks.

The distinction is the Lexicon's own: the **Charter** is the unit of *legitimacy* and does
no work; the **Spec** is the unit of *contract* and governs work. Genesis records the
former. That is why this Spec's surface is the constitutive documents themselves, and why
it declares no code.

## Capabilities

- **CAP-1 — the Charter is authoritative and current.** *Intent:* one document constitutes
  the Guild, and nothing downstream may contradict it. *Success:* the eight stations, the
  seven-noun Lexicon, the doctrine and the branding law are stated in one place; every
  amendment is a **recorded** entry in the Realization log, never a silent edit.
- **CAP-2 — membership is legible.** *Intent:* a reader can answer "who are the Smiths, and
  what does each own?" without reading code. *Success:* the roster, each station's mandate,
  motto and craft, and the `owner:` through-line are readable from the Charter alone.
- **CAP-3 — the Dream tier is self-describing.** *Intent:* the frontmatter contract
  (`type` · `owner` · `status`) and the lifecycle are documented where Dreams live.
  *Success:* `docs/dreams/README.md` states the vocabulary, the lifecycle order, and the
  practice/dream distinction, and matches what the detectors enforce.
- **CAP-4 — constitutive claims are enforced, not asserted.** *Intent:* the Charter's own
  enforcement claims are real. *Success:* `dream-unowned` fires on a Dream with no station
  or a third `guild`; the Guildhall refuses to publish an unattributable row (§7); and
  `GUILD_DREAMS` in **both** detectors matches the two Dreams §5 names.

## Constraints

- **Amendment, never silent edit.** Constitutional documents change by a dated Realization
  log entry that states what was superseded and why. Three amendments on 2026-07-28 follow
  this form; a fourth that did not would be a defect regardless of its content.
- **`owner: guild` is closed at two.** This Dream and the Charter. A third is an unassigned
  Dream hiding behind a collective noun — the retired `owner: crew` was exactly that, on
  four Dreams.
- **Constitutive ≠ homeless, and ≠ buildable.** These chains live in `pyforge-genesis`,
  alongside the stations rather than in a placeholder. The Charter carries its own Spec
  (`spec-pyforge-charter`, amendment discipline); this one records the Lexicon and
  membership. Nothing here ships as code.
- **The mirror must not drift.** `GUILD_DREAMS` exists in `scripts/bmad_drift_check.py`
  **and** `docs/dashboard/generate.py`. Updating one and not the other made the board warn
  on a Dream the Charter explicitly permits (2026-07-28). Duplicated constitutional
  constants are a standing hazard here.
- **This project holds no station's work.** If a chain lands here that is owned by a Smith,
  that is a filing error, not an exception.

## Non-goals

- **The installer** — `genesis init` / `adopt` is [[genesis-installer]], Marshal's.
- **A ninth station.** `guild` marks a Dream above the roster, never beside it.
- **Being the placeholder's successor.** `local-recipes` was retired 2026-07-28; this
  project is not where un-triaged Dreams land. An unassigned Dream is a finding.
- **Prescribing craft.** The Charter says who is accountable, never how a craft works —
  that belongs to each station's own Spec.

## Success signal

A newcomer reads the Charter and can name the eight Smiths, what each is accountable for,
and how a Dream becomes code — without reading a line of source. Every claim the Charter
makes about enforcement is backed by a detector that fails, and every amendment since
2026-07-25 is legible as a dated entry stating what it superseded.

Concretely today: 30 Dreams across 8 stations · 2 constitutive · 9 projects · the
`dream-unowned` check live in `bmad_drift_check.py`, and the Guildhall gating on
attribution.
