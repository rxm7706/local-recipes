---
title: "33.2: The spine counts twelve pipelines, and the MCP face names its eight as the MCP-triggerable ones"
type: 'fix'
created: '2026-10-25'
status: 'done'
baseline_revision: '529f06d52b6d6469b847519905c20bf528a60334'
review_loop_iteration: 1
followup_review_recommended: false
declared_low_risk: true
context:
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/architecture/architecture-pyforge-atlas-2026-07-17/ARCHITECTURE-SPINE.md
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/retros/retro-pyforge-atlas-2026-10-25.md
  - src/shared/packages/pyforge-atlas/src/pyforge/atlas/pipeline_registry.py
  - src/shared/packages/pyforge-atlas/src/pyforge/atlas/mcp/server.py
  - src/shared/packages/pyforge-atlas/src/pyforge/atlas/mcp/tools.py
  - src/shared/packages/pyforge-atlas/tests/unit/mcp/test_audit_mapping.py
deferred: []
---

<intent-contract>

## Intent

**Problem:** two texts still count the pipelines atlas had before Stories 19.3 and 37.10. Line numbers are at
`529f06d52b`.

- `register_pipelines()` (`pipeline_registry.py`) registers twelve pipelines: core, vcs_health, pypi_intelligence,
  vulnerability, seed_gaps, universal_sbom, derived_artifacts, upstream_discovery, artifactory_downloads,
  query_plane_cache, semantic_packages and catalog_index. `__default__` sums all but `catalog_index`
  (`AFTER_RUN_PIPELINES`, :10, :23-25). `tests/unit/test_pipeline_inventory.py` pins the package README's "12".
- AD-3 (spine :90-94) keeps the sealed seven, and its 2026-08-26 amendment names three as-built packages
  (`upstream_discovery`, `artifactory_downloads`, `query_plane_cache`) and says its rule "holds across all ten".
  `semantic_packages` (Story 19.3) and `catalog_index` (Story 37.10) were never written in; the spine's 2026-10-25
  currency section (:1626-1636) records the divergence.
- The MCP face calls `PIPELINE_NAMES`' eight (`mcp/tools.py:97-106`) "the registered pipelines": the
  `list_atlas_pipelines` docstring (`mcp/server.py:106-108`), which the official SDK serves as the tool description;
  the `TOOL_SPECS` `list_pipelines` description (`tools.py:70-73`); the comment above `PIPELINE_NAMES`
  (`tools.py:88-96`, "the four registered pipelines from B1/B2 … the 5 create_pipeline modules"); the `list_pipelines`
  docstring (`tools.py:246-248`); the audit test's module docstring (`tests/unit/mcp/test_audit_mapping.py:1-10`);
  and the station skill's `list_pipelines` line (`.claude/skills/pyforge-atlas/0.1.0/pyforge-atlas/SKILL.md:85`).
  The four others are CLI-only by design (`NO_MCP_TRIGGER_PIPELINES`, `test_audit_mapping.py:73`).

**Approach:**
- AD-3's amendment parenthetical is edited in place, as its earlier amendments were (2026-08-26; 2026-09-18 edited
  its Epic numbers in place because "that parenthetical is a live rule"): it names the five as-built packages and
  says the rule holds across all twelve, eleven in `__default__` and `catalog_index` after a build. AD-3's rule and
  its heading (the sealed seven) do not change. The spine's currency section of this story records it.
- Each MCP text says the eight are the MCP-triggerable pipelines and the other four are CLI-only. Wording only.
- A `fix` under CAP-9 (agents trigger and read the pipeline natively) and AD-3: no CAP, no flag.

Ledger key: `33-2-the-spine-counts-twelve-pipelines-and-the-mcp-face-names-its-eight`. Type / Effort / Deps:
fix / XS / —.

## Acceptance Criteria

- **AC1 — AD-3.** The amendment names the twelve registered pipelines and which run in `__default__`; AD-3's rule
  and heading are unchanged; the spine's currency section names the edit.
- **AC2 — The MCP texts.** None of the six texts above calls the eight "the registered pipelines"; each names them as
  the MCP-triggerable pipelines. `grep -rn "registered pipeline" src/shared/packages/pyforge-atlas/src/pyforge/atlas/mcp`
  matches nothing that describes `PIPELINE_NAMES`.
- **AC3 — No behaviour change.** No pipeline, tool, trigger set, registry or test assertion changes;
  `pixi run -e pyforge-atlas pyforge-atlas-test` passes, including the SKF skill meta-test's provenance line check.

## Boundaries & Constraints

**Never:** change `PIPELINE_NAMES`, `NO_MCP_TRIGGER_PIPELINES`, `register_pipelines()` or any assertion; re-compile
the SKF skill (one line of its text changes, in place).

</intent-contract>

## Binding

- Parent capability: `spec-pyforge-atlas` CAP-9; architecture decision AD-3. No CAP is minted.
- Dream: `docs/dreams/pyforge-atlas.md` § *Realization log*, 2026-10-25 (twelve pipelines, eight triggers).
- Epic 33 (done; reopened by this story under doctor Story 41.5's rule). Ledger key above. Deps: —.

## Verification

**Commands:**
- `pixi run -e pyforge-atlas kedro-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run -e pyforge-atlas kedro-catalog-check` — expected: pass (the station's `verify_commands`).
- `pixi run -e pyforge-atlas pyforge-atlas-test` — expected: pass (AC3).

## Spec Change Log

- 2026-10-25: drafted from the Dream entry of 2026-10-25 (twelve pipelines, eight triggers) and the 2026-10-25 atlas
  retro's Finding 7.
- 2026-10-25: the Problem's "Story 20.3" corrected to its post-rekey number, Story 19.3 (`rekey-2026-09-17.md`).
- 2026-10-25: implemented (`147dc077b4`), adding `run_pipeline`'s docstring and the skill's `run_pipeline` row, which
  made the same claim; review round 1 PASS with 2 should-fixes, both fixed: the SKF anchors into `mcp/tools.py` re-pinned
  two lines lower, and AD-3's `semantic_packages` entry names `derived_artifacts` as an input. Moved to `in-review`.
- 2026-10-25: promoted to `done` in the landing PR (#2317) after its review round 1 fixes, with its ledger key, as
  multi-story landings do (Pages #2240; steward 105.1).

## Run results

2026-10-25, after the round-1 fixes:
- `grep -rn "registered pipeline" src/shared/packages/pyforge-atlas/src/pyforge/atlas/mcp .claude/skills/pyforge-atlas`:
  no match (AC2).
- `pixi run -e pyforge-atlas pyforge-atlas-test`: 3478 passed, 20 skipped (AC3); after the fixes, the SKF, audit-mapping,
  pipeline-inventory and CLI-parity tests: 38 passed.
- `pixi run -e pyforge-guild lint-types`: exit 0.

## Review Triage Log

**Review 1 (independent, 2026-10-25): PASS** — AC1-AC3 met; 2 should-fix, 5 nits; all fixed.
- should-fix: the `tools.py` comment grew two lines, so every SKF anchor below it (`provenance-map.json`
  `source_line`s 116/140/202/215/241/252 and six `[SRC:]` ranges in `SKILL.md`) pointed two lines high. Fixed:
  re-pinned by hand, as Story 33.1 did, and the skill's note names this story.
- should-fix: AD-3 said `semantic_packages` sits downstream of `core` and `vcs_health`; since Story 38.1 it also reads
  `derived_artifacts`. Fixed.
- nits, fixed: the test `test_pipeline_trigger_tools_match_the_registered_pipelines` renamed to
  `..._match_the_mcp_triggerable_pipelines`; the audit test's two pre-rekey "Story 20.3" citations read "Story 19.3
  (pre-rekey 20.3)"; this spec's 20.3 edit now has a Change Log line; `SKILL.md`'s `PIPELINE_NAMES` entry no longer
  calls it a "static registry mirror".
