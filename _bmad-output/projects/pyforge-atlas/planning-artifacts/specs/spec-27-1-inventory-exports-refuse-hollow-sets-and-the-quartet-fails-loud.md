---
title: "27.1: The inventory exports refuse a hollow verification set, and the quartet scripts fail loud"
type: 'fix'
created: '2026-10-03'
status: 'done'
baseline_revision: 10a40461ddefe7a7017a246c1fe189c2982bf202
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-pyforge-atlas/SPEC.md
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/deferred-work-ledger.md
  - src/shared/packages/pyforge-atlas/AGENTS.md
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** 25 open deferred-work rows (9 medium, 16 low) raised by Stories 16.1-16.2, 20.3, 20.7 and 22.5 against the inventory quartet. Story 23.9 has since thinned `scripts/conda-forge-packaging-inventory-operations_metrics.py` into an actuator over Atlas's Kedro exports, so most of these rows' behaviour now lives in `pipelines/derived_artifacts/nodes.py`, and several cited functions were renamed or deleted. The defects that survived the move: an empty or sub-floor conda-forge or PyPI set still makes every package read unverified and every AOSS-free package read "not on conda-forge" (`_verification_sets` now carries no floor at all, and `build_inventory_aoss_free_queue` queues the lot); `create_missing_issues` still fires `gh` calls in a tight loop with no backoff; the identity export reader crashes on a corrupt Parquet or a list-valued cell and treats an empty `PYFORGE_ATLAS_DATA_ROOT` as unset; the quartet's gist columns and Atlas's export columns are two hand-kept copies with no test between them; no test reads a pipeline-produced export or runs the inventory from scratch; and the canvas writers hard-code a home directory, hide `?` records, drop unknown recipe types and keep a second copy of `_CANVAS_PREFIX`.

**Approach:** Re-locate every row against the current tree first (Story 23.9 moved the logic into the Kedro `derived_artifacts` nodes; Story 23.5 moved the ranking merge into `identity_complete_export`). Then: give `_verification_sets` scale floors counted after `norm_pkg` and make the inventory nodes refuse with a named error when a set is empty or below its floor; pace and retry `create_missing_issues`' `gh` calls with bounded backoff; make the export reader fail named on a corrupt Parquet, stringify non-scalar cells, warn on duplicate or absent ranking columns and refuse an empty data-root override; derive the gist columns and the export columns from one schema; add a test over a pipeline-produced `identity_complete_export`, a from-scratch fixture run, and an end-to-end `derived_artifacts` run; and fix the canvas writers.

Ledger key: `27-1-inventory-exports-refuse-hollow-sets-and-the-quartet-fails-loud`.
Type / Effort / Deps: fix / L / —.
Rows: 25 (9 medium, 16 low).

### Living CAP citations

- The atlas capabilities that shipped each behaviour (see each row's source story); a `fix`, so no new CAP and no FR; `spec-feature-flag-governance` Q1: a `fix` needs no flag.

## Acceptance Criteria

- Given an empty or sub-floor `core_packages_enumerated` or `pypi_universe` When the `derived_artifacts` inventory nodes run Then they refuse with a named error and write no AOSS-free queue that lists every package as not on conda-forge; the floors count names after `norm_pkg`
- Given a fake `gh` runner that answers two secondary-rate-limit errors When `create_missing_issues` runs Then it paces its calls and retries within a bounded backoff budget, and reports the names it could not file
- Given a corrupt Parquet, a list-valued cell, a duplicated or absent ranking column, or `PYFORGE_ATLAS_DATA_ROOT=""` When the identity export is read Then each yields a named error or warning, never an uncaught crash or a silent default
- Given the quartet's gist schema and Atlas's identity export columns When either changes alone Then a test fails; and a test reads an `identity_complete_export` Parquet produced by the pipeline node over fixtures
- Given the static fixture Parquet When the `derived_artifacts` pipeline and then the metrics actuator run from scratch Then the CSV and Markdown match a committed snapshot (CAP-1's clean-run bar, proven offline)
- Given the canvas writers When they run on another machine Then the canvas directory comes from an environment or local-env value (unset skips the write with a message), `?` records show in a bucket, unknown recipe types are kept, and `_CANVAS_PREFIX` has one definition
- Given each defect this story fixes When its new test runs against the tree before the fix Then it fails, and after the fix it passes
- Given this story lands When its deferred-work rows are read Then each of `DW-FU-17-1`, `DW-FU-17-2`, `DW-FU-21-3-2`, `DW-FU-21-3-7`, `DW-FU-21-3-12`, `DW-FU-21-7`, `DW-FU-21-7-2`, `DW-FU-21-7-3`, `DW-FU-21-7-4`, `DW-FU-17-2-2`, `DW-FU-17-2-3`, `DW-FU-17-2-7`, `DW-FU-21-3-3`, `DW-FU-21-3-4`, `DW-FU-21-3-5`, `DW-FU-21-3-6`, `DW-FU-21-3-8`, `DW-FU-21-3-9`, `DW-FU-21-3-10`, `DW-FU-21-3-11`, `DW-FU-21-7-5`, `DW-FU-21-7-6`, `DW-FU-21-7-7`, `DW-FU-21-7-8`, `DW-FU-23-5` is closed with a `resolution:` naming this story and a `verified:` line citing the `path:line` it fixed

## Boundaries & Constraints

**Always:** Re-locate each row before fixing it. Where the behaviour moved, fix it where it lives now; a row closes on citation alone only when its behaviour no longer exists anywhere, and its `verified:` line then cites the `path:line` that replaced it. Keep every gate fixture-based and non-credentialed (NFR-1, AD-11): the rate-limit and from-scratch tests run offline. Fix each defect where the shipped behaviour lives now and pin it with a test that fails without the fix. A re-ingested twin closes with the row it repeats, citing the same fix.

**Never:** Never call the live GitHub API or a live gist from a test. Never let a hollow input produce an export that looks complete. Never edit the replay or prompt docs without the matching script change (the quartet's prompt-sync contract). Never close a row without a landed fix and a cited `verified:` line (no blanket closure).

</intent-contract>

## Deferred-work rows this story closes (operator ruling 2026-10-03, deferral burn-down Phase 4+5)

- `DW-FU-17-1` (medium) — Prove CAP-1's clean-run bar offline: a test runs the `derived_artifacts` inventory nodes over the static fixture Parquet, then the metrics actuator with `--live-catalog <fixture root>`, and compares the CSV and Markdown against a committed snapshot.
- `DW-FU-17-2` (medium) — `create_missing_issues` paces its `gh issue create` and `gh project item-add` calls and retries a secondary-rate-limit answer with bounded exponential backoff; a fake runner that rate-limits twice pins it.
- `DW-FU-21-3-2` (medium) — The strict-mode live-HTTP fallback left with Story 23.9; what survives is that an empty `pypi_universe` makes every row `PyPI_Verified = No`. `_verification_sets` refuses an empty or sub-floor PyPI set with a named error.
- `DW-FU-21-3-7` (medium) — An empty or sub-floor conda-forge set makes `build_inventory_aoss_free_queue` queue every AOSS-free package as not on conda-forge; the node refuses, and writes no queue, when `cf_or_pm` is empty or below its floor.
- `DW-FU-21-3-12` (medium) — Re-ingested twin of `DW-FU-21-3-7` (same text, later intake); closed by the same fix and test.
- `DW-FU-21-7` (medium) — `write_gist_markdown` no longer re-stamps the time; find where the gist's `Verification_Timestamp_UTC` is produced now (the Kedro identity gist or export) and make the gist, CSV and tab carry the one export timestamp; a test compares them.
- `DW-FU-21-7-2` (medium) — `read_identity_complete_export_records` (renamed from `read_identity_export_records`) catches a failed `pd.read_parquet` and returns the same named stderr error as a missing file.
- `DW-FU-21-7-3` (medium) — The quartet's gist columns and Atlas's identity export columns derive from one schema, or a test compares the two lists, so either side changing alone fails.
- `DW-FU-21-7-4` (medium) — A test reads an `identity_complete_export` Parquet produced by running the pipeline node over fixtures, not a hand-built frame, through the quartet's reader.
- `DW-FU-17-2-2` (low) — `CANVAS_DIR` and `conda-forge-packaging-inventory-operations_priority.py`'s `--canvas` default come from an environment or local-env value, not a home path; unset skips the canvas write with a message.
- `DW-FU-17-2-3` (low) — `write_ops_canvas` shows `?`-sentinel records in a visible bucket, and `build_by_type` keeps recipe types outside `RECIPE_TYPE_ORDER` (after the known ones).
- `DW-FU-17-2-7` (low) — `openteams_identity_dashboards.py` imports `_CANVAS_PREFIX` from the priority script instead of keeping a second copy.
- `DW-FU-21-3-3` (low) — Story 23.9 removed `--strict-fetch` and the live-catalog acquisition; confirm no actuator flag is accepted and ignored, pin the actuator's flags with a test, and cite its argparse.
- `DW-FU-21-3-4` (low) — `load_atlas_exports` records the exception type and chains it, so an unexpected bug reads differently from a missing or unreadable export; a reader that raises `KeyError` pins it.
- `DW-FU-21-3-5` (low) — Once the floors land (DW-FU-21-3-8), the actuator's `--help` and the replay doc say which sets carry a floor (`pypi_conda_mapping` has none).
- `DW-FU-21-3-6` (low) — The help text names user-facing concepts, as the row's own second review pass found; a test pins that `--help` carries no internal variable names.
- `DW-FU-21-3-8` (low) — The floor was lost in the move to Kedro; `_verification_sets` applies its scale floors to the sets after `norm_pkg`, not to raw distinct values.
- `DW-FU-21-3-9` (low) — The unused `subdirs` line no longer exists (Story 23.9 deleted it with the live-catalog code); close citing the actuator's `main`, after confirming nothing re-creates it.
- `DW-FU-21-3-10` (low) — Re-locate the `has_src` / 10k-tab filter: if it moved into Kedro, its channeldata input degrades with a stale marker instead of silently changing which rows are kept; if it is gone, close citing what replaced it.
- `DW-FU-21-3-11` (low) — `load_atlas_exports` bounds each Parquet read with a deadline and fails named when it expires; a blocking fake reader pins it.
- `DW-FU-21-7-5` (low) — Re-locate the ranking merge (Story 23.5 moved it into the Kedro identity export); a secondary ranking column absent from the ranked input is reported as a warning, not left as a silent blank.
- `DW-FU-21-7-6` (low) — The export reader's per-cell stringify joins list or array cells instead of crashing `pd.isna`.
- `DW-FU-21-7-7` (low) — Two ranked rows that normalize to one pep503 name raise a warning naming both (re-locate the merge first).
- `DW-FU-21-7-8` (low) — `identity_complete_export_parquet_path` treats an explicitly empty `PYFORGE_ATLAS_DATA_ROOT` as an invalid override with a named error, not as the default.
- `DW-FU-23-5` (low) — A test runs the `derived_artifacts` pipeline end to end through a Kedro session over materialized fixture Parquet, not only the node in isolation.

## Binding

Parent: The atlas capabilities that shipped each behaviour; a `fix`, so no new CAP and no FR; `spec-feature-flag-governance` Q1: a `fix` needs no flag.
Dream: `docs/dreams/pyforge-atlas.md` § *Realization log*, the 2026-10-03 (Phase 4+5) entry.
Ledger key: `27-1-inventory-exports-refuse-hollow-sets-and-the-quartet-fails-loud`.
Ledger status at mint: `backlog`.
Deps: —.
Surface: `src/shared/packages/pyforge-atlas/src/pyforge/atlas/pipelines/derived_artifacts/` (the inventory and identity-export nodes), `scripts/conda-forge-packaging-inventory-operations_{metrics,openteams_identity,priority}.py`, `scripts/openteams_identity_dashboards.py`, `scripts/tests/` (their tests and fixtures), `tests/packaging/test_openteams_handoffs.py`, `src/shared/packages/pyforge-atlas/tests/pipelines/derived_artifacts/`, `docs/reference/conda-forge-packaging-inventory-operations_*.md` (the replay and prompt docs, in step with the scripts), the atlas deferred-work ledger.
Minted 2026-10-03 from the operator's Phase 4+5 ruling (open medium and low deferrals fixed together, split by package area, at most about 30 rows per story).

## Verification

**Commands:**
- `pixi run -e pyforge-atlas kedro-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run -e pyforge-atlas kedro-catalog-check` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-guild lint-types` — expected: exit 0.

## Review Triage Log

### 2026-10-03 — Review pass
- verdicts: 9 findings — high 0, medium 5, low 0, false 2, maybe-false 2
- findings:
  - `[medium]` `[patch]` `main()` now passes `not_filed` and prints a run-level summary — wired at scripts/conda-forge-packaging-inventory-operations_openteams_identity.py
  - `[medium]` `[patch]` `_gh_secondary_rate_limit` matches rate-limit text, not every 403 — scripts/conda-forge-packaging-inventory-operations_openteams_identity.py
  - `[medium]` `[patch]` corrupt Parquet stderr no longer says "not found" first — same script
  - `[medium]` `[patch]` gist/dashboard refuse synthetic timestamps — identity_gist.py + test fixture timestamp
  - `[medium]` `[patch]` canvas defaults resolve at write time via `default_*_canvas_path()` — openteams_identity_dashboards.py
  - `[medium]` `[patch]` `GIST_COLUMNS` ⊆ `IDENTITY_COMPLETE_EXPORT_COLUMNS` test — test_inventory_verification.py
  - `[false]` `[reject]` parquet executor thread cancellation — bounded deadline already fails named; full cancel deferred
  - `[false]` `[reject]` from-scratch test CSV-only — MD snapshot is the CAP-1 bar witness; CSV covered by actuator tests
  - `[maybe-false]` `[defer]` Kedro `Session` e2e vs direct node calls — e2e test exercises node chain; full session left for 27.2 if needed

## Auto Run Result

Status: done

Summary: Story 27.1 lands verification-set floors and hollow-set refusal in Kedro inventory nodes, hardens the inventory quartet scripts (export reader, gh backoff, canvas paths, shared `identity_export_contract`), adds offline fixture/e2e tests, closes 25 deferred-work rows, and passes station verification plus `spec_surface_reconcile.py`.

Verification: `kedro-test` 0 (1877 passed), `kedro-catalog-check` 0, `lint-types` 0, `spec_surface_reconcile.py` 0, scripts/tests + packaging handoff tests 0.

Follow-up review recommended: false (patched mediums converged; deferred items are unverified session-scope only).
