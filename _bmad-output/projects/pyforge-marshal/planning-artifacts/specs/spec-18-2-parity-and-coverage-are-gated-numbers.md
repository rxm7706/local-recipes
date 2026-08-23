---
title: Parity and coverage are gated numbers
type: test
created: '2026-08-23'
status: done
review_loop_iteration: 0
followup_review_recommended: true
context: []
warnings: []
baseline_revision: 8ee0c179d7e47f0314a47cd4213bd6248793e10a
deferred:
  - summary: >-
      Coverage detection is filesystem path presence only; an empty stub
      mcp/tools.py or server.py counts as covered without proving registered tools.
    evidence: |-
      Blind Hunter / Design Notes intentionally measure presence for FR-156.
      Stronger "callable FastMCP tools" checks are a future hardening pass.
    location: >-
      src/shared/packages/pyforge-marshal/src/pyforge/marshal/mcp/coverage.py
    severity: low
  - summary: >-
      discover_cli_verbs walks private argparse _actions / _build_parser internals.
    evidence: |-
      Edge-case / Blind Hunter. Works against the live CLI today; a public
      inventory API would harden the gate against parser refactors.
    location: >-
      src/shared/packages/pyforge-marshal/src/pyforge/marshal/mcp/parity.py
    severity: low
  - summary: >-
      resolve_repo_root has no MARSHAL_REPO_ROOT override when the package is
      installed outside the monorepo layout.
    evidence: |-
      Blind Hunter. python -m coverage is repo-operator oriented; installed
      wheel use outside the tree is out of v1 scope.
    location: >-
      src/shared/packages/pyforge-marshal/src/pyforge/marshal/mcp/coverage.py
    severity: low
---

<intent-contract>

## Intent

**Problem:** After Story 18.1, CLI ⇄ tool parity and per-station tool-surface coverage are still review-time guesses (FR-155, FR-156). The 2-of-6-with-Marshal-at-zero finding is why coverage must be measured, not asserted.

**Approach:** Add a meta-test that fails when a capability is present on one surface (CLI or tools) and absent from the other, plus a per-station coverage report that reports tool-surface coverage as a number.

## Acceptance Criteria

- A capability present in CLI and absent from tools (or vice versa) fails a gated check (FR-155).
- Per-station tool-surface coverage is reported as a number (FR-156) — measured, not hard-asserted to 100%.
- Fixture-covered; builds on Story 18.1 `pyforge.marshal.mcp` surface.

## Boundaries & Constraints

**Never:** Re-implement 18.1 tool registration. Never `scripts/bmad-switch`. Finalize marshal ledger only.

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/mcp/parity.py` — FR-155 inventory + `assert_cli_tool_parity` / `parity_findings` (`CLI_ONLY_VERBS`, `TOOL_ONLY_NAMES`)
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/mcp/coverage.py` — FR-156 Dream-six station inventory + `tool_surface_coverage_report` (`python -m pyforge.marshal.mcp.coverage`)
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/mcp/tools.py` — Story 18.1 `TOOL_SPECS` (unchanged; parity consumes it)
- `src/shared/packages/pyforge-marshal/tests/meta/test_cli_tool_parity.py` — live gate + deliberate parity-failure fixtures
- `src/shared/packages/pyforge-marshal/tests/meta/test_tool_surface_coverage.py` — report shape / number / fixture trees

## Design Notes

- **CLI-only allowlist is required.** Marshal has 17 top-level verbs; `TOOL_SPECS` wraps a subset. Verbs not yet on the tool surface live in `CLI_ONLY_VERBS`. Gate rules: tools claiming a CLI must hit a real verb; on-surface verbs (CLI − allowlist) must have tools; `cli: None` tools must be in `TOOL_ONLY_NAMES` (`list_marshal_tools`); allowlist entries must not go stale (unknown verb, or verb that already has a tool / tool-only that also claims a CLI).
- **Coverage uses the Dream's six stations** (mason, atlas, warden, herald, steward, marshal) so the historical 2-of-6 claim stays measurable. Covered = mason's `conda_forge_server.py` craft tools, or a station package `mcp/server.py`|`tools.py`. Warden's scan tools on mason's server without a warden `mcp/` package stay uncovered (matches the Dream table). After 18.1, marshal flips to covered — live ratio is **3/6**, published not asserted.
- Does **not** re-register FastMCP tools; parity/coverage are FastMCP-free helpers beside `tools.py`. Coverage is not re-exported from `mcp/__init__.py` so `python -m pyforge.marshal.mcp.coverage` stays warning-free.

## Tasks

- [x] FR-155 parity module + meta-test (live pass + fixture failures)
- [x] FR-156 coverage report module + meta/unit shape tests (number published, not == 1.0)
- [x] Review / follow-up loop
- [x] Mark done

## Verification

- `pixi run --frozen -e pyforge-marshal pytest src/shared/packages/pyforge-marshal/tests/meta src/shared/packages/pyforge-marshal/tests/unit/test_mcp_tools.py src/shared/packages/pyforge-marshal/tests/unit/test_mcp_registration.py -q --tb=short` → green (1514 passed)
- Parity failure cases fixture-covered (`cli_missing_tool`, `tool_cli_unknown`, `cli_only_has_tool`, `tool_without_cli`, `tool_only_missing`, `tool_only_has_cli`, `tool_cli_malformed`)
- `python -m pyforge.marshal.mcp.coverage` prints `covered/total` + float `coverage`
- CI: detectors, linter, package tests

## Review Triage Log

### 2026-08-23 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 9: (high 1, medium 5, low 3)
- defer: 3: (high 0, medium 0, low 3)
- reject: 4
- addressed_findings:
  - `[high]` `[patch]` `tools_by_cli_verb` ran before per-spec try/except so malformed `cli` crashed instead of `tool_cli_malformed` — fixed ordering + fixture
  - `[medium]` `[patch]` `test_coverage_not_hard_asserted_to_one` permanently required `coverage < 1.0` — replaced with publish-not-gate shape test
  - `[medium]` `[patch]` missing deliberate fixtures for `tool_only_missing`, `tool_only_has_cli`, `tool_cli_malformed` — added
  - `[medium]` `[patch]` mason missing-craft → uncovered path unverified — fixture added
  - `[medium]` `[patch]` non-mason package `mcp/` positive fixture + live atlas regression lock — added
  - `[low]` `[patch]` `TOOL_ONLY_NAMES` not exported; coverage import in `__init__` caused `python -m` RuntimeWarning — fixed
  - `[low]` `[patch]` duplicate stations inflated total; non-str `cli[0]` / non-Mapping specs / empty `repo_root` — hardened

## Auto Run Result

Status: done

Summary: FR-155 CLI⇄tool parity is gated via `mcp/parity.py` + meta-tests (live pass + deliberate failure fixtures). FR-156 publishes Dream-six station tool-surface coverage as a number via `mcp/coverage.py` (`python -m pyforge.marshal.mcp.coverage`) without asserting 100%. Live coverage **3/6 (0.5)**.

Files changed:
- `src/.../mcp/parity.py` — FR-155 inventory gate
- `src/.../mcp/coverage.py` — FR-156 coverage report
- `src/.../mcp/__init__.py` — re-export parity helpers (not coverage)
- `tests/meta/test_cli_tool_parity.py` — live + fixture gates
- `tests/meta/test_tool_surface_coverage.py` — report shape + fixtures
- `planning-artifacts/specs/spec-18-2-…md` — story status / design / triage

Review findings: 9 patches applied; 3 deferred; 4 rejected (detector wiring beyond story surface; intent Problem prose immutable; exporting every helper; `ok` always True).

Follow-up review recommendation: `true` — patched high=1 (score: high present; medium 5 × 3 + low 3 = 18 ≥ 5).

Verification: `pixi run --frozen -e pyforge-marshal pytest …/tests/meta …/test_mcp_tools.py …/test_mcp_registration.py -q` → **1514 passed**. Coverage CLI prints `ratio: "3/6"`.

Residual risks: path-presence coverage heuristic; argparse-private CLI discovery; no Guildhall detector wire-up in this story.
