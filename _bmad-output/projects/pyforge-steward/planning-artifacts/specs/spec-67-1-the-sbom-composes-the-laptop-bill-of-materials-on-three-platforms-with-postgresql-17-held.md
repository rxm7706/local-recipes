---
title: '67.1: The SBOM composes the laptop bill of materials on three platforms, with PostgreSQL 17 held'
type: 'feature'
created: '2026-09-25'
status: 'ready'
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
