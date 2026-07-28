---
spec: packaging-factory
status: shipped
owner-dream: docs/dreams/packaging-factory.md
program: regenerable-factory (Wave 4, Rule 1 invoked)
surface:
  - .claude/skills/conda-forge-expert/**
  - .claude/scripts/conda-forge-expert/**
  - .claude/tools/conda_forge_server.py
surface-drift: sentinel:.claude/skills/conda-forge-expert/CHANGELOG.md
companions:
  - ../../../../../.claude/skills/conda-forge-expert/SKILL.md        # adopted: the living operating contract (v8.79.0)
  - ../../../../../.claude/skills/conda-forge-expert/CHANGELOG.md    # adopted: the release record Rule 2 maintains
open_questions: []
---

# SPEC — the packaging factory (conda-forge-expert machinery)

## Why

The origin product: an AI-assisted, semi-autonomous factory for the whole
conda-forge recipe lifecycle — generate → validate → build → debug → submit →
maintain — plus the atlas intelligence layer that tells the operator what to
work on. Owner: Mason. This kernel does NOT restate the skill's contract —
`SKILL.md` (adopted companion) IS the operating contract, kept current by the
Rule-2 retro loop and the bmad drift-check sync loop; this kernel binds that
self-documenting surface into the repo-wide governance map.

## Capabilities

- **CAP-1 — recipe lifecycle machinery.** Intent: the 10-step autonomous
  loop (generators for PyPI/npm/CRAN/CPAN/LuaRocks, validators, optimizer,
  security scan, native/docker builds, submission tooling) as specified in
  SKILL.md. Success: the skill's own meta-test suite green; gates enforced
  per SKILL.md (no skipped gate).
- **CAP-2 — atlas intelligence.** Intent: `cf_atlas.db` (15 phases B→N,
  17 CLIs, offline-safe reads) answering "what should I work on / is this
  safe / what depends on this". Success: `bmad-groundtruth` facts match the
  BMAD artifacts (the existing detector); read CLIs answer offline.
- **CAP-3 — MCP surface.** Intent: `conda_forge_server.py` exposes the
  recipe-authoring + atlas + scanning tools to agent sessions. Success:
  tool count and schemas match `reference/mcp-tools.md`.
- **CAP-4 — the self-improvement loop.** Intent: every conda-forge effort
  ends with a Rule-2 retro landing skill edits + a CHANGELOG semver entry —
  the skill's contract moves with its code. Success: the CHANGELOG sentinel
  (frontmatter above) means a governed edit without a CHANGELOG move is a
  checker finding, mechanizing Rule 2's "the retro is not optional".

## Constraints

- SKILL.md and its references are authoritative over any BMAD story that
  conflicts (CLAUDE.md Rule 1); this kernel never overrides them.
- Runtime state (`.claude/data/conda-forge-expert/`) is gitignored and
  ungoverned by design — contracts govern code, not caches.
- Skill semver discipline: PATCH fixes, MINOR new gotchas/sections, MAJOR
  breaking workflow changes.

## Non-goals

- Re-documenting the skill (its docs are the documentation).
- Governing `recipes/**` — that is the product line, owned by
  `spec-fleet-stewardship`.

## Success signal

`spec_surface_check` green with the CFE surface governed and the CHANGELOG
sentinel active; the skill's meta-test suite green; the next Rule-2 retro
moves CHANGELOG + code together without a drift finding.
