---
type: frame
identifier: pyforge/mason
license: https://www.apache.org/licenses/LICENSE-2.0
name: PyForge Mason
description: Station Frame for Mason — recipe craft through conda-forge-expert, plus package, environment and doctor verbs. Load when generating, validating, building, or preparing conda-forge recipes, or building, shipping or locking a package.
visibility: private
version: 0.2.0
scope: station
maintainer:
  - mason
inherits:
  - pyforge/company
---

# Mason

- Seed: `docs/dreams/pyforge-mason.md`
- Seed: `_bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-pyforge-mason/.memlog.md`
- Derived: `_bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-pyforge-mason/SPEC.md`, `_bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-pyforge-mason/contract.md`
- Six skills: five of its own (`pyforge-mason`, `mason-package`, `mason-environment`, `mason-feedstock-platform-expansion`, `mason-feedstock-failure-remediation`) plus `conda-forge-expert`, which every recipe task invokes. B rebuilds the station skill under `skills/stations/`.
- Persona grammar is `pyforge mason …` and `POST /stations/mason/mcp`: `recipe` verbs go through `conda-forge-expert`; `package build|ship`, `environment lock|check` and `doctor` do not need it. Do not freelance recipe files.
- Green local build ends a recipe task. No feedstock, staged-recipes, or upstream PR without an explicit ask.
- Never mix `meta.yaml` and `recipe.yaml` in one build run.
