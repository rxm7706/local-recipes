---
title: Product Brief — BMAD marketplace reset
status: draft
created: 2026-10-21
updated: 2026-10-21
chain: pyforge-steward
caps: [CAP-169, CAP-170, CAP-171, CAP-172, CAP-173]
---

# Product Brief: BMAD marketplace (reset)

## Executive Summary

The estate already hosts a catalog. Epic 60 shipped a git-edited registry, a conda/Artifactory ship path, trust-tier names, and a thin browse list of modules and Frames. Teammates still cannot find a BMAD skill, copy it into the tool they actually use, and follow steps that run in their own repository. The 2026-10-20 design-thinking session re-decided the product: a marketplace of BMAD skills and modules, of station skills built with BMAD, and of agents built with BMAD. The four jobs are find, install, create, and publish. Skills are the first artifact. The first user is a teammate on a mixed set of tools, not the operator of this factory.

The reset stays on steward. `steward catalog` remains the engine. A teammate-facing `bmp` command is a later face on that engine. The 2026-10-20 session selected every concept A–F (find and install, contribution, skill cards, portable agents, in-tool discovery and capture, trust and freshness) as one thin slice. GitHub and GitHub Pages are the browse host. A skill is a folder with `SKILL.md`, `steps.md`, and `listing.yaml`, installed by copying it into `.agents/skills/<scope>-<slug>/` and `.claude/skills/<scope>-<slug>/`. A GitHub release and Artifactory conda and pip are the install sources once a listing is published; until then the copy is the install. This brief is the contract for Epic 109. Stories 109.1–109.3 land the brief, three pilot skills, and the Pages skeleton. Stories 109.4 and 109.5 stay ready for the CLI and for contribution automation, and they wait on the desk test and the Wizard-of-Oz gates.

## The Problem

A teammate who wants a BMAD skill today has two unusable paths. The estate catalog's installer resolves the catalog directory and then reports that it found 0 modules, because the v1 rows are GitHub pointers and discovery wants a module tree (`DW-FU-60-1-4`). The station skills that do exist (`mason environment`, `mason package`, `warden scan`) are written for this repository: they assume `pixi run -e` and paths inside local-recipes. The packages behind those commands (`pyforge-mason`, `pyforge-warden`, `pyforge-core`) were not on PyPI, conda-forge, or SelfExplainML on 2026-10-21. A teammate on Claude Code, Cursor, Copilot, Devin, Gemini, or no agent tool has no single place that says what exists, how to copy it, and which step cannot run yet.

## The Solution

A marketplace tree in this repository, ready to push to an internal GitHub after the operator confirms that repository. Each skill folder carries `listing.yaml`. `index.yaml` (`pyforge.bmad-marketplace/v1`, `index_version: 1`) is the committed concatenation, compatible with `registry/estate.yaml`. bmp `tier` maps onto the v1 trust names. The three pilots are `community`, which maps to `unverified`, because they have no review record. They are `code-backed` because each requires a package. An instructions-only skill is one with no package. A static index and one card per listing are generated from those listings. The card renders `steps.md`. The paper prototype's sample lock command is not the runbook. Find and install, for the pilot, are a person reading the card and copying the folder. Create is the `SKILL.md` template, and later `bmp new skill --from-session` driven by `@bmp/skillify`. Publish is a pull request against the checklist, in one of two lanes, and it is not automated until the Wizard-of-Oz exit criteria in `prototypes/p4-wizard-of-oz-pilot.md` are met.

## What Makes This Different

The difference from v1 is the artifact, not a second catalog. v1 lists modules and Frames and emits Claude/Codex marketplace manifests. The reset's primary artifact is a skill folder that does not require those manifests. The difference from a public skill registry is scope: our listings, steward's trust-tier names, no community dump, no billing, no Layer 3. The difference from rewriting mason or warden is that those stations keep their procedures. The marketplace holds portable copies. `CatalogEngine.render` and the committed manifests stay as they are.

## Who This Serves

The primary user is a teammate of rxm7706 at work, not the operator. The pilot is two or three of them: T1 uses Cursor and conda or pip, T2 uses Copilot or Gemini and publishes packages, T3 has no AI tool. They may use Claude Code, Cursor, Copilot in VS Code, Devin, Gemini, Codex, or no agent tool. Success for one of them is: they open one index, open one card, copy one folder into both skill directories, and follow `steps.md` in their own project until a step either finishes or says which package is unpublished. T3's success is completing that task from the steps alone. The operator remains the reviewer. A review record is what promotes `community` to `estate-reviewed` (upstream `community-reviewed`). Mason and warden remain the owners of the commands the seed skills describe. The listing owner on the three pilots is `@rxm7706` until a teammate's pull request names another.

## Success Criteria

- The primary success signal is a teammate installing and using a skill that a different teammate, not rxm7706, contributed.
- The archived seed Dream stays archived and points at this station's 2026-10-21 realization-log entry and at the verbatim session folder.
- A teammate can read `site/index.html` and three skill cards without a server. Each card names both install directories, renders `steps.md`, and does not use the paper prototype's sample lock command.
- Each pilot `steps.md` contains no `pixi run -e` and names a command that was verified on 2026-10-21, or names the unpublished package that blocks the station command.
- `load_listings` on the committed `registry/estate.yaml` returns no listings. A module row still maps. `write_site` writes nothing while `pyforge.steward.marketplace_pages` is off. Committed pilots are `tier: community` and `trust_tier: unverified`.
- `bmp` is not required for the pilot. `bmp install` is not built until two teammates have installed a skill with the manual copy and used it. Lint and clean-machine CI wait on three pull requests that caught a real problem. `bmp publish` and `bmp new`, including `@bmp/skillify`, wait on one merged contribution from someone other than rxm7706.
- `DW-FU-60-1`, `DW-FU-60-1-4`, and `DW-FRR-60-1` stay open, with a carried note. This brief does not close them.

## Scope

**In now (Stories 109.1–109.3):** this brief; the three pilot folders `@mason/environment`, `@mason/package`, `@warden/scan`; the marketplace tree (`skills/<scope>/<slug>/`, index schema, generated index and cards, `SKILL.md` template, PR template, manual checklist); flag `pyforge.steward.marketplace_pages`.

**Ready, not built (Stories 109.4–109.5):** `bmp` sharing `CatalogEngine`, including `@bmp/skillify` as `bmp new skill --from-session`; automated contribution lanes. The manual checklist records the P4 gates those stories wait on.

**Out:** a new GitHub repository (operator confirm); billing; Layer 3; a community import; per-tool adapter generation (no format confirmed); changing `CatalogEngine.render` or the committed marketplace manifests; replacing the estate skill procedures; vendoring BMAD module trees (that would be a closure of `DW-FU-60-1-4`, and it is not this scope).

## Vision

If the desk test holds, a teammate installs a skill by copying a folder, and `bmp` becomes a thin client of the catalog engine for find and install. Publish stays a reviewed pull request in a named lane. Agents appear as skill-first listings, with an adapter only after a tool's format is confirmed. The internal GitHub is a push of this tree, not a second product. Artifactory remains how a machine without GitHub gets a snapshot.

## assumptions[]

- **A1.** The verbatim session is the decision. Concepts A–F were all selected, as one thin slice. The files are `design-thinking-bmad-marketplace-2026-10-20/`. Sample data in the prototypes (checksums, example hosts, review records, the paper card's lock command) is not a listing.
- **A2.** The brief folder is `brief-bmad-marketplace-reset-2026-10-21`, the same kind of deviation the steward founding brief recorded: `{project_name}` would resolve to `local-recipes`.
- **A3.** Steward remains the owner. `bmp` does not create a station.
- **A4.** "Published" for the three packages means an HTTP 200 on PyPI or conda-forge or SelfExplainML. A 404 on 2026-10-21 is the flag the skills carry. A later publish does not silently make the skills true; the listing's `published` field has to change.
- **A5.** Copying a folder into `.agents/skills/` and `.claude/skills/` is enough for the tools the brief names. A tool that ignores both directories is an open question, not a generated manifest.

## open_questions[]

- **OQ1.** The operator has not confirmed the internal GitHub repository. `dedicated_repo` stays null until they do.
- **OQ2.** Should `bmp install` also vendor module trees, which is the closure named on `DW-FU-60-1-4`, or only copy skill folders?
- **OQ3.** Which per-tool agent formats are confirmed, if any? None are generated until one is named.
- **OQ4.** P2 leaves the licence as sample, and leaves open whether station persona agents stay `bmad-agent-<station>` or become `@station/agent`. This brief does not pick a licence or rename those agents. `bmp` still needs a check that the name does not collide with an internal tool.
- **OQ5.** `DW-FRR-60-1` is an independent review of Story 60.1. Who runs it, and does Epic 109 wait on it? This brief does not.
