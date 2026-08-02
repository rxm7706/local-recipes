# PyForge Station: herald

**Status**: Active  
**Created**: 2026-08-02  
**Component**: PyForge Guild

## Overview

herald is the **visual media & communications** station in the PyForge
factory, responsible for the Design↔Code bridge (`herald seed/pull`), deck
and infographic production, and the Guild's presentation surfaces.

## Structure

```
_bmad-output/projects/pyforge-herald/
├── planning-artifacts/
│   ├── epics.md                    — Epic breakdown
│   ├── epics-with-stories.md       — Stories with acceptance criteria
│   ├── test-architecture.md        — Test strategy (Unit/Integration/E2E)
│   ├── sprint-status.yaml          — Sprint plan (epics + stories)
│   ├── specs/                      — Story-level implementation specs
│   ├── prds/                       — Product requirements documents
│   ├── architecture/               — Architectural design specs
│   └── briefs/                     — Brief summaries
├── implementation-artifacts/       — Local-only (gitignored)
├── .bmad-config.toml                — Team config (checked in)
└── .bmad-config.user.toml           — User config (gitignored)
```

Real unit/integration/meta tests live at `src/shared/packages/pyforge-herald/tests/`,
not in this planning tree — this project has no `pytest.ini`, `playwright.config.ts`,
or `tests/` of its own.

## Tiers

- **Tier 0 (Dream)**: `docs/dreams/pyforge-herald*.md`
- **Tier 2 (Planning)**: `_bmad-output/projects/pyforge-herald/planning-artifacts/`
- **Tier 3 (Execution)**: `_bmad-output/projects/pyforge-herald/implementation-artifacts/` (gitignored)

## Key Documents

- **Dream** (Tier 0): Vision, problem statement, success criteria
- **Spec** (Tier 2): BMAD-generated specification contract
- **PRD** (Tier 2): Product requirements
- **Architecture** (Tier 2): Design specifications
- **Epics** (Tier 2): Epic breakdown (epics.md)
- **Stories** (Tier 2): Stories with acceptance criteria (epics-with-stories.md)
- **Test Architecture** (Tier 2): Test strategy, coverage targets, fixtures
- **Sprint Status** (Tier 3): Sprint plan with epic/story tracking

## Getting Started

1. Read the Dream (`docs/dreams/pyforge-herald*.md`) to understand the vision
2. Review the Spec and PRD for the product contract
3. Check the Epics and Stories for implementation scope
4. Look at Test Architecture for coverage expectations
5. Run the real test suite: `pixi run -e local-recipes pytest src/shared/packages/pyforge-herald/tests/`

## Testing

```bash
pixi run -e local-recipes pytest src/shared/packages/pyforge-herald/tests/ -v
```

See `src/shared/packages/pyforge-herald/README.md` for the full test/coverage setup.

## Next Steps

See the epic breakdown in `planning-artifacts/epics.md` and story specs in `planning-artifacts/specs/` for implementation details.

---

**Last updated**: 2026-08-02
