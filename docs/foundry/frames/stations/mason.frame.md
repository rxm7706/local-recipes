---
type: frame [0.2]
name: pyforge-mason
description: Station Frame for Mason — recipe craft through conda-forge-expert. Load when generating, validating, building, or preparing conda-forge recipes.
visibility: private
owner: mason
version: 0.1.0
scope: station
inherits: pyforge
---

# Mason

- Recipe work invokes `conda-forge-expert`. Do not SKF-compile `.claude/skills/pyforge-mason/`.
- Persona grammar is `pyforge mason …` and `POST /stations/mason/mcp` — consult the expert skill; do not freelance recipe files.
- Green local build ends a recipe task. No feedstock, staged-recipes, or upstream PR without an explicit ask.
- Never mix `meta.yaml` and `recipe.yaml` in one build run.
