---
title: '59.8: The registry, the baselines and the chain close once, after every unit''s last edit'
type: 'chore'
created: '2026-11-17'
status: 'in-review'
story: 59-8-the-registry-the-baselines-and-the-chain-close-once-after-every-unit-s-last-edit
spec: spec-pyforge-doctor
difficulty: 'heavy'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
flag-exempt: detector-or-gate   # a check that judges; a gated gate is a silent green (spec-feature-flag-governance Q1; roster list)
surface:
  - 'docs/map.yaml'
  - 'docs/MAP.md'
  - 'docs/how-to/README.md'
  - 'docs/reference/README.md'
  - 'docs/explanation/README.md'
  - 'scripts/.spec-surface-baseline.json'
  - '_bmad-output/projects/pyforge-*/planning-artifacts/specs/spec-pyforge-*/.memlog.md'
  - '_bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-pyforge-doctor/SPEC.md'
  - '_bmad-output/projects/pyforge-doctor/planning-artifacts/sprint-status-ledger.yaml'
  - '_bmad-output/projects/pyforge-doctor/planning-artifacts/deferred-work-ledger.md'
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

**Problem:** Stamps and renders are valid only for the tree they read; on a branch with seven parallel writers they must run once, last.

**Approach:** Register, render, regenerate, reconcile, stamp, close the chain, replay the bar. Each file is written by its own tool.

Ledger key: `59-8-the-registry-the-baselines-and-the-chain-close-once-after-every-unit-s-last-edit`.
Type / Effort / Deps: chore / M / S-59.1, S-59.2, S-59.3, S-59.4, S-59.5, S-59.6, S-59.7.

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

**Given** seven stories edit the shelf in parallel on one branch, a generated page's stamp and a spec-surface stamp are valid only until the next edit, and new and folded pages are not yet rows of `docs/map.yaml`
**When** the story runs last: new and moved pages are registered and indexed, `docs-map-render` renders `MAP.md`, the six generators and the estate catalog run from the committed tree, each governing Spec's memlog names the paths that moved and is stamped scoped, CAP-84 reads shipped through `bmad-spec`, and the skill-audit findings are deferred-work rows
**Then** `docs-currency-check`, `docs-map-hygiene-check`, `spec-surface-check`, `chain-completeness-check` and `story-status-check` exit 0; `pages-build`, `pages-check` and `docs-site-validate` exit 0; a full-scope `pr-preflight` exits 0 on the final head, run alone on the machine
**And** no stamp is bare and no Spec this change did not touch is stamped; this story's own key is the last ledger write

- **AC1 — The documentation detectors read green.** Expected: exit 0 each.

  ```bash
  pixi run --frozen -e pyforge-guild docs-currency-check && pixi run --frozen -e pyforge-guild docs-map-hygiene-check && pixi run --frozen -e pyforge-guild spec-surface-check
  ```

- **AC2 — The site builds and its links resolve.** Expected: exit 0 each.

  ```bash
  pixi run --frozen -e site pages-build && pixi run --frozen -e site pages-check && pixi run --frozen -e site docs-site-validate
  ```

- **AC3 — The PR bar passes on the final head.** Expected: exit 0.

  ```bash
  PYFORGE_PREFLIGHT_SCOPE=full pixi run --frozen -e pyforge-guild pr-preflight
  ```

- **AC4 — The flag gate passes this story's spec.** Expected: exit 0; the printed JSON object has "verdict": "pass".

  ```bash
  pixi run --frozen -e pyforge-guild flag-gate-check -- --spec "$(ls _bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-59-8-*.md)"
  ```

</intent-contract>

## Binding

- Capabilities: spec-pyforge-doctor CAP-84 (amended 2026-11-17); FR-17 ← CAP-84.
- Dream: `docs/dreams/pyforge-doctor.md` § *Realization log*, the 2026-11-17 (the full documentation refresh) entry; operator ruling of 2026-11-17.
- Epic: Epic 59, minted with this story.
- Ledger key: `59-8-the-registry-the-baselines-and-the-chain-close-once-after-every-unit-s-last-edit` (`backlog`).
- Deps: S-59.1, S-59.2, S-59.3, S-59.4, S-59.5, S-59.6, S-59.7.
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
