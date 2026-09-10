---
title: Atlas Kedro CLI introspection (preparatory)
type: chore
created: '2026-08-25'
status: superseded
superseded_by: spec-25-3-atlas-s-mcp-tools-pass-the-cli-tool-parity-gate
context: []
warnings: []
deferred: []
updated: '2026-09-10'
---

<intent-contract>

## Intent

**Problem:** Atlas's console script is Kedro `find_run_command` (Click), not a static argparse/Typer parser tree. Story 22.1 cannot AST-introspect its verbs without copying Kedro/atlas routing into `pyforge-core`.

**Approach:** Keep `pyforge atlas …` → `pyforge-atlas …` dispatch (22.1). A later story must generate the CAP-5 parity matrix for atlas verbs from Kedro's own command surface, still without reimplementing pipelines in core.

## Boundaries & Constraints

**Always:** Named in `PREPARATORY_UNINTROSPECTABLE["atlas"]`. Dispatch still forwards.

**Never:** Silent skip; copying Kedro click groups into pyforge-core.

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-atlas/src/pyforge/atlas/__main__.py` — Kedro intercept + `find_run_command`
- `src/shared/packages/pyforge-core/src/pyforge/core/dispatch.py` — `PREPARATORY_UNINTROSPECTABLE`

## Tasks & Acceptance

**Execution:** not this story (22.1 names it only).

**Acceptance Criteria:**
- Given atlas, when 22.1's matrix runs, then this spec id is required instead of an empty silent skip.
- Given a later implementation, when Kedro verbs are listed, then each is reachable via `pyforge atlas …` without atlas logic in core.

## Spec Change Log

## Review Triage Log

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — expected: pass (this station's own verify suite; backfilled generically, no per-story claim).
