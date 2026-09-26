---
title: '67.1: The SBOM composes the laptop bill of materials on three platforms, with PostgreSQL 17 held'
type: 'feature'
created: '2026-09-25'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - docs/dreams/pyforge-unifying-strategy.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-python-foundry-cutover/SPEC.md
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** `pyforge-foundry-full` is closure-only; the laptop still needs the 10 GB `local-recipes` env; `scribe-pg`, `pyforge-scribe`, `mcp-host` and `platform-ci-test` resolve libpq 18 (psycopg-c 3.3.4); PR #1564's compose would shrink the SBOM to linux-64.

**Approach:** Compose `build`, `grayskull`, `crm` into `pyforge-foundry-full` on three platforms and move `pnpm` into `python` (one declaration); put `platform-dev` + `platform-object-storage` in a layer environment; cap psycopg / pgvector below the first builds that need libpq 18 (psycopg-c 3.3 as measured 2026-09-25 — 3.2.10 already solves on libpq 17.11; re-measure at dispatch) and move `scribe-pg` to PG17, proven against scribe's Postgres suite.

## Boundaries & Constraints

**Always:**
- PostgreSQL major 17 everywhere (`>=17.11,<18`); psycopg and pgvector capped below the libpq-18 boundary, measured in the lock before pinning — never a number copied from PR #1564's text.
- `pyforge-foundry-full` keeps linux-64, osx-arm64 and win-64; platform-limited features go in the layer env only.
- Verify `pixi.toml` is the full manifest after every write; regenerate `environment.yaml` in the same change.
- The `AGENTS.md` foundry-full line is inside the managed block: change it through `bmad-project-context`.
- Co-governor reconcile before landing: a memlog entry on every Spec `spec-surface-check` names, `git add`, then `python scripts/spec_surface_check.py --write-baseline --spec <project>/<spec>` per named Spec, re-run the check and read its exit code; never a bare stamp.

**Never:**
- Do not merge PRs #1563 / #1564 / #1576; port their payload by hand where this story names it.
- Do not flip any Epic 44 `blocked` key or `pyforge.cutover_root`.
- Do not hand-edit `sprint-status-ledger.yaml` or any `SPEC.md`.
- Do not edit `rxm7706/python-foundry`.
- Do not bump PostgreSQL or drop `platform-dev` to clear a solve.
- Do not compose `local-recipes` or any `desktop-lab` feature.
- Do not push a stub or placeholder `pixi.toml`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| scribe below the libpq-18 boundary | scribe Postgres suite on PG17 | passes | halt `blocked: intent gap`; never bump Postgres |
| pnpm declaration | `grep -n '^pnpm' pixi.toml` | exactly one site, in `[feature.python.dependencies]` | fail loud |
| win-64 solve | `pixi lock` with the three added features | foundry-full resolves on win-64 | name the unsolvable package; do not drop the platform |
| layer env | platform-dev + platform-object-storage over the SBOM | solves on the features' own platforms | fail loud |

</intent-contract>

## Binding

Parent Spec capability: `spec-python-foundry-cutover fnd:CAP-12`.
Dream: `docs/dreams/pyforge-unifying-strategy.md` § *Where next* → *Consolidation — 2026-09-25*.
Ledger key: `67-1-the-sbom-composes-the-laptop-bill-of-materials-on-three-platforms-with-postgresql-17-held`.
Ledger status at mint: `backlog`.
Minted 2026-09-25 from `epics.md` so `marshal factory dispatch` can resolve `spec-67-1-the-sbom-composes-the-laptop-bill-of-materials-on-three-platforms-with-postgresql-17-held.md`.

## Epic excerpt

**Type:** feature • **Effort:** L • **Deps:** — • **FR/AD:** fnd:CAP-12 • Dream 2026-09-25 (Consolidation, Input 1); reference payload PR #1564 (branch `sbom/pyforge-foundry-full-compose`, not merged)
**Surface:** `pixi.toml` (`[environments] pyforge-foundry-full` gains the `build`, `grayskull` and `crm` features; `pnpm` **moved** from `[feature.local-recipes.dependencies]` to `[feature.python.dependencies]` — one declaration, never a second copy; a new layer environment composing the SBOM's features plus `platform-dev` and `platform-object-storage` on their platforms; psycopg capped below the first psycopg-c that needs libpq 18 (`<3.3` as measured 2026-09-25 — `python-agent-platform` and `platform-dev` already solve 3.2.10 on libpq 17.11 — re-measured at dispatch) in `pyforge-scribe`, `mcp-host` and `platform-ci-test`; `[feature.scribe-pg.dependencies]` `postgresql >=17.11,<18` and pgvector capped the same way (`<0.8.2` per #1564, re-measured), with the PG18 comment replaced by the reason), `pixi.lock`, `environment.yaml`, `scripts/pixi_version_registry.py` (new pin sites; `pnpm`'s site follows its move), `docs/reference/library-llms-full.md` (regenerated), the measured pixi env matrix in `docs/dreams/pyforge-unifying-strategy.md` (regenerated), `AGENTS.md` (the "`pyforge-foundry-full` … never installed by default" line — inside the managed block, so through `bmad-project-context`).
**Given** `pyforge-foundry-full` is closure-only and solves on three platforms (680 / 646 / 629 packages), `scribe-pg` sits on PostgreSQL 18 because scribe's `psycopg >=3.3.4` needs libpq ≥18.3, and #1564's compose would have left the SBOM on linux-64 alone
**When** this story lands
**Then** `pixi lock` solves `pyforge-foundry-full` on linux-64, osx-arm64 and win-64 with the three added features; the layer environment solves on every platform its features declare; every `postgresql` pin in `pixi.toml` is `>=17.11,<18` and no feature resolves libpq 18; `pixi run -e pyforge-scribe-pg scribe-pg-up` then scribe's Postgres-backed tests pass on PG17; `pyforge-station-tests`, `llms-full-check` and `pixi-version-check` are green; `environment.yaml` is regenerated with `pixi project export conda-environment -e build`
**And** neither `local-recipes` nor any `desktop-lab` feature is composed; `pixi.toml` is verified as the full manifest after every write; if scribe cannot run below the libpq-18 boundary, the story halts `blocked: intent gap` and Postgres is not bumped; the red `doctor-test` on #1564 is explained in the story's triage log; co-governor reconcile: a memlog entry on every Spec `spec-surface-check` names, then a scoped stamp per Spec, never a bare `--write-baseline`

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — expected: pass (the station's `verify_commands`).

**Manual checks:**
- `pixi run -e pyforge-scribe-pg scribe-pg-up` then `pixi run --frozen -e pyforge-scribe pyforge-scribe-test` — expected: pass on PG17 (the cluster's `server.log` reports PostgreSQL 17.x).
- `pixi run -e pyforge-guild pyforge-station-tests` — expected: pass (shared surface).
- `pixi run -e pyforge-guild llms-full-check` and `pixi-version-check` — expected: exit 0.
- `pixi run -e pyforge-guild pr-preflight` — expected: exit 0, read from the exit code.

## Review Triage Log

Implemented 2026-09-26 in an interactive session (the documented convenience path, not `marshal factory dispatch`): `pixi.toml`'s co-governors span doctor, herald, marshal, scribe and steward Specs, whose memlogs sit outside Epic 67's declared surface (`MRS-GATE-007`).

**Re-measured, as the story required (conda-forge file metadata, 2026-09-26):**
- **psycopg:** the libpq-18 boundary is **psycopg-c 3.2.11, not 3.3**. 3.2.10 is the last release with libpq-17 builds (it ships both), and every 3.2.11+ and 3.3.x build needs libpq 18. Caps are `>=3.2.10,<3.2.11`. The Spec's `<3.3` would have resolved 3.2.13 on libpq 18. #1564's `<3.2.10` was one release too low.
- **pgvector:** 0.8.1 is the last linux-64/osx-arm64 release with a libpq-17 build (`<0.8.2`, as #1564 had it). win-64 pgvector is built against libpq 16 only; `scribe-pg` has no win-64.
- **psycopg2:** 2.9.10 is the last release with libpq-17 builds. The `local-recipes` and `dbgpt-sidecar` floors of 2.9.13, raised by the 2026-09-26 upgrade pass, needed libpq 18.

**Deviations and operator decisions:**
1. **`crm` is not composed; operator decision 2026-09-26, a named SBOM gap.**
   - `conda-recipe-manager` 0.8+ caps click (0.10.6: `>=8.2.1,<=8.4.1`, a range; 0.10.0–0.10.5: `==8.2.1`; 0.8–0.9: `<8.2`). herald's `httpx2 >=2.13.1`, mirroring `mcp`, needs `click >=8.4.2`, so crm ≥0.8, the `crm` feature's floor, cannot join.
   - Its `feedrattler` needs `conda-smithy >=3.45`, which caps `py-rattler <0.26` or `conda <26.3`. The SBOM holds pyforge-warden's `py-rattler >=0.26` and `build`'s `conda >=26.5`.
   - **Corrected after review:** the SBOM is not crm-free. grayskull 3.1.1 depends on an unversioned `conda-recipe-manager`, which the solver holds at 0.5.0, the last release with no click cap. The gap is current crm (≥0.8) plus feedrattler, and grayskull's v1 output in the SBOM runs against crm 0.5.0, a risk for 67.3 to assess.
   - Owner: the conda-recipe-manager feedstock's click cap. This goes to 67.3's gap list and 67.4's upstream tickets.
   - Current crm and feedrattler stay in the `grayskull` env. The CAP-12 success wording needs a memlog amendment (recorded) and a `bmad-spec` re-derive.
2. **libpq is held at 17 in every environment; operator decision 2026-09-26, "every environment".**
   - Why a direct pin is needed: capping the drivers is not enough, because psycopg-c 3.2.10 and psycopg2 2.9.10 both ship libpq-18 builds of the same version, and the solver picks those.
   - `libpq >=17.11,<18` is pinned in `pyforge-scribe`, `mcp-host`, `platform-ci-test`, `dbgpt-sidecar` and `local-recipes`.
   - `postgresql >=17.11,<18` is pinned in `bmad-ui` and `bmad-suite-full`, where `mybmad-dashboard`'s `postgresql >=14` floated to 18.
3. **`local-recipes` swaps `matplotlib` for `matplotlib-base`; a consequence of decision 2.**
   - The `matplotlib` metapackage pulls `pyside6` → `qt6-main`. Every Qt 6.10+ build on linux-64/osx-arm64 links libpq 18, and the Qt 6.9 builds on libpq 17 need `icu 75`, where the environment runs `icu 78.3`.
   - Agg and headless plotting are unchanged; the Qt GUI backend is gone from the recipe factory.
4. **Scribe runs below the libpq-18 boundary, so the halt clause did not trigger.**
   - `graph_store_pg.py` uses only `psycopg.connect`, `psycopg.sql` and `psycopg.errors`, all present in 3.2, and its suite passes on psycopg 3.2.10 / PostgreSQL 17.11.
   - Scribe's `pyproject.toml` `postgres` extra (`psycopg>=3.3.4`) is **left unchanged**. A floor drop there was tried and reverted before landing: the extra is pip metadata only, and the conda package pixi builds for scribe takes its run-dependencies from `src/shared/packages/pyforge-scribe/pixi.toml` (`python`, `typer`, `pydantic`, `pyforge-core`), so the extra feeds no pixi solve.
   - Touching scribe's package would also have moved scribe's chain-currency code stage past its PRD, architecture and retro (`chain_currency_sweep_check` went red on it).
   - The `pyforge-scribe` feature's `psycopg <3.2.11` and `libpq <18` pins are what hold PostgreSQL 17.
5. **`pyforge-foundry-full-stack` solves on linux-64 only.** Its features' shared platform set is just linux-64, because `platform-object-storage` declares linux-64 alone.
6. **`scripts/pixi_version_registry.py` needed no change.** It tracks only pixi-version pin sites; neither the composition nor the `pnpm` move adds or moves one. `pixi-version-check` exits 0.
7. **`pnpm` in the `python` feature** reaches every environment that composes `python`, not only the SBOM. That is how the story specified the move ("one declaration").

**The red `doctor-test` on #1564, explained:** it failed on governance, not the pixi change.
- #1564 added a standalone Dream `docs/dreams/pyforge-foundry-full-sbom.md` with no `fold-exemption`, which failed `test_sources_one_chain.py::test_live_tree_chain_sprawl_has_no_fail_at_ruling_snapshot` (chain-sprawl-unexempted).
- It also had no README row, which failed `test_sources_chain_dreams_hygiene.py::test_live_tree_dream_readme_missing_count` (66 ≠ 65).
- This story ports only the pixi payload and adds no Dream, so neither recurs.

## Outcome

Verified 2026-09-26:
- `pixi lock` solves every environment. `pyforge-foundry-full` covers linux-64, osx-arm64 and win-64 (720 / 686 / 747 lock package entries per platform; 709 conda records in the Dream's matrix); `pyforge-foundry-full-stack` covers linux-64 (731 entries; 720 conda records).
- No environment resolves libpq or postgresql ≥ 18, or psycopg-c ≥ 3.3. Every `postgresql` pin reads `>=17.11,<18` (`python-agent-platform`, `platform-dev`, `bmad-ui`, `bmad-suite-full`, `scribe-pg`).
- **Scribe on PostgreSQL 17.11:**
  - The cluster was started from this change's `pyforge-scribe-pg` env on `127.0.0.1:5433`: `postgres (PostgreSQL) 17.11`, pgvector 0.8.1, psycopg 3.2.10 on libpq 170011.
  - `pixi run --frozen -e pyforge-scribe pyforge-scribe-test`: 398 passed, 11 skipped. `test_graph_store_pg.py`: 15 passed, none skipped.
  - The cluster ran TCP-only, because `scripts/scribe_pg.py`'s socket directory exceeds the unix-socket path limit from a worktree (scribe 22.1).
- `environment.yaml` is regenerated (the `build` env gains `pnpm`). `llms-full-check` and `pixi-version-check` exit 0.
- The Dream's measured env matrix is regenerated (`scripts/pixi_env_matrix.py --update`).
- The `AGENTS.md` block is refreshed through `bmad-project-context` (operator-approved): the foundry-full line, plus a PostgreSQL 17 policy line.

## Review

An adversarial read-only review of the branch diff (general-purpose subagent, 2026-09-26) found nine items. All were addressed in this PR:

1. **HIGH, fixed.** `tests/packaging/test_bmad_suite_full_feature.py::test_bmad_ui_feature_is_untouched` pinned `bmad-ui`'s dependency table byte-for-byte; the baseline now carries the 67.1 `postgresql` pin with a dated reason. Its sibling `test_eval_quality_pin_lives_in_the_shared_table` was already red on `main` (it expected `>=1.4.1`; #1607 moved the pin to `>=4.3.0`) and is fixed in the same file. `tests/packaging`: 131 passed. No PR lane runs it; `pyforge-deps-test` / `test-packaging` do.
2. **MEDIUM, fixed.** An existing PostgreSQL 18 `var/scribe-pg/data`, as in the primary checkout, would fail `pg_ctl start` under the new PG17 binaries. `scripts/scribe_pg.py` now compares `PG_VERSION` with `pg_ctl --version`; on a mismatch it moves the directory aside (`data.pg18`, never deleted) and re-initialises, and it refuses outright while an old-major server still holds 5433. New test: `tests/scripts/test_scribe_pg_major_version.py`, 4 passed.
3. **MEDIUM, fixed.** "The SBOM lacks crm" was wrong; see triage item 1. `AGENTS.md` is corrected through `bmad-project-context` (operator-approved), along with the `pixi.toml` comment and the owning Spec's memlog.
4. **Resolved by revert.** `spec-pyforge-scribe` warned drift-presumed on scribe's `pyproject.toml`; the file was then restored to `main` (triage item 4), so there is nothing left to reconcile.
5. **Fixed.** The `pyforge-foundry-full-stack` comment claimed osx-arm64; it now says linux-64 only (macOS laptops get no layer env yet).
6. **Fixed.** `docs/reference/environments.md` (drift introduced here) and `docs/how-to/pixi-tasks.md` (already stale on `main`) are regenerated.
7. **Fixed.** The library catalog moves `pnpm` to § 1 (the `python` feature); the libpq bullet says `python-agent-platform` holds libpq 17 through its `postgresql` pin; the `default` env comment lists `pnpm`.
8. **Fixed.** CI's scribe Postgres service moves from `pgvector/pgvector:pg16` to `:pg17` in `coverage-gates.yml` and `pyforge-station-tests.yml`, so CI proves scribe on PostgreSQL 17 too.
9. **Noted.** The `AGENTS.md` provenance line cites `6022314f3c` (this branch's base) while describing `pyforge-foundry-full-stack`, which exists only on this branch. The facts hold at this PR's merge.
