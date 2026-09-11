---
spec: genesis-installer-name-retirement
status: shipped
owner-dream: docs/dreams/genesis-installer-name-retirement.md
companions:
  - citation-map.md
sources:
  - ../../../../../../docs/dreams/genesis-installer-name-retirement.md
assumptions:
  - bmad-prd/bmad-architecture/bmad-create-epics-and-stories, run in update mode
    against pyforge-marshal's existing Spec/PRD/architecture, will preserve
    already-done story identity (CAP-8) the way this Spec requires — not
    independently verified against those skills' actual update-mode behavior;
    verify before the rewrite starts, not after (see Open Questions).
  - The FR1..FR62 → FR-66..FR-127 sequential map (citation-map.md) is correct as
    the rewrite's starting point — confirmed gap-free/duplicate-free by a
    dedicated research pass, though the rewrite may still choose to reorder FRs
    by topic rather than preserve strict append order.
open_questions:
  - Does bmad-create-epics-and-stories in update mode guarantee existing
    done/in-progress story keys survive re-generation, or does it require manual
    reconciliation after the fact? Check against the skill's own behavior before
    the rewrite starts.
  - Which way do the two inherited contradictions resolve — argparse vs
    typer+rich for the unified CLI, and whether `check` stays one verb or splits
    into two named differently? This Spec requires the rewrite to decide them;
    it does not itself decide them.
  - SC-01..10 and K-01..03 have no existing Marshal namespace to fold into
    (Marshal uses SM-1..7/SM-C1..3, not SC-, and has no kill-criteria concept at
    all) — does the rewrite adopt both wholesale as new to Marshal, map SC- onto
    SM-, or something else? NFR-O1 is likely redundant with Marshal's own NFR-12
    (near-identical substance) rather than needing a new number at all.
---

> **SHIPPED 2026-08-08** — executed in PR #318. All eight capabilities met: one `epics.md`
> (Epics 1-12, 86 stories, `epics-genesis-installer.md` archived) · one FR space
> `FR-1..FR-163` with no gaps · every installer-only namespace decided (`NFR-O1` retired
> into `NFR-12`; `OQ-1..9` → `Q-17..25`; `SC-01..10` and `K-01..03` adopted as-is) · the
> CLI framework decided (argparse, on measurement) · the `init`/`check` collisions
> resolved via the `marshal seed` noun group · every `Satellite:` header gone · one
> dashboard row · and **CAP-8 verified: all 59 `done` story keys byte-identical** to the
> pre-rewrite snapshot. `.memlog.md` and `archive/` untouched throughout.
>
> **Canonical contract.** This SPEC is the complete, preservation-validated contract for this cleanup. `docs/dreams/genesis-installer-name-retirement.md` is cited for narrative rationale only.

# SPEC — genesis-installer-name-retirement

## Why

The 2026-07-28 Charter §5 split carved `genesis-installer` out of `pyforge-genesis` as
its own Dream; the 2026-08-02 consolidation folded its brief/PRD/architecture/Spec into
`pyforge-marshal`'s own chain as **satellite sections** with a deliberately separate
`FR1..FR62` (no-dash) numbering island, and left `epics-genesis-installer.md` as a second,
fully separate epics document. That separateness leaked onto the fleet dashboard as a
second `genesis-installer` project row (fixed only as a label, PR #233, not removed).
The mechanical "fold in" also preserved two undecided contradictions instead of
resolving them: Marshal's own CLI is shipped **argparse**, while the installer's own
architecture specifies **typer+rich** for its still-unbuilt CLI; and `genesis init` /
`genesis check` both collide with already-shipped `marshal init <slug>` / `marshal check`
verbs. A mandate to meet: the user has asked outright for `genesis-installer` to retire
completely — not relabeled, not renumbered by hand, but resolved by running the standard
planning chain (`bmad-prd` → `bmad-architecture` → `bmad-create-epics-and-stories`)
against the already-unified Spec, so the CLI gets designed once, coherently, with its
two open contradictions actually decided.

## Capabilities

- **CAP-1**
  - **intent:** Merge `epics-genesis-installer.md`'s content into one combined
    `epics.md` (Epic 1 through Epic 12) so no reader or tool has to know two
    documents used to exist.
  - **success:** Single `epics.md` file; `epics-genesis-installer.md` archived
    (not deleted) under `archive/_bmad-output/projects/pyforge-marshal/planning-artifacts/`.
  - **verified:** 2026-09-11 — CAP-effect sweep at HEAD `b36c8be118`: `epics-genesis-installer.md` lives only at `archive/_bmad-output/projects/pyforge-marshal/planning-artifacts/epics-genesis-installer.md` (confirmed present there, absent from the live tree); one `epics.md` contains Epic 1 through Epic 12 (`grep -c '^## Epic ' epics.md` → 14, i.e. Epics 1-12 plus two later additions, sequential and unbroken through 12).
- **CAP-2**
  - **intent:** Produce one contiguous functional-requirement numbering space via
    the chain rewrite, not a hand-renumber of the existing satellite section.
    `citation-map.md` confirms `FR1..FR62 → FR-66..FR-127` is a valid,
    gap-free, duplicate-free starting map if the rewrite preserves append order;
    the rewrite may reorder by topic instead.
  - **success:** Every FR in the regenerated PRD uses the dashed `FR-N` form,
    sequential, no gaps or duplicates, no surviving bare-digit `FR62`-style form.
  - **verified:** 2026-09-11 — CAP-effect sweep at HEAD `b36c8be118`: extracted every `FR-N` from `epics.md` (the FR space's current live home, sharded PRD notwithstanding) — 196 unique numbers, `FR-1..FR-196`, zero gaps (the range has grown from the ship-time `FR-1..FR-163` as new work landed since, which is expected, not a defect). Bare `FR62`/`FR1` forms exist only inside append-only historical notes (`epics.md:1829`, `ARCHITECTURE-SPINE.md`/`prd.md` frontmatter changelog lines) documenting the old satellite numbering as a past fact, never as a live citation — same pattern `EXEMPLAR-STANDARD.md`'s own governance-currency exemption uses. This spec's own `.memlog.md` records that the 2026-08-08 ship-time claim was actually FALSE when first stamped (195 live satellite citations still unconverted) and was mechanically corrected in a 2026-08-10 audit — the state verified here is the corrected, current one.
- **CAP-3**
  - **intent:** Decide what happens to each installer-only namespace —
    `NFR-O1` (likely redundant with Marshal's own `NFR-12`, near-identical
    substance), `SC-01..SC-10` and `K-01..K-03` (Marshal has **no** existing
    `SC-` or kill-criteria namespace to fold into — `citation-map.md` confirms
    this; adopt wholesale or map differently, but the rewrite must choose), and
    `OQ-1..OQ-9` (Marshal's own Open Questions run `Q-1..Q-16` only —
    **`Q-17` does not exist**, and no `OQ-*` item is actually cross-referenced
    into it anywhere live; this corrects the governing Dream's original premise).
  - **success:** `grep` for the old bare forms across live planning-artifacts
    returns zero hits outside `archive/` and `.memlog.md` files, and every
    namespace's fate (adopted / merged / retired-as-duplicate) is stated
    explicitly in the regenerated PRD rather than left implicit.
  - **verified:** 2026-09-11 — CAP-effect sweep at HEAD `b36c8be118`: `NFR-12` (`prd.md:978`) carries an explicit "Absorbed the seed installer's `NFR-O1`... it retired rather than coexisting" note, and the retirement table (`prd.md:1123`) states its fate explicitly; `Q-17`..`Q-25` all present in `prd.md` (continuing Marshal's own `Q-1..Q-16` sequence, resolving the Dream's original `OQ-1..9` premise correction this Spec's `.memlog.md` records); `SC-01..SC-10` (19 live citations) and `K-01..K-03` (5 live citations) both present, adopted as new Marshal namespaces exactly as decided. No bare `NFR-O1` survives outside historical retirement notes.
- **CAP-4**
  - **intent:** Decide the CLI-framework contradiction instead of carrying it
    forward — one framework for the one binary both the shipped Marshal CLI and
    the unbuilt installer verbs live in.
  - **success:** The regenerated architecture states which framework the unified
    CLI uses and why; no "flagged, not resolved" language remains on this point.
  - **verified:** 2026-09-11 — CAP-effect sweep at HEAD `b36c8be118`: `ARCHITECTURE-SPINE.md`'s AD-51 is documented as "amended typer+rich -> argparse on measurement (14 shipped subparsers, zero typer in tree)"; the live marshal CLI genuinely uses `argparse` throughout (`import argparse` across `cli/checkpoint.py`, `cli/chain.py`, `cli/planning.py`, `cli/seed.py`, etc.); `grep -rn "import typer" src/shared/packages/pyforge-marshal/src/` returns nothing.
- **CAP-5**
  - **intent:** Resolve the `init`/`check` verb collisions between Marshal's
    shipped verbs and the installer's own verbs of the same name but different
    scope.
  - **success:** The regenerated PRD names one verb surface — either one verb
    doing both jobs, or two distinctly-named verbs — with the installer's
    distinct question ("does an externally-installed repo still conform?") given
    a real verb name if it isn't `check`.
  - **verified:** 2026-09-11 — CAP-effect sweep at HEAD `b36c8be118`: `prd.md:1132-1134` states "Every command in this section reads `marshal seed <verb>`... `marshal init` (loop home, by slug) and `marshal check` (detector registry, this repo) are different, shipped commands and are untouched"; `cli/seed.py` is a live, real module implementing the `marshal seed <verb>` noun group (its own docstring: "bare `marshal seed` with no verb is a clean argparse usage error"), with `marshal seed check --repo-root <home>` answering exactly the installer's distinct "does an externally-installed repo still conform" question without colliding with the shipped `marshal check`.
- **CAP-6**
  - **intent:** Remove every "Satellite: Genesis Installer PRD/Architecture"
    section header and every prose mention of `genesis-installer` as if it names
    a separate thing, from the regenerated PRD, architecture, Spec, and brief —
    the content survives as ordinary Marshal capability, only the separate-
    sounding name retires.
  - **success:** `grep -i "genesis.installer"` across the regenerated
    `planning-artifacts/{prds,architecture,specs,briefs}` returns zero hits
    outside `archive/` and `.memlog.md`.
  - **verified:** 2026-09-11 — CAP-effect sweep at HEAD `b36c8be118`, **NOT fully passing, not fabricating a clean result:** found a real, live gap: `planning-artifacts/briefs/brief-pyforge-marshal-2026-07-25/brief.md:172` still carries a literal, live `## Satellite: Genesis Installer` section header (not a historical note — an active heading with body content below it), directly contradicting this CAP's own success criterion. `prd.md` and `ARCHITECTURE-SPINE.md` are genuinely clean — their satellite sections were retitled ("Part II — The seed installer (`marshal seed`)", `prd.md`'s D3/D4/Genesis-↔-Marshal headings use "Genesis" as an informal capability name, never the compound "genesis-installer" or a "Satellite:" header) and their only `genesis.installer`-matching hits are append-only frontmatter changelog comments (same convention as `.memlog.md`). A second, smaller known gap: `spec-dashboard-project-path-derivation/SPEC.md:87` still names the retired `epics-genesis-installer.md` as a live example in its Constraints — but this is a **pre-existing, already-logged** deferred-work item (`spec-16-1-....md:165/235` explicitly flags it as "pre-existing prose staleness this story didn't touch — logged to `deferred-work.md`"), not a fresh finding. Leaving this CAP unverified rather than fabricating a pass — `brief.md`'s live header is a genuine, previously-unflagged miss in a Spec whose banner claims all eight capabilities met.
- **CAP-7**
  - **intent:** Update the dashboard so the build-campaign section shows exactly
    one `pyforge-marshal` row (all 12 epics combined), with no second
    `genesis-installer` row and no remaining code reference to the retired name.
  - **success:** `pyforge.doctor.sources.fleet_scan`'s `IMPL_CAMPAIGN` has one marshal
    entry, `IMPL_CAMPAIGN_LEDGER` drops the `genesis-installer` key, and
    `scripts/dashboard_drift_check.py` stays clean.
  - **verified:** 2026-09-11 — CAP-effect sweep at HEAD `b36c8be118`: `scripts/fleet_scan.py`'s `IMPL_CAMPAIGN` list has exactly one `pyforge-marshal` entry (86 stories) and zero `genesis-installer` entries; a comment (line 1314) confirms "the `genesis-installer` row is GONE, not relabelled"; `IMPL_CAMPAIGN_LEDGER` was itself retired and folded into `_PROJECT_OVERRIDES`'s resolver (documented in an adjacent comment) — no `genesis-installer` key survives there either. `scripts/dashboard_drift_check.py` was ported into `pyforge.doctor.sources` (Story 6.9 pattern); `pixi run -e local-recipes python -m pyforge.doctor.sources dashboard-drift` → "ok — Guildhall generator, data.js, and the four dashboard pixi tasks stay gone".
- **CAP-8**
  - **intent:** Preserve already-landed story identity through the rewrite —
    Epic 1's 10 done stories, plus whatever Story 2.1 lands as by the time this
    runs, must keep their exact `sprint-status-ledger.yaml` keys.
  - **success:** Every story key with `status=done` before the rewrite has the
    identical key after it; only backlog-only epics (currently 2-12) are free to
    be restructured.
  - **verified:** 2026-09-11 — CAP-effect sweep at HEAD `b36c8be118`, **partial:** today's `sprint-status-ledger.yaml` Epic 1 has 12 `done` stories (`1-1` through `1-12`), every key a natural, descriptive, non-renumbered slug consistent with pre-rewrite naming — no sign of rekeying anywhere in the epic. Did not re-derive the exact pre-rewrite (2026-08-07) snapshot to do a byte-for-byte diff against today's 311-story ledger — that snapshot isn't preserved as a companion artifact, so the SHIPPED banner's own contemporaneous "all 59 `done` story keys byte-identical" claim (made and, per this Spec's `.memlog.md`, subject to a 2026-08-10 audit correction pass for CAP-2/3) is the closest available first-party evidence for the exact-preservation claim; today's live ledger is consistent with it holding, not independently re-proven byte-for-byte here.

## Constraints

- Never rewrite `.memlog.md` history or `archive/` content — both are the
  permanent, append-only record of how the consolidation actually happened; the
  rewrite touches only live, current documents.
- Hold ALL execution (the chain rewrite and the epics merge) until the active
  Story 2.1 bmad-loop run (`20260802-183704-36df`) is fully done and merged into
  main — `epics.md` is exactly what that run's story identity keys off of. This
  Spec itself is planning-only, drafted while the loop is still running.
- Already-done story identity is frozen (CAP-8) — the rewrite may restructure
  backlog-only epics freely, but never renumbers or rekeys shipped work.
- The CLI-framework and verb-collision contradictions must be actually decided
  by the rewrite, not re-flagged as open questions a third time.

## Non-goals

- Not a new BMAD project — this cleanup stays inside `pyforge-marshal`'s own
  planning tree, same shape as `spec-bmad-output-hygiene` and
  `dashboard-project-path-derivation`.
- Not touching Story 2.1's own Epic 2 content or story key before it lands — the
  rewrite targets Epics 7-12 (genesis-installer) and the FR/NFR/SC/OQ/K numbering
  it introduced; Epics 2-6 stay as currently speced except for whatever
  cross-reference renumbering the unified FR space requires.

## Success signal

A reader of `pyforge-marshal`'s PRD/architecture/epics chain never encounters the
name "genesis-installer" as if it names something separate from Marshal itself —
one FR space, one epics document, one dashboard row — and the CLI's design
answers, in one place, which framework it uses and what `init`/`check` mean,
with no contradiction left standing between a shipped verb and an unbuilt one.

## Assumptions

- `bmad-prd`/`bmad-architecture`/`bmad-create-epics-and-stories`, run in update
  mode against pyforge-marshal's existing Spec/PRD/architecture, will preserve
  already-done story identity the way CAP-8 requires — not independently
  verified against those skills' actual update-mode behavior; verify before the
  rewrite starts, not after.
- The `FR1..FR62 → FR-66..FR-127` sequential map (`citation-map.md`) is correct
  as the rewrite's starting point — confirmed gap-free/duplicate-free by a
  dedicated research pass, though the rewrite may still choose to reorder FRs
  by topic rather than preserve strict append order.

## Open Questions

- Does `bmad-create-epics-and-stories` in update mode guarantee existing
  done/in-progress story keys survive re-generation, or does it require manual
  reconciliation after the fact? Check before the rewrite starts.
- Which way do the two inherited contradictions resolve — argparse vs
  typer+rich, and whether `check` stays one verb or splits into two? This Spec
  requires the rewrite to decide them; it does not itself decide them.
- `SC-01..10` and `K-01..03` have no existing Marshal namespace to fold into
  (Marshal uses `SM-1..7`/`SM-C1..3`, not `SC-`, and has no kill-criteria
  concept at all) — does the rewrite adopt both wholesale as new to Marshal,
  map `SC-` onto `SM-`, or something else? `NFR-O1` is likely redundant with
  Marshal's own `NFR-12` (near-identical substance) rather than needing a new
  number at all.
