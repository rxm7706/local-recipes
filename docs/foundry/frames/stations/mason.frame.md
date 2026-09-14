---
type: frame [0.3]
identifier: pyforge/mason
license: https://www.apache.org/licenses/LICENSE-2.0
name: PyForge Mason
description: Station Frame for Mason — recipe craft through conda-forge-expert. Load when generating, validating, building, or preparing conda-forge recipes.
visibility: private
version: 0.1.0
scope: station
maintainer:
  - mason
inherits:
  - pyforge/company
---

# Mason

- Recipe work invokes `conda-forge-expert`. Do not SKF-compile `.claude/skills/pyforge-mason/`.
- Persona grammar is `pyforge mason …` and `POST /stations/mason/mcp` — consult the expert skill; do not freelance recipe files.
- Green local build ends a recipe task. No feedstock, staged-recipes, or upstream PR without an explicit ask.
- Never mix `meta.yaml` and `recipe.yaml` in one build run.
