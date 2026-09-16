---
spec: one-chain-per-station
status: ready   # 2026-09-16 — seeded `draft` the morning the token-savings fold (PRs #1382/#1383)
                # proved one Dream -> one Spec -> one epic chain on marshal; ruled and flipped the
                # same day. Six operator rulings (memlog 5-10) settled the rule and the pilot; the
                # three open questions were ruled by delegated research (memlog 26-28): no fifth
                # Dream status (the existing ladder yields `specified` once CAP-6 lands);
                # pyforge-core is the first cross-station-seam exemption, marshal-owned; the
                # Charter's only ritual is CAP-1, applied in this PR. Lives under docs/governance/
                # because its Dream is guild-owned (chain.py `_expected_spec_dir`: guild ->
                # docs/governance/spec-<slug>/) — the second instance of the 09-14 §5 shape.
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
open_questions: []
  # RAISED 2026-09-16 (morning) AND CLOSED 2026-09-16 (delegated research, memlog 26-28):
  #   fifth-dream-status-or-perpetually-specified -> neither is a new rule; the roster's
  #     act-based ladder rejects 'living' (same failure as the rejected 'building'), and
  #     README's "specified requires a Spec at ready or beyond" yields `specified` for
  #     every station Dream once CAP-6 flips its Spec to in-progress. Zero vocabulary change.
  #   pyforge-core-placement -> first cross-station-seam exemption; marshal stays accountable;
  #     Guild ruled out by the Charter's structural test (serves every Smith, judges none);
  #     a marshal CAP range ruled out because seven stations append against the kernel's
  #     contract and the foundry regenerates core as its own leaf. Same for testing-charter.
  #   charter-ritual -> none beyond CAP-1 (no vote exists); the ruling suffices as the decision
  #     and is fully applied by the Charter memlog + Dream log entries in the same PR.
---

> **Canonical contract.** Derived from `.memlog.md` (34 entries, the
> decision-of-record) and the Dream in `sources:`. Every question is ruled;
> the precedence order (standard > history > implementation) and the
> sequence (marshal, then steward) are operator constraints. Downstream may
> bind. Do not hand-edit — append the memlog and re-derive.

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
    FR ← CAP; (g) epics and ledger untouched except one new fold Epic. The
    record survives; derived bodies are disposable (Constraints, precedence).
  - **success:** Exactly one Spec folder with an open status per station
    **plus its declared seams** — a folder that survives the fold carries
    `fold-exemption: cross-station-seam` (marshal: `spec-pyforge-core`,
    `spec-pyforge-testing-charter` — the kernel and the testing kit, imported
    by every other station, regenerated by the foundry as their own leaves);
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
- **CAP-6 — Living station tiers, with zero new vocabulary.**
  - **intent:** The eight `spec-pyforge-<s>` flip `shipped` → `in-progress`
    and stay; `shipped` belongs to CAPs and stories. Station Dreams then read
    `specified` by the README's existing rule ("a Spec at `ready` or beyond")
    and never flip again — no fifth status (the roster's act-based ladder
    rejected `building` for the same reason it would reject `living`). One
    README sentence records the consequence; the eight `realized` station
    Dreams that today carry progress phrases under a terminal label
    (`status-body-consistency` warns on herald, marshal, mason) are corrected
    by the same act.
  - **success:** No station Spec is terminal; every station Dream reads
    `specified`; `status-body-consistency` reports zero findings on the eight
    station Dreams; `dream_statuses` in the roster is unchanged.
- **CAP-7 — The foundry on-ramp is recorded, standard included.**
  - **intent:** `spec-foundry-regenerate-not-fold`'s memlog names the eight
    folded station Specs as B's starting five-fields (its CAP-5, "one
    starting contract across two git roots") **and names this standard** —
    Dream-append-first, the exemption list, the seam rule, FR ← CAP — as
    B's starting discipline, so the shape is evergreen across both roots.
  - **success:** The entry exists before the second station fold (steward)
    lands.
- **CAP-8 — The marshal pilot.**
  - **intent:** CAP-3 executed on pyforge-marshal: 58 Spec folders → 1,
    55 Dreams → 1 (eight already folded 2026-08-08), CAP-4 sharding live,
    CAP-5 PRD re-derive done.
  - **success:** Marshal renders one Dream, one Spec, one PRD, one spine, one
    `epics.md`; planning detectors green; `fleet-picture` story counts
    unchanged.

## Constraints

- **Precedence (operator, 2026-09-16): the evergreen standard > historical
  accuracy > current implementation.** CAP re-mint renumbers freely into the
  station namespace — provenance is a memlog line, not preserved numbering.
  An absorbed folder is reduced to a pointer header plus its memlog; derived
  bodies are disposable, git is the historical record. The PRD is re-derived
  *to* the standard, never reconciled to past FR numbering. Where a detector,
  doc, or README convention encodes the old shape, the standard wins and the
  artifact moves — never the reverse.
- **Eventual consistency.** The fleet converges one station PR at a time; a
  folded station and an unfolded one both pass every detector throughout.
  `chain-sprawl-check` baselines from a dated snapshot — only *new*
  unexempted folders are findings. No flag day.
- **Evergreen and portable.** Written once, applied to both roots —
  local-recipes now, pyforge-foundry on cutover. B inherits Dream-append-
  first, the exemption vocabulary, the seam rule, and FR ← CAP as its
  starting discipline (CAP-7 records the standard, not just the eight Specs).
- **Sequence.** Marshal (CAP-8), then steward, then scribe · herald · doctor
  · atlas · warden; mason is already one Spec. CAP-1/2 land before marshal's
  fold so it does not refill while underway.
- No new machinery beyond CAP-2 and CAP-5's check; every fold mechanism
  already exists with precedent (archive-in-place ×14, `covers-dreams:`,
  `absorbed` ×5, `superseded` ×2, `bmad-spec` ID preservation, INV-A ranges,
  surface-overlap tolerance).
- Never hand-edit a `SPEC.md`; a fold is memlog appends plus re-derive.
- The decision **record** is never deleted — memlogs and git history survive
  every fold. Folders archive and point; their bodies need not.
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
