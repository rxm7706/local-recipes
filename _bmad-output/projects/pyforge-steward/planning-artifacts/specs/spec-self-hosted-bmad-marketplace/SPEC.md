---
spec: self-hosted-bmad-marketplace
status: draft   # 2026-09-14 — seeded so the Dream's chain link is durable (dream-chain INV-1).
                # Seven open questions remain; every capability below is a candidate.
                # Per docs/dreams/README.md:71-78 a `draft` Spec establishes the CHAIN, not the
                # CONTRACT — the owning Dream therefore stays `dreamt`.
created: "2026-09-14"
updated: "2026-09-14"
owner-dream: docs/dreams/self-hosted-bmad-marketplace.md
surface: []
companions: []
sources:
  - ../../../../../../docs/dreams/self-hosted-bmad-marketplace.md
open_questions:
  - v1-sku-a-only-or-a-plus-skillsctl
  - browse-ui-in-v1
  - registry-home-git-or-object-storage
  - fork-vs-mirror-and-public-index
  - trust-review-owner-and-tiers
  - billing-v1-nongoal-or-later-cap
  - lc3-sibling-or-hoist
---

> **Seed Spec — the chain, not the contract.** Derived 2026-09-14 from
> `docs/dreams/self-hosted-bmad-marketplace.md`. It exists so `dream-chain` INV-1
> has a durable link and so the dated org inventory is where research and a later
> `bmad-spec` re-derive can see it. **Every capability below is a candidate.
> Nothing is chosen.**

# SPEC — the estate hosts its own BMAD catalog

## Why

The suite on A is fully wielded. Air-gap and estate installers still have only
Claude's public plugin marketplace and github.com as an index. The BMAD org
already ships the YAML registry, schema, trust tiers, and installer hook
(`bmad-plugins-marketplace` + `extraKnownMarketplaces`). OpenTeams / Nebari /
ownyourintelligence.ai ship Frame and Claude-skill *adjacent* registries and
OCI pack plumbing — not a BMAD App Store. Hub Layer 3 is still thesis. This
Spec is the later product `spec-bmad-suite-lifecycle` and Hub LC-3 deferred.

Owner: **steward**.

## What the 2026-09-14 inventory CLEARED (do not re-litigate)

Recorded in the Dream § *What is real*. Short form:

- **No store on A, no store at ownyourintelligence.ai, no store in openteams-ai.**
  Public marketplace is thesis (field guide 2026-08-18). Collab Desktop exists
  and is the Desktop/Web Application we will not rebuild.
- **SKU A lives in bmad-code-org.** Fork/mirror `bmad-plugins-marketplace`;
  Builder + template + SKF are the publish path already on A.
- **SKU B is skillsctl**, still the Claude Code skill registry; nebari-frames
  is its successor *for Frames*, SQLite single-writer, wrong artifact.
- **SKU C is Hub Layer 3.** catalog-pack / Harbor / nebi are OCI-pack
  miniature, not `extraKnownMarketplaces`.
- **Scribe planning recall** that morning: no grounded prior answer.

## Capabilities — all candidates, none chosen

- **CAP-1 — estate-owned BMAD registry (SKU A).**
  - *intent:* `registry/` is served from a clone we control (git and/or object
    storage), not only github.com.
  - *success:* `bmad-method install` and Claude/Codex `extraKnownMarketplaces`
    resolve listings from that clone. *(Open: fork vs mirror; git vs object
    storage; empty index vs carry the public three.)*
- **CAP-2 — publish path is Builder / template / SKF plus our trust review.**
  - *intent:* a module or skill enters the estate catalog through tools we
    already wield, then a named review — not a silent copy from labs or Claude.
  - *success:* a listing cannot appear without a recorded trust review.
    *(Open: who reviews; reuse upstream tiers or write our own.)*
- **CAP-3 — air-gap index.**
  - *intent:* an air-gapped host can install from an index that does not
    require github.com or Claude's public marketplace at install time.
  - *success:* one documented index blob or git bundle plus a pointer in the
    installer. Harbor/catalog-pack do **not** satisfy this unless the artifact
    is OCI packs (SKU C / later).
- **CAP-4 — hosted browse/install UI** *(contingent on open question 2).*
  - *intent:* operators can browse and install without reading YAML by hand.
  - *success:* a surface that is not MyBMAD, not Collab, not nebari-frames.
    *(Open: whether v1 invents this at all.)*
- **CAP-5 — optional skillsctl face (SKU B)** *(contingent on open question 1).*
  - *intent:* Claude Code skills use the existing skillsctl registry pointed
    at an internal clone — consume, do not remint.
  - *success:* `skillsctl explore` / `install` hit our clone; we do not operate
    its SQLite as a new Helm kind.
- **CAP-6 — Hub Layer 3 (SKU C)** *(contingent on open question 7).*
  - *intent:* only if LC-3 is hoisted here. Otherwise this CAP is a recorded
    non-goal of *this* Spec and stays on Hub `later-caps.md`.
  - *success:* named later, not inferred.

## Constraints

- AD-1 lock: do not self-host skillsctl or nebari-frames SQLite as a fourth
  kind we operate. Object storage is consumed (Epic 50).
- Do not replace Foundry with Nebari or `conda-forge-expert` with anything.
- Do not endorse/market OpenTeams; cite `inthub-whitepaper` by tag.
- Do not bind ACs to `frame-spec`'s unlicensed validator.
- Do not remint Hub Launch CAP-1..4. Do not flip Epic 44 blocked keys.
- Suite-lifecycle "whole labs marketplace" remains that Spec's non-goal.
- A-only (factory / suite / Hub). No foundry-product Dream on B.

## Non-goals

- Dumping the labs marketplace into `.claude/skills/`.
- Rebuilding Collab / Desktop-Web Application / MyBMAD-as-store.
- Folding `src/shared/packages/` (44.4). First-install on B / P18.
- Billing, four-class exchange, or Layer 3 in v1 unless an open question
  answers that way.

## Success signal

An air-gapped or estate-local installer resolves BMAD module listings from a
catalog we host and review, without depending on Claude's public marketplace
as the only index. Layer 3 and billing are either explicit later-caps or
explicit non-goals — never silent.

## Open Questions

All seven are carried from the Dream's § *Open questions for the Spec*.
Nothing downstream may bind until they are answered.
