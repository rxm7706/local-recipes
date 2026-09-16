---
title: One Dream, one Spec, one PRD, one architecture, one epic chain — per station
type: dream
owner: guild
status: dreamt   # 2026-09-16 — seeded from the operator's fleet-consolidation ruling the
                 # morning the token-savings fold (PRs #1382/#1383) proved the shape on one
                 # chain. Six rulings recorded below; bmad-spec derives the Spec next.
fold-exemption: governance   # first live use of the vocabulary this Dream mints — a
                             # Lexicon amendment cannot be a dated section of a station Dream
---

# One Dream, one Spec, one PRD, one architecture, one epic chain — per station

## The Dream

A station's plan is one chain, readable end to end from one starting point:
the station Dream says *why*, the station Spec holds every capability in one
namespace, the PRD decomposes those capabilities into requirements, the
architecture spine holds the decisions, and one `epics.md` with one ledger
holds the work. Eight such chains, plus the Guild's — Charter and unifying
strategy — for what judges all eight. An operator, an agent, or a
whitepaper opens one file per tier and has the whole station.

Today the fleet has **171 Dreams and 172 Specs** for eight stations. Three of
the five tiers are already one-per-station (PRD, architecture spine,
epics/ledger). The two that sprawl — Dream and Spec — sprawl **by rule**:
Dream-first with no exemption for gap-closure, `bmad-spec`'s one-folder-
per-slug, and Spec → Story before code compose into a new Dream + Spec pair
for every effort. Sixty-one Dreams were folded on 2026-08-08; five weeks
later the count was back at 171, with 30 Dreams and 33 Specs minted in
the week of 2026-09-07 alone. **Consolidation without a minting rule is a
treadmill.** This Dream is the rule first, the fold second.

## The two findings that shape it

- **Two requirement namespaces.** Stories cite `spec-X CAP-n` 228 times and
  `FR-n` 185 times; INV-A accepts both. Marshal's PRD carries 196 FRs and
  its 58 Specs ~290 CAPs — and the PRD is already downstream of the Specs
  (its own header records FR-182..187 "backfilled" from Specs after the
  stories shipped). The PRD is a core BMAD artifact and stays; the fix is
  the Charter's own reading — **the PRD is the Spec's decomposition, so FRs
  derive from CAPs**, never independently. Steward's PRD already carries 26
  FR↔CAP cross-references, marshal's 13; this makes the emerging habit the
  rule.
- **Mason is the finished model.** Zero open Specs. Scribe is the disease
  in miniature: twelve open Specs carrying nineteen CAPs, nine of them
  single-CAP folders.

## What it looks like when real

- **Dream-append-first.** New work is a dated section in the station Dream,
  a memlog append and a `CAP-n` on the station Spec, and a Story. A *new*
  `docs/dreams/*.md` or `specs/spec-*/` folder carries a frontmatter
  `fold-exemption:` naming a reason from a closed list — `different-owner`,
  `different-lifecycle`, `cross-station-seam`, `governance` — and a doctor
  detector (`chain-sprawl-check`) fails an unexempted new folder. This is
  compatible with the 2026-09-12 gap-closure ruling: a dated section *is* a
  Dream seed; it is not a new file.
- **Eight station chains plus the Guild's.** Per station:
  `docs/dreams/pyforge-<s>.md` (living) → `spec-pyforge-<s>` (living, one
  CAP namespace) → the existing PRD, `ARCHITECTURE-SPINE.md`, `epics.md`
  and ledger. Guild: Charter + `spec-pyforge-unifying-strategy`. Not one
  fleet chain — the Charter's ownership grammar (a Spec lives in its owner's
  project; the station dispatches its stories) is what made the token-
  savings fold work.
- **Everything folds, nothing is deleted.** Every station ends with exactly
  one Spec folder. Open Specs fold as CAP ranges via `covers-dreams:`;
  shipped Specs' CAPs re-mint into the station namespace with provenance in
  the memlog (`CAP-n ← spec-old CAP-m, shipped <date>`); the old folders
  become `absorbed` pointers that keep their memlogs — the decision record
  (5,298 entries fleet-wide) survives intact. Regenerate-not-fold is
  honored: history stays on A.
- **The station Spec is a living contract.** `shipped` belongs to CAPs and
  stories, not to a station's standing contract; the eight `spec-pyforge-<s>`
  flip from `shipped` to `in-progress` and stay there. Station Dreams get a
  living status (or the README rules them perpetually `specified`).
- **FRs derive from CAPs.** Every FR minted after the rule date carries its
  source CAP; the PRD is re-derived as part of each fold, not backfilled
  weeks later; `fr-without-cap` (post-rule-date only) holds it.
- **The memlog is sharded before it eats the token economy.** A station
  memlog per CAP range (or a compiled summary the derive reads first) — at
  marshal scale the single log would pass 1,100 entries and every re-derive
  would re-read it whole, the `epics.md` problem in a new coat.
- **The fold is the foundry on-ramp.** The eight folded station Specs are
  B's starting five-fields (`spec-foundry-regenerate-not-fold` CAP-5's
  "one starting contract across two git roots"); recorded in that Spec's
  memlog.

## Constraints

- No new machinery beyond one detector and one FR check. Every fold
  mechanism already exists with precedent: archive-in-place banners (14),
  `covers-dreams:` (chain.py:348), `absorbed` + `absorbed-into:` (5),
  `superseded` + `superseded_by:` (2), `bmad-spec` ID preservation and
  next-N minting, INV-A range citations, surface-overlap tolerance (Epic 42).
- Never hand-edit a `SPEC.md`; every fold is memlog appends + re-derive.
- Never delete a Dream or Spec folder; archive and point.
- The PRD stays a BMAD artifact. It is derived, not retired.
- Accept two known costs, named: surface drift degrades from "which Spec's
  memlog must move" to "which station's"; and every fold at marshal scale is
  a multi-day effort of real stories, not a script.
- Pilot is **marshal** (operator, 2026-09-16): 58 Specs → 1, 55 Dreams → 1
  (eight already folded into `pyforge-marshal.md` on 2026-08-08). Biggest
  payoff and it forces the memlog sharding on day one.

## Kinships

- [[pyforge-charter]] — this amends the Lexicon's reading of Dream-first
  (Dream-append-first) and mints the `fold-exemption` vocabulary.
- [[coverage-gate-independence]] — the shape precedent: Guild-owned Spec,
  mechanism stories in doctor's `epics.md`.
- [[marshal-token-economy]] — the proof on one chain (2026-09-16: five
  Dreams and one Spec folded; `spec-marshal-token-economy` CAP-19..24;
  Epic 46).
- [[foundry-regenerate-not-fold]] · [[foundry-capability-ledger]] — the
  folded station Specs are B's starting contract (never `move`;
  `spec-python-foundry-cutover` is the cutover's own Spec); the ledger
  indexes what each station Spec absorbed.
- [[fleet-chain-completeness]] — the detector family (`chain-completeness`,
  `dream-chain`, `dreams-hygiene`) this Dream's `chain-sprawl-check` and
  `fr-without-cap` sit beside.
- [[vocabulary-one-name-one-job]] — the naming discipline the station
  namespace inherits.
- [[pyforge-unifying-strategy]] — the Guild chain's second member; already
  the de-facto fleet Spec (19 CAPs, 999 governed files, five Specs absorbed).

## Realization log

- **2026-09-16** — Seeded from the operator's ruling after the token-savings
  consolidation (PRs #1382/#1383) proved one Dream → one Spec → one epic
  chain on marshal's token-economy chain. Fleet analysis the same morning:
  171 Dreams / 172 Specs / 8 PRDs / 8 spines / 8 epic chains; 73 open Specs
  with 334 CAPs and 1,764 memlog entries; the 2026-08-08 61-Dream fold
  regrown in five weeks. Six operator rulings recorded: (1) Dream-append-
  first with a detector and a closed exemption list; (2) eight station
  chains plus the Guild's; (3) fold everything, shipped included, nothing
  deleted; (4) the PRD stays and derives from the Spec (operator: "isn't
  the PRD a required and critical artifact of the BMAD-METHOD" — yes; the
  retire option was withdrawn); (5) the fold is the foundry on-ramp; (6)
  marshal is the pilot. Next act: `bmad-spec` derives the Guild Spec under
  `docs/governance/spec-one-chain-per-station/`.
