---
title: "Atlas's MCP tools pass the CLI⇄tool parity gate"
type: feature
created: '2026-09-10'
status: done
review_loop_iteration: 0
followup_review_recommended: false
context:
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/mcp/parity.py
  - src/shared/packages/pyforge-marshal/tests/meta/test_cli_tool_parity.py
warnings: []
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** Marshal alone enforces FR-155 CLI⇄tool parity; atlas's thirteen MCP tools are registered on the HTTP/MCP face with no inventory gate, so verb/tool drift cannot fail CI.

**Approach:** Add atlas `TOOL_SPECS`, runtime `discover_cli_verbs()` from Kedro's project command surface, and a marshal-shaped `parity.py` plus gated meta-test. Re-point `PREPARATORY_UNINTROSPECTABLE["atlas"]` at this story.

## Boundaries & Constraints

**Always:** Verb inventory from Kedro runtime via `__main__.discover_cli_verbs`; every CLI-only verb carries a reason sentence; `TOOL_SPECS` keys match `audit.registered_surface_tools()`.

**Never:** Copy Click groups into `pyforge-core`; widen to mason's 46 CFE tools; reimplement Kedro routing in atlas `__main__`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Live inventory | Production `TOOL_SPECS` + CLI-only allowlist | `assert_cli_tool_parity()` passes | N/A |
| Missing tool for on-surface verb | Fixture drops all `run` tools | `cli_missing_tool` finding | `AssertionError` in meta-test |
| Tool claims unknown verb | Fixture adds phantom verb | `tool_cli_unknown` finding | `AssertionError` in meta-test |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-atlas/src/pyforge/atlas/mcp/tools.py` — add `TOOL_SPECS` dict (13 server tools)
- `src/shared/packages/pyforge-atlas/src/pyforge/atlas/mcp/parity.py` — FR-155 gate (new)
- `src/shared/packages/pyforge-atlas/src/pyforge/atlas/__main__.py` — `discover_cli_verbs()` via `project_group.commands`
- `src/shared/packages/pyforge-atlas/tests/meta/test_cli_tool_parity.py` — gated meta-test (new)
- `src/shared/packages/pyforge-core/src/pyforge/core/dispatch.py` — re-point preparatory entry
- `src/shared/packages/pyforge-core/tests/meta/test_cli_parity_matrix.py` — resolve atlas prep spec under pyforge-atlas

## Tasks & Acceptance

**Execution:**
- `src/shared/packages/pyforge-atlas/src/pyforge/atlas/mcp/tools.py` — declare `TOOL_SPECS` for all registered MCP tools
- `src/shared/packages/pyforge-atlas/src/pyforge/atlas/mcp/parity.py` — implement FR-155 parity contracts
- `src/shared/packages/pyforge-atlas/src/pyforge/atlas/__main__.py` — add runtime verb discovery
- `src/shared/packages/pyforge-atlas/tests/meta/test_cli_tool_parity.py` — live + fixture drift tests
- `src/shared/packages/pyforge-core/src/pyforge/core/dispatch.py` — re-point preparatory story stem
- `src/shared/packages/pyforge-core/tests/meta/test_cli_parity_matrix.py` — atlas-owned preparatory spec path

**Acceptance Criteria:**
- Given production inventories, when `pixi run -e pyforge-atlas pyforge-atlas-test` runs, then `tests/meta/test_cli_tool_parity.py` passes live and fixture drift cases
- Given injected drift in either direction, when parity fixtures run, then the meta-test fails with the matching FR-155 code
- Given `PREPARATORY_UNINTROSPECTABLE["atlas"]`, when pyforge-core matrix tests run, then the named spec resolves under pyforge-atlas planning-artifacts

## Spec Change Log

### 2026-09-10 — Review pass 1
- Trigger: verification-gap finding on pipeline argv tails
- Amended: added `test_run_tool_cli_pipeline_tokens_match_tool_names`
- Avoids: green FR-155 gate with wrong `--pipeline` slug in `TOOL_SPECS`

## Review Triage Log

### 2026-09-10 — Review pass
- verdicts: 12 findings — high 0, medium 1, low 2, false 7, maybe-false 2
- findings:
  - `[false]` `[reject]` Diff omits parity.py — files exist untracked in worktree; full implementation present
  - `[false]` `[reject]` TOOL_SPECS inert without parity.py — parity.py added and wired
  - `[false]` `[reject]` spec-22 date format broken — corrected to YYYY-MM-DD and superseded status
  - `[false]` `[reject]` event line in spec-22 Verification — removed from Verification section
  - `[medium]` `[patch]` `_preparatory_spec_path` misroutes spec-22-prep-atlas — dropped spec-22 from atlas prefix branch
  - `[low]` `[reject]` prefix heuristics brittle — acceptable for two known stems; defer broader registry
  - `[maybe-false]` `[defer]` discover_cli_verbs logging banner — Kedro configure side effect; unverified harm in CI
  - `[maybe-false]` `[defer]` empty project_group.commands — Kedro always ships run/ipython/package today
  - `[medium]` `[patch]` TOOL_SPECS argv tails not verified — added pipeline token test
  - `[false]` `[reject]` Intent audit: diff incomplete — git diff excluded untracked files only
  - `[low]` `[reject]` TOOL_SPECS description duplication with server.py — pre-existing pattern; out of scope
  - `[false]` `[reject]` spec-25-3 missing — spec file created at planning-artifacts path

## Auto Run Result

Status: done

**Summary:** Atlas now enforces marshal-shaped FR-155 CLI⇄tool parity: `TOOL_SPECS` for all 13 MCP tools, runtime `discover_cli_verbs()` from Kedro's project command surface, `mcp/parity.py` gate, and gated meta-test with live + fixture drift cases. `PREPARATORY_UNINTROSPECTABLE["atlas"]` re-pointed to this spec; pyforge-core matrix resolves atlas-owned preparatory specs.

**Files changed:**
- `pyforge/atlas/mcp/tools.py` — `TOOL_SPECS` registry
- `pyforge/atlas/mcp/parity.py` — FR-155 parity gate (new)
- `pyforge/atlas/__main__.py` — `discover_cli_verbs()`
- `tests/meta/test_cli_tool_parity.py` — gated meta-test (new)
- `pyforge-core/dispatch.py` — preparatory re-point
- `pyforge-core/tests/meta/test_cli_parity_matrix.py` — atlas spec path resolver
- `spec-22-prep-atlas-kedro-cli-introspection.md` — superseded
- `spec-25-3-…md` — story spec (this file)

**Review:** 2 patches applied (prefix routing, pipeline argv test); 2 deferred (logging side effect, empty commands edge); 8 rejected/false.

**Follow-up review recommended:** false

**Verification:**
- `pixi run -e pyforge-atlas pytest …/test_cli_tool_parity.py` — 12 passed
- `pixi run -e pyforge-atlas pyforge-atlas-test` — 1743 passed, 21 skipped
- `pixi run -e pyforge-core pytest …/test_cli_parity_matrix.py` — 4 passed

**Residual risks:** Kedro `project_group` lists `ipython`/`package` as CLI-only while `pyforge-atlas` forwards only `run`; trending_candidates remains tool-only (separate module CLI, not Kedro verb).

## Verification

**Commands:**
- `pixi run -e pyforge-atlas pytest src/shared/packages/pyforge-atlas/tests/meta/test_cli_tool_parity.py -v` — expected: 11 passed
- `pixi run -e pyforge-core pytest src/shared/packages/pyforge-core/tests/meta/test_cli_parity_matrix.py -v` — expected: all passed
