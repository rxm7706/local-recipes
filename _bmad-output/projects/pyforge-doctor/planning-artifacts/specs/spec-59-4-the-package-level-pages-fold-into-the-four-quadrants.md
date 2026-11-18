---
title: '59.4: The package-level pages fold into the four quadrants'
type: 'chore'
created: '2026-11-17'
status: 'ready-for-dev'
story: 59-4-the-package-level-pages-fold-into-the-four-quadrants
spec: spec-pyforge-doctor
difficulty: 'easy'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
flag-exempt: docs-only   # documentation pages only; no runtime path (roster list)
surface:
  - 'src/shared/packages/pyforge-doctor/docs/**'
  - 'src/shared/packages/pyforge-herald/docs/**'
  - 'src/shared/packages/pyforge-marshal/docs/**'
  - 'src/shared/packages/pyforge-scribe/docs/**'
  - 'src/shared/packages/pyforge-steward/docs/**'
  - 'src/shared/packages/pyforge-*/README.md'
  - 'docs/how-to/**'
  - 'docs/reference/**'
  - 'docs/explanation/**'
  - 'docs/map.yaml'
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

**Problem:** Thirteen operator pages live beside the code, where the registry, the site and the currency detector cannot see them.

**Approach:** Fold by content, not by file: verify, place by quadrant, stamp, register, remove the original, repoint inbound references outside the chain's historical records.

Ledger key: `59-4-the-package-level-pages-fold-into-the-four-quadrants`.
Type / Effort / Deps: chore / M / —.

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

**Given** thirteen pages sit under five packages' `docs/` directories, outside `docs/map.yaml` (herald's `web-ux-guide.md` last edited 2026-08-13, steward's `keys-runbook.md` 2026-09-18), and the operator ruled 2026-11-17 that they fold into `docs/`
**When** each page is verified, written as a new stamped page in its quadrant, and its original removed, with every inbound reference in package files and workflows repointed
**Then** no `.md` remains under `src/shared/packages/pyforge-*/docs/` (test fixtures are not documentation and stay); each new page is a `docs/map.yaml` row owned by its station; a duplicate of an existing page folds only what is unique
**And** a reference in a Spec, a memlog, an epic or a Dream is a historical record and is left as written; each station suite whose test named a moved page exits 0

- **AC1 — No package-level documentation page remains.** Expected: prints 0.

  ```bash
  git ls-files 'src/shared/packages/pyforge-*/docs/*.md' | wc -l
  ```

- **AC2 — The registry and the map agree.** Expected: exit 0 each.

  ```bash
  pixi run --frozen -e pyforge-guild docs-map-hygiene-check && pixi run --frozen -e pyforge-guild docs-shelf-occupancy-check
  ```

- **AC3 — The flag gate passes this story's spec.** Expected: exit 0; the printed JSON object has "verdict": "pass".

  ```bash
  pixi run --frozen -e pyforge-guild flag-gate-check -- --spec "$(ls _bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-59-4-*.md)"
  ```

</intent-contract>

## Binding

- Capabilities: spec-pyforge-doctor CAP-84 (amended 2026-11-17); FR-17 ← CAP-84.
- Dream: `docs/dreams/pyforge-doctor.md` § *Realization log*, the 2026-11-17 (the full documentation refresh) entry; operator ruling of 2026-11-17.
- Epic: Epic 59, minted with this story.
- Ledger key: `59-4-the-package-level-pages-fold-into-the-four-quadrants` (`backlog`).
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
