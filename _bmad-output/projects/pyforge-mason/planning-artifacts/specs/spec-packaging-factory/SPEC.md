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
  - ../../../../../../.claude/skills/conda-forge-expert/SKILL.md        # adopted: the living operating contract (v8.90.1)
  - ../../../../../../.claude/skills/conda-forge-expert/CHANGELOG.md    # adopted: the release record Rule 2 maintains
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

## Currency re-read — 2026-09-09

Status stays `shipped` and the Dream stays `realized`; what moved is the FACTS
both quote. Verified live against `.claude/skills/conda-forge-expert/` (Rule 1:
`conda-forge-expert` was invoked to read the skill tree): SKILL.md frontmatter
version is **8.90.1** (five releases landed on 2026-09-09 alone), the gotcha
corpus is **G1–G117** (117 sections), and `.claude/tools/conda_forge_server.py`
registers **46 MCP tools**. The Dream body was eleven minor versions stale
(v8.79.x, ~90 gotchas, "30+ tools") and has been corrected in place; this Spec's
`companions:` parenthetical moved `(v8.79.0) → (v8.90.1)` in the same pass. **No
contract change.**

**Standing hazard for whoever maintains it:** a stamped literal version in a
companion comment is a permanent drift source against a skill that ships several
releases a day. Recorded fleet-wide as decision-batch **D6** — propose a DERIVED
pin that reads `SKILL.md:10` rather than a stamped literal.

## Open gap — CLI⇄tool parity is UNGATED for this Spec's MCP surface

Filed here rather than on `spec-conda-forge-expert-rebuild` (which also declares
`.claude/tools/conda_forge_server.py`) because the parity gate is standing factory
machinery, not campaign work, and the rebuild Spec is closing.

Parity between a station's CLI verbs and its MCP tools is a **gated number for
marshal only** — `pyforge-marshal/tests/meta/test_cli_tool_parity.py` drives
`pyforge.marshal.mcp.parity` (`assert_cli_tool_parity`, `discover_cli_verbs`,
`parity_findings`, `tools_by_cli_verb`, with explicit `CLI_ONLY_VERBS` /
`TOOL_ONLY_NAMES` allowlists) against live `TOOL_SPECS`, per FR-155 / Story 18.2.
CAP-3's 46 `@mcp.tool` registrations have **no parity gate at all**, so a CLI
wrapper can gain or lose a verb with no tool counterpart and nothing reds.

**Vessel: mason Story 16.3** (minted 2026-09-09). Design constraint carried into
its ACs: **EXTEND marshal's primitive, do not fork it** — a second independent copy
of a gate is exactly how the `_http.py` JFrog credential leak survived a landing
that called itself durable, a lesson this skill's own SKILL.md records. Atlas's half
of the same routing (`pyforge/atlas/mcp/tools.py`) is ATLAS's to mint; mason's story
touches no atlas file.

## Cross-station trigger — steward Epic 44 carries two Mason capabilities

Decision-batch D11 / mason-E1: `fnd:CAP-3 → S-44.6` (CFE comes home; moves the whole
CFE cell to `skills/domain/conda-forge-expert/`) and `fnd:CAP-6 → S-44.9` (Mason
submits to conda-forge; marked *outward*, dispatched only on explicit operator
confirmation). Both read `blocked` in steward's ledger and both carry CLAUDE.md
Rule 1 / Rule 2 (Mason) in their own AC lines — Mason work carried on steward's
chain. A Kinship line pointing at them was added to `docs/dreams/packaging-factory.md`
so the practice Dream names them rather than leaving mason's decomposition silently
incomplete against the greenfield spine.

**Sequencing that matters for this Spec's surface:** the CFE-rebuild campaign closes
BEFORE 44.6, otherwise 44.6 has to re-point a live campaign's surface and slice map
as well as move the cell.
