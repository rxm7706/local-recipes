---
title: "115.3: marshal-mcp registers every tool it lists, and a seed failure exits with the code its taxonomy documents"
type: 'fix'
created: '2026-11-10'
status: 'backlog'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
difficulty: medium
story: '115.3'
spec: pyforge-marshal
surface:
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/mcp/server.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/mcp/tools.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/mcp/parity.py
  - src/shared/packages/pyforge-marshal/tests/meta/test_mcp_server_registers_every_tool_spec.py
  - src/shared/packages/pyforge-marshal/tests/unit/test_mcp_story_103.py
  - src/shared/packages/pyforge-marshal/tests/unit/test_mcp_tools.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/main.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/seed/errors.py
  - src/shared/packages/pyforge-marshal/tests/unit/test_seed_exit_codes_at_main.py
  - src/shared/packages/pyforge-marshal/tests/meta/test_ad7_verdict_sole_ownership.py
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/.memlog.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md
  - docs/dreams/pyforge-marshal.md
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/mcp/server.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/mcp/tools.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/main.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/seed/errors.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/verdict.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/preserve.py
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-87-15-a-preserve-reaches-origin-only-through-the-content-gate.md
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** Two audit defects at marshal's two entry points, at `82a2b18828`. (1) `list_marshal_tools` reports 11 tools and `build_server()` registers 8: `marshal_preserve_list`, `marshal_preserve_push` and `marshal_preserve_retire` have bodies that run the CLI and no registration, while spec-87-15 and Story 87.15's Surface say the MCP face carries push and retire. (2) The seed handlers return 5 (state invalid) and 10 (internal); `main` admits only {0, 1, 2, 3, 4, 130} and turns both into 2, against CAP-13's distinct-per-failure-mode codes.

**Approach:** A fix under CAP-23 and CAP-13 (their amendments are in the memlog of 2026-11-10); no CAP minted. (1) The operator ruled on 2026-11-10: register all three preserve tools on the MCP face; eleven tools. The push and retire bodies run the CLI, which reads `pyforge.marshal.preserve_refs` (off everywhere), so they refuse while the flag is off. `test_mcp_story_103.py`'s `eight` assertions read `len(TOOL_SPECS)`. (2) `seed/errors.py` exports the closed set derived from `SeedError.__subclasses__()`; `main` admits it only when the dispatched command is `seed`; `GUARDED_EXIT_CODES` and `test_verdict.py:67` do not move; AD-7's sentence is in Story 114.1's render. The other reading (one frozen domain, renumbered seed codes) cannot keep 'distinct' with six failure modes in four free values.

Ledger key: `115-3-marshal-mcp-registers-every-tool-it-lists-and-a-seed-failure-exits-with-the-code-its-taxonomy-documents`. Type / Effort / Deps: fix / M / none.

## Boundaries & Constraints

**Always:**
- The registered tool names equal `TOOL_SPECS`, and counts in the tests derive from `TOOL_SPECS`.
- Seed's six codes (1, 2, 3, 4, 5, 10) reach the process exit only for `seed` verbs.

**Never:**
- Never remove the preserve tools (the operator ruled registration).
- Never add a kill switch (operator ruling of 2026-11-10); the preserve verbs stay behind `pyforge.marshal.preserve_refs`.
- Never widen `GUARDED_EXIT_CODES` for other verbs.

## Acceptance Criteria

- **AC1 — Registered names equal TOOL_SPECS, and the test's two mutations fail it (drop a registration; add a spec).**

  ```bash
  pixi run --frozen -e pyforge-marshal pytest src/shared/packages/pyforge-marshal/tests/meta/test_mcp_server_registers_every_tool_spec.py -q
  ```

  Expected: exit 0.

- **AC2 — The server, tool and parity tests pass with the count derived from TOOL_SPECS, not typed.**

  ```bash
  pixi run --frozen -e pyforge-marshal pytest src/shared/packages/pyforge-marshal/tests/unit/test_mcp_story_103.py src/shared/packages/pyforge-marshal/tests/unit/test_mcp_tools.py src/shared/packages/pyforge-marshal/tests/meta/test_cli_tool_parity.py -q
  ```

  Expected: exit 0.

- **AC3 — Eleven tools (the operator's ruling of 2026-11-10: register all three), and push and retire refuse with the flag off.**

  ```bash
  test "$(git grep -c -E 'def marshal_preserve_(list|push|retire)' -- src/shared/packages/pyforge-marshal/src/pyforge/marshal/mcp/server.py | cut -d: -f2)" = 3 && pixi run --frozen -e pyforge-marshal pytest src/shared/packages/pyforge-marshal/tests/unit/test_mcp_tools.py -q -k 'preserve and flag_off'
  ```

  Expected: exit 0; 2 or more selected.

- **AC4 — Through `main`, a schema-breaking state file exits 5 and a broken packaged manifest exits 10; a non-seed handler that returns 5 still exits 2.**

  ```bash
  pixi run --frozen -e pyforge-marshal pytest src/shared/packages/pyforge-marshal/tests/unit/test_seed_exit_codes_at_main.py -q
  ```

  Expected: exit 0.

- **AC5 — The lattice domain is unchanged and solely owned.**

  ```bash
  pixi run --frozen -e pyforge-marshal pytest src/shared/packages/pyforge-marshal/tests/unit/test_verdict.py src/shared/packages/pyforge-marshal/tests/meta/test_ad7_verdict_sole_ownership.py src/shared/packages/pyforge-marshal/tests/unit/test_cli.py src/shared/packages/pyforge-marshal/tests/unit/test_seed_errors.py -q
  ```

  Expected: exit 0.

- **AC6 — Lint and types hold.**

  ```bash
  pixi run -e pyforge-guild lint-types
  ```

  Expected: exit 0.

</intent-contract>

## Binding

Parent: `spec-pyforge-marshal` CAP-23 and CAP-13 (amended 2026-11-10). FR-155 and FR-126 body sentences (written by Story 114.1).

- Epic: Epic 115 (`_bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md`, `### Story 115.3: marshal-mcp registers every tool it lists, and a seed failure exits with the code its taxonomy documents`).
- Dream: `docs/dreams/pyforge-marshal.md`, 2026-11-10 — The Spec says what marshal is, and its roots come from one place.
- Rulings: `docs/dreams/pyforge-unifying-strategy.md`, Realization log, the 2026-11-10 entry and its two addenda.

## Notes

- The plan's removal variant is void: the operator ruled registration on 2026-11-10.
- Cross-station: the compiled skill's 'frozen exit domain' line is steward:S-29.5's.

## Spec Change Log

- 2026-11-10: minted at `backlog` by the cutover-readiness mint (operator 2026-11-10, "Accept all, run mint"; `docs/dreams/pyforge-unifying-strategy.md`, Realization log, the 2026-11-10 entry and its two addenda). The Dream entry (`docs/dreams/pyforge-marshal.md`, 2026-11-10) and the memlog entries of `spec-pyforge-marshal` came first; `SPEC.md` is rendered by Story 114.1.
