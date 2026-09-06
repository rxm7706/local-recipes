---
spec: intelligence-hub
status: draft   # 2026-09-05 seeded so the Dream's chain link is durable (dream-chain INV-1); 2026-09-06 RB-1/RB-2 research closed (Frame Spec v0.2.0 exists; nebari + nebi on conda-forge, NIC absent). Still nothing chosen: CAP-1..5 are candidate shapes behind the operator's open questions. Registered in doctor's DEFERRED_SPECS until those clear.
owner-dream: docs/dreams/intelligence-hub.md
surface: []
companions:
  - vocabulary-map.md
sources:
  - ../../../../../../docs/dreams/intelligence-hub.md
open_questions:
  - "Owner: steward (the estate; already owns the Unifying Strategy, eval-quality and the channel product) vs marshal (Ops, Gates) vs scribe (Frames, memory) — owning is the post, not the product."
  - "Which of the seven Guard categories does the repo lack entirely, and is source-grounding of LLM output the first to add? Shapes CAP-4."
  - "Does a bmad-loop run already emit enough to constitute a Track, and what retention does the operator want? Shapes CAP-3."
  - "Does the repo publish its own context as Frames (a Community Frame for local-recipes)? RB-1 removed the 'does a protocol exist' blocker; this is now purely the operator's call on CAP-2."
  - "Derived from RB-2: package `nebari-infrastructure-core` (Go CLI, GitHub-release binaries + Homebrew only, v0.14.0) and the `frames` registry client (Go, v0.1.7) as local recipes — is that wanted, now that CAP-5's verified gap is exactly those two?"
  - "Derived from RB-1: author the first conformant `.frame.md` for local-recipes now (v0.2 is a single Markdown file with four required frontmatter fields — cheap, validator in-repo) or wait for the shape decision?"
---

> **Canonical contract — in `draft`.** This SPEC and `vocabulary-map.md` are the chain link for
> `docs/dreams/intelligence-hub.md`, not yet a contract downstream can bind to: the capabilities
> below are the Dream's five candidate shapes, **none chosen**, and the choice waits on the
> `open_questions`. The two pre-Spec research items (RB-1, RB-2) closed on 2026-09-06; their
> findings live in the Dream's § Research backlog.

# SPEC — PyForge speaks the Intelligence Hub vocabulary deliberately

## Why

The whitepaper *The Distributed AI Economy* (Oliphant, August 2026, Rev 9) argues an
organisation should own its intelligence — context, AI workers, workflows, the checks on their
work and the evidence they leave, inside a perimeter it governs, built from shared abstractions
(Frames, Cogs, Ops, Guards, Gates, Tracks, Organizational Memory). PyForge is already such a hub
in miniature: an owned factory on pixi + conda-forge, context in tracked files, workers as
station skills, workflows as bmad-loop runs, checks as detectors + Warden, evidence in ledgers.
It speaks that vocabulary by accident. This Spec exists to decide which of the paper's shapes
PyForge adopts, aligns to, or merely names — deliberately. One tension is carried, not assumed:
PyForge rents the model and the harness (Claude Code sits on the paper's rented-black-box list)
while owning the context, the workflows, the checks and the evidence — the split the paper says
matters most. Owner: **steward** (the estate) until the owner question is answered.

## Capabilities

*Candidate shapes. Selecting among them is this Spec's first decision and is deferred behind
the open questions; an unchosen shape becomes a non-goal at that point, never silently dropped.*

- **CAP-1 — Vocabulary alignment only.**
  - **intent:** the Charter's Lexicon and the station roster map once to Frames / Cogs / Ops /
    Guards / Gates / Tracks / Organizational Memory, recorded in `pyforge-charter.md` or the
    Unifying Strategy — the cheapest realisation; no code.
  - **success:** every row of `vocabulary-map.md` names its Charter term and its gap, and the
    rented-model / owned-context tension is stated in the recording document.
- **CAP-2 — Frames as first-class** *(gate lifted 2026-09-06 — RB-1: Frame Spec v0.2.0 is
  published; single-file Markdown + YAML frontmatter; registries, identity and provenance out
  of its scope).*
  - **intent:** the repo's own context — the `AGENTS.md` block, station personas, the
    recipe-authoring conventions — published as Frame-shaped artifacts with named accountable
    owners; a Community Frame for local-recipes.
  - **success:** each artifact passes the spec's own `tools/validate_frames.py` (the v0.2
    required fields) and names its owner; if the `nebari-frames` registry is adopted, each also
    survives its `.frame.md` import/export round trip.
- **CAP-3 — A declared validation strategy per run.**
  - **intent:** a bmad-loop run or `marshal factory spin` declares its Guards by stage, its
    Gates as threshold rules, and its Track contents + retention, so the several evidence files
    converge on one structured Track (landing-evidence grammar and durable-runs are the
    precedents it extends).
  - **success:** one run yields one structured Track record with enumerated fields and a stated
    retention; the Guards and Gates it ran are readable from the record, not inferred from
    policy TOML.
- **CAP-4 — Guards as a library.**
  - **intent:** detectors, Warden axes and review lenses exposed as reusable Guards, each with a
    declared category from the paper's seven.
  - **success:** a Spec can name which Guard categories it lacks; Warden stays the sole PR
    verdict and doctor stays advisory — no Guard mints a second verdict.
- **CAP-5 — Package the Nebari / Nebi lineage where missing** *(narrowed 2026-09-06 — RB-2:
  `nebari` 2025.10.1 and `nebi` 0.15 are already on conda-forge and are consumed as-is).*
  - **intent:** a Mason / `conda-forge-expert` lane builds local recipes for what is actually
    missing — `nebari-infrastructure-core` (Go, Apache-2.0, v0.14.0; GitHub-release binaries and
    a Homebrew cask only) and, if the registry is adopted, the `frames` client (Go, Apache-2.0,
    v0.1.7) — in the Go-source shape `nebi-feedstock` already uses.
  - **success:** a green local build ends the task; nothing is re-packaged that conda-forge
    already ships; no external PR without an ask.

## Constraints

- **Dream-first.** No code from the seed; this Spec chooses among CAP-1..5 before any code — and
  has not chosen yet.
- **The whitepaper is the source of record.** No claim the paper does not make; re-verify any
  statistic or vendor fact at intake; cite later revisions by tag from
  `openteams-ai/inthub-whitepaper` (Revision 9 = `v9`), never by PDF URL alone.
- **Copyright.** Distilled in our words with short attributed quotations; the PDF is not tracked.
- **Foundry invariants stand.** `src/platform/` never imports `pyforge.*`; the infra-kinds lock
  and AD-1 (re-affirmed 2026-09-05) are untouched; the paper's Organizational Memory menu is its
  menu, not a licence to add stores to the platform.
- **One PR verdict.** Warden stays the sole gate; doctor findings stay advisory; "Guard" language
  must not mint a second verdict.
- **No implied platform adoption.** Naming Nebari / Nebi adopts nothing; the Unifying Strategy
  owns the platform shape.
- **No new `docs/specs/` file; no external PRs; no outward dispatch without operator
  confirmation.**

## Non-goals

- Building a marketplace or a Desktop / Web Application.
- Replacing the Foundry with a Nebari deployment, or `conda-forge-expert` with anything.
- Endorsing or marketing OpenTeams — an architecture-and-vocabulary seed only.
- Reproducing the whitepaper; readers who need the text go to the source.
- Re-packaging `nebari` or `nebi` — both are on conda-forge (RB-2); version bumps there are
  PRs to feedstocks rxm7706 does not maintain, not this chain's work.

## Success signal

The operator has chosen among CAP-1..5 (each choice a memlog decision; unchosen shapes recorded
as non-goals), RB-1 and RB-2 are closed in the Dream with dated evidence (done 2026-09-06), the
remaining questions are answered, and this Spec reaches `ready` — at which point it leaves
doctor's `DEFERRED_SPECS` and decomposes into steward epics. Until then the signal is only this:
the chain link exists and the contract is honestly unsettled.

## Assumptions

- Owner `steward` stands until the owner question is answered; the Spec moves with the owner
  (dream-chain INV-2) if it changes.
- The candidate shapes are independent; more than one may be chosen, and CAP-1 may be chosen
  alone.
- Frame Spec v0.2 stays a single-file format (its directory form is deferred) and its repository
  stays licence-less until upstream says otherwise; conformant documents can be authored
  regardless, and the spec text itself is never vendored here.
- `nebari-feedstock` and `nebi-feedstock` stay maintained by nebari-dev people; rxm7706 is not a
  maintainer on either, so any bump there is a reviewed PR, never a push.
