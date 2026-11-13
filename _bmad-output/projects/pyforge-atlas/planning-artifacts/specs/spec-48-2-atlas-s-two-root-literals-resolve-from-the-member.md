---
title: "48.2: Atlas's two root literals resolve from the member"
type: 'fix'
created: '2026-11-10'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
difficulty: easy
story: '48.2'
spec: pyforge-atlas
surface:
  - src/shared/packages/pyforge-atlas/src/pyforge/atlas/query_plane_boot.py
  - src/shared/packages/pyforge-atlas/src/pyforge/atlas/dashboard/identity_gist.py
  - src/shared/packages/pyforge-atlas/tests/unit/test_query_plane_boot.py
  - src/shared/packages/pyforge-atlas/tests/unit/test_dashboard_identity_gist.py
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-48-2-atlas-s-two-root-literals-resolve-from-the-member.md
context:
  - src/shared/packages/pyforge-atlas/src/pyforge/atlas/query_plane_boot.py
  - src/shared/packages/pyforge-atlas/src/pyforge/atlas/dashboard/identity_gist.py
  - src/shared/packages/pyforge-atlas/src/pyforge/atlas/dashboard/data.py
  - src/shared/packages/pyforge-atlas/src/pyforge/atlas/admission.py
  - src/shared/packages/pyforge-atlas/tests/unit/test_query_plane_boot.py
  - src/shared/packages/pyforge-atlas/tests/unit/test_dashboard_identity_gist.py
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/research/cutover-readiness-audit-2026-11-10.md
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** Code is wrong: two hard-coded roots the audit found. `query_plane_boot.DEFAULT_PLANE_PATH` is the working-directory-relative literal `src/shared/packages/pyforge-atlas/data/plane`, and `dashboard/identity_gist._pyforge_atlas_root` falls back to the same literal under a guessed repository root. Each is wrong the moment the command runs from another directory or the package sits in another tree.

**Approach:**
- **The plane default.** `query_plane_boot.DEFAULT_PLANE_PATH` becomes `<member>/data/plane/atlas.duckdb`, absolute and the same from any working directory. The member is found the way `dashboard/data.default_data_root` already finds it: `Path(__file__).resolve().parents[3]` when that directory holds `conf/base/catalog.yml`, else the working directory (an installed layout has no member, and `parents[3]` would land in site-packages; `admission.py` records the same trap). `--path` still overrides it and `PYFORGE_ATLAS_DATA_ROOT` still does not move it (stated in CAP-69 by Story 46.2 and in `contract.md` by Story 47.1). For the pixi task, which runs at the repository root, the resolved file is the one it used before.
- **The gist fallback.** `identity_gist._pyforge_atlas_root`'s fallback returns the same member root instead of `<repo>/src/shared/packages/pyforge-atlas`; `test_pyforge_atlas_root_falls_back_to_repo_root` is rewritten to match.
- **New cases** in the two existing test modules: the plane default from two working directories, the installed-layout branch (no `catalog.yml` beside the package), and the fallback. They read nothing outside the package and carry no marker.
- **Not touched** (withdrawn from the first plan on the reviewer's evidence): `tools/bootstrap.py` (its `or "data"` already treats an empty value as unset and mirrors Kedro's resolver) and `observability.PRODUCER` (any corrected tail is a new A-layout literal; deferred row DW-atlas-46-1-7); `tools/normalize_viz_build.py`'s `_ATLAS_PKG_RELATIVE` and `dashboard/factory_status.py` read A's tree by design. The story appends nothing to the memlog (Story 48.4 does).

Ledger key: `48-2-atlas-s-two-root-literals-resolve-from-the-member`.
Type / Effort / Deps: fix / S / S-48.1.

### Living CAP citations

- Fix under `spec-pyforge-atlas` CAP-48 and CAP-69; no CAP, no FR

## Acceptance Criteria

Each command runs from the worktree root; read every verdict from its exit code, never through a pipe.

- **AC1 — No path in the package source is built from the A-tree literal.** Expected: exit 0 (today it matches query_plane_boot.py:79 and dashboard/identity_gist.py:204).

  ```bash
  ! git grep -qE 'Path\("src/shared/packages|/ "src/shared/packages' -- src/shared/packages/pyforge-atlas/src
  ```

- **AC2 — The suites of the two touched modules pass, with the new cases.** Expected: exit 0.

  ```bash
  pixi run --frozen -e pyforge-atlas pytest src/shared/packages/pyforge-atlas/tests/unit/test_query_plane_boot.py src/shared/packages/pyforge-atlas/tests/unit/test_dashboard_identity_gist.py src/shared/packages/pyforge-atlas/tests/unit/query_plane -q
  ```

- **AC3 — The plane default is absolute and does not depend on the working directory.** Expected: exit 0 (today the path is relative, so the same command exits 1).

  ```bash
  cd /tmp && pixi run --manifest-path "$OLDPWD/pixi.toml" --frozen -e pyforge-atlas python -c 'import sys;from pyforge.atlas.query_plane_boot import DEFAULT_PLANE_PATH as p;sys.exit(0 if p.is_absolute() and p.parts[-3:]==('"'"'data'"'"','"'"'plane'"'"','"'"'atlas.duckdb'"'"') and '"'"'pyforge-atlas'"'"' in p.parts else 1)'
  ```

- **AC4 — The touched modules meet the unit coverage floor.** Expected: exit 0.

  ```bash
  pixi run --frozen -e pyforge-atlas pyforge-atlas-coverage-gate
  ```

- **AC5 — Lint and types hold.** Expected: exit 0.

  ```bash
  pixi run -e pyforge-guild lint-types
  ```

## Boundaries & Constraints

**Always:**
- Resolve the member from the package's own file, with the installed-layout fallback.
- Keep a run from the repository root on the same file it used before.

**Never:**
- Never add a flag or a new behaviour (a fix restores intended behaviour).
- Never let `PYFORGE_ATLAS_DATA_ROOT` move the plane default.

</intent-contract>

## Binding

- Parent: Fix under `spec-pyforge-atlas` CAP-48 and CAP-69; no CAP, no FR.
- Dream: `docs/dreams/pyforge-atlas.md` § *Realization log*, the 2026-11-10 (cutover readiness) entry; the operator's rulings of 2026-11-10 in `docs/dreams/pyforge-unifying-strategy.md` § Realization log (the entry of that date and its two addenda).
- Epic: Epic 48, minted 2026-11-10 with this story.
- Ledger key: `48-2-atlas-s-two-root-literals-resolve-from-the-member`.
- Deps: S-48.1.
- Cross-station deps: none.
- Flag: none (`type: fix`: restores intended behaviour; spec-feature-flag-governance Q1).
- Surface: `marshal-policy.toml` `[epic_surfaces]."48"`, narrowed by this spec's `surface:`.
- Minted 2026-11-10 in the atlas mint of the one cutover-readiness PR (branch `cutover-readiness-2026-11-10`); built in the same PR.

## Verification

**Commands:**
- `pixi run -e pyforge-atlas kedro-test` — expected: exit 0.

**Run before the push:** the acceptance commands above, each read from its exit code.

## Auto Run Result

Status: backlog (minted 2026-11-10).

## Spec Change Log

- 2026-11-10: minted from the station Dream's entry of 2026-11-10 (cutover readiness) under the operator's rulings of 2026-11-10 ("Accept all", "Retire both", "Accept all, run mint"). Acceptance adjusted by the rulings: no adjustment.

## Review Triage Log

- (none yet)
