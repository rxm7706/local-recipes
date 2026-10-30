---
title: Product Brief — BMAD marketplace reset
status: ready
created: 2026-10-21
updated: 2026-10-29
chain: pyforge-steward
caps: [CAP-169, CAP-170, CAP-171, CAP-172, CAP-173]
---

# Product Brief: BMAD marketplace (reset)

## Executive Summary

The estate already hosts a catalog. Epic 60 shipped a git-edited registry, a conda/Artifactory ship path, trust-tier names, and a thin browse list of modules and Frames. Teammates still cannot find a BMAD skill, copy it into the tool they actually use, and follow steps that run in their own repository. The 2026-10-20 design-thinking session re-decided the product: a marketplace of BMAD skills and modules, of station skills built with BMAD, and of agents built with BMAD. The four jobs are find, install, create, and publish. Skills are the first artifact. The first user is a teammate on a mixed set of tools, not the operator of this factory.

The reset stays on steward. `steward catalog` remains the engine. A teammate-facing `bmp` command is a later face on that engine. The 2026-10-20 session selected every concept A–F (find and install, contribution, skill cards, portable agents, in-tool discovery and capture, trust and freshness) as one thin slice. The slice in Stories 109.1–109.3 touches A, B, C and F. D's generated adapters wait on P4's per-tool-manifest and adapter gate, and D's agent-as-skill listing (P4's optional fourth seed) is not in the slice. E's in-tool search waits on P4's search gate, and E's capture is `@bmp/skillify`, backlog in Story 109.4. GitHub and GitHub Pages are the browse host. A skill is a folder with `SKILL.md`, `steps.md`, and `listing.yaml`, installed by copying it into `.agents/skills/<scope>-<slug>/` and `.claude/skills/<scope>-<slug>/`. A GitHub release and Artifactory conda and pip are the install sources once a listing is published; until then the copy is the install. This brief is the contract for Epic 109. Stories 109.1–109.3 land the brief, three pilot skills, and the Pages skeleton. Stories 109.4 and 109.5 are backlog: the CLI and contribution automation wait on the desk test and the Wizard-of-Oz gates.

## The Problem

A teammate who wants a BMAD skill today has two unusable paths. The estate catalog's installer resolves the catalog directory and then reports that it found 0 modules, because the v1 rows are GitHub pointers and discovery wants a module tree (`DW-FU-60-1-4`). The station skills that do exist (`mason environment`, `mason package`, `warden scan`) are written for this repository: warden's runs `pixi run -e pyforge-warden`, and all three assume an estate install run from the local-recipes root and link estate paths. The packages behind those commands (`pyforge-mason`, `pyforge-warden`, `pyforge-core`) were not on PyPI, conda-forge, or SelfExplainML on 2026-10-21. A teammate on Claude Code, Cursor, GitHub Copilot in VS Code, Google Gemini, Devin (Cognition AI), or no AI tool yet has no single place that says what exists, how to copy it, and which step cannot run yet.

## The Solution

A marketplace tree in this repository, at `docs/foundry/marketplace/`. Decision 2026-10-21: this monorepo hosts and publishes it. There is no separate marketplace repository. Teammates use an internal mirror of local-recipes. Each skill folder carries `listing.yaml`. `index.yaml` (`pyforge.bmad-marketplace/v1`, `index_version: 1`) is the committed concatenation, compatible with `src/shared/packages/pyforge-steward/catalog/registry/estate.yaml`. bmp `tier` maps onto the v1 trust names. The three pilots are `community`, which maps to `unverified`, because they have no review record. They are `code-backed` because each requires a package. An instructions-only skill is one with no package. A static index and one card per listing are generated from those listings. The card renders `steps.md`. The paper prototype's sample lock command is not the runbook. Find and install, for the pilot, are a person reading the card and copying the folder. Create is the `SKILL.md` template, and later `bmp new skill --from-session` driven by `@bmp/skillify`. Publish is a pull request against the checklist, in one of two lanes, and it is not automated until the Wizard-of-Oz exit criteria in `_bmad-output/projects/pyforge-steward/planning-artifacts/design-thinking-bmad-marketplace-2026-10-20/prototypes/p4-wizard-of-oz-pilot.md` are met.

## What Makes This Different

The difference from v1 is the artifact, not a second catalog. v1 lists modules and Frames and emits Claude/Codex marketplace manifests. The reset's primary artifact is a skill folder that does not require those manifests. The difference from a public skill registry is scope: our listings, steward's trust-tier names, no community dump, no billing, no Layer 3. The difference from rewriting mason or warden is that those stations keep their procedures. The marketplace holds portable copies. `CatalogEngine.render` and the committed manifests stay as they are.

## Who This Serves

The primary user is a teammate of rxm7706 at work, not the operator. The pilot audience is that teammate on Claude Code, Cursor, GitHub Copilot in VS Code, Google Gemini, Devin (Cognition AI), or with no AI tool yet. P4's two or three people are drawn from this list: one example is Cursor with conda or pip, one is Copilot or Gemini and publishes packages, one has no AI tool. Claude Code and Devin are in the same audience, not a later add-on. The 2026-10-20 tool matrix documents Claude Code's project skill path as `.claude/skills/` and marks Claude Code reading `.agents/skills/` as uncertain. It documents Devin's skill path as `.agents/skills/<name>/SKILL.md` and does not list `.claude/skills/` for Devin. Cursor and Copilot read both directories. Gemini CLI reads `.agents/skills/`. Codex, also in that matrix, reads `.agents/skills/`. A teammate with no AI tool uses the Pages card and `steps.md`. The install is a copy into both directories. No other skill-directory format is generated. For Round 0, success for one of them is: they open one index, open one card, copy one folder into both skill directories, and follow `steps.md` in their own project until a step either finishes or says which package is unpublished. In the pilot, each teammate completes find → install → use on a real task, and the no-AI teammate does that from the steps alone. The operator remains the reviewer. A review record is what promotes `community` to `estate-reviewed` (upstream `community-reviewed`). Mason and warden remain the owners of the commands the seed skills describe. The listing owner on the three pilots is `@rxm7706` until a teammate's pull request names another.

## Success Criteria

- The primary success signal is a teammate installing and using a skill that a different teammate, not rxm7706, contributed.
- Each pilot teammate completes find → install → use on a real task; the teammate with no AI tool does it from the steps alone.
- Plain skill folders work unmodified in every pilot tool, or the gap is named per tool.
- Operator interventions per task trend down, and the most frequent manual step is the first one automated.
- Stop or rethink if no teammate uses a seed skill on a real task, or nobody contributes after being asked.
- The archived seed Dream stays archived and points at this station's 2026-10-21 realization-log entry and at the verbatim session folder.
- A teammate can read `docs/foundry/marketplace/site/index.html` and three skill cards without a server. Each card names both install directories, renders `steps.md`, and does not use the paper prototype's sample lock command.
- Each pilot `steps.md` contains no `pixi run -e` and names a command that was verified on 2026-10-21, or names the unpublished package that blocks the station command.
- `load_listings` on the committed `src/shared/packages/pyforge-steward/catalog/registry/estate.yaml` returns no listings. A module row still maps. `write_site` writes nothing while `pyforge.steward.marketplace_pages` is off. Committed pilots are `tier: community` and `trust_tier: unverified`.
- `bmp` is not required for the pilot. `bmp install` is not built until two teammates have installed a skill with the manual copy and used it. Lint and clean-machine CI wait until the manual checks have run on three or more pull requests and caught at least one real problem. `bmp publish` and `bmp new`, including `@bmp/skillify`, wait on one merged contribution from someone other than rxm7706. Search or MCP discovery waits on people looking for a skill inside their tool first. Generated per-tool manifests or agent adapters wait on a pilot tool failing to pick up the plain folder.
- `DW-FU-60-1`, `DW-FU-60-1-4`, and `DW-FRR-60-1` stay open, with a carried note. This brief does not close them.

## Scope

**In now (Stories 109.1–109.3):** this brief; the three pilot folders `@mason/environment`, `@mason/package`, `@warden/scan`; the marketplace tree (`skills/<scope>/<slug>/`, index schema, generated index and cards, `SKILL.md` template, PR template, manual checklist); flag `pyforge.steward.marketplace_pages`.

**Backlog, not built (Stories 109.4–109.5):** `bmp` sharing `CatalogEngine`, including `@bmp/skillify` as `bmp new skill --from-session`; automated contribution lanes. The manual checklist records the P4 gates those stories wait on.

**Out:** a separate marketplace repository (decision 2026-10-21: this monorepo hosts it); billing; Layer 3; a community import; per-tool adapter generation (no format confirmed); changing `CatalogEngine.render` or the v1 catalog manifests; replacing the estate skill procedures; vendoring BMAD module trees (that would be a closure of `DW-FU-60-1-4`, and it is not this scope).

## Vision

If the desk test holds, a teammate installs a skill by copying a folder, and `bmp` becomes a thin client of the catalog engine for find and install. Publish stays a reviewed pull request in a named lane. Agents appear as skill-first listings, with an adapter only after a tool's format is confirmed. An internal GitHub is a mirror of this repository, not a second product. Artifactory remains how a machine without GitHub gets a snapshot.

## assumptions[]

- **A1.** The verbatim session is the decision, except where a dated decision in this brief overrides it: the session's marketplace repository on internal GitHub became this monorepo (decision 2026-10-21). Concepts A–F were all selected, as one thin slice. The files are `_bmad-output/projects/pyforge-steward/planning-artifacts/design-thinking-bmad-marketplace-2026-10-20/`. Sample data in the prototypes (checksums, example hosts, review records, the paper card's lock command) is not a listing.
- **A2.** The brief folder is `brief-bmad-marketplace-reset-2026-10-21`, the same kind of deviation the steward founding brief recorded: `{project_name}` would resolve to `local-recipes`.
- **A3.** Steward remains the owner. `bmp` does not create a station.
- **A4.** "Published" for the three packages means an HTTP 200 on PyPI or conda-forge or SelfExplainML. A 404 on 2026-10-21 is the flag the skills carry. A later publish does not silently make the skills true; the listing's `published` field has to change.
- **A5.** Copying a folder into `.agents/skills/` and `.claude/skills/` is enough for the tools the brief names. A tool that ignores both directories is an open question (OQ7), not a generated manifest.

## open_questions[]

- **OQ1.** Which internal GitHub or GHES mirror of local-recipes, and is mirroring the full repository allowed at work? Decision 2026-10-21: this monorepo hosts and publishes the marketplace. There is no dedicated marketplace repository. `edit_store.mirrors` stays empty until that mirror is named.
- **OQ2.** Should `bmp install` also vendor module trees, which is the closure named on `DW-FU-60-1-4`, or only copy skill folders?
- **OQ3.** Which per-tool agent formats are confirmed, if any? None are generated until one is named.
- **OQ4.** P2 leaves the licence as sample, and leaves open whether station persona agents stay `bmad-agent-<station>` or become `@station/agent`. This brief does not pick a licence or rename those agents. `bmp` still needs a check that the name does not collide with an internal tool.
- **OQ5.** `DW-FRR-60-1` is an independent review of Story 60.1. Who runs it, and does Epic 109 wait on it? This brief does not.
- **OQ6.** Each pilot's station command needs an unpublished package (`pyforge-mason`, `pyforge-warden`, `pyforge-core`). Today only step 0 (installing the published tools) and the engine steps run (`conda-lock lock`, `pyproject-build` and `pixi build`, warden's two version probes), so warden's verdict and mason's station lock and check cannot run on a teammate's machine, and a contributed skill that needs an unpublished `pyforge-*` package would hit the same wall. The session's refinements publish one listing to Artifactory, and P4 names one Artifactory package as real. Who publishes which `pyforge-*` package, and does Round 1 wait on it or rely on a contribution that needs no unpublished package?
- **OQ7.** The tool matrix marks SKILL.md support in Gemini Code Assist outside agent mode (IDE chat) as uncertain; Gemini CLI and agent mode read `.agents/skills/`. Which one does the "Google Gemini" teammate use, and if it is IDE chat, what does the pilot do for them?

## Currency reconciliation — 2026-10-29

Everything above this section is dated 2026-10-28 (the `updated` value before this section), except the corrections the
Story 109.1 review made on 2026-10-29: the estate-skill sentence in The Problem (only warden's skill runs
`pixi run -e`); repository-root paths for P4, `estate.yaml`, the session folder and the site index; the slice's
concepts in the Executive Summary; the Round 0 and pilot split of a teammate's success in Who This Serves; the
session's pilot metrics and stop rule in Success Criteria; P4's lint gate in P4's words, and the two P4 gates the brief
lacked (search or MCP, per-tool manifests); A1's override; A5's pointer to OQ7; OQ6 and OQ7; and `status: ready`.

- **Stories, as of 2026-10-29.** 109.1 closes with this review (done in the same change). 109.2 and 109.3 landed as done with PR #2274. 109.4 is
  backlog. 109.5 is in-progress: it records Round 0 and the Wizard-of-Oz pilot, and only then may spec the smallest
  automation the notes justify; the Executive Summary's "contribution automation" is that later step. Round 0's Claude Code
  leg ran on 2026-10-29; the other tools' legs and the pilot have not. 109.6 (PR #2337) carried the Claude Code result into
  the generated cards and the `steward catalog pointers` note.
- **Round 0, Claude Code leg** (`_bmad-output/projects/pyforge-steward/planning-artifacts/design-thinking-bmad-marketplace-2026-10-20/round0-desk-test-2026-10-29.md`). Claude Code 2.1.311 does not read
  `.agents/skills/`, which settles the 2026-10-20 matrix's "uncertain" quoted in Who This Serves. Copying into both
  directories stays the install. A plugin install from `docs/foundry/marketplace` exposes the skill as
  `<scope>-<slug>:<scope>-<slug>` (run on `@warden/scan` with the `claude plugin` CLI at local scope); use the plugin or the
  copy in one project, not both (the advice the 109.6 cards carry; Round 0 did not test the two together). The cards also offer the rolling `pages-site` release zip with its `.sha256`. Step 1 of
  `@warden/scan` stops on the unpublished `pyforge-warden` (exit 127), as OQ6 expects.
- **Generated manifests, a recorded deviation from P4.** The marketplace tree generates
  `docs/foundry/marketplace/.claude-plugin/marketplace.json` (since 2026-10-21, Story 109.3) and
  `docs/foundry/marketplace/.agents/plugins/marketplace.json` (Codex, since 2026-10-28), both written by
  `pyforge.steward.marketplace_pages`. In now (above) does not list them, and P4 builds generated per-tool manifests only
  after a pilot tool fails on the plain folder. They list the same folders and add no format the folder lacks, so Out's "per-tool
  adapter generation" still holds; the Claude one is now a working install route, and the Codex one stays a discovery
  pointer until its Round 0 row runs.
- **Still open.** OQ1 (the mirror host; `edit_store.mirrors` is empty), OQ6 and OQ7. `DW-FU-60-1`, `DW-FU-60-1-4` and
  `DW-FRR-60-1` stay open.
