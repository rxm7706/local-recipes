---
title: '126.4: Marshal reads a zombie without /proc, and its remedies name commands that exist'
type: 'fix'
created: '2026-11-18'
status: 'ready-for-dev'
story: 126-4-marshal-reads-a-zombie-without-proc-and-its-remedies-name-commands-that-exist
spec: spec-pyforge-steward
difficulty: 'easy'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
flag-exempt: detector-or-gate   # tests, a gate's own module and the scripts a gate runs; a gated gate is a silent green (roster list)
surface:
  - 'src/shared/packages/pyforge-marshal/**'
  - 'src/shared/packages/pyforge-herald/src/pyforge/herald/cli.py'
  - 'docs/reference/marshal-seed-findings.md'
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/SPEC.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/deferred-work-ledger.md
  - docs/dreams/pyforge-steward.md
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** `dispatch_verify._is_zombie` reads `/proc` only, so on macOS an exited, unreaped session leader reads alive; `REMEDIES` names `marshal seed adopt --reinstate` and `marshal doctor check`, which the CLI does not have; herald's scheduler docstring describes `--repo-root` as the package checkout.

**Approach:** The zombie check reads the process table where there is no `/proc` (proved on a real zombie), the two remedy strings name what an operator can run, and the docstring says what the callers do.

Ledger key: `126-4-marshal-reads-a-zombie-without-proc-and-its-remedies-name-commands-that-exist`.

### Living CAP citations

- spec-pyforge-steward CAP-175 and CAP-5 (realized, no text change); FR-49 ← CAP-175; no AD moves.

## Boundaries & Constraints

**Always:**
- Read every verdict from its exit code, never through a pipe.
- Close the deferred-work row this story names with the commit that resolves it.

**Never:**
- Never weaken an assertion that holds on Linux, hand-edit a compiled skill, a `SPEC.md`, a generated page or `sprint-status-ledger.yaml`.

## Acceptance Criteria

**Given** `dispatch_verify._is_zombie` reads `/proc` only, so on macOS an exited, unreaped session leader reads alive; `REMEDIES` names `marshal seed adopt --reinstate` and `marshal doctor check`, which the CLI does not have; herald's scheduler docstring describes `--repo-root` as the package checkout
**When** the zombie check reads the process table where there is no `/proc` (proved on a real zombie), the two remedy strings name what an operator can run, and the docstring says what the callers do
**Then** marshal's two lanes exit 0 on macOS and Linux; the remedy reference page and its sync test agree; no test is skipped by platform name
**And** `DW-steward-125-2-1` and marshal's and herald's items of `DW-doctor-59-4-1` reads resolved in its ledger with the commit that closed it

- **AC1 — The story's own check passes.** Expected: exit 0.

  ```bash
  pixi run --frozen -e pyforge-marshal pyforge-marshal-test && pixi run --frozen -e pyforge-marshal pyforge-marshal-live-test
  ```

</intent-contract>

## Binding

- Capabilities: spec-pyforge-steward CAP-175 and CAP-5 (realized, no text change); FR-49 ← CAP-175; no AD moves.
- Dream: `docs/dreams/pyforge-steward.md` § *Realization log*, the 2026-11-18 entry; operator ruling of 2026-11-18: "THIS MACHINE WILL BE A FIRST CLASS DEVELOPMENT HOST -- JUST FIX ALL THE DEFERRED ROW ITEMS NOW.. AND NOT LEAVE ANYTHING FOR LATER", "JUST USE ctranslate2 and remove the other one", "we should continue to support manticore and antigravity", "we still want to do everything in this session as one PR".
- Epic: Epic 126, minted with this story.
- Ledger key: `126-4-marshal-reads-a-zombie-without-proc-and-its-remedies-name-commands-that-exist` (`backlog`).
- Surface: `marshal-policy.toml` `[epic_surfaces]."126"`.

## Verification

**Commands:** the Acceptance Criteria above, each read from its exit code.

## Spec Change Log

- 2026-11-18: minted from the station Dream's 2026-11-18 entry and the operator's rulings of the same date.
