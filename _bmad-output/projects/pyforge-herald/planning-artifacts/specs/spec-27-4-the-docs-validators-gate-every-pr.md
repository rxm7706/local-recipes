---
title: '27.4: The docs validators gate every PR'
type: 'feature'
created: '2026-09-27'
status: 'done'
baseline_revision: 'f1cc68bab7fef224a9d5a78994db73e6b7af0895'
followup_review_recommended: false
difficulty: 'medium'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-pyforge-herald/SPEC.md
  - _bmad-output/projects/pyforge-herald/planning-artifacts/research/docs-site-bmad-method-pattern-2026-09-20.md
  - .github/workflows/docsite-check.yml
  - docs/_STYLE_GUIDE.md
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** BMAD-METHOD gates its docs with `validate-doc-links.js` and `validate-sidebar-order.js`. Story 27.1 vendors both, but no lane runs them. Run unchanged over this repo's `docs/` on 2026-09-27, `validate-doc-links.js` scanned 268 files and reported 16 findings in 10 files, exiting 1:

- 6 dead links: a wrong relative path, a `file:///` absolute path, `restore.md`, `DR.md` twice, and a path outside the repo.
- 5 directory links into index pages.
- 5 links to repo files outside `docs/`: `AGENTS.md`, two `.claude/skills/conda-forge-expert` guides, a `scripts/` file and a `conf/` file.

`validate-sidebar-order.js` exited 0. As things stand, a dead link can merge with every gate green.

**Approach:** Wire both validators as pixi tasks in the `site` feature. The sidebar task also runs 27.3's `sidebar_from_map.py --check`. Run them in `docsite-check.yml` on every PR that touches `docs/**` or `docs-site/**`, and add a `pr-preflight` leg. Fix the 16 findings in their pages, never in the validators (CAP-52 D5, D6).

## Boundaries & Constraints

**Always:**
- The vendored validators stay byte-identical to the recorded upstream commit; their sha256 still matches `docs-site/README.md`.
- Each finding is fixed in its page: a dead link is repaired to its real target or removed; a directory link points at its index page; a repo file outside `docs/` is linked by `https://github.com/rxm7706/local-recipes/blob/main/<path>`.
- Doctor's `docs-map-hygiene` and `docs-currency` stay the repo-side twin, and the page fixes add no finding to either.
- `pixi.toml` changed: run `pixi run -e pyforge-guild pyforge-station-tests` first; regenerate `environment.yaml` (expected byte-identical).
- Before landing, reconcile each co-governor. The page edits touch Specs that govern `docs/**` and `docs/dreams/README.md`, so add a memlog entry on every Spec that `spec-surface-check` names, `git add`, run one scoped stamp per named Spec, re-check, and read the exit code.
- The PR carries the `maintenance` label.

**Never:**
- Do not edit, wrap or fork `validate-doc-links.js` or `validate-sidebar-order.js` to make them pass.
- Do not move or rename a page. Change only the named links.
- Do not register the validators in `scripts/detectors.py`: the `detectors` env has no node (D5).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| story's tree | the 16 findings fixed | `pixi run -e site docs-site-validate` exits 0 | none |
| planted dead link | `[x](nope.md)` in a quadrant page | `docs-site-validate-links` exits 1 naming the page | fail loud |
| planted duplicate order | two pages with `sidebar.order: 1` in one directory | `docs-site-validate-sidebar` exits 1 | fail loud |
| map drift | a quadrant page missing from `docs/map.yaml` | `docs-site-validate-sidebar` exits 1 (27.3's `--check`) | fail loud |
| PR lane | a PR touching `docs/**` | `docsite-check.yml` runs `docs-site-validate` | red on exit 1 |
| local | `pixi run -e pyforge-guild pr-preflight` | runs the `docs-site-validate` leg in `site` | exit code read, never through a pipe |

</intent-contract>

## Binding

Parent Spec capability: `spec-pyforge-herald CAP-52` (FR-8.4; decisions D5, D6 in the Spec's `.memlog.md`).
Architecture: AD-21.
Ledger key: `27-4-the-docs-validators-gate-every-pr`.
Ledger status at mint: `backlog`.
Deps: S-27.2 (the reshaped `docsite-check.yml`, already path-filtered on `docs/**` and `docs-site/**`, that this extends), S-27.3 (the map check the sidebar task runs). Amended 2026-09-27 (D8): no Epic 27 story runs `pages-check` in `pr-preflight` except 27.5; this story's own leg, `docs-site-validate`, is node-only.
Minted 2026-09-27 from `epics.md` so `marshal factory dispatch` can resolve this spec.

## Epic excerpt

**Type:** feature • **Effort:** M • **Deps:** S-27.2, S-27.3 • **FR/AD:** spec-pyforge-herald CAP-52 (FR-8.4; D5, D6); AD-21

**Surface:**
- `pixi.toml`:
  - `[feature.site.tasks]` gains `docs-site-validate-links` (`node docs-site/scripts/validate-doc-links.js`), `docs-site-validate-sidebar` (`node docs-site/scripts/validate-sidebar-order.js`, then `python docs-site/scripts/sidebar_from_map.py --check`) and `docs-site-validate` (both)
  - `pr-preflight` gains `{ task = "docs-site-validate", environment = "site" }`, with its description saying why
- `.github/workflows/docsite-check.yml`: a step runs `pixi run --frozen -e site docs-site-validate`. The `docs/**` and `docs-site/**` path filters are already there from 27.2 (D8).
- `pr-preflight`'s `docs-site-validate` leg needs only node (no npm install, no build), so it runs unconditionally until steward Story 71.2 selects it by `docsite-check.yml`'s paths, like every other lane.
- The 16 link findings the vendored `validate-doc-links.js` reported on 2026-09-27, each fixed in its page, never by editing the validator:
  - `docs/dreams/README.md` (`../../AGENTS.md`, `../specs/`)
  - `docs/dreams/archive/pyforge-unifying-strategy-2026-08-23-topology.md` (`marshal-token-economy.md`)
  - `docs/how-to/antigravity-developer-startup.md` (a `file:///` path)
  - `docs/how-to/disaster-recovery.md` (`restore.md`)
  - `docs/how-to/feedstock-platform-expansion.md` (two `.claude/skills/…` links)
  - `docs/how-to/ocp-cluster-bringup.md` (`../../../ingest/…`)
  - `docs/how-to/restore-operations.md` (`DR.md` twice)
  - `docs/reference/README.md` (three directory links)
  - `docs/reference/conda-forge-packaging-inventory-operations_replay.md` (`scripts/` and `conf/` links)
  - `docs/tutorials/getting-started.md` (`../how-to/`)
  - a dead link is repaired or removed, a directory link points at its index page, and a repo file outside `docs/` is linked by its `https://github.com/rxm7706/local-recipes/blob/main/<path>` URL
- `src/shared/packages/pyforge-herald/tests/meta/test_docs_site_validators.py` (new), asserting:
  - the three tasks are registered
  - `docsite-check.yml` carries the step
  - `pr-preflight` carries the leg
  - the vendored validators' sha256 still equals what `docs-site/README.md` records

**Given** the vendored `validate-doc-links.js` exits 1 over `docs/` (268 files scanned, 16 findings in 10 files, measured 2026-09-27) and no lane runs it
**When** the findings are fixed in their pages and the validators are wired as pixi tasks, a `docsite-check.yml` step and a `pr-preflight` leg
**Then** `pixi run -e site docs-site-validate` exits 0 on the story's tree; a planted dead link in any quadrant page makes it exit 1 and name the page; two pages with the same `sidebar.order` in one directory make `docs-site-validate-sidebar` exit 1
**And** `docsite-check.yml` runs the validators on a PR that touches `docs/**`; `pr-preflight` carries the leg; the vendored validators are byte-identical to the recorded upstream commit; `test_docs_site_validators.py` passes in `pyforge-herald-test`; the fixed pages keep `docs-currency-check` and `docs-map-hygiene-check` free of new findings

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-herald pyforge-herald-test` — expected: pass (the station's `verify_commands`; `tests/meta/test_docs_site_validators.py` runs inside it).

**Manual checks:**
- `pixi run -e site docs-site-validate` — expected: exit 0 on the story's tree.
- Plant `[x](nope.md)` in one quadrant page and re-run `pixi run -e site docs-site-validate-links` — expected: exit 1 naming that page; then revert the plant.
- `pixi run -e pyforge-guild docs-currency-check` and `pixi run -e pyforge-guild docs-map-hygiene-check` — expected: no new finding.
- `pixi run -e pyforge-guild pr-preflight` — expected: exit 0 (read the exit code, never through a pipe).
