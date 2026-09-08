# Parity evidence record — attended B4 credentialed event (template)

This is the shape the **attended credentialed parity run** records (Story B4,
AC-3; AD-19/FR-4). It is filled in ONLY at the attended wave-boundary event
against a **real operator `cf_atlas.db`** — never in the loop. The machine gate
`pyforge.atlas.parity.may_retire_legacy` consumes the corresponding
`ParityEvidenceRecord`s and permits legacy retirement (FR-4 `phase_state`
removal) **only** when every legacy-surface view here is credentialed +
zero-material-drift + human-signed.

## Run metadata

| field | value |
|---|---|
| run mode | `credentialed` |
| legacy `cf_atlas.db` ref | `<path / snapshot id>` |
| kedro Parquet store ref | `<path / commit>` |
| captured at (UTC) | `<ISO-8601>` |
| operator | `<handle>` |
| Q1 tolerance | exact row-count + value parity on the actionable views; timestamp/ordering-only diffs benign |

## Per-view evidence (the `v_actionable_packages` family — AD-14: legacy-surface only)

| view | legacy row count | kedro row count | Δ rows | material drift? | benign diffs (timestamp/ordering) | notes |
|---|---|---|---|---|---|---|
| `v_actionable_packages` | | | | | | |
| `v_pypi_candidates` | | | | | | |
| `v_pypi_intelligence_valid` | | | | | | |
| `v_packages_enriched` | | | | | | |
| `v_current_version_vulns` | | | | | | |

> B8/B9/B10 new-signal datasets (basilisk / release-velocity / migration-readiness)
> are **NOT** in this table — they are never parity-gated (AD-14).

## Human sign-off (the retirement gate)

- [ ] All 5 legacy-surface views show **no material drift** under the Q1 tolerance.
- [ ] Every difference is documented **benign** (timestamp/ordering-only) with a reason above.
- [ ] The fixtures were **recaptured from this credentialed legacy run** (DW-B1-1 part a) — no shape-only seeds remain.
- [ ] DW-B2-4 pre-flight done: `pypi_bigquery_downloads_raw` routed to `BigQueryDownloadsDataset` before any credentialed Phase-P run.

**Sign-off:** `<name>` — `<date>` — signature: `______________________`

Only after this sign-off is recorded may the legacy orchestrator + `phase_state` +
`bootstrap-data` be marked for retirement (AD-19). `may_retire_legacy` returns
`allowed=True` only when a signed, zero-drift, credentialed record exists for
**every** view above.
