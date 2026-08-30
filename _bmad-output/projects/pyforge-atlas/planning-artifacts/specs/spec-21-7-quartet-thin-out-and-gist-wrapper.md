---
title: 'Quartet thin-out and gist wrapper (Story 21.7, Epic 21)'
type: 'feature'
created: '2026-08-30'
status: 'ready-for-dev'
context:
  - '{project-root}/_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-atlas-kedro-catalog-expansion/SPEC.md'
  - '{project-root}/_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-atlas-kedro-catalog-expansion/identity-contract.md'
  - '{project-root}/_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-conda-forge-packaging-inventory-operations/SPEC.md'
  - '{project-root}/_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-conda-forge-packaging-inventory-operations/.memlog.md'
---

<intent-contract>

## Intent

**Problem:** The identity script
(`scripts/conda-forge-packaging-inventory-operations_openteams_identity.py`) still live-fetches
`ASSOCIATOR_URL`, the inventory tab, and the OpenTeams board, then joins/overlays it all itself.
`--gist-only` depends on that join already having populated the identity xlsx tab. Story 21.6
lands `identity_export_parquet` (Atlas's own parity-tested Phase D join) but nothing consumes it,
and Epic 17's "purl-associator fetch stays in the quartet" constraint is now stale.

**Approach:** Replace `main()`'s fetch+join+overlay block with a read of `identity_export_parquet`.
Make `--gist-only` read that Parquet for identity/overlay columns, merged with ranking columns
(`P`/`Rank`/`Score`/`Work` + JFROG) still sourced from the existing ranked identity xlsx tab
(`priority.py`'s output, untouched -- Epic 23.5 supersedes this merge). Supersede Epic 17's
constraint with a dated memlog entry.

## Boundaries & Constraints

**Always:**
- No direct HTTP/GraphQL call to a public/board endpoint remains; `main()` builds `records` from
  one `identity_export_parquet` read.
- Parquet path resolves via the `PYFORGE_ATLAS_DATA_ROOT` / `${paths.data_root}/...` convention
  `globals.yml` uses (Story 21.1) -- use the landed filepath, do not guess it.
- `--gist-only` reads that Parquet for identity/overlay columns, merges ranking columns from the
  ranked xlsx tab by `Core_Python_Package_Name`; today's missing-ranking-columns error stays.
- `write_xlsx_tab`, `create_missing_issues`, canvas/gist writers, `--skip-gist`/`--create-issues`
  unchanged (`create_missing_issues`'s `board` arg becomes `{}` -- write-only, never read back).
- Append a dated inventory-memlog entry superseding the 2026-08-22 Story 17.1 clause,
  cross-referencing `identity-contract.md`.

**Block If:** None -- `identity-contract.md` fully specifies the target row shape.

**Never:**
- Touch `priority.py` or ranking logic (Epic 23.3).
- Touch gist/dashboard/canvas markdown generation beyond input-row source.
- Implement `identity_export_parquet` or the Atlas Phase D node (Story 21.6 dependency).
- Implement Epic 23.5's ranking-merged complete export -- merge stays a `--gist-only`-time join.
- Remove `write_xlsx_tab`/the identity-out tab (`priority.py`'s input).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| `main()`, Parquet present | Atlas bootstrap + Phase D ran | Records match today's identity columns | No error expected |
| `main()`, Parquet missing | Fresh clone / no bootstrap | Exit non-zero naming the missing file/step | Never fall back to a live fetch |
| `--gist-only`, tab has ranking columns | Steady state | Parquet rows merged with ranking by name; gist published | No error expected |
| `--gist-only`, tab missing ranking columns | `priority.py` never ran | Return 1, existing error message | Unchanged from today |
| `--gist-only`, a name has no cross-source match | Universe drift | Row skipped, stderr warning names it | Never silent-drop; never raise |

</intent-contract>

## Code Map

- Identity script -- `ASSOCIATOR_URL` (~L79), `main()`'s fetch+join+overlay block (~L1382-1436),
  `publish_gist_from_tab` (~L1198-1236), and the 9 now-dead CLI flags feeding the associator/
  inventory-tab/board/overlay fetch (~L1256-1301 argparse block) -- all retired together with the
  helper functions they call (`lookup_assoc`, `from_assoc`, `from_inventory`, `from_board_only`,
  `attach_packaging_urls`, `overlay_live_local`, `read_inventory_tab`, `fetch_project_issues`,
  `board_packaging_urls`).
- `src/shared/packages/pyforge-atlas/conf/base/globals.yml` (~L104-109, `paths.data_root`) --
  path convention to mirror (reference only).
- `identity-contract.md` -- Join semantics + Gist publish section (this story's target).
- Inventory `.memlog.md` + `SPEC.md` `## Constraints` -- where the superseding entry lands.
- `tests/packaging/test_openteams_handoffs.py` -- `create_missing_issues`/canvas coverage
  unaffected; add coverage for the new read/merge paths.

## Tasks & Acceptance

**Execution:**
- Identity script -- swap `main()`'s fetch+join+overlay block for a `pandas.read_parquet` read
  (pandas already in `local-recipes`) into `records`, path via `PYFORGE_ATLAS_DATA_ROOT`; exit
  non-zero with a clear message if the file is missing.
- Same file -- retire the dead functions/flags in Code Map; pass `board={}` to
  `create_missing_issues`.
- Same file -- rewrite `publish_gist_from_tab`: read the Parquet for identity/overlay columns,
  merge ranking + JFROG columns from the ranked xlsx tab by name; keep the missing-columns error;
  warn (not raise) on a per-name merge miss.
- Inventory `.memlog.md` -- append a dated entry superseding Story 17.1's clause, cross-ref
  `identity-contract.md`; update `SPEC.md` `## Constraints` with a superseding note (keep
  history, mirror the Epic 16->17 renumber entry).
- `docs/reference/conda-forge-packaging-inventory-operations_replay.md` -- update flag docs for
  the retired/changed CLI surface.
- `tests/packaging/test_openteams_handoffs.py` (or a sibling) -- cover the I/O matrix.
- Housekeeping -- grep for orphaned callers of the retired symbols; re-stamp
  `scripts/.spec-surface-baseline.json` scoped to the inventory spec.

**Acceptance Criteria:**
- Given a full `main()` + `--gist-only` run against a bootstrapped Atlas data root, when audited,
  then neither makes a direct HTTP/GraphQL call to `ASSOCIATOR_URL` or the OpenTeams board API,
  and published gist rows carry both Parquet-sourced identity/overlay columns and tab-sourced
  ranking columns.
- Given the inventory `.memlog.md`, when this story lands, then it carries a dated entry
  superseding the Story 17.1 purl-associator-stays-in-quartet clause, cross-referencing
  `identity-contract.md`.

## Verification

**Commands:**
- `python -m py_compile scripts/conda-forge-packaging-inventory-operations_openteams_identity.py`
  -- expected: exit 0.
- `pixi run -e local-recipes pytest tests/packaging/test_openteams_handoffs.py -q` -- expected:
  all green, no regressions.
- `pixi run -e local-recipes test-packaging` -- expected: current pass count plus new tests.
- `grep -rn 'ASSOCIATOR_URL\|lookup_assoc\|fetch_project_issues\|board_packaging_urls' scripts/`
  -- expected: zero hits outside fixtures/history.
