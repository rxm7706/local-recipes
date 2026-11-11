---
title: "114.3: Marshal's public contract is one companion, and a meta-test keeps it complete"
type: 'feature'
created: '2026-11-10'
status: 'blocked'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
flag-exempt: detector-or-gate   # a companion and a check that judges; nothing a user reaches at runtime (roster flag_exemptions; the exempt form of spec-110-38)
difficulty: heavy
story: '114.3'
spec: pyforge-marshal
surface:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/contract.md
  - src/shared/packages/pyforge-marshal/tests/meta/test_public_contract.py
  - src/shared/packages/pyforge-marshal/tests/_support/contract_inventory.py
  - src/shared/packages/pyforge-marshal/README.md
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/.memlog.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md
  - docs/dreams/pyforge-marshal.md
  - docs/reference/story-spec-flag-block.md
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/main.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/mcp/tools.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/mcp/server.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/findings.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/verdict.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/seed/errors.py
  - src/shared/packages/django-marshal/src/django_marshal_portal/mcp_asgi.py
warnings: []
deferred: []
---

> **Blocked 2026-11-10 (forward dependency).** Its Deps name stories in later epics (S-115.3, S-115.4, S-116.1).
> The key stays `blocked` until those stories are `done` on branch `cutover-readiness-2026-11-10`;
> the orchestrator of that PR unblocks it only with operator confirmation (AGENTS.md § Policy).

<intent-contract>

## Intent

**Problem:** At `82a2b18828` the Spec lacks marshal's public contract. A walk of `pyforge marshal ... --help` finds 66 verb paths (57 leaves), 33 never named in the Spec body, and 64 of 103 help-visible flags absent. `core/findings.py` registers 333 `MRS-*` codes against 32 in `SPEC.md`; `mcp/tools.py` holds 11 `TOOL_SPECS` and none of the names appears in the Spec folder; 38 of 46 `pyforge.marshal.*` flag keys are absent. The README covers seed only.

**Approach:** Realizes spec-pyforge-marshal:CAP-304. The inventory is derived, never typed twice: `tests/_support/contract_inventory.py` walks `cli.main._build_parser()` (sub-parser choices and option strings), reads `mcp.tools.TOOL_SPECS` and the names `mcp.server.build_server()` registers, `core.findings.REGISTERED_CODES`, the seed `FindingType` enum, `core.verdict.GUARDED_EXIT_CODES` with the seed error leaves, every `pyforge.<station>.<key>` string constant that is not a module path, and every `ENV_*` constant or `os.environ` / `os.getenv` key. One rule covers the seam: a module that imports `root_of_record` from `pyforge.core.cutover_root` contributes `pyforge.core.cutover_root.CUTOVER_FLAG` (`pyforge.cutover_root`) to the flag-key set, since after Story 115.4 no marshal module holds that string. The test parses `contract.md`'s tables and compares sets in both directions; it is `live_tree` because `contract.md` sits outside the package. The station face's tools (`run_loop`, `start_loop`, `get_loop`, `list_loop_story_tasks`, `marshal_watch` and the held-loop tools in `django_marshal_portal/mcp_asgi.py`, read by AST) are a sub-table, with the 2026-11-06 fact that `start_loop` runs `marshal factory dispatch` for a `pyforge:admin` caller when `pyforge.steward.start_loop_dispatch` is on (spec-pyforge-unifying-strategy:CAP-20).

Ledger key: `114-3-marshal-s-public-contract-is-one-companion-and-a-meta-test-keeps-it-complete`. Type / Effort / Deps: feature / L / S-115.3, S-115.4, S-116.1.

## Boundaries & Constraints

**Always:**
- `contract.md` has exactly six `## ` sections: CLI verbs and flags; MCP tools; Feature-flag keys; Environment variables; Diagnostic codes; Exit codes.
- Both exit domains are written: the lattice {0, 1, 2, 3, 4, 130} and the seed group's six codes (Story 115.3).
- Each family has a mutation test that proves the check fires in both directions.

**Never:**
- No generator script and no new verb: the companion is written once and the test keeps it true.
- Never import a station's internals to read its face; the station face is read by AST.
- Never type an inventory list into the test.

## Acceptance Criteria

- **AC1 — The contract test passes on the tree.**

  ```bash
  pixi run --frozen -e pyforge-marshal pytest src/shared/packages/pyforge-marshal/tests/meta/test_public_contract.py -q -m live_tree
  ```

  Expected: exit 0.

- **AC2 — Each family has a mutation test that proves the check fires (verb path, flag, tool, flag key, environment variable, diagnostic code, exit code) and a reverse one (a row the code lacks).**

  ```bash
  pixi run --frozen -e pyforge-marshal pytest src/shared/packages/pyforge-marshal/tests/meta/test_public_contract.py -q -m live_tree -k 'missing_from_the_contract or stale_in_the_contract'
  ```

  Expected: exit 0; 8 or more passed.

- **AC3 — The flag-key family includes the root-of-record key through the seam.**

  ```bash
  grep -c '`pyforge.cutover_root`' _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/contract.md
  ```

  Expected: prints 1 or more.

- **AC4 — contract.md has its six sections.**

  ```bash
  grep -c '^## ' _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/contract.md
  ```

  Expected: prints 6.

- **AC5 — The README points at the contract.**

  ```bash
  grep -c 'contract.md' src/shared/packages/pyforge-marshal/README.md
  ```

  Expected: prints 1 or more.

- **AC6 — Lint and types hold.**

  ```bash
  pixi run -e pyforge-guild lint-types
  ```

  Expected: exit 0.

</intent-contract>

## Binding

Parent: `spec-pyforge-marshal:CAP-304` (memlog 2026-11-10; rendered by Story 114.1). FR-246 (written by Story 114.1).

- Epic: Epic 114 (`_bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md`, `### Story 114.3: Marshal's public contract is one companion, and a meta-test keeps it complete`).
- Dream: `docs/dreams/pyforge-marshal.md`, 2026-11-10 — The Spec says what marshal is, and its roots come from one place.
- Rulings: `docs/dreams/pyforge-unifying-strategy.md`, Realization log, the 2026-11-10 entry and its two addenda.

## Notes

- Depends on Stories 115.3 and 115.4 so the tool set, the exit domains and the flag set it records are final, and on Story 116.1 for the `live_tree` marker.
- Cross-station: steward:S-124.5 takes the persona tool names from `contract.md`.
- Deferred row this story's finding feeds (written by Story 116.5): DW-marshal-114-3-1 (about 290 capabilities name no test or command that proves them).

## Spec Change Log

- 2026-11-10: minted at `blocked` (forward dependency: until S-115.3, S-115.4 and S-116.1 are done) by the cutover-readiness mint (operator 2026-11-10, "Accept all, run mint"; `docs/dreams/pyforge-unifying-strategy.md`, Realization log, the 2026-11-10 entry and its two addenda). The Dream entry (`docs/dreams/pyforge-marshal.md`, 2026-11-10) and the memlog entries of `spec-pyforge-marshal` came first; `SPEC.md` is rendered by Story 114.1.
