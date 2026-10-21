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

The reset stays on steward. `steward catalog` remains the engine. A teammate-facing `bmp` command is a later face on that engine. GitHub and GitHub Pages are the browse host. A skill is a folder with `SKILL.md` and `steps.md`, installed by copying it into `.agents/skills/` and `.claude/skills/`. Conda/Artifactory remains a ship backend. This brief is the contract for Epic 109. Stories 109.1–109.3 land the brief, three pilot skills, and the Pages skeleton. Stories 109.4 and 109.5 stay ready for the CLI and for contribution automation, and they wait on a desk test.

## The Problem

A teammate who wants a BMAD skill today has two unusable paths. The estate catalog's installer resolves the catalog directory and then reports that it found 0 modules, because the v1 rows are GitHub pointers and discovery wants a module tree (`DW-FU-60-1-4`). The station skills that do exist (`mason environment`, `mason package`, `warden scan`) are written for this repository: they assume `pixi run -e` and paths inside local-recipes. The packages behind those commands (`pyforge-mason`, `pyforge-warden`, `pyforge-core`) were not on PyPI, conda-forge, or SelfExplainML on 2026-10-21. A teammate on Claude Code, Cursor, Copilot, Devin, Gemini, or no agent tool has no single place that says what exists, how to copy it, and which step cannot run yet.

## The Solution

A marketplace tree in this repository, ready to push to an internal GitHub after the operator confirms that repository. Listings live in `index.yaml` (`pyforge.bmad-marketplace/v1`), compatible with `registry/estate.yaml`. A static index and one card per listing are generated from those listings. Each pilot skill is a folder a person can copy, with human steps that use real commands and that name every unpublished package. Find and install, for the pilot, are a person reading the card and copying the folder. Create is the `SKILL.md` template. Publish is a pull request against the checklist, in one of two lanes, and it is not automated until a Round 0 desk test and a Wizard-of-Oz pilot have been done.

## What Makes This Different

The difference from v1 is the artifact, not a second catalog. v1 lists modules and Frames and emits Claude/Codex marketplace manifests. The reset's primary artifact is a skill folder that does not require those manifests. The difference from a public skill registry is scope: our listings, steward's trust-tier names, no community dump, no billing, no Layer 3. The difference from rewriting mason or warden is that those stations keep their procedures. The marketplace holds portable copies. `CatalogEngine.render` and the committed manifests stay as they are.

## Who This Serves

The primary user is a teammate of rxm7706 at work. They may use Claude Code, Cursor, Copilot in VS Code, Devin, Gemini, or no agent tool. Success for them is: they can open one index, open one card, copy one folder into both skill directories, and follow `steps.md` in their own project until a step either finishes or says which package is unpublished. The operator remains the reviewer of what gets listed, under the v1 tier names. Mason and warden remain the owners of the commands the seed skills describe.

## Success Criteria

- The archived seed Dream stays archived and points at this station's 2026-10-21 realization-log entry and at the session folder.
- A teammate can read `site/index.html` and three skill cards without a server, and each card names install targets `.agents/skills` and `.claude/skills`.
- Each pilot `steps.md` contains no `pixi run -e` and names a command that was verified on 2026-10-21, or names the unpublished package that blocks the station command.
- `load_listings` on the committed `registry/estate.yaml` returns no listings. A module row still maps. `write_site` writes nothing while `pyforge.steward.marketplace_pages` is off.
- `bmp` is not required for the pilot. Contribution automation does not start before the manual checklist has a recorded desk test.
- `DW-FU-60-1`, `DW-FU-60-1-4`, and `DW-FRR-60-1` stay open, with a carried note. This brief does not close them.

## Scope

**In now (Stories 109.1–109.3):** this brief; the three pilot folders `@mason/environment`, `@mason/package`, `@warden/scan`; the marketplace tree (`skills/<scope>/<slug>/`, index schema, generated index and cards, `SKILL.md` template, PR template, manual checklist); flag `pyforge.steward.marketplace_pages`.

**Ready, not built (Stories 109.4–109.5):** `bmp` sharing `CatalogEngine`; automated contribution lanes. The manual checklist is the pilot those stories wait on.

**Out:** a new GitHub repository (operator confirm); billing; Layer 3; a community import; per-tool adapter generation (no format confirmed); changing `CatalogEngine.render` or the committed marketplace manifests; replacing the estate skill procedures; vendoring BMAD module trees (that would be a closure of `DW-FU-60-1-4`, and it is not this scope).

## Vision

If the desk test holds, a teammate installs a skill by copying a folder, and `bmp` becomes a thin client of the catalog engine for find and install. Publish stays a reviewed pull request in a named lane. Agents appear as skill-first listings, with an adapter only after a tool's format is confirmed. The internal GitHub is a push of this tree, not a second product. Artifactory remains how a machine without GitHub gets a snapshot.

## assumptions[]

- **A1.** The session's applied direction, as stated in the restart brief, is the decision. Concepts A–F were named and their verbatim text was not mounted, so they are not product options in this brief.
- **A2.** The brief folder is `brief-bmad-marketplace-reset-2026-10-21`, the same kind of deviation the steward founding brief recorded: `{project_name}` would resolve to `local-recipes`.
- **A3.** Steward remains the owner. `bmp` does not create a station.
- **A4.** "Published" for the three packages means an HTTP 200 on PyPI or conda-forge or SelfExplainML. A 404 on 2026-10-21 is the flag the skills carry. A later publish does not silently make the skills true; the listing's `published` field has to change.
- **A5.** Copying a folder into `.agents/skills/` and `.claude/skills/` is enough for the tools the brief names. A tool that ignores both directories is an open question, not a generated manifest.

## open_questions[]

- **OQ1.** The operator has not confirmed the internal GitHub repository. `dedicated_repo` stays null until they do.
- **OQ2.** Should `bmp install` also vendor module trees, which is the closure named on `DW-FU-60-1-4`, or only copy skill folders?
- **OQ3.** Which per-tool agent formats are confirmed, if any? None are generated until one is named.
- **OQ4.** The verbatim session files were not in the checkout. If they turn up, do any applied decisions in them differ from this brief?
- **OQ5.** `DW-FRR-60-1` is an independent review of Story 60.1. Who runs it, and does Epic 109 wait on it? This brief does not.
