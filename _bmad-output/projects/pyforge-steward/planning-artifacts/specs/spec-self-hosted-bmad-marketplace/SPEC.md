---
spec: self-hosted-bmad-marketplace
status: ready
created: "2026-09-14"
updated: "2026-09-15"
owner-dream: docs/dreams/self-hosted-bmad-marketplace.md
surface: []
companions:
  - backends-and-sources.md
sources:
  - ../../../../../../docs/dreams/self-hosted-bmad-marketplace.md
open_questions: []
---

> **Canonical contract.** Derived 2026-09-15 from
> `docs/dreams/self-hosted-bmad-marketplace.md` § *Operator rulings (accepted
> 2026-09-15)* and this folder's `.memlog.md`. CAP-1..6 IDs are stable from the
> 2026-09-14 seed (CAP-5 is a later empty slot; CAP-6 is a recorded non-goal).
> CAP-7 is the Frame index. CAP-4 is in v1 (thin list, not an App Store).

# SPEC — the estate hosts its own BMAD catalog

## Why

The suite on A is fully wielded. Installers still treat Claude's public
plugin list and github.com as the only index. This Spec is the later product
`spec-bmad-suite-lifecycle` and Hub LC-3 deferred: a catalog we host and
review, plus estate Frames listed on the same rails. Owner: **steward**.

## Capabilities

- **CAP-1 — estate catalog and config.**
  - **intent:** listings are edited in git we control; backends and sources
    are named in config so ship path and feed can swap without a rewrite.
  - **success:** `bmad-method install` / `--custom-content` and Claude/Codex
    `extraKnownMarketplaces` can resolve our catalog; every listing names a
    source; a new backend or source is a plugin. Tables:
    `backends-and-sources.md`.

- **CAP-2 — publish path plus steward trust review.**
  - **intent:** a module enters the catalog through Builder / module-template
    / SKF, then a named steward review — not a silent copy from labs or
    Claude.
  - **success:** a listing cannot appear without a recorded review, unless it
    is already in the wielded suite (Certified). Tiers: Unverified,
    Community Reviewed, BMad Certified (their names; our reviewers).

- **CAP-3 — ship backends.**
  - **intent:** an air-gapped or estate-local machine gets a snapshot without
    github.com or Claude's public store at install time.
  - **success:** default ship path is a noarch pixi/conda index package on
    the channel we already use (Artifactory when air-gapped). Object storage
    and git bundle / tarball are switchable extras. Harbor/OCI packs do not
    satisfy this.

- **CAP-4 — thin browse list.**
  - **intent:** an operator can read the catalog without opening YAML by
    hand.
  - **success:** a generated index and/or a page in existing chrome lists
    modules and Frames (name, trust tier, link or install hint). Not a
    hosted buy/install App Store. Not MyBMAD, Collab, or nebari-frames.

- **CAP-5 — Claude-skill source slot (SKU B).** *(Later; empty in v1.)*
  - **intent:** a future `skillsctl` feed can plug in without reminting the
    catalog.
  - **success:** the slot exists in config; v1 does not operate skillsctl or
    its SQLite.

- **CAP-6 — Hub Layer 3 (SKU C).** *(Recorded non-goal of this Spec.)*
  - **intent:** buying/selling Frames, Cogs, Ops, Guards across Hubs, and
    billing, stay on Hub `later-caps.md` LC-3.
  - **success:** this Spec does not implement them.

- **CAP-7 — estate Frame index.**
  - **intent:** list, share, and add-as-a-reviewed-listing the Frames that
    already live in git. Hub LC-2 is realized here.
  - **success:** `docs/foundry/frames/` is a source; a new Frame listing is a
    reviewed git add; share uses the same ship backends as CAP-3. Frame
    authoring and Foundry regenerate stay Hub / those files. No nebari-frames
    server.

## Constraints

- AD-1: do not self-host skillsctl or nebari-frames SQLite as a new kind.
  Object storage, if enabled, is consumed (Epic 50).
- Do not replace Foundry with Nebari or `conda-forge-expert`.
- Do not endorse OpenTeams; cite `inthub-whitepaper` by tag.
- Do not bind ACs to `frame-spec`'s unlicensed validator.
- Do not remint Hub Launch CAP-1..4. Do not flip Epic 44 `blocked` keys.
- Suite-lifecycle "whole labs marketplace" remains that Spec's non-goal.
- A-only. Creating a new GitHub catalog repo needs operator confirm at the
  story.
- Git remains the edit store; backends only ship snapshots.

## Non-goals

- Dumping the labs marketplace into `.claude/skills/`.
- Rebuilding Collab / Desktop-Web Application / MyBMAD-as-store.
- Folding `src/shared/packages/` (44.4). First-install on B / P18.
- Billing, four-class exchange, Layer 3, or a hosted App Store.
- A blind mirror of the public BMAD catalog.

## Success signal

An estate or air-gapped installer resolves BMAD listings from a catalog we
host and review; Frames appear on the same list and ship through the same
configured backends; a reader can name the source and backend for any row.

## Assumptions

- Steward Epic 60 is the dispatch home (60.1–60.4).
- Channel publish follows the `bmad-suite` metapackage shape already on A.
