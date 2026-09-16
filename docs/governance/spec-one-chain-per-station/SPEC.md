---
spec: one-chain-per-station
status: draft   # 2026-09-16 — seeded the same morning the token-savings fold (PRs #1382/#1383)
                # proved one Dream -> one Spec -> one epic chain on marshal. Six operator rulings
                # are already in the memlog (entries 5-10); three open questions below gate CAP-6
                # and the pyforge-core placement, not the rule or the pilot. Lives under
                # docs/governance/ because its Dream is guild-owned (chain.py `_expected_spec_dir`:
                # guild -> docs/governance/spec-<slug>/) — it amends the Charter's Lexicon reading.
created: "2026-09-16"
updated: "2026-09-16"
owner-dream: docs/dreams/one-chain-per-station.md
surface: []     # Deliberately empty until the mechanism stories land: chain-sprawl-check and
                # fr-without-cap will be doctor sources (declared here when they exist, the way
                # coverage-gate-independence declares its evaluator); the per-station fold PRs
                # touch surfaces already governed by each station's own Spec and stay there.
companions: []
sources:
  - ../../../docs/dreams/one-chain-per-station.md
open_questions:
  - "Do station Dreams get a fifth README status ('living'), or the rule 'a station Dream is perpetually specified'? (README change either way; gates CAP-6.)"
  - "Where does spec-pyforge-core live after the fold — a package, not a station (marshal-owned, 528 governed files)? A marshal CAP range, or the Guild chain beside unifying-strategy?"
  - "Does the Lexicon amendment need the Charter's §5 Guild ritual, or is the operator ruling as recorded sufficient?"
---

> **Canonical contract (draft).** Derived from `.memlog.md` (25 entries, the
> decision-of-record) and the Dream in `sources:`. The rule (CAP-1/2), the fold
> procedure (CAP-3), and the marshal pilot (CAP-8) are settled by operator
> ruling; the three `open_questions` gate only CAP-6's status vocabulary and
> one placement. Do not hand-edit — append the memlog and re-derive.

# SPEC — One Dream, one Spec, one PRD, one architecture, one epic chain — per station

## Why

Eight stations carry 171 Dreams and 172 Specs. Three of the five planning
tiers are already one-per-station (PRD, architecture spine, epics + ledger);
the two that sprawl do so **by rule** — Dream-first with no gap-closure
exemption, `bmad-spec`'s one-folder-per-slug, and Spec → Story before code
compose into a Dream + Spec pair per effort. Sixty-one Dreams were folded on
2026-08-08 and the count regrew to 171 in five weeks (30 Dreams and 33 Specs
in the week of 2026-09-07 alone). Two requirement namespaces coexist (`FR-n`
in PRDs, `CAP-n` in Specs; stories cite both, INV-A accepts both) and the
PRD is already downstream of the Specs it should decompose. The token-savings
fold (2026-09-16) proved the target shape on one chain. This Spec makes it
the fleet's shape — **the minting rule first, the fold second** — and keeps
the PRD as the BMAD artifact it is, derived rather than duplicated.

## Capabilities

- **CAP-1 — Dream-append-first is the Lexicon's reading of Dream-first.**
  - **intent:** New work is a dated section in the station Dream, a memlog
    append and a `CAP-n` on the station Spec, and a Story. A *new*
    `docs/dreams/*.md` or `specs/spec-*/` folder carries a frontmatter
    `fold-exemption:` from the closed list `different-owner` ·
    `different-lifecycle` · `cross-station-seam` · `governance`. A dated
    section *is* a Dream seed (compatible with the 2026-09-12 ruling).
  - **success:** `AGENTS.md`, `CLAUDE.md`, and `docs/dreams/README.md` state
    the rule and the list; the Lexicon amendment is logged in
    `spec-pyforge-charter`'s memlog.
- **CAP-2 — `chain-sprawl-check`.**
  - **intent:** A doctor source that fails any new Dream or Spec folder
    (against a dated baseline) lacking a valid `fold-exemption:`; wired into
    `detectors-ci` as a real FAIL, not advisory.
  - **success:** An unexempted new folder reds CI; this Spec's own Dream
    (exemption `governance`) passes.
- **CAP-3 — The station fold procedure, one PR per station.**
  - **intent:** (a) `covers-dreams:` on `spec-pyforge-<s>` for every folded
    Dream; (b) CAP re-mint with provenance for every open *and* shipped Spec
    (`CAP-n ← spec-old CAP-m, shipped <date>`); (c) old Spec folders become
    `absorbed` pointers keeping their memlogs; (d) Dreams archived in place
    with `Consolidated into` banners pointing at `pyforge-<s>.md`; (e) surface
    manifests merged with scoped baseline stamps; (f) PRD re-derived with
    FR ← CAP; (g) epics and ledger untouched except one new fold Epic.
    Nothing deleted.
  - **success:** Exactly one Spec folder with an open status per station;
    `dream-chain`, `dreams-hygiene`, `spec-surface`, `chain-completeness`,
    `story-status` green; every prior memlog entry still present.
- **CAP-4 — Memlog sharding.**
  - **intent:** The station Spec's memlog is a per-CAP-range shard set (or a
    compiled summary the derive reads first); `memlog.py append` routes by
    CAP. Mandatory before the marshal pilot's fold lands.
  - **success:** A marshal re-derive reads less than the whole log; entry
    count is preserved across the shard.
- **CAP-5 — FRs derive from CAPs.**
  - **intent:** Each PRD's frontmatter carries `fr-derivation-from: <date>`;
    every FR minted after it cites its source CAP; the PRD is re-derived as a
    step of each fold PR, never backfilled later; doctor `fr-without-cap`
    flags a post-date FR with no CAP.
  - **success:** Zero post-date FRs without a CAP fleet-wide.
- **CAP-6 — Living station tiers.**
  - **intent:** The eight `spec-pyforge-<s>` flip `shipped` → `in-progress`
    and stay; `shipped` belongs to CAPs and stories. Station Dreams get a
    status that does not flip on every fold (open question 1).
  - **success:** No station Spec is terminal; no station Dream changes status
    because a fold landed.
- **CAP-7 — The foundry on-ramp is recorded.**
  - **intent:** `spec-foundry-regenerate-not-fold`'s memlog names the eight
    folded station Specs as B's starting five-fields (its CAP-5, "one
    starting contract across two git roots").
  - **success:** The entry exists before the second station fold lands.
- **CAP-8 — The marshal pilot.**
  - **intent:** CAP-3 executed on pyforge-marshal: 58 Spec folders → 1,
    55 Dreams → 1 (eight already folded 2026-08-08), CAP-4 sharding live,
    CAP-5 PRD re-derive done.
  - **success:** Marshal renders one Dream, one Spec, one PRD, one spine, one
    `epics.md`; planning detectors green; `fleet-picture` story counts
    unchanged.

## Constraints

- No new machinery beyond CAP-2 and CAP-5's check; every fold mechanism
  already exists with precedent (archive-in-place ×14, `covers-dreams:`,
  `absorbed` ×5, `superseded` ×2, `bmad-spec` ID preservation, INV-A ranges,
  surface-overlap tolerance).
- Never hand-edit a `SPEC.md`; a fold is memlog appends plus re-derive.
- Never delete a Dream or Spec folder; archive and point.
- The PRD stays a BMAD artifact — derived, not retired (operator, 2026-09-16).
- Eight station chains plus the Guild's; never one fleet chain.
- Known costs accepted and named: surface drift degrades from "which Spec"
  to "which station"; a station fold is multi-day real-story work.

## Non-goals

- Rewriting shipped stories or renumbering existing epics.
- Touching `implementation-artifacts/` (Tier 3).
- Any change on B (`python-foundry`) — this Spec prepares A's contract; B
  re-derives (`spec-foundry-regenerate-not-fold`).
- Consolidating across stations (a marshal CAP never moves to steward).

## Success signal

An operator opens `docs/dreams/pyforge-<s>.md`, follows one link to
`spec-pyforge-<s>`, one to the PRD, one to the spine, one to `epics.md`, and
has the whole station — for all eight, and for the Guild. A new effort adds a
section, a CAP, and a Story, not a folder; the one detector that guards this
has been red at least once in CI and was fixed by an exemption or a fold,
never by silence.
