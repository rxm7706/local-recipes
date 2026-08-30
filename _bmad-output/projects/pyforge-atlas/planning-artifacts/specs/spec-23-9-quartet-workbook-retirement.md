---
title: 'Quartet workbook retirement: thin actuators over Atlas exports, no openpyxl in scripts/ (Story 23.9, Epic 23)'
type: 'feature'
created: '2026-08-30'
status: 'ready-for-dev'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - '{project-root}/_bmad-output/projects/pyforge-atlas/planning-artifacts/change-history/sprint-change-proposal-2026-08-30.md'
  - '{project-root}/_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-atlas-kedro-catalog-expansion/SPEC.md'
  - '{project-root}/_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-atlas-kedro-catalog-expansion/complete-export-contract.md'
  - '{project-root}/_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-atlas-kedro-catalog-expansion/identity-contract.md'
  - '{project-root}/_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-conda-forge-packaging-inventory-operations/SPEC.md'
  - '{project-root}/_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-23-8-workbook-free-metrics-universe.md'
  - '{project-root}/_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-23-4-deliverable-a-packaging-candidate-status.md'
  - '{project-root}/_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-23-5-identity-complete-export-parquet.md'
  - '{project-root}/_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-23-6-bsl-gist-aggregates.md'
  - '{project-root}/_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-21-7-quartet-thin-out-and-gist-wrapper.md'
warnings: []
---

<intent-contract>

## Intent

**Problem:** After Story 23.8 the workbook is optional for `metrics.py`, but it is still
the spine of the other three quartet scripts, and `openpyxl` is imported by all three:

| Script | Workbook touchpoints today |
|---|---|
| `..._openteams_identity.py` | `read_inventory_tab(xlsx, TAB_IN="inventory-2026-08-12")` (input), `write_xlsx_tab(..., TAB_OUT="identity-2026-08-12")` (priority.py's input — kept by 21.7's *Never*), `--gist-only` merges `P`/`Rank`/`Score`/`Work` + JFROG columns from the ranked identity tab, gist provenance lines `source_workbook: docs/Analysis_Dataset-2026-08-12.xlsx` + `Workbook sha256`, `--xlsx` flag |
| `..._priority.py` | `--xlsx` (defaults to the workbook), `load_workbook(args.xlsx)` reads the identity tab, ranks, then `wb2.create_sheet(args.tab)` / `wb2.save` writes the ranked tab back into the workbook |
| `openteams_identity_dashboards.py` | `read_xlsx_tab(xlsx, "CDO-ENT-JFROG")` for the JFROG workbook canvas, `load_workbook` sheet statistics for the "Workbook tabs" gist/canvas section, `render(records, xlsx, ...)` signature |
| `..._metrics.py` | the `--analysis-xlsx` path, `XlsxReader`, `try_source` xlsx fallbacks, and — after 23.8 — a universe/verification/aggregation engine that 23.4 duplicates in Kedro |

Stories 23.3/23.4/23.5/23.6 land every one of those inputs as Kedro Parquet
(`inventory_priority_assignments`, `inventory_verified_packages` +
`inventory_aoss_free_queue`, `identity_complete_export`, BSL gist aggregates), but none
of them *removes* the workbook code — 23.7 only reads the `--live-catalog`/`--gist-only`
paths and offers an optional `INVENTORY_USE_LEGACY_SCRIPTS` refuse-flag. Without an
owning story the quartet keeps `openpyxl`, dated tab constants, and a write-back into a
file that is not even git-tracked.

**Approach:** Retire the workbook from all four scripts and thin each to an actuator over
Atlas exports, per `complete-export-contract.md` § "North star export" consumers table:
- **identity.py:** input is `identity_complete_export.parquet` (23.5) — remove
  `read_inventory_tab`, `write_xlsx_tab`, `TAB_IN`/`TAB_OUT`, `--xlsx`; `--gist-only`
  merges nothing (ranking + JFROG columns are already on the export); provenance lines
  become `source_export: identity_complete_export.parquet`, its sha256, and the export's
  `Verification_Timestamp_UTC`. Gist edit (`gh gist edit`) and `--create-issues` stay as
  thin actuators (unchanged semantics, 21.7).
- **priority.py:** the rule engine is retired — 23.3 owns `P`/`Score`/`Work` with proven
  parity — and the script reduces to a CLI shim that reads
  `inventory_priority_assignments.parquet` and writes the legacy ranked CSV / the 22.1
  `identity_ranked_export.parquet` shape; `--xlsx`/`--tab` removed, no `load_workbook`.
- **dashboards.py:** JFROG rows from `enterprise_jfrog_consumption.parquet` (23.2);
  the "Workbook tabs" section becomes "Catalog sources" over `inventory_universe`'s
  per-source counts (23.8) / 23.6's BSL aggregates; `render(records, xlsx, ...)` takes the
  export path instead.
- **metrics.py:** under `--live-catalog` the script reads `inventory_verified_packages.parquet`
  + `inventory_aoss_free_queue.parquet` (23.4) and only formats CSV / MD / the regenerated
  prompt — the universe read (23.8), the verification loop, `packaging_status`, and the
  `Counter`-over-rows aggregation are removed from the script (they live in Kedro). The
  `--analysis-xlsx` path, `XlsxReader`, and the xlsx `try_source` fallbacks are deleted;
  passing `--analysis-xlsx` exits 2 with a pointer to the Atlas path.
- `openpyxl` disappears from `scripts/` imports; `docs/reference/…_prompt.md` / `_replay.md`
  describe the workbook-free flow only (the 2026-08-12 tab names remain as historical notes).

## Boundaries & Constraints

**Always:**
- Output parity first: on the frozen fixtures 23.3–23.6 established, the thinned scripts'
  CSV / gist markdown / canvas DATA blobs are byte-identical to the last pre-retirement
  run except the provenance lines named above (`done_checkpoint`).
- `grep -rn 'openpyxl\|load_workbook\|XlsxReader\|analysis-xlsx' scripts/` returns zero
  hits after this story (test-asserted).
- The three dated constants (`TAB_IN`, `TAB_OUT`, `OUTPUT_TABS`, `TENK_TABS`,
  `CLONE_TABS`) are deleted, not renamed.
- Every removed flag is listed in `_replay.md`'s change log with its replacement.
- `--create-issues` remains live-and-irreversible with the same dry-run default; its
  input is the export's OpenTeams-handoff columns (`complete-export-contract.md` § 8).
- `tests/packaging/test_openteams_handoffs.py` and `scripts/tests/` stay green; the parity
  fixtures move from `.xlsx` to Parquet/CSV — no test may load a workbook.

**Block If:** any of Stories 23.4, 23.5, 23.6, 23.8, or 22.1 is not `status: done`
(the exports this story reads must exist); or if Story 23.7 has already been dispatched
(23.7 gates on this story — order is 23.9 → 23.7).

**Never:**
- Do not re-implement ranking, verification, identity join, or aggregation logic in
  `scripts/` — thin actuators only (23.7 AC7).
- Do not keep a hidden xlsx fallback "just in case"; a deprecation refusal with a pointer is
  the only workbook-related behavior left.
- Do not touch Kedro nodes/datasets — this story is script-side + docs.
- Do not remove the Cursor canvas writers (Story 22.6's switch owns that).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Steady-state gist publish | `identity_complete_export.parquet` present | identity.py renders gist markdown from the export; provenance lines cite the export path + sha256 + timestamp | none |
| Export missing | file absent | exit 2 naming the expected path and `pyforge-atlas-bootstrap` | no partial gist edit |
| `--xlsx` / `--analysis-xlsx` / `--tab` passed | legacy flag | exit 2: "retired by Story 23.9 — use --live-catalog / the Atlas export" | — |
| priority.py shim | `inventory_priority_assignments.parquet` present | legacy ranked CSV + `identity_ranked_export.parquet` written, values identical to 23.3's node output | — |
| dashboards JFROG pane | `enterprise_jfrog_consumption.parquet` absent | honest empty shell (same shape 22.4 uses) | warning, never blocks gist |
| metrics.py `--live-catalog` | 23.4 exports present | CSV/MD/prompt written from the exports; no verification HTTP, no universe union | — |
| Workbook on disk but unreferenced | `docs/*.xlsx` exists | ignored — assert no open() of any `.xlsx` in the test's syscall/spy | — |

</intent-contract>

## Code Map

- `scripts/conda-forge-packaging-inventory-operations_openteams_identity.py` — `from
  openpyxl import load_workbook` (~L45), `TAB_IN`/`TAB_OUT` (~L72-73), `read_xlsx_tab` /
  `read_inventory_tab` / `write_xlsx_tab` (~L892-926), provenance lines (~L1005-1081),
  `publish_gist_from_tab` (~L1199-1231), `--xlsx` (~L1242), `--gist-only` (~L1328).
- `scripts/conda-forge-packaging-inventory-operations_priority.py` — `load_workbook`
  import (~L31), `--xlsx`/`--tab` (~L584-585), read (~L600), write-back (~L731-805).
- `scripts/openteams_identity_dashboards.py` — import (~L14), `render(records, xlsx, ...)`
  (~L61-82), JFROG rows (~L187), sheet stats (~L270-308), "Workbook tabs" sections
  (~L588-611, ~L821-834), `write_workbook_canvas` (~L958-971; DW-FU-17-2-4/5/6 close here).
- `scripts/conda-forge-packaging-inventory-operations_metrics.py` — `XlsxReader`
  (~L145-200), `parse_sheet_sources` and the other readers, `try_source` lambdas,
  `--analysis-xlsx`, and the 23.8 universe branch — all deleted in favor of reading
  23.4's exports; `write_csv` / `write_md` / the prompt template stay as formatters.
- `docs/reference/conda-forge-packaging-inventory-operations_prompt.md` / `_replay.md` —
  every `--analysis-xlsx` invocation and "workbook tab" input rule rewritten to the Atlas
  flow; §"Output snapshot tabs" becomes historical.
- `_bmad-output/projects/pyforge-atlas/planning-artifacts/deferred-work-ledger.md` —
  close DW-FU-17-2-4/5/6 (`write_workbook_canvas`) with citations if this story deletes or
  rewrites that function.

## Tasks & Acceptance

**Execution:**
- Pre-flight: confirm 23.4/23.5/23.6/23.8/22.1 are `done`; confirm the export column names
  against the live Parquet (the 63-column table in 23.5), never against this spec's memory.
- identity.py → export-driven; delete tab constants + `write_xlsx_tab`; rewrite provenance.
- priority.py → shim over `inventory_priority_assignments`; delete the rule engine after
  the parity test against 23.3's node passes on the frozen corpus.
- dashboards.py → export-driven JFROG pane + "Catalog sources" section.
- metrics.py → formatter over 23.4's exports; delete the workbook path and the 23.8
  universe branch; `--analysis-xlsx` refuses with a pointer.
- Remove `openpyxl` from the scripts' import surface; if nothing else in the repo imports
  it, leave the pixi dependency alone (a dependency change is Steward's, and would require
  the `environment.yaml` re-export).
- Rewrite `_prompt.md` / `_replay.md`; add the zero-xlsx grep test; close the three
  `write_workbook_canvas` DW entries with citations.

**Acceptance Criteria:**
1. Given the frozen fixtures, when the four scripts run in the Atlas flow, then CSV, gist
   markdown, and canvas DATA blobs match the pre-retirement outputs except the provenance
   lines (`done_checkpoint`).
2. Given `scripts/`, when `grep -rn 'openpyxl\|load_workbook\|XlsxReader\|analysis-xlsx'`
   runs, then zero hits (asserted by a test).
3. Given any retired flag, when passed, then exit 2 with a pointer message, no output.
4. Given `metrics.py --live-catalog`, `identity.py --gist-only`, `priority.py`, and
   `dashboards.py` read end-to-end, then none contains ranking, verification, join, or
   raw-aggregation business logic (23.7 AC7's precondition).
5. Given `docs/reference/…_prompt.md` and `_replay.md`, when read, then no step requires a
   workbook; the 2026-08-12 tab names appear only as history.

## Spec Change Log

- 2026-08-30: Initial draft, minted by `change-history/sprint-change-proposal-2026-08-30.md`. Owns the
  quartet-side retirement of `docs/Analysis_Dataset-2026-08-12.xlsx` that Stories
  23.3–23.7 assumed but no story performed. Story 23.7's `Deps` now include this story.

## Design Notes

**Why priority.py survives as a shim rather than being deleted.** Story 22.6's
`INVENTORY_IDENTITY_UI` switch and the gist workflow still name the ranked CSV; deleting
the CLI would break the documented operator flow before 22.6 lands. Deleting only the
rule engine keeps one source of ranking truth (23.3) and one entrypoint name.

**Why metrics.py sheds the 23.8 universe branch here.** 23.8 exists to make the
operator run workbook-free as early as 21.5 allows; once 23.4 produces deliverable A in
Kedro the script-side union is redundant, and 23.7 AC7 forbids keeping it. The
`inventory_universe` dataset 23.8 built is not lost — 23.4 consumes it.

## Verification

- `python3 -m pytest scripts/tests/ tests/packaging/` — expected: green, incl. the
  zero-xlsx grep test and the provenance-line assertions.
- `pixi run -e pyforge-atlas kedro-test` — expected: green (no Kedro change, regression
  only).
- Attended, on a bootstrapped `PYFORGE_ATLAS_DATA_ROOT` with `docs/*.xlsx` renamed away:
  the four scripts complete in the Atlas flow; `strace -e openat -f … 2>&1 | grep -c
  '\.xlsx'` = 0.
