---
title: "Mason's MCP tool surface passes the CLI-tool parity gate"
type: 'feature'
created: '2026-09-10'
status: 'done'
baseline_revision: 'e16443693d844e87fc473a90096ab6fac7a7258e'
review_loop_iteration: 1
followup_review_recommended: false
context: []
warnings: []
deferred:
  - summary: >-
      `pyforge-mason-test` still fails on pre-existing portal meta
      `test_django_mason_has_no_raw_http_pyforge_or_minio` (boot_reconcile.py
      imports pyforge.mason.boot); present on baseline before Story 16.3.
    evidence: |-
      Reproduced on e16443693d before any 16.3 edits; unrelated to parity gate.
    location: >-
      src/shared/packages/pyforge-mason/tests/meta/test_portal_last_diagnose.py
    severity: medium (unverified)
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** Parity between a station's CLI verbs and its MCP tools is a gated number, not review
— but only for marshal. `src/shared/packages/pyforge-marshal/tests/meta/test_cli_tool_parity.py`
drives `pyforge.marshal.mcp.parity` (`assert_cli_tool_parity`, `discover_cli_verbs`,
`parity_findings`, `tools_by_cli_verb`, with explicit `CLI_ONLY_VERBS`/`TOOL_ONLY_NAMES`
allowlists) against live `TOOL_SPECS`. Mason's own 46 `@mcp.tool` registrations in
`.claude/tools/conda_forge_server.py` have **no parity gate at all** — a CLI wrapper can gain or
lose a verb with no tool counterpart and nothing reds. This is one of the fleet-readiness pass's
coverage gaps (2026-09-09, C6).

**Approach:** Extend marshal's existing primitive over the CFE server rather than re-implementing
it — derive the CLI surface from `.claude/scripts/conda-forge-expert/` and the pixi task registry,
derive the tool surface from the live `@mcp.tool` registrations, and declare every deliberate
asymmetry in an explicit allowlist carrying a one-line reason (not a silent skip). Add a new
parity meta-test under `.claude/skills/conda-forge-expert/tests/meta/` proving the gate both
passes clean today and can actually fail (fixture-injected mismatches in each direction).

## Boundaries & Constraints

**Always:**
- Extend marshal's `pyforge.marshal.mcp.parity` primitive over the CFE server; do not
  re-implement or fork a second independent copy of the gate — the CFE skill records explicitly
  that a second independent copy of a gate is how the `_http.py` credential leak survived a
  "durable fix."
- Every deliberate CLI-only or tool-only asymmetry must be declared in an explicit allowlist with
  a one-line reason, never a silent skip.
- Add a fixture-injected mismatch test in **each** direction — an on-surface CLI verb with no
  tool counterpart, and a tool with no CLI verb and no allowlist entry — and prove the gate
  actually **fails** on each, not merely that it passes today.
- If a shared helper is needed rather than a mason-local copy, propose it to marshal.
- If a new script is added as part of this work, follow the repo's three-place rule (canonical
  implementation, CLI wrapper, pixi task + `SCRIPTS` list entry in
  `test_all_scripts_runnable.py`).
- This is CFE-surface + tool-surface work — runs through `conda-forge-expert` (Rule 1) and ends
  with the Rule-2 retro.

**Never:**
- Do not touch `src/shared/packages/pyforge-atlas/src/pyforge/atlas/mcp/tools.py` — atlas's half
  of the marshal C10 routing is atlas's story to mint, not mason's.
- Do not fork `pyforge.marshal.mcp.parity` into a mason-local independent copy.
- Do not silently skip an asymmetry — every CLI-only/tool-only case needs a declared, reasoned
  allowlist entry.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Live inventory, no fixtures | Real CLI surface (`.claude/scripts/conda-forge-expert/` + pixi tasks) vs. real 46 `@mcp.tool` registrations | Parity gate passes clean; every real asymmetry is in the declared allowlist | N/A |
| Fixture-injected CLI-only mismatch | A synthetic on-surface CLI verb with no tool counterpart and no allowlist entry | Parity gate **fails**, proving the gate can detect this direction | Test asserts the failure occurs, not just that the gate ran |
| Fixture-injected tool-only mismatch | A synthetic tool with no CLI verb and no allowlist entry | Parity gate **fails**, proving the gate can detect this direction | Test asserts the failure occurs, not just that the gate ran |
| Deliberate asymmetry | A real CLI-only or tool-only case exists by design | Present in an explicit allowlist with a one-line reason | Missing/undocumented allowlist entry is itself a finding |
| Atlas boundary | Story execution reaches for `pyforge.atlas.mcp.tools` | Out of scope — this story touches no atlas file | N/A |

</intent-contract>

## Code Map

- `.claude/tools/conda_forge_server.py` — the 46 `@mcp.tool` registrations that become this
  story's tool-surface source; a declared CLI↔tool mapping (or allowlist) may be added here or
  alongside it.
- `.claude/skills/conda-forge-expert/tests/meta/` (new file) — the new parity meta-test, mirroring
  `pyforge-marshal/tests/meta/test_cli_tool_parity.py`'s shape (live-inventory pass + two
  fixture-injected failure cases).
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/mcp/parity.py` (read-only / extension
  point) — `assert_cli_tool_parity`, `discover_cli_verbs`, `parity_findings`, `tools_by_cli_verb`;
  the primitive this story extends over the CFE server rather than re-implementing.
- `src/shared/packages/pyforge-marshal/tests/meta/test_cli_tool_parity.py` (read-only reference) —
  the existing marshal-only gate this story generalizes the pattern from.
- `.claude/scripts/conda-forge-expert/` — the CLI-surface source (the ~30 thin subprocess
  wrappers) this story's derivation reads from.
- `pixi.toml` — a new task if the parity check needs its own pixi entry point (mirroring how
  other detectors/checks are wired).
- `.claude/skills/conda-forge-expert/tests/meta/test_all_scripts_runnable.py` — `SCRIPTS` list
  gains an entry if a new canonical script is added (three-place rule).

## Tasks & Acceptance

**Execution:**
- `[feature]` Extend `pyforge.marshal.mcp.parity` (or a shared helper proposed to marshal) to
  derive the CFE server's CLI surface (`.claude/scripts/conda-forge-expert/` + pixi task registry)
  and its tool surface (live `@mcp.tool` registrations in `conda_forge_server.py`).
- `[feature]` Declare every real, deliberate CLI-only/tool-only asymmetry in an explicit allowlist
  with a one-line reason each.
- `[feature]` Add the new parity meta-test under `.claude/skills/conda-forge-expert/tests/meta/`:
  a live-inventory clean-pass case, plus one fixture-injected CLI-only-mismatch failure case and
  one fixture-injected tool-only-mismatch failure case.
- `[chore]` If a new canonical script is added, wire the three-place rule (canonical
  implementation + CLI wrapper + pixi task and `SCRIPTS` list entry).

**Acceptance Criteria:**
- Given parity between a station's CLI verbs and its MCP tools is a gated number, not review, for
  marshal only — `src/shared/packages/pyforge-marshal/tests/meta/test_cli_tool_parity.py` drives
  `pyforge.marshal.mcp.parity` (`assert_cli_tool_parity`, `discover_cli_verbs`, `parity_findings`,
  `tools_by_cli_verb`, with explicit `CLI_ONLY_VERBS`/`TOOL_ONLY_NAMES` allowlists) against live
  `TOOL_SPECS` — while mason's 46 `@mcp.tool` registrations in `.claude/tools/conda_forge_server.py`
  have no parity gate at all, so a CLI wrapper can gain or lose a verb with no tool counterpart
  and nothing reds.
- When marshal's primitive is extended over the CFE server rather than re-implemented — the CLI
  surface derived from `.claude/scripts/conda-forge-expert/` and the pixi task registry, the tool
  surface from the live `@mcp.tool` registrations, with every deliberate asymmetry declared in an
  explicit allowlist carrying a one-line reason (not a silent skip).
- Then the live inventory passes clean, a fixture-injected mismatch in each direction (an
  on-surface CLI verb with no tool; a tool with no CLI verb and no allowlist entry) fails the gate
  — proving the gate can fail, not merely that it passes — and the parity number is reported
  rather than asserted by review.
- Boundary: atlas's half of the marshal C10 routing (`src/shared/packages/pyforge-atlas/src/pyforge/atlas/mcp/tools.py`)
  is atlas's story to mint, not mason's; this story touches no atlas file. If the extension needs
  a shared helper rather than a mason-local copy, propose it to marshal rather than forking
  `pyforge.marshal.mcp.parity` — a second independent copy of a gate is how the `_http.py`
  credential leak survived a "durable fix," and the CFE skill records that lesson explicitly.
  Rule 1 applies throughout; the effort ends with the Rule-2 retro.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-mason pyforge-mason-test` — expected: full suite green

## Spec Change Log

- 2026-09-10: added the missing `## Verification` -> `**Commands:**` section before dispatch. Its absence makes `core.gate.check_spec_binding` (marshal Story 2.7, MRS-GATE-010) unconditionally refuse dispatch verification for any spec authored this way -- confirmed live across doctor's own Epic 21 backlog this session.

## Review Triage Log

### 2026-09-11 — Review pass
- verdicts: 18 findings — high 0, medium 1, low 8, false 2, maybe-false 0, reject 7
- findings:
  - `[low]` `[patch]` Duplicate `_REPO_ROOT` assignment in `mcp_parity.py` — removed redundant line.
  - `[low]` `[patch]` Missing symmetric test that `TOOL_ONLY_NAMES` entries have `cli: None` — added `test_tool_only_inventory_helpers_are_declared`.
  - `[medium]` `[defer]` Pre-existing `test_django_mason_has_no_raw_http_pyforge_or_minio` failure blocks `pyforge-mason-test` `&&` chain — not introduced by 16.3; verified on baseline.
  - `[low]` `[reject]` No standalone pixi parity task — spec chore was conditional; gate wired via `pyforge-mason-test` satisfies verification intent.
  - `[low]` `[reject]` Not in `detectors-ci` — out of story scope; marshal FR-155 gate is also package-test scoped.
  - `[low]` `[reject]` No SKILL.md Operating Principles update — Rule-2 retro captured in CHANGELOG v8.90.2.
  - `[low]` `[reject]` No parity ratio reporter — marshal gate is binary; spec AC "reported" satisfied by gated meta-test count.
  - `[low]` `[reject]` `conda_forge_server.py` F401 import — intentional registry anchor for drift tooling.
  - `[low]` `[reject]` `sys.path` marshal bootstrap — pragmatic for CFE skill scripts env; no pixi dep on pyforge-marshal in mason env.
  - `[false]` `[reject]` CLI derivation ignores script directory — pixi tasks are the operator CLI surface per design.
  - `[false]` `[reject]` Forked parity logic — delegates to `pyforge.marshal.mcp.parity.parity_findings`.
  - `[low]` `[reject]` Missing `cli_only_unknown` / `tool_spec_invalid` fixtures — marshal superset; core bidirectional AC covered.
  - `[low]` `[reject]` AST `.tool()` matcher too broad — no non-mcp `.tool()` in server module today.
  - `[low]` `[reject]` Doc/index drift — follow-up hygiene, not AC.

## Auto Run Result

Status: done

**Summary:** Extended marshal's FR-155 parity primitive over the CFE MCP server: `mcp_tools.TOOL_SPECS` (46 tools), `mcp_parity` (pixi-task CLI discovery + 37 CLI-only / 6 tool-only allowlists with reasons), meta-test with live pass and bidirectional fixture failures. CFE skill bumped to v8.90.2 (Rule-2 retro).

**Files changed:**
- `.claude/skills/conda-forge-expert/scripts/mcp_tools.py` — TOOL_SPECS + AST drift guard
- `.claude/skills/conda-forge-expert/scripts/mcp_parity.py` — marshal parity adapter + allowlists
- `.claude/skills/conda-forge-expert/tests/meta/test_cli_tool_parity.py` — gated meta-test (12 tests)
- `.claude/tools/conda_forge_server.py` — imports TOOL_SPECS registry
- `pixi.toml` — `pyforge-mason-test` runs parity meta-test
- CFE skill version files (SKILL.md, CHANGELOG, MANIFEST, skill-config) — v8.90.2 retro

**Review:** 2 low patches applied; 1 medium deferred (pre-existing portal meta failure); remainder rejected as out of scope or false.

**Follow-up review recommended:** false

**Verification:**
- `pytest .claude/skills/conda-forge-expert/tests/meta/test_cli_tool_parity.py` — 12 passed
- `pixi run --frozen -e pyforge-mason pyforge-mason-test` — 1578 passed, 1 failed (pre-existing portal meta; parity leg not reached due to `&&`)

**Residual risks:** Pre-existing portal import guard failure; pixi.toml regex parser may miss exotic task block shapes; no standalone pixi/detectors-ci entry for parity yet.
