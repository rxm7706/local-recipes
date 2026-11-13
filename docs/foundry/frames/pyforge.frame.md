---
type: frame
identifier: pyforge/company
license: https://www.apache.org/licenses/LICENSE-2.0
name: PyForge
description: Company Frame for the PyForge estate — Dream-first recipe factory and eight stations. Load when work must follow owned context, Warden as sole PR verdict, and foundry path rules.
visibility: private
version: 0.2.0
scope: company
maintainer:
  - steward
  - guild
---

# PyForge

- Dream in `docs/dreams/` then a Spec in `_bmad-output/projects/<station>/planning-artifacts/` before code.
- A (`rxm7706/local-recipes`) writes every Dream, Frame, Spec and the capability ledger until the flip of `pyforge.cutover_root` to `foundry`; B reads A at a pinned SHA.
- The seed is the Dream plus the Spec's `.memlog.md`. A Frame is a pointer, not a seed (operator ruling 2026-11-10): each station Frame names its seed on two `Seed:` lines and the files rendered from it (SPEC.md, `contract.md`) on one `Derived:` line.
- Eight Smiths: herald, marshal, atlas, warden, mason, doctor, scribe, steward. Recipe craft uses `conda-forge-expert`. Mason has its own skills, and `conda-forge-expert` is one of them.
- Warden is the sole PR verdict; doctor findings stay advisory.
- Never mix `meta.yaml` and `recipe.yaml` in one build run.
- Lasting new paths prefer the foundry target tree (`docs/foundry/`, `src/packages/`, `factory/`). Do not mint a lasting `src/shared/packages/` package. `.claude/skills/pyforge-mason/` is A-only until the flip; B rebuilds it under `skills/stations/`.
- `src/platform/` never imports `pyforge.*`. Parallel agents use `BMAD_ACTIVE_PROJECT` and physical project paths — never `scripts/bmad-switch`.
- Rent the model and harness; own the context, workflows, checks, and evidence.
