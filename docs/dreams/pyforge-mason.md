---
title: Mason — forge the blocks, bind the environment, ship the structure
type: dream
owner: mason
status: specified
---

# Mason — the craft of shipping, made a command

## The Dream

The Artisan Builder's dream: **packaging stops being archaeology and becomes a
craft anyone can command.** Atlas maps the terrain, Warden clears the perimeter —
then Mason takes raw ingredients and binds them into structures that install
correctly on every platform a user might bring. Recipes authored, environments
resolved into strict lockfiles, wheels and conda packages shipped from one pass.
A human states intent; Mason handles syntax, selectors, pins, and the hundred
gotchas that turn an afternoon into a week.

The station exists because *the hand that builds must not be the gate that
judges*: Mason ships, Warden decides whether shipping was allowed.

## Mason the Smith vs. the factory he tends

This Dream is Mason **the station** — the Smith, and the `mason` CLI that gives
his craft a command surface. It is deliberately distinct from
[[packaging-factory]], the **practice** Dream: the perpetual conda-forge factory,
its 769 feedstocks, and the `conda-forge-expert` craft-skill that carries ~90
hard-won gotchas. The practice is the estate Mason tends; this Dream is Mason
himself. *(Separated 2026-07-25 — until then `packaging-factory` did double duty,
leaving Mason the only Smith without his own charter.)*

## What it looks like when real

```bash
mason recipe build ./recipes/recipe.yaml      # author + build a v1 conda recipe
mason package ship --to pypi,conda-forge      # one pass, both ecosystems
mason environment lock                        # conflicting worlds -> one lockfile
```

- **dist** `pyforge-mason` · **module** `pyforge.mason` · **CLI** `mason` — the
  Smith's craft as an installable product, mirroring the Warden pattern.
- **The seam is by capability** (the chain's decision D-1, "Option C"): `mason
  recipe` **wraps** the conda-forge-expert craft by subprocess — the skill stays
  canonical for recipe semantics and keeps improving through the Rule-2 retro
  loop — while `package` and `environment` are **built natively**, because no
  wheel-build, upload path, or lock orchestration exists anywhere to wrap.
- **Never fork the craft.** A fork is structurally adversarial: Rule 2 mandates
  that every conda-forge effort *edits the skill*, so a fork is invalidated by
  the loop that governs its own domain. The in-repo cautionary precedent is
  [[pyforge-atlas]], which chose full rebuild and whose legacy orchestrator is
  still the live runtime.

## The frontier

- The `mason` CLI built (5 epics / 38 stories planned; 50 FRs).
- Multi-ecosystem autotick + scaffolders (CRAN/npm/cargo) — the factory is still
  Python-first ([[packaging-factory]]'s standing frontier).
- The smart test extractor; the static dependency-version checker.
- The standalone question: `mason recipe` is inert without a co-located craft
  root — bought deliberately, in exchange for zero knowledge duplication.

## Kinships

[[pyforge-charter]] (§5, the station's charter) · [[packaging-factory]] (the
practice he tends) · [[pyforge-atlas]] (maps before he builds; the rebuild
cautionary tale) · [[pyforge-warden]] (judges what he ships) ·
[[fleet-stewardship]] (the estate, tended with Doctor) ·
[[enterprise-airgap]] (every artifact must resolve behind a firewall).

## Realization log

- **2026-07-25** — persona Dream authored, closing the last asymmetry among the
  eight Smiths: Mason was the only station whose charter lived inside a practice
  Dream. Grounded in the planning chain landed the same day (research → brief →
  PRD → architecture → 5 epics / 38 stories) and its D-1 seam decision.
