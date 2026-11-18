---
title: '40.1: The CFE scripts merge the pixi config layers, and the MCP reference names the server it is'
type: 'fix'
created: '2026-11-18'
status: 'done'
story: 40-1-the-cfe-scripts-merge-the-pixi-config-layers-and-the-mcp-reference-names-the-server-it-is
spec: spec-pyforge-mason
difficulty: 'easy'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
flag-exempt: detector-or-gate   # tests, a gate's own module and the scripts a gate runs; a gated gate is a silent green (roster list)
surface:
  - '.claude/skills/conda-forge-expert/**'
  - '.claude/scripts/conda-forge-expert/**'
  - 'docs/explanation/enterprise-deployment.md'
  - 'docs/reference/pixi-config-jfrog.example.toml'
context:
  - _bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-pyforge-mason/SPEC.md
  - _bmad-output/projects/pyforge-mason/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-mason/planning-artifacts/deferred-work-ledger.md
  - docs/dreams/pyforge-mason.md
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** `_http.read_pixi_config` returns the first of the project, user and system config files that exists; the tracked `.pixi/config.toml` always exists here, so mirrors an operator sets in `~/.pixi/config.toml` never reach the CFE scripts although pixi itself merges the layers; `reference/mcp-tools.md` calls the server FastMCP.

**Approach:** The reader merges system, user and project layers the way pixi does (later layer wins per key), its tests cover the three-layer case, the reference says `MCPServer`, and the skill's CHANGELOG carries the retro entry and semver bump.

Ledger key: `40-1-the-cfe-scripts-merge-the-pixi-config-layers-and-the-mcp-reference-names-the-server-it-is`.

### Living CAP citations

- spec-pyforge-mason CAP-1 (the CFE seam; realized, no text change).

## Boundaries & Constraints

**Always:**
- Read every verdict from its exit code, never through a pipe.
- Close the deferred-work row this story names with the commit that resolves it.

**Never:**
- Never weaken an assertion that holds on Linux, hand-edit a compiled skill, a `SPEC.md`, a generated page or `sprint-status-ledger.yaml`.

## Acceptance Criteria

**Given** `_http.read_pixi_config` returns the first of the project, user and system config files that exists; the tracked `.pixi/config.toml` always exists here, so mirrors an operator sets in `~/.pixi/config.toml` never reach the CFE scripts although pixi itself merges the layers; `reference/mcp-tools.md` calls the server FastMCP
**When** the reader merges system, user and project layers the way pixi does (later layer wins per key), its tests cover the three-layer case, the reference says `MCPServer`, and the skill's CHANGELOG carries the retro entry and semver bump
**Then** a mirror set only in a user-level config reaches `auth_headers_for`'s host gate and the resolver; the CFE meta and unit suites exit 0; the enterprise deployment page and the JFrog template say what the scripts now do
**And** the conda-forge-expert items of `DW-doctor-59-3-1` reads resolved in its ledger with the commit that closed it

- **AC1 — The story's own check passes.** Expected: exit 0.

  ```bash
  pixi run --frozen -e local-recipes test-ci
  ```

</intent-contract>

## Binding

- Capabilities: spec-pyforge-mason CAP-1 (the CFE seam; realized, no text change).
- Dream: `docs/dreams/pyforge-mason.md` § *Realization log*, the 2026-11-18 entry; operator ruling of 2026-11-18: "THIS MACHINE WILL BE A FIRST CLASS DEVELOPMENT HOST -- JUST FIX ALL THE DEFERRED ROW ITEMS NOW.. AND NOT LEAVE ANYTHING FOR LATER", "JUST USE ctranslate2 and remove the other one", "we should continue to support manticore and antigravity", "we still want to do everything in this session as one PR".
- Epic: Epic 40, minted with this story.
- Ledger key: `40-1-the-cfe-scripts-merge-the-pixi-config-layers-and-the-mcp-reference-names-the-server-it-is` (`backlog`).
- Surface: `marshal-policy.toml` `[epic_surfaces]."40"`.

## Verification

**Commands:** the Acceptance Criteria above, each read from its exit code.

## Spec Change Log

- 2026-11-18: minted from the station Dream's 2026-11-18 entry and the operator's rulings of the same date.
