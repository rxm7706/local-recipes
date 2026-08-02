# PyForge Station: genesis

**Status**: Active
**Created**: 2026-08-02
**Component**: PyForge Guild

## Overview

genesis is the **constitutive** project (Charter §5): it records the operating
model — the Charter, the Lexicon, the Guild's membership — and **ships no
product**. See `planning-artifacts/prds/prd-pyforge-genesis-2026-07-28/prd.md`
§ *This tier has nothing to require, and says so*. The installer that
bootstraps this model into other repos (`genesis init`/`genesis adopt`) is
buildable work that moved to `pyforge-marshal` in the 2026-07-28 split.

## Structure

```
_bmad-output/projects/pyforge-genesis/
├── planning-artifacts/
│   ├── epics.md                    — Epic breakdown
│   ├── epics-with-stories.md       — Stories with acceptance criteria
│   ├── test-architecture.md        — States there is nothing to test
│   ├── specs/                      — Story-level implementation specs
│   ├── prds/                       — Product requirements documents
│   ├── architecture/               — Architectural design specs
│   └── (no briefs/ — a constitutive project has no product to brief)
├── implementation-artifacts/       — Local-only (gitignored)
├── .bmad-config.toml                — Team config (checked in)
└── .bmad-config.user.toml           — User config (gitignored)
```

There is no `src/pyforge_genesis` package, no CLI, and no `tests/` — nothing
here is buildable code.

## Tiers

- **Tier 0 (Dream)**: `docs/dreams/pyforge-genesis.md`
- **Tier 2 (Planning)**: `_bmad-output/projects/pyforge-genesis/planning-artifacts/`
- **Tier 3 (Execution)**: `_bmad-output/projects/pyforge-genesis/implementation-artifacts/` (gitignored)

## Key Documents

- **Dream** (Tier 0): the master idea, the alignment instrument (vision deck), the seed
- **Spec** (Tier 2): the Charter and Lexicon kernels (`specs/spec-pyforge-charter/`, `specs/spec-pyforge-genesis/`)
- **PRD** (Tier 2): states plainly there is no product to require
- **Architecture** (Tier 2): the constitutive structure, not a buildable design
- **Epics** (Tier 2): epic breakdown (`epics.md`)

## Getting Started

1. Read the Dream (`docs/dreams/pyforge-genesis.md`) to understand the vision
2. Read the PRD to see why this tier has no requirements
3. See `pyforge-marshal`'s `spec-genesis-installer` for the buildable installer

## Next Steps

See `planning-artifacts/epics.md` for epic breakdown and `planning-artifacts/specs/`
for the Charter/Lexicon spec kernels.

---

**Last updated**: 2026-08-02
