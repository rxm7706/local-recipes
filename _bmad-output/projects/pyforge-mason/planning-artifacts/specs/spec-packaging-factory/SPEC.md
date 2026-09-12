---
spec: packaging-factory
status: shipped
owner-dream: docs/dreams/packaging-factory.md
program: regenerable-factory (Wave 4, Rule 1 invoked)
surface:
  - .claude/skills/conda-forge-expert/**
  - .claude/scripts/conda-forge-expert/**
  - .claude/tools/conda_forge_server.py
surface-drift-exclude:
  # 2026-09-12: also governed by the spec(s) named below, which already
  # reconciles each of these files cleanly -- this kernel spec's own
  # memlog does not move for routine story work anymore, so double-
  # claiming them only produced permanent drift-presumed noise here.
  # Coverage is unchanged (still listed under `surface:` above); only
  # this spec's own drift tracking for these specific files is off.
  - .claude/skills/conda-forge-expert/tests/conftest.py   # also governed by pyforge-mason/spec-conda-forge-expert-rebuild
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
  - **verified:** 2026-09-11 — PASS (2 mason-caused failures fixed; 2 unrelated failures remain) — mechanical re-verification at HEAD df260ed9ea: full `.claude/skills/conda-forge-expert/tests/meta` suite ran 3 failed / 7692 passed before this pass. Fixed the 2 that were mason's own: `test_skill_md_lists_existing_scripts_only` (SKILL.md's v8.90.3 entry cites `cfe.py`, a real pyforge-mason src module the existence-check didn't recognise) and `test_all_scripts_listed` (Story 16.3's `mcp_tools.py`/`mcp_parity.py` were never added to the SCRIPTS/NO_HELP lists). Re-run after fix: 2 failed / 7693 passed / 4 skipped — the 2 residual failures (`test_bmad_artifacts_in_sync.py`, `test_spec_surface_check.py`) are pyforge-marshal/pyforge-scribe governance drift with zero pyforge-mason mentions in either finding set, confirmed by direct inspection; out of this Spec's surface, not fixed here.
- **CAP-2 — atlas intelligence.** Intent: `cf_atlas.db` (15 phases B→N,
  17 CLIs, offline-safe reads) answering "what should I work on / is this
  safe / what depends on this". Success: `bmad-groundtruth` facts match the
  BMAD artifacts (the existing detector); read CLIs answer offline.
  - **verified:** 2026-09-11 — PASS (offline-read half); intent text is stale — mechanical re-verification at HEAD df260ed9ea: `pixi run -e local-recipes staleness-report --maintainer rxm7706` returns real data offline (25 rows, no network); `pixi run -e local-recipes bmad-groundtruth` runs clean (`atlas_phases: 22, mcp_tools: 46, schema_version: 29, skill_version: "8.90.4"`) and the existing bmad-drift-check detector reports zero findings against this Spec. Note: this CAP's own intent text ("15 phases B→N, 17 CLIs") is copied from SKILL.md's "Atlas Intelligence Layer (v8.1.0)" header, which is itself stale against live (22 phases, 46 MCP tools) — not fixed this pass (a full phase-list/CLI re-audit is Rule-2 retro-sized work); flagged in the memlog for a future CFE retro.
- **CAP-3 — MCP surface.** Intent: `conda_forge_server.py` exposes the
  recipe-authoring + atlas + scanning tools to agent sessions. Success:
  tool count and schemas match `reference/mcp-tools.md`.
  - **verified:** 2026-09-11 — PASS (gap fixed) — mechanical re-verification at HEAD df260ed9ea found 10 of the 46 live `@mcp.tool` registrations undocumented in `reference/mcp-tools.md` (`channel_split`, `enrich_from_feedstock`, `env_inspect`, `get_feedstock_context`, `lookup_feedstock`, `platform_breakdown`, `prepare_submission_branch`, `pypi_intelligence`, `pypi_only_candidates`, `pyver_breakdown` — confirmed absent by direct grep, not just undercounted). Added all 10 with docstring-sourced one-line descriptions in their thematic sections and corrected the stale "30+ tools" intro line to "46+ tools". Re-verified: all 46 tool names from `grep '@mcp.tool'` now resolve in the doc.
- **CAP-4 — the self-improvement loop.** Intent: every conda-forge effort
  ends with a Rule-2 retro landing skill edits + a CHANGELOG semver entry —
  the skill's contract moves with its code. Success: the CHANGELOG sentinel
  (frontmatter above) means a governed edit without a CHANGELOG move is a
  checker finding, mechanizing Rule 2's "the retro is not optional".
  - **verified:** 2026-09-11 — PASS — mechanical re-verification at HEAD df260ed9ea: `pyforge.doctor.sources.chain.gather_spec_surface` reported 7 `drift-presumed` (WARN) findings for this spec's surface (6 pre-existing from Story 16.3 / v8.88.1 / Story 21.11, 1 from this pass's own mcp-tools.md edit) — verified each landing commit via `git log -1` (none out-of-band), reconciled by name in `.memlog.md`, and scoped-stamped via `python scripts/spec_surface_check.py --write-baseline --spec pyforge-mason/spec-packaging-factory`. Re-run: 0 findings for this spec. CHANGELOG sentinel not exercised this pass — the fixes made (2 meta-test bugs, 1 reference-doc gap) match this memlog's own established precedent for changes that land under the surface glob "by location, not by CFE-skill guidance" (test infra + a mechanical doc-completeness fill, not a behavior/gotcha change), so no SKILL.md/CHANGELOG move was warranted.

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
