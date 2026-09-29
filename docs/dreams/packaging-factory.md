---
title: The Packaging Factory
type: practice
owner: mason
status: archived
archived-reason: folded-into-station-dream
---

> **Consolidated into [[pyforge-mason]]** on 2026-09-17 (one-chain-per-station mason fold; folded from `packaging-factory`).
# The Packaging Factory — every library, packaged before you ask

> **Scope note (2026-07-25):** this is the **practice** Dream — the perpetual
> conda-forge factory and its craft-skill. Mason **the station** (the Smith and the
> `mason` CLI) now has his own charter: [[pyforge-mason]].

## The Dream

**The origin dream of this repository**: an AI-assisted, semi-autonomous packaging
factory for conda-forge — Mason's domain. A machine that takes any upstream
(PyPI, npm, CRAN, CPAN, LuaRocks, GitHub) and carries it through the entire
recipe lifecycle — generate, security-scan, build, debug, submit, maintain —
with a human steering intent, not syntax. Where packaging a library stops being
an afternoon of YAML archaeology and becomes a sentence.

This is a **perpetual** dream: realized as a running factory, never "done."

## What is real

- The **`conda-forge-expert` skill** (v8.90.1): the 9-step autonomous lifecycle
  loop, build-failure protocol, **117 gotchas (G1–G117)**, the retro system that
  makes every effort improve the skill (CLAUDE.md Rule 2).
- **769 feedstocks** under maintenance; the staged-recipes campaign machinery
  (langflow suite, db-gpt, flyte, mindroom chains).
- The **FastMCP tool surface** (**46 tools**; `docs/reference/mcp-server-architecture.md`) and
  the atlas intelligence layer feeding it ([[pyforge-atlas]]).
- Shipped intelligence releases: `lts-registry-gap`, `seed-gap-suggesters`,
  `cyclonedx-universe-inventory`, the `cfe-shipped-releases` archive.

## The frontier (unrealized aspirations, from the 2026-04-25 roadmap)

- **Multi-ecosystem autotick + scaffolders** — CRAN/npm/cargo updaters and
  `generate_recipe_from_{cran,cratesio,npm}`; the factory is still Python-first.
- **Smart test extractor** — re-run recipe tests against an existing artifact
  without rebuilding (huge for slow C++ packages).
- **Static dependency version checker** — validate version ranges, not existence.

## Graveyard (recorded so it is never re-dreamed ignorantly)

- **copilot-cli** — cannot ship to conda-forge; staged-recipes#32522 rejected on
  LICENSE.md §2 standalone-redistribution. The recipe lives on locally only.

## Kinships

[[pyforge-mason]] (the station that tends this practice) · [[fleet-stewardship]]
(the estate the factory keeps) · [[pyforge-atlas]] (the intelligence that feeds it) ·
[[conda-forge-expert-rebuild]] (the campaign over the factory's own machinery — endgame
declared 2026-09-09 over slices 1–2) ·
**steward Epic 44** (the python-foundry cutover moves this practice's machinery:
`fnd:CAP-3` → S-44.6 *"CFE comes home"* relocates the whole CFE cell to
`skills/domain/conda-forge-expert/`, and `fnd:CAP-6` → S-44.9 *"Mason submits to
conda-forge"* — both carry Mason's Rule 1/2 ACs, both read `blocked` in steward's ledger,
and mason's chain has no counterpart story for either; noted 2026-09-09, decision-batch
D11).

## Realization log

- **2025→2026** — the factory built and operated across hundreds of sessions;
  history lives in the CFE CHANGELOG, the spec archives, and git.
- **2026-07-23** — Dream retro-seeded under the Dream-first model; roadmap
  aspirations folded in as the frontier. Chapters: [[pyforge-atlas]],
  [[pyforge-warden]], [[fleet-stewardship]], [[upstream-discovery]].
- **2026-07-23 (gist audit)** — grounding: the SelfExplainML 36-package channel drop (third-party-channel publishing!) + the rattler-build macOS codesign-stub cross-compile trick (`docs/intake/gists/`).
- **2026-09-09 (currency re-read)** — the practice is the **most actively exercised thing in the
  fleet**, and this Dream's own body had drifted eleven minor versions behind it. Verified live
  against `.claude/skills/conda-forge-expert/` (`conda-forge-expert` invoked per CLAUDE.md Rule 1):
  **v8.90.1** — with *five* releases landing on 2026-09-09 alone — **G1–G117** gotchas, **46**
  FastMCP tools, and **7,873** `recipes/` directories. The "What is real" block above is corrected
  in place (was v8.79.x / ~90 gotchas / 30+ tools). Status stays `realized`; the Spec stays
  `shipped`. Recorded alongside a standing hazard the pass named fleet-wide: stamped literal
  version numbers in companion comments and downstream artifacts cannot keep pace with a skill
  that ships several releases a day — a **derived** pin (read `SKILL.md`'s own `version:`) is the
  durable shape.
