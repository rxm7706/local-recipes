---
spec: vocabulary-one-name-one-job
status: ready
created: "2026-09-14"
updated: "2026-09-15"
owner-dream: docs/dreams/vocabulary-one-name-one-job.md
surface: []
companions:
  - ../research/technical-vocabulary-three-source-reconciliation-2026-09-14.md
  - ../research/technical-identifier-shapes-inventory-2026-09-14.md
sources:
  - ../../../../../../docs/dreams/vocabulary-one-name-one-job.md
open_questions: []
---

> **Canonical contract.** Derived 2026-09-15 from
> `docs/dreams/vocabulary-one-name-one-job.md` § *Operator rulings (accepted
> 2026-09-15)* and this folder's `.memlog.md`. CAP-1..5 IDs are stable from the
> 2026-09-14 seed; CAP-6..8 are the shape half. CAP-4 is already met.

# SPEC — One name, one job

## Why

A pain: the estate speaks BMAD, Lexicon/status, Hub/Frame, and a Design teaching
layer, and writes the same story three non-derivable ways. A reader cannot tell
which vocabulary a status belongs to, and an agent cannot parse an id from the
place it was told about. The 2026-09-14 research measured that; the 2026-09-15
rulings choose what to do. This Spec is the contract those rulings bind.

## Corrections established by research (independent of the 2026-09-15 batch)

- **C-1** — the Hub has six shared abstractions, not seven. Charter amendment
  with a Realization-log entry, never an edit. (`DW-VOCAB-2026-09-14-1`, closed.)
- **C-2** — Guard category order follows whitepaper §5.5 (Source-Grounding is
  second). (`DW-VOCAB-2026-09-14-2`, closed.)
- **C-3** — `extension-point` is a parked Spec state, the sibling of `dreamt`.

## Capabilities

- **CAP-1 — the Spec ladder is declared.**
  - **intent:** the eight live Spec statuses get a stated naming rule, a
    definition per value, and the coupling rules to the Dream ladder, in one
    place a reader can use without opening `board.py`.
  - **success:** `draft`, `ready`, `in-progress` (grandfathered only), `shipped`,
    `archived`, `absorbed`, `superseded`, and `extension-point` are defined; the
    three ended-acts are not collapsed; `shipped` remains Spec-terminal; the
    enum is recommended, not required; unknown values are preserved and warned,
    never reset.

- **CAP-2 — one declared vocabulary source the detectors (and exit-code
  lattices) read.**
  - **intent:** replace the hard-coded status sets in `board.py`, `chain.py`, and
    `status_body_consistency.py`, and finish the exit-code unification half
    already scoped here (`DW-VOCAB-2026-09-14-8`).
  - **success:** adding or retiring a status is a one-place change; Doctor⊂Warden
    stays a declared subset; the aggregator's colliding `2` is named in that
    same file under a different key; new Specs are not written `in-progress`.

- **CAP-3 — the BMAD↔Lexicon cross-walk.**
  - **intent:** BMAD's daily nouns (Epic, Story, Sprint, PRD, Retrospective) map
    to a Lexicon noun or are named as having none, beside the Hub walk.
  - **success:** the Charter carries the walk (map, never join) and records
    Spec `shipped` ≠ story `done` ≠ Dream `realized`; ledger `blocked` is ours;
    `optional` is BMAD's retrospective lattice used where it belongs; `pitched`
    stays a declared optional Dream act, not required, not backfilled.

- **CAP-4 — the unnamed collisions get rulings.** *(Met 2026-09-14.)*
  - **intent:** `Track` and `Gate`/`Guard` are named and scoped.
  - **success:** artifacts write **evidence Track** vs **planning track**; Gate
    has three senses; `verdict` is the narrow word. No new story.

- **CAP-5 — the Design tier stops drifting.**
  - **intent:** practice vocabulary is teaching-only (except method-vs-machinery
    and project-context-as-constitution, which already describe this estate);
    retired BMAD names and Paige are corrected on the deck; a silent size/etag
    drift cannot recur.
  - **success:** the deck says it is teaching-only; Herald owns the pull;
    a detector flags recurrence; steward wrote the vocabulary ruling
    (`DW-VOCAB-2026-09-14-3`).

- **CAP-6 — mint-time story identity and new `DW-` ids.**
  - **intent:** one function, at mint time, makes the three story spellings
    derivable, and new deferred-work ids use two families with a station token.
  - **success:** heading `### Story N.N:` is human-canonical; the ledger key is
    machine-canonical; the spec filename is `spec-` plus that key; the 53
    existing slug divergences and 1338 existing `DW-` ids are not renamed;
    `deferred_work_promote.py` cannot mint a third family.

- **CAP-7 — remaining declared shapes.**
  - **intent:** long vs short station form, frontmatter casing, `S-N.N`, commit
    subjects, and Dream `status:` comments each have one rule.
  - **success:** one roster of eight stations (LONG for paths/packages/envs,
    SHORT for `owner:` / `Source` / prose); named `SPEC.md` stays kebab-led and
    story specs stay snake-led; `S-N.N` is legal in prose only; commit subjects
    are Capitalized sentences with no trailing period except `type(scope):`
    under `recipes/` and the CFE changelog; a trailing `#` on Dream `status:`
    is a finding.

- **CAP-8 — `check=` is a finding code.**
  - **intent:** the field that carries `spec-surface` does not also carry a
    package name.
  - **success:** the six `atlas.py` call sites put runtime data in `evidence`;
    124 kebab codes stay the code vocabulary.

## Constraints

- The Charter is Tier 0: corrections are amendments with Realization-log entries.
- Charter CAP-4: an external vocabulary is cross-walked and never joins the seven.
- Do not rename a Lexicon noun.
- Upstream BMAD literals are not ours to redefine; differ in the open.
- Status is not a proxy for work remaining — the ledger is.
- Memlogs are append-only; no migration rewrites history.
- A vocabulary change lands with the detector that reads it, in the same change.
- A shape change that is a mass rename is out of scope until reader-update cost
  is measured; this Spec does not pay that cost.
- `### Story N.N:` and the 124 kebab finding codes are not up for redesign.
- Do not flip any Epic 44 `blocked` key.

## Non-goals

- Adopting Cogs / Ops as PyForge nouns.
- A Frame registry. Frame v0.3 adoption already landed as steward Story 53.6.
- Renaming `sprint-status-ledger.yaml` as an end in itself.
- Re-litigating the Dream ladder.
- Renaming Spec `shipped` to `done`.
- Unifying branch names.
- Retro-fixing the 53 divergent slugs or the 1338 `DW-` ids.
- A vocabulary UI or linter-as-product outside this estate.

## Success signal

A reader can name the vocabulary and the act for any live status; detectors and
exit-code domains read one declaration; a newly minted story has one slugify;
a newly minted `DW-` id names its station and family; Design drift is detected
rather than noticed.

## Assumptions

- Steward Epic 59 is the dispatch home. Herald executes CAP-5's deck pull;
  doctor sources consume CAP-2; atlas owns the six `check=` call sites. Those
  surfaces are named on the stories; they are not a second epic.
