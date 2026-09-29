---
title: 'The suite watched set matches the channel catalog and upstream follows recipe registry'
type: 'feature'
created: '2026-09-01'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - docs/dreams/bmad-suite-channel-product.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-bmad-suite-channel-product/install-matrix.md
  - _bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-15-1-github-releases-unblind-the-npm-invisible-packages.md
  - _bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-15-2-channel-and-recipe-staleness-are-ambient-findings.md
warnings: []
deferred: []
baseline_revision: ''
---

<intent-contract>

## Intent

**Problem:** Doctor's suite pass (Epic 14/CAP-4, Stories 15.1/15.2) still under-reports drift for
most SelfExplainML channel packages. Two independent bugs:

1. **Watched-set gap:** `_suite_packages` only keys starting `bmad-`, so `mybmad-dashboard` —
   pixi-pinned in `feature.bmad-ui` — is never watched despite being one of the 13 channel
   products (`install-matrix.md`). Any future channel name that does not start `bmad-` would
   repeat this blind spot.
2. **Upstream resolution gap:** npm is queried first; GitHub fallback runs only when npm returns
   `None`. Packages with **stale npm stubs** (builder 1.1.0 vs GitHub 2.2.2, CIS 0.1.9 vs 0.3.2,
   dashboard name-collision npm) look "current" even when recipe and installed versions lag GitHub.
   Only TEA (npm-authoritative) reliably fires `bmad-recipe-upstream-drift` and
   `bmad-suite-upstream-drift` today.

**Approach:** Close both gaps in `sources/bmad_method.py` without duplicating steward's full
pipeline-truth report (CAP-1):

- Derive the suite watched set from the **tracked suite manifest**
  (`recipes/bmad-suite/suite-members.yaml`, introduced by steward spec `spec-bmad-suite-metapackage`
  CAP-1) — the same 13-member catalog the channel publishes — intersected with packages that have
  a local `recipes/<name>/recipe.yaml`. Fall back to today's pixi-derived `bmad-*` set only when
  the manifest is absent (fail-open, never crash).
- Replace npm-first upstream resolution with **`_resolve_upstream_latest(package, target,
  timeout)`** that reads each member's `recipes/<package>/recipe.yaml` `extra.cfe-upstream-registry`
  and queries the authoritative registry only:
  - `github` → `_fetch_latest_github_release` (never npm for that package)
  - `pypi` → existing PyPI/npm seam (CORE `bmad-method` keeps its CAP-2 path)
  - `npm` (explicit) → `_fetch_latest_upstream_version`
  - When registry is absent or unknown → today's npm-then-GitHub fallback (backward compatible)
- When multiple registries could apply (legacy recipes without `cfe-upstream-registry`), take
  **`max()` of every successfully resolved release triple** — never a stale npm stub alone.

## Boundaries & Constraints

**Always:**
- Entirely fail-open per package; suite pass never raises; CAP-1/CAP-2 CORE paths unchanged.
- No hardcoded package→repo table — owner/repo and registry class come from each member's own
  tracked `recipe.yaml`, same discipline as Story 15.1.
- Manifest-driven watched set is the **union** of manifest members and pixi-pinned suite names
  (deduped, sorted) so a manifest-only member still gets recipe/channel drift checks even when
  not installed; installed-vs-upstream (`bmad-suite-upstream-drift`) still requires conda-meta
  presence (Story 15.2 deferred item — unchanged scope here).
- Bump `_SUITE_FETCH_TOTAL_BUDGET_SECONDS` proportionally (manifest may grow fetch count); update
  `scripts/fleet_picture.py::bmad_core_drift_findings` timeout + comment (Stories 14.1/15.2
  precedent).
- Update the three in-sync comment blocks (`bmad_method.py` module docstring, `models.py`,
  `sources/__init__.py`).

**Block If:** `recipes/bmad-suite/suite-members.yaml` does not land in the same PR train — doctor
story can ship with pixi-only fallback but AC fixtures require the manifest for the mybmad-dashboard
case.

**Never:**
- Never become steward CAP-1's pipeline-truth command — doctor stays ambient, warn-only, install-
  scoped for the suite-upstream axis.
- Never touch `recipes/**` build logic except read-only helpers (manifest read is read-only).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Builder drift (live 2026-09-01) | recipe 2.2.1, GitHub 2.2.2, npm 1.1.0, registry github | `bmad-recipe-upstream-drift` WARN; installed 2.2.1 → `bmad-suite-upstream-drift` WARN | npm ignored |
| CIS drift | recipe 0.3.1, GitHub 0.3.2, npm 0.1.9, registry github | both WARNs fire | npm ignored |
| TEA | registry github but npm also current | same findings as today (1.23.2 vs 1.23.4) | unchanged |
| mybmad-dashboard | manifest member, pixi-pinned, recipe present | enters watched set; drift checks run when installed | prefix no longer gates |
| Manifest missing | no `suite-members.yaml` | fall back to pixi `bmad-*` set only (today's behavior) | fail-open |
| Manifest lists unknown name | no `recipes/<name>/` | skip that member silently | fail-open |
| Budget exhausted mid-loop | slow network | remaining packages skipped | fail-open |

## Acceptance Criteria

- [ ] `_suite_packages` (or successor) includes all 13 names from `install-matrix.md` when the
  manifest is present, including `mybmad-dashboard`.
- [ ] Live `pixi run -e pyforge-doctor pyforge doctor check --bmad-core` WARNs for builder and CIS
  recipe-upstream drift (not only TEA) when network available.
- [ ] Unit tests stub registry seams — no live network in CI — covering github-primary, npm-primary,
  npm-stale+github-canonical, and manifest fallback paths.
- [ ] `test_sources_bmad_method.py` count increases; meta-test fleet-picture pass-through unchanged.

## Code Map

- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/bmad_method.py` — manifest reader,
  `_upstream_registry(target, package)`, `_resolve_upstream_latest(...)`, rewire `_gather_suite_findings`
  and CORE-side Story 15.2 call sites to use it.
- `src/shared/packages/pyforge-doctor/tests/unit/test_sources_bmad_method.py` — new fixtures.
- `scripts/fleet_picture.py` — timeout bump if inner budget grows.
- `recipes/bmad-suite/suite-members.yaml` — **read-only consumer**; authored by steward metapackage spec.

## Design Notes

**Why manifest instead of widening `_SUITE_PREFIX`:** a prefix heuristic (`bmad-` + `mybmad-`) still
omits the next oddly named channel package. The manifest is the same artifact the metapackage recipe
uses for run requirements — one catalog, two consumers (doctor + conda metapackage).

**Closes deferred work:** Story 15.1's npm-stale blind spot (builder/CIS/dashboard) was out of scope
for "npm miss → GitHub"; this story is the deliberate follow-on authorized by operator review
2026-09-01.

**Relationship to steward:** `steward suite pipeline-truth` remains the five-stage operator report;
doctor relays ambient WARNs for installed/pinned members only.

</intent-contract>

## Auto Run Result

**Status:** done — reconstructed 2026-09-20 from git during the fleet consistency pass before the foundry cutover; no run record survived in this tracked spec.
**Summary:** landed on `main` as `770672a156` (2026-09-01, "doctor: Story 19.1 manifest-driven suite drift + steward Epic 39 ledger"). Ledger row `19-1-the-suite-watched-set-matches-the-channel-catalog-and-upstream-follows-recipe-registry: done`.
**Verification:** the station's `verify_commands` ran in the landing session; the durable record here is git only — see the landing commit(s) above.
**Files changed:** `_bmad-output/projects/pyforge-doctor/planning-artifacts/epics.md`, `_bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-19-1-the-suite-watched-set-matches-the-channel-catalog-and-upstream-follows-recipe-registry.md`, `_bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-19-1-the-suite-watched-set-matches-the-channel-catalog-and-upstream-follows-recipe-registry/.memlog.md`, `_bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-pyforge-doctor/.memlog.md`, `_bmad-output/projects/pyforge-doctor/planning-artifacts/sprint-status-ledger.yaml`, `_bmad-output/projects/pyforge-marshal/planning-artifacts/deferred-work-ledger.md`, `_bmad-output/projects/pyforge-steward/planning-artifacts/epics.md`, `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-bmad-suite-metapackage/.memlog.md`, `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-bmad-suite-metapackage/SPEC.md`, `_bmad-output/projects/pyforge-steward/planning-artifacts/sprint-status-ledger.yaml`, `scripts/.spec-surface-baseline.json`, `scripts/fleet_picture.py` (+4 more)
**Residual risks:** none recorded — no run record survived to carry them.
**Follow-up review recommendation:** false

## Status reconcile 2026-09-20

- frontmatter `status` `shipped` → `done` (ledger row `19-1-the-suite-watched-set-matches-the-channel-catalog-and-upstream-follows-recipe-registry: done`).
- `## Auto Run Result` reconstructed from git (none survived).
