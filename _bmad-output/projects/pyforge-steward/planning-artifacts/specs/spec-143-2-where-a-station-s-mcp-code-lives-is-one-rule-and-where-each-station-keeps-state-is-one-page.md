---
title: '143.2: Where a station''s MCP code lives is one rule, and where each station keeps state is one page'
type: 'docs'
created: '2026-11-26'
status: 'done'
story: 143-2-where-a-station-s-mcp-code-lives-is-one-rule-and-where-each-station-keeps-state-is-one-page
spec: spec-pyforge-steward
difficulty: 'easy'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
surface:
  - 'src/shared/packages/pyforge-steward/tests/meta/test_mcp_placement.py'
  - 'docs/reference/station-state.md'
  - 'docs/map.yaml'
  - 'docs/MAP.md'
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/SPEC.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/epics.md
  - docs/dreams/pyforge-steward.md
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** Every portal ships the mounted MCP face, and two base packages also hold server code; no rule says which case is which. Where each station keeps state is written in no one place.

**Approach:** Amend canopy:AD-5 with a placement clause that states what the tree already does, and hold it with a live-tree test in steward's suite. Write `docs/reference/station-state.md` from a read of each station's stores and register it in the docs map. Unify nothing.

Ledger key: `143-2-where-a-station-s-mcp-code-lives-is-one-rule-and-where-each-station-keeps-state-is-one-page`.

### Living CAP citations

- spec-pyforge-unifying-strategy:CAP-4 (realized, no text change).
- canopy:AD-5 (amended 2026-11-26).

## Boundaries & Constraints

**Always:**
- Read every verdict from its exit code, never through a pipe.

**Never:**
- Never move MCP code or unify a store here.

## Acceptance Criteria

**Given** MCP placement has no stated rule and station state has no page
**When** canopy:AD-5 gains the placement clause, the test is added, and the page is written and registered
**Then** the test fails on a missing or second portal face, an undeclared base-package server, or an undeclared portal import; the page classifies each store
**And** no code moves

- **AC1 — The placement test passes.** Expected: exit 0.

  ```bash
  pixi run --frozen -e pyforge-steward pytest src/shared/packages/pyforge-steward/tests/meta/test_mcp_placement.py -q -m live_tree
  ```

- **AC2 — The docs map is consistent.** Expected: exit 0.

  ```bash
  pixi run --frozen -e pyforge-guild docs-map-hygiene-check
  ```

</intent-contract>

## Review (2026-11-26)

Independent review by a fresh reviewer running `bmad-review`, given the diff and the stated intent only. Applied from the review: the placement test now reads `from pyforge import x` and import strings and finds a face at any depth; it still reads the face file alone, so an import made by a sibling portal module is not seen (warden's `tasks.py` imports its station by design). The state page was wrong on three points and is corrected: atlas's locks are a live guard in a sibling directory and are not derived; `atlas.duckdb` does not follow the data root; marshal's journals are in the project's Tier-3 store, not the loop home.
