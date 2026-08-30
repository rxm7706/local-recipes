---
title: 'Ranked identity export Parquet for Vizro feed (Story 22.1, Epic 22)'
type: 'feature'
created: '2026-08-30'
status: 'ready-for-dev'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - '{project-root}/_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-atlas-kedro-catalog-expansion/SPEC.md'
  - '{project-root}/_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-atlas-kedro-catalog-expansion/vizro-canvas-parity.md'
  - '{project-root}/_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-atlas-kedro-catalog-expansion/complete-export-contract.md'
  - '{project-root}/_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-atlas-kedro-catalog-expansion/identity-contract.md'
  - '{project-root}/_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-conda-forge-packaging-inventory-operations/SPEC.md'
  - '{project-root}/_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-21-8-end-to-end-verification-gate.md'
warnings: []
---

<intent-contract>

## Intent

**Problem:** `priority.py` (`scripts/conda-forge-packaging-inventory-operations_priority.py`)
computes the P1-P10 bucket, Rank, Score, and Work columns entirely from a hand-maintained
Excel workbook — identity, JFROG telemetry, OpenTeams board state, and inventory batch/cohort
all come from four workbook tabs. Once Story 21.6 lands `identity_export_parquet` (Atlas's
Kedro `upstream_discovery` identity join), the ranked-identity data Epic 22's Vizro pages
(22.2-22.4) need has no Parquet source — `priority.py`'s ranking stays trapped in the xlsx
workbook, and Vizro loaders, which must stay BSL read-only per `vizro-canvas-parity.md`, have
nothing to read.

**Approach:** Swap only `priority.py`'s identity-tab input from the xlsx sheet to
`identity_export_parquet` (Story 21.6's output) — JFROG/OpenTeams-board/inventory tabs stay
xlsx-sourced, since their Parquet equivalents are Epic 23 territory, not yet landed — and add a
new Parquet write of the already-computed ranked `records` list as
`identity_ranked_export.parquet`, bridging Vizro 22.2-22.4. The existing xlsx write-back (ranked
tab, inventory sync, canvas TSX) is unchanged: additive on the output side, substitutive only on
the identity-tab input side. No ranking LOGIC changes — this is a plumbing swap; Epic 23.3 ports
the rules into Kedro, not this story.

## Boundaries & Constraints

**Always:**
- Ranking logic (`assign_lane`, `work_label`, `use_score`, `percentile_1_100`,
  `PRIORITY_DESC`, `BUCKET_ORDER`, `WORK_ORDER`, `sort_key`) stays byte-identical — this story
  changes I/O only, never the hierarchy.
- The identity-tab read switches from the xlsx `--tab` sheet to a new `--identity-parquet` input
  reading `identity_export_parquet` (Story 21.6's landed `catalog.yml` path under
  `${PYFORGE_ATLAS_DATA_ROOT}` — resolve the exact relative path from the actual landed entry at
  implementation time, never from a guess baked into this spec).
- `CDO-ENT-JFROG`, `OpenTeams`, and `inventory-2026-08-12` tabs stay read from `--xlsx`
  unchanged — their Parquet equivalents are Story 23.2/23.3, not this story.
- The existing xlsx write-back (ranked `--tab` sheet, `--skip-inventory-sync`-gated inventory
  sync, `--canvas` TSX) stays unchanged — the gist actuator (through the Epic 21-22 bridge) and
  `openteams_identity_dashboards.py`'s ops/workbook canvases still depend on it until Epic 23.5/23.6.
- A new `--ranked-export` output writes `identity_ranked_export.parquet` unconditionally (no skip
  flag — Vizro 22.2-22.4 need it every run) with at minimum: `Core_Python_Package_Name`, `P`,
  `Rank`, `Score`, `Work`, `Platforms`, `Apps`, `Downloads`, `Versions`, `Vuln`,
  `Priority_Bucket_Description`, `Priority_Source`, `Priority_Reason`, `JFROG_risk_level`,
  `JFROG_latest_vuln_count`, `internal_component_count`, `internal_lob_count`. All but one come
  straight from the already-computed `records`/`rec` fields (the same values `write_canvas`
  already consumes — zero new ranking computation); `Verification_Timestamp_UTC` is the one new
  value, a plain run-time stamp, not a ranking field.
- `priority.py` never imports `pyforge.atlas` package internals — it runs under the
  `local-recipes` pixi env (already has pandas/pyarrow/openpyxl), a different env than
  `pyforge-atlas`; resolve `PYFORGE_ATLAS_DATA_ROOT` via a local `os.environ.get(...)` mirror,
  not a cross-env import.
- After editing `priority.py`, re-stamp `scripts/.spec-surface-baseline.json` scoped to
  `priority.py`'s OWNING spec (`spec-conda-forge-packaging-inventory-operations` — its `SPEC.md`
  § surface lists this file explicitly), not this story's own
  `spec-atlas-kedro-catalog-expansion`: `python scripts/spec_surface_check.py --write-baseline
  --spec pyforge-atlas/spec-conda-forge-packaging-inventory-operations`, run AFTER `git add` of
  any changed/new files.

**Block If:** Story 21.6 (`identity_export_parquet`'s producer) is not `status: done`, or
Story 21.8 (this story's own `depends_on`) is not `status: done`. This spec may be authored
ahead of that (as this document is); implementation must not dispatch until both are done.

**Never:**
- Do not port ranking rules into a Kedro node — that is Epic 23.3
  (`inventory_priority_assignments`), explicitly out of scope here (no Kedro ranking nodes).
- Do not touch `..._openteams_identity.py` or `..._metrics.py` — their gist-only /
  `--live-catalog` read paths are untouched; only `priority.py` changes.
- Do not remove or alter the xlsx write-back path — Epic 23.7 ("quartet data logic retired")
  retires it, not this story.
- Do not add JFROG/OpenTeams-board/inventory Parquet reads — those inputs stay xlsx-sourced
  until Story 23.2/23.3.
- Do not add a new pixi task or pixi.toml dependency — pandas, pyarrow, and openpyxl are already
  in `[feature.local-recipes.dependencies]`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Normal run, post-21.6/21.7/21.8 | `identity_export_parquet` exists at its landed catalog path; `--xlsx` has CDO-ENT-JFROG/OpenTeams/inventory-2026-08-12 tabs | Same P/Rank/Score/Work as today (byte-identical logic); xlsx ranked tab + inventory sync + canvas written unchanged; new `identity_ranked_export.parquet` written with the columns above | N/A |
| `identity_export_parquet` missing/not yet materialized | Operator runs `priority.py` before `pyforge-atlas-bootstrap` + `kedro run` ever produced it | Raise a clear, actionable error naming the missing path and the bootstrap command to run — never silently fall back to an empty identity universe | Non-zero exit, message names the missing file |
| Package present in CDO-ENT-JFROG/inventory but absent from `identity_export_parquet` | No matching `Core_Python_Package_Name` in the identity Parquet | Row is simply not ranked (same as today's semantics — only identity-tab/Parquet rows are ranked) | N/A, matches existing behavior |
| `--ranked-export` parent directory does not exist | Fresh data root, `derived/` not yet created | Directory created (`mkdir(parents=True, exist_ok=True)`, mirroring the existing `--canvas` flag) | N/A |

</intent-contract>

## Code Map

- `scripts/conda-forge-packaging-inventory-operations_priority.py` — the sole file this story
  touches. `main()` (~L581-813): `ident_header, ident_rows = load_tab(wb, args.tab)` (~L601)
  currently loads the identity tab from the xlsx workbook; replace with a new
  `load_identity_parquet(path: Path) -> tuple[list[str], list[dict]]` returning the same
  `(header, rows)` shape `load_tab()` produces, so `pep503()`/`assign_lane()`/`work_label()`/the
  whole `records` loop (~L619-660) need zero changes. JFROG/OpenTeams/inventory loads
  (`load_tab(wb, "CDO-ENT-JFROG")` etc., ~L602-604) stay untouched.
- `write_canvas()` (~L250-309) — reference for exactly which `rec`/`records` fields already exist
  in-memory (`name`, `bucket`, `rank`, `score100`, `work`, `plat`, `apps`, `ic`, `lob`, `dl`,
  `ver`, `vuln`, `src`, `why`); the new `write_ranked_export()` reuses these, adding zero new
  ranking computation.
- `main()`'s xlsx write-back block (~L727-813) — `out_header`/`ws.append(row)` loop and the
  `--skip-inventory-sync`-gated inventory sync stay byte-identical; only its input
  (`ident_rows`/`ident_header`) now comes from Parquet instead of `load_tab(wb, args.tab)`.
- `argparse` block (~L583-598) — add `--identity-parquet` (default resolved from
  `PYFORGE_ATLAS_DATA_ROOT`, mirroring `globals.yml`'s `${env_or:PYFORGE_ATLAS_DATA_ROOT,data}`
  convention; exact relative path resolved from Story 21.6's landed `catalog.yml` entry at
  implementation time, never from a guess in this spec) and `--ranked-export` (default
  `${PYFORGE_ATLAS_DATA_ROOT}/derived/identity_ranked_export.parquet`), following the existing
  `--canvas` flag's default-path-plus-override pattern (~L591-597).
- `src/shared/packages/pyforge-atlas/conf/base/catalog.yml` (Story 21.6, not yet landed) — the
  source of truth for `identity_export_parquet`'s actual relative filepath; grep this file at
  implementation time rather than trusting any path in this spec.
- `identity-contract.md` § "Export columns" — the column list `identity_export_parquet` carries
  (`Core_Python_Package_Name`, `OpenTeams_Issue_URL`, `conda_purl`, `Conda-Forge_FeedStock_URL`,
  etc.) that `priority.py`'s `work_label()`/`board_lock()` already key off of by name — confirms
  no field-name changes are needed in the ranking logic itself.
- `complete-export-contract.md` § 3.2 "Priority assignment (Story 23.3)" — the future
  Kedro-ported column shape (`P`, `Rank`, `Score`, `Work`, `Priority_Bucket_Description`,
  `Priority_Source`, `Priority_Reason`); this story's `identity_ranked_export.parquet` column
  names deliberately match these verbatim so Story 23.3's eventual Kedro port is a
  schema-compatible superset, not a rename exercise.
- `scripts/.spec-surface-baseline.json` + `scripts/spec_surface_check.py` — `priority.py` is
  governed by `spec-conda-forge-packaging-inventory-operations` (its `SPEC.md` § surface lists it
  explicitly), a different spec than this story's own; re-stamp scoped to THAT spec.
- `tests/packaging/test_openteams_handoffs.py` — the precedent pattern for testing this quartet:
  `pytest.importorskip("openpyxl")` module-scope guard (so `-e pyforge-ci`'s
  `pyforge-deps-test` skips cleanly rather than erroring) plus `importlib.util` dynamic import
  (the script's hyphenated filename isn't a valid module path).
- `pixi.toml` `[feature.local-recipes.tasks.test-packaging]` (~L1117-1119) — `pytest
  tests/packaging -q`, the existing task the new test file runs under.
- `pixi.toml` `[feature.local-recipes.dependencies]` (~L1404-1405 pandas/pyarrow, ~L1603
  openpyxl) — confirms all three are already present; no dependency change needed.

## Tasks & Acceptance

**Execution:**
- Pre-flight: confirm Story 21.6 and Story 21.8 are `status: done` (check `stories.yaml` /
  `fleet-picture`) before dispatching implementation; if not, this story cannot run (see Design
  Notes).
- `scripts/conda-forge-packaging-inventory-operations_priority.py` — add
  `load_identity_parquet(path: Path) -> tuple[list[str], list[dict]]` reading
  `identity_export_parquet` via `pandas.read_parquet`, returning the same `(header, rows)` shape
  as `load_tab()`; replace the `ident_header, ident_rows = load_tab(wb, args.tab)` call in
  `main()` with it. JFROG/OpenTeams/inventory loads stay on `load_tab(wb, ...)` unchanged.
- `scripts/conda-forge-packaging-inventory-operations_priority.py` — add `--identity-parquet`
  and `--ranked-export` argparse arguments (defaults resolved from `PYFORGE_ATLAS_DATA_ROOT`,
  mirroring `--canvas`'s existing default-path pattern); raise a clear error naming the missing
  path plus the `pyforge-atlas-bootstrap` command if `--identity-parquet` does not exist at load
  time.
- `scripts/conda-forge-packaging-inventory-operations_priority.py` — add
  `write_ranked_export(path: Path, records: list[dict]) -> None`, serializing the already-computed
  `records` list into the column shape from Boundaries via
  `pandas.DataFrame(...).to_parquet(path, engine="pyarrow")`, plus a fresh
  `Verification_Timestamp_UTC` run-time stamp; create `path.parent` first
  (`mkdir(parents=True, exist_ok=True)`, mirroring `--canvas`); call unconditionally at the end
  of `main()`, alongside the existing `write_canvas` call.
- Confirm the exact `identity_export_parquet` relative filepath against Story 21.6's landed
  `catalog.yml` entry (grep `conf/base/catalog.yml` for the dataset key) and set
  `--identity-parquet`'s default accordingly — do not hardcode a guessed path from this spec.
- Add `tests/packaging/test_priority_ranked_export.py` (new; `pytest.importorskip("openpyxl")`
  guard + `importlib.util` dynamic import, mirroring `test_openteams_handoffs.py`) covering the
  I/O matrix: normal run produces both xlsx write-back and the new Parquet with the expected
  columns; missing `identity_export_parquet` raises with an actionable message; a
  JFROG-only/inventory-only package (absent from the identity Parquet) is silently excluded from
  ranking, matching today's behavior.
- Re-stamp `scripts/.spec-surface-baseline.json` scoped to
  `spec-conda-forge-packaging-inventory-operations` after `git add`ing any changed/new files.

**Acceptance Criteria:**
- Given `identity_export_parquet` exists at its landed path and `--xlsx` has the
  CDO-ENT-JFROG/OpenTeams/inventory-2026-08-12 tabs, when `priority.py` runs, then the computed
  P/Rank/Score/Work per package is byte-identical to running the same fixture through the
  pre-this-story xlsx-only path.
- Given a normal run, when `priority.py` completes, then `identity_ranked_export.parquet` exists
  with at least `Core_Python_Package_Name`, `P`, `Rank`, `Score`, `Work` populated for every
  ranked row, AND the existing xlsx ranked-tab write-back, inventory sync, and canvas TSX are all
  still produced exactly as before this story.
- Given `--identity-parquet` points at a missing file, when `priority.py` runs, then it exits
  non-zero with a message naming the missing path and the bootstrap command to produce it —
  never a silent empty-universe run.
- Given a package present in CDO-ENT-JFROG or inventory-2026-08-12 but absent from
  `identity_export_parquet`, when `priority.py` runs, then that package is excluded from the
  ranked output (both xlsx and Parquet) — matching today's identity-tab-driven semantics.
- Given this story's code changes are complete and staged, when
  `python scripts/spec_surface_check.py --write-baseline --spec
  pyforge-atlas/spec-conda-forge-packaging-inventory-operations` runs, then the baseline
  re-stamp succeeds with no unscoped/foreign-spec drift.

## Spec Change Log

- 2026-08-30: Initial draft. Bridges `priority.py` off the xlsx-only identity read onto Story
  21.6's `identity_export_parquet`, and adds a new `identity_ranked_export.parquet` write for
  Epic 22 Vizro pages (22.2-22.4). Written ahead of Stories 21.6/21.7's implementation (only
  21.1, 21.2, and 21.8's draft spec exist as of this drafting) — see Design Notes for the
  resulting dispatch-timing consequence.

## Design Notes

**This story cannot be dispatched yet.** As of this spec's drafting (2026-08-30), Story 21.6
(`identity_export_parquet`'s producer) and Story 21.7 (quartet thin-out) have no landed code or
even a drafted spec file yet (confirmed: no `spec-21-6-*.md` or `spec-21-7-*.md` under this
project's `planning-artifacts/specs/`), and Story 21.8 (this story's other listed dependency) is
itself only `status: ready-for-dev`, not `done` — its own Design Notes record the same upstream
chain being incomplete. Do not dispatch `bmad-build` / `bmad-loop` against this spec until
Stories 21.6, 21.7, and 21.8 are all `status: done`.

**Why `status: ready-for-dev` despite the hard dependency.** Mirrors Story 21.8's own precedent:
the spec itself (Intent, Boundaries, I/O matrix, Code Map, Tasks & Acceptance) is complete and
actionable — what's missing is upstream code, a dispatch-ordering constraint recorded in the
`Block If` boundary above, not an ambiguity in what this story must do.

**Exact `identity_export_parquet` path is unresolved by design.** `identity-contract.md`'s
"Derived outputs" table names the dataset but Story 21.6 hasn't landed a `catalog.yml` entry
yet, so this spec cannot cite a real filepath. Whoever implements this story must resolve it
from the actual landed `catalog.yml` (Code Map, above) rather than trusting a guess baked into
this document at drafting time — the same discipline Story 21.8's Code Map applied to the
not-yet-landed `--live-catalog` CLI flag.

**Column-name choice mirrors the future Kedro port, not today's gist markdown.**
`identity_ranked_export.parquet` uses `Core_Python_Package_Name` (not the xlsx gist's shorthand
`Package` column) plus the gist-shorthand rank/detail columns verbatim, so Story 23.3's eventual
`inventory_priority_assignments` Kedro node (`complete-export-contract.md` § 3.2) is a
schema-compatible superset, not a rename exercise.

## Verification

**Commands (run once Stories 21.6/21.7/21.8 are done and this story dispatches):**
- `pixi run -e local-recipes python scripts/conda-forge-packaging-inventory-operations_priority.py
  --xlsx <fixture.xlsx> --identity-parquet <fixture identity_export_parquet>` — expected: exit 0;
  `identity_ranked_export.parquet` written with the columns from Boundaries; xlsx ranked tab
  still written.
- `pixi run -e local-recipes test-packaging` (or the new test file's own `pytest` invocation) —
  expected: all green, including the missing-identity-parquet error-message test.
- `python scripts/spec_surface_check.py --write-baseline --spec
  pyforge-atlas/spec-conda-forge-packaging-inventory-operations` (after `git add`) — expected:
  succeeds, baseline reflects `priority.py`'s new content hash.

**Manual checks:**
- Diff a fixture run's P/Rank/Score/Work output against the same fixture run through the
  pre-this-story code path (or a frozen snapshot) — confirm byte-identical ranking, proving the
  I/O swap introduced no logic drift.
