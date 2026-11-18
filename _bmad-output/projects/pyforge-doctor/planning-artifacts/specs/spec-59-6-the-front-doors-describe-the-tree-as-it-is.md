---
title: '59.6: The front doors describe the tree as it is'
type: 'chore'
created: '2026-11-17'
status: 'done'
story: 59-6-the-front-doors-describe-the-tree-as-it-is
spec: spec-pyforge-doctor
difficulty: 'easy'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
flag-exempt: docs-only   # documentation pages only; no runtime path (roster list)
surface:
  - 'README.md'
  - 'src/platform/README.md'
  - 'src/shared/packages/pyforge-*/README.md'
  - 'docs/index.md'
  - 'docs/MAP.md'
  - 'docs/tutorials/README.md'
  - 'docs/how-to/README.md'
  - 'docs/reference/README.md'
  - 'docs/explanation/README.md'
  - 'docs/dashboard/README.md'
  - 'docs/intake/README.md'
  - 'docs-site/README.md'
context:
  - _bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-pyforge-doctor/SPEC.md
  - _bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-pyforge-doctor/.memlog.md
  - _bmad-output/projects/pyforge-doctor/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-doctor/planning-artifacts/prds/prd-pyforge-doctor-2026-07-25/prd.md
  - _bmad-output/projects/pyforge-doctor/planning-artifacts/architecture/architecture-pyforge-doctor-2026-07-25/ARCHITECTURE-SPINE.md
  - docs/dreams/pyforge-doctor.md
  - docs/MAP.md
  - docs/_STYLE_GUIDE.md
  - docs/governance/spec-one-chain-per-station/CHAIN-STANDARD.md
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** The front doors age fastest and are checked least.

**Approach:** Claim-by-claim check, surgical edits, pointers over restatement. Skills are audited, not edited.

Ledger key: `59-6-the-front-doors-describe-the-tree-as-it-is`.
Type / Effort / Deps: chore / S / —.

### Living CAP citations

- **`spec-pyforge-doctor` CAP-84** — documentation currency; amended 2026-11-17: every authored page is stamped or declares its detector, the currency classes fail, the workflow inventory is generated, package-level pages fold into the quadrants.

## Boundaries & Constraints

**Always:**
- Check every command, path, flag, count and link in a page against the tree before its stamp moves; keep `sources:` narrow (the file a page restates, not a hub file).
- Read every verdict from its exit code, never through a pipe.

**Never:**
- Never hand-edit a generated page, the generated section of `docs/MAP.md`, a compiled station skill, a `SPEC.md` or `sprint-status-ledger.yaml`.
- Never run a bare `spec_surface_check.py --write-baseline`; Story 59.8 stamps each governing Spec scoped, once, last.
- Never move a station's code, CLI or capability to make a page true: fix the page.

## Acceptance Criteria

**Given** the root `README.md` was last edited 2026-10-11 and `src/platform/README.md` 2026-10-01, and the `docs/MAP.md` preamble sizes the shelf at "14 markdown files"
**When** each front door is checked claim by claim against the tree and corrected, pointing into `docs/` instead of restating it
**Then** `general-docs-consistency` stays OK; every link and path in the front doors resolves; the `MAP.md` preamble describes the shelf as it is and the generated section is untouched by hand
**And** the eight station skills are audited against their CLIs and each mismatch is a deferred-work row for the SKF refresh, since a compiled skill is never hand-edited

- **AC1 — The identity detector and the instruction-surface checks stay green.** Expected: exit 0 each.

  ```bash
  pixi run --frozen -e pyforge-guild general-docs-consistency-check && pixi run --frozen -e pyforge-guild governance-currency
  ```

- **AC2 — The MAP preamble no longer carries the stale count.** Expected: prints 0.

  ```bash
  grep -c '14 markdown files' docs/MAP.md
  ```

- **AC3 — The flag gate passes this story's spec.** Expected: exit 0; the printed JSON object has "verdict": "pass".

  ```bash
  pixi run --frozen -e pyforge-guild flag-gate-check -- --spec "$(ls _bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-59-6-*.md)"
  ```

</intent-contract>

## Binding

- Capabilities: spec-pyforge-doctor CAP-84 (amended 2026-11-17); FR-17 ← CAP-84.
- Dream: `docs/dreams/pyforge-doctor.md` § *Realization log*, the 2026-11-17 (the full documentation refresh) entry; operator ruling of 2026-11-17.
- Epic: Epic 59, minted with this story.
- Ledger key: `59-6-the-front-doors-describe-the-tree-as-it-is` (`backlog`).
- Deps: —.
- Surface: `marshal-policy.toml` `[epic_surfaces]."59"`.
- Minted 2026-11-17 in the chain commit of the integration branch `docs-full-refresh-2026-11-17`, the first commit of the branch.

## Notes

- One integration branch and one PR carry Stories 59.1 to 59.8 (operator ruling 2026-11-17). Stories 59.1 to 59.6 run in parallel on disjoint files; 59.7 lands on a tree its source already reads green; 59.8 runs last.
- Measured at main `33c96fd0bb`: 57 authored pages, 19 stamped, 17 of those stale, 38 unstamped; 6 generated; 7 pointers.

## Verification

**Commands:** the Acceptance Criteria above, each read from its exit code (never through a pipe).

**Run before the push:**
- `pixi run --frozen -e pyforge-guild chain-completeness-check`, `story-status-check`, `flag-gate-check` — expected: exit 0 each.

## Spec Change Log

- 2026-11-17: minted from the station Dream's 2026-11-17 entry (the full documentation refresh) and the operator's ruling of 2026-11-17.
