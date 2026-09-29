---
id: SPEC-pyforge-charter
spec: pyforge-charter
status: in-progress
owner-dream: docs/dreams/pyforge-charter.md
covers-dreams:
  # Absorbed 2026-08-08 as CAP-5..CAP-8 + the Dream's § Satellite: The Seed.
  # `owner: guild` closed at one; this Spec is the whole constitutive chain.
  # 2026-09-14: `guild` re-opened by §5 amendment for one further shape only — a gate
  # that judges all eight Smiths (spec-coverage-gate-independence, beside this one).
  # This Spec is still the whole CONSTITUTIVE chain; the sibling is a gate, not a constitution.
  - archive/docs/dreams/pyforge-genesis.md   # moved out of docs/dreams/ in the same commit
surface:
  - docs/dreams/pyforge-charter.md
  - docs/dreams/README.md          # the Tier-0 frontmatter contract (absorbed: was spec-pyforge-genesis's surface)
sources:
  - ../../../docs/dreams/pyforge-charter.md
  - ../../../archive/docs/dreams/pyforge-genesis.md   # absorbed 2026-08-08; archived, not deleted
open_questions:
  - "THE GUILDHALL REFERENT (§7): which surface is the hall, and where does CAP-7's refusal-to-publish gate live? The machine that gate lived in no longer exists — `docs/dashboard/generate.py` + `check_render.js` are retired and `retired-console-check` fails CI if they return (`scripts/detectors.py:216`), and `[[factory-console]]`'s own Spec is `superseded`. The three live surfaces are Atlas's Vizro/BSL fleet board (zero occurrences of `owner`/`unowned`), the Wagtail Lane-1 CMS, and eight `django-*` station portals — none of them Marshal's. §7 is a Lexicon noun, so the ruling is constitutional: a Charter amendment, not a station decision. Natural input: the Intelligence Hub's Track/Frame answers (a Track is exactly what a Guildhall displays). Sequence it AFTER the CAP-3/CAP-7 re-basings — adding an eighth constitutional claim while two existing ones are unbacked is what CAP-2 refuses."
  # RAISED AND CLOSED 2026-09-09 (operator, batch row guild-B1): "Is `guild` still the right
  # owner value for a single Dream?" — verbatim from the `(open)` entry of 2026-07-31, which
  # asked to be carried into the re-render and never was; this key read `[]` for forty days, so
  # no reader could see it. CLOSED: KEEP `guild`. The smell points the other way — `guild` does
  # not name the artifact, it names the ABSENCE OF A STATION, the one legal way for a Dream to
  # have no accountable Smith. That is a job no other value does, so CAP-4 is satisfied, not
  # strained. Every alternative fails structurally: `owner: charter` is circular, `owner: none`
  # re-creates the `dream-unowned` hole §5 exists to close, and a Smith owning the Charter breaks
  # §5 ("the hand that builds is never the gate that judges"). See the Non-goal below.
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
- **CAP-3 — constants have exactly one home, and every reader reads it.** *(Re-based
  2026-09-09; the superseded success criterion, quoted per CAP-1: "`STATIONS` and
  `GUILD_DREAMS` agree across `bmad_drift_check.py` and `generate.py`" — neither file holds
  them any more. Doctor Story 6-8 moved the constants into `docs/governance/guild-roster.json`
  and 6-9 retired the copy, reasoning preserved at `scripts/fleet_scan.py:995-1003`;
  `generate.py` is gone, with `retired-console-check` existing to fail CI if it returns. The
  Charter's one capability about keeping constants true was being graded against a comparison
  that cannot be performed.)* *Intent:* a value the Charter fixes (the eight stations, the one
  `guild` Dream, the Dream statuses and types) is declared once and read everywhere.
  *Success:* `docs/governance/guild-roster.json` is the sole declaration; a hardcoded copy of
  `stations` / `guild_dreams` / `dream_statuses` / `dream_types` anywhere is a finding on
  sight. Live readers today: `scripts/fleet_scan.py:1002-1003`,
  `pyforge.doctor.sources.factory:1295`, `pyforge.doctor.sources.chain:838-852`. **One
  unguarded mirror is outstanding:** `pyforge.doctor.sources.chain:96` hardcodes
  `CONSTITUTIVE = frozenset({"pyforge-charter"})` and gates on it at `:634`, while the same
  module reads statuses, types and stations from the roster; it agrees today by luck, not by
  construction, and a second `guild` Dream would leave `chain.py` reporting it unowned while
  `factory.py` and `fleet_scan.py` permit it. A doctor story is minted for the fix (re-point
  `CONSTITUTIVE` at `guild_dreams` through `_load_dream_roster`) — doctor's verb under §5's
  outcome/mechanism rule, not a guild edit.
- **CAP-4 — the Lexicon stays exhaustive.** *Intent:* every noun does one job, every job has
  one noun. *Success:* a new organizational concept either maps to one of the seven or the
  Lexicon gains an entry — never a synonym smuggled into prose. **Ruling, 2026-09-09:** *an
  external vocabulary that overlaps the Lexicon is recorded here as a cross-walk and never
  enters the seven; adopting one of its terms as a Lexicon noun requires a §-level amendment
  with its own Realization-log entry.* Without that ruling, CAP-4 read literally would COMPEL
  the Lexicon to grow to nine or ten to absorb a third-party whitepaper's Frames, Ops and
  Organizational Memory — none of which is an organizational concept.
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
  the Guildhall refuses to publish an unattributable row (§7); and `guild_dreams` as declared
  in `guild-roster.json` matches the one Dream §5 names (re-based 2026-09-09; the superseded
  clause, quoted per CAP-1: "`GUILD_DREAMS` in **both** detectors matches the one Dream §5
  names"). **The Guildhall half is UNBACKED as of 2026-09-09** — the console it gated is
  retired and no successor surface enforces attribution, so §7's central claim is currently an
  assertion rather than an enforcement, which is what CAP-2 forbids in CAP-2's own document.
  It stays recorded, not quietly dropped, pending the Guildhall-referent amendment (see
  `open_questions:`).
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
- **~~Duplicated constitutional constants are a standing hazard. `GUILD_DREAMS` lives in two
  files by necessity (one runs in bare CI). Any change touches both, in the same commit.~~ —
  RETIRED 2026-09-09.** The necessity it rested on is gone: `guild-roster.json` is stdlib-JSON
  and repo-relative for exactly the bare-CI reason, so the constants have one home and no
  second file is required. What replaces it is stricter, not looser — see CAP-3: a hardcoded
  copy is now a finding on sight, not a maintenance obligation.
- **An external vocabulary is cross-walked, never merged.** The Intelligence Hub's terms land
  as a cross-walk subsection in the Charter's § The Lexicon (after § *Outcome and mechanism*,
  before § *The chain, read both ways*), in two blocks: Hub noun → Lexicon noun(s) with a
  closed `Relation` enum (`identity` · `subset` · `collision (n→1)` · `rule, not noun` ·
  `none`), and — the point of the exercise — a reverse block of Lexicon nouns with no Hub
  counterpart (Charter §1, Guild §3, Stations §5), showing the seven doing work the paper's
  seven cannot express. Two hazards the first block must not blur: **Cogs is a collision
  (2→1)** over Smiths §4 and Skills §6, and adopting it would undo §6's argument ("the unit of
  execution, *wielded, never worn*"); **Gates maps to a rule, not a noun**, since "the hand
  that builds is never the gate that judges" already makes Gate load-bearing at the doctrine
  level, so importing the paper's Gate gives one word two jobs. The gap analysis, tool
  inventories and file-path cells stay in steward's `spec-intelligence-hub/vocabulary-map.md`;
  the Charter gets the correspondence and the rule, which keeps it free of anything that goes
  stale when the paper revs.
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
  `guild` is an unassigned Dream hiding behind a collective noun. **And not retiring it
  either (2026-09-09):** `guild` names the *absence of a station* — the one legal way for a
  Dream to have no accountable Smith — which is a job no other value does. §5 states the
  reason on the next amendment.
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
1 constitutive Dream · 8 projects**.

**Realization status (2026-09-09): HELD at `in-progress`, deliberately not advanced.** The
success signal above is unmet by two of this Spec's own capabilities — CAP-3's named readers
no longer hold the constants and a third unguarded mirror has appeared at `chain.py:96`, and
CAP-7's Guildhall refusal-to-publish has no successor after the console retirement. Advancing
would assert exactly the unbacked enforcement CAP-2 exists to refuse. The `dream-unowned`
check is live, but through the roster, not through `bmad_drift_check.py`. **Owed to doctor,
not doable here:** this Spec is registered in neither `board.py`'s `DEFERRED_SPECS` nor any
decomposition — `in-progress` with eight capabilities, zero epics and zero ledger keys
anywhere in the fleet — so it is exempt from neither the decomposition expectation nor the
documented-deferral list. Register it with a reason ("a constitutive Spec whose
CAP-1/4/5/6/8 are document-integrity properties no story can pick up"), and route the three
detector-shaped capabilities (CAP-2, CAP-3, CAP-7) to doctor as stories under §5's
outcome/mechanism rule — guild owns the outcome, doctor owns the verb.
