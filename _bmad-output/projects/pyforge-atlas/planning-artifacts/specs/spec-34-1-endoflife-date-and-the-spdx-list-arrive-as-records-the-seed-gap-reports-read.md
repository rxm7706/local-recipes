---
title: '34.1: endoflife.date and the SPDX list arrive as records the seed-gap reports read'
type: 'fix'
created: '2026-10-18'
status: 'done'
baseline_revision: '221ebb302b'
review_loop_iteration: 1
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-pyforge-atlas/SPEC.md
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-pyforge-atlas/live-sources.md
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/epics.md
  - src/shared/packages/pyforge-atlas/AGENTS.md
  - src/shared/packages/pyforge-atlas/conf/base/catalog.yml
  - src/shared/packages/pyforge-atlas/src/pyforge/atlas/pipelines/seed_gaps/nodes.py
  - src/shared/packages/pyforge-atlas/src/pyforge/atlas/datasets/refresh.py
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** `pypi_endoflife_raw` and `seed_spdx_upstream_list_raw` are bare `api.APIDataset` entries
(`conf/base/catalog.yml` at `221ebb302b`), whose `load()` returns a `requests.Response`. `report_lts_registry_gap`
reads a list (`seed_gaps/nodes.py:152`) and `_spdx_upstream_ids` a dict or list (`:369`-`:380`), so both reports
always read an empty input: the unattended refresh of 2026-10-17 wrote `seed_gaps_spdx_report` and
`seed_gaps_lts_registry_report` at 0 rows. The shared decoder `_api_json` (`datasets/core_sources.py:53`) returns
dicts only, so it cannot serve endoflife.date's list either.

**Measured live, 2026-10-18:** `https://endoflife.date/api/all.json` is a JSON list of 485 product slugs;
`https://raw.githubusercontent.com/spdx/license-list-data/main/json/licenses.json` is a dict with `licenses` (740 ids,
list version 3.29.0).

**Approach:**
1. A new `JSONSourceDataset` (`datasets/json_sources.py`, exported from `pyforge.atlas.datasets`) composes the same
   `kedro_datasets.api.APIDataset` (no client of its own; the no-inline-IO scan holds), decodes the body, and checks
   it: the declared top-level shape (`expect: list | dict`), non-empty, and for a dict source a non-empty
   `require_key` (`licenses` for SPDX). The check is top-level only; the node reads the elements.
2. AD-13: a good body is also written as `last_good.json` under the entry's `filepath` (atomically, through
   `pyforge.core.atomic_write`) and clears the marker. A failed fetch, a body that is not JSON, or a body of the wrong
   shape, empty, or missing its required key returns the last-good copy and stamps the same `.staleness.json` marker
   (`refresh.StalenessMarker`) the external-refresh stores write; with no last-good copy it returns the empty
   container of the declared shape under the marker. The marker's reason names the exception and the cause kedro's
   load wrapper hides (`fetch failed: DatasetError: … (cause: HTTPError: 404 …)`). A filesystem error on the copy or
   the marker is logged, never raised: no path raises.
3. The two catalog entries become `pyforge.atlas.datasets.JSONSourceDataset` with `expect: list` / `expect: dict`
   (`require_key: licenses`) and `filepath: ${globals:paths.data_root}/raw/<entry>`; the URLs and their override points
   are unchanged and no credential is attached.
4. Provenance (`provenance.py`, the MCP and dashboard read surface): a fresh load is `live-fetch`, as a bare
   `APIDataset` was; a load that served last-good reports the copy's `file-mtime` with `reason: stale: <marker>`, and
   one with no copy is `unavailable` with that reason (review should-fix 3: wrapping `APIDataset` had dropped these
   entries to `unavailable`).

Ledger key: `34-1-endoflife-date-and-the-spdx-list-arrive-as-records-the-seed-gap-reports-read`.
Type / Effort / Deps: fix / S / none.

### Living CAP citations

- **`spec-pyforge-atlas` CAP-64** (a plain run fills every dataset a public source serves; `live-sources.md` rows 1–2):
  this story restores two public sources that were meant to work. A `fix`, so no flag (`spec-feature-flag-governance`
  Q1) and no `flag:` block.
- **AD-2** (no credential on a public host), **AD-13** (keep last-good, mark stale, never fail), **AD-11** (gates
  network-free: the composed `APIDataset` is replaced by a fake in every test).
- **Origin.** `docs/dreams/pyforge-atlas.md` § *Realization log*, the 2026-10-18 entry (atlas fills its own data), root
  cause R8.

## Acceptance Criteria

- **AC1 — Records, not a Response.** `JSONSourceDataset.load()` returns the decoded `list` or `dict`; a test fails if it
  ever returns an object with `.json()` (the defect). `expect` outside `list`/`dict`, and `require_key` on a list
  source, are refused at construction. Recorded bodies (trimmed copies of the live `all.json` and `licenses.json`,
  2026-10-18, under `tests/fixtures/json_sources/`) decode through the real `APIDataset` with only
  `requests.Session.request` patched.
- **AC2 — AD-13.** A failed fetch, a body that is not JSON, and a body of the wrong shape, empty, or missing its
  required key each return last-good when a copy exists, else the empty shape, never overwrite the copy, and stamp
  `.staleness.json` with `stale: true`, the reason (with the cause) and `last_good_exists`; a corrupt copy counts as
  none; a later good fetch clears the marker; a filesystem error on the copy or the marker does not raise.
- **AC2b — Provenance.** `resolve_for_catalog_dataset` reports `live-fetch` after a fresh load, the copy's
  `file-mtime` with a `stale:` reason after a degraded load, and `unavailable` with that reason when there is no copy.
- **AC3 — The report fills.** `report_spdx_schema_gap` over the loaded SPDX document yields `upstream-drift` rows; over
  the old `Response` it returns an empty frame (pinned).
- **AC4 — Catalog.** Both entries resolve to `JSONSourceDataset` with the declared `expect`, a `filepath` under
  `raw/<entry>`, and no `credentials` key.
- **AC5 — Live parity (recorded).** `pyforge atlas run --pipelines seed_gaps` on a scratch copy of the data root:
  `seed_gaps_spdx_report` 0 → 13 rows, all `upstream-drift`, equal to legacy `spdx-schema-gap --drift` (13,
  2026-10-18); `seed_gaps_lts_registry_report` 0 → 83 rows against legacy `lts-registry-gap`'s 219 proposals (209
  exact, 10 likely): atlas builds LTS candidates from `pypi_conda_mapping`, which stays empty until Story 34.2, and 34.2
  re-measures this row. endoflife.date's 485 products match legacy's `products: 485`. Legacy's 337 `non-standard`
  SPDX rows need the atlas `conda_license` column (DW-B6-1), outside this story.
- **AC6 — Gates.** `pyforge-atlas-test`, `kedro-test`, `kedro-catalog-check`, the atlas coverage gate and
  `lint-types` exit 0; the no-inline-IO scan passes with the new module; every governing Spec is reconciled and stamped
  scoped.

## Boundaries & Constraints

**Always:** compose `APIDataset` for the fetch; read every verdict from an exit code.

**Never:** add an HTTP client import to the package; attach a credential to either host; change a seed-gap node's
logic; hand-edit `SPEC.md` or the ledger.

**Residual risk:**
- `last_good.json` sits under the data root (gitignored); a fresh root has none, so a first run with the host down
  yields the empty shape under a marker, as the external-refresh stores do.
- The LTS report reaches legacy's count only with Story 34.2's mapping.
- A store that turns read-only after a degraded load keeps its old marker through a later good fetch (the fetch is
  served; the marker cannot be removed), so provenance reads stale until a load can clear it: errs toward stale,
  which AD-13 permits, and logs a warning saying so.

## I/O & Edge-Case Matrix

| Situation | Before | After |
|---|---|---|
| Host up, good body | `Response` → report empty | decoded records → report rows; `last_good.json` written |
| Host down, last-good present | raises (`DatasetError`) | last-good, `stale` marker naming the cause |
| Host down, no last-good | raises | empty shape, `stale` marker |
| HTTP 404 (a moved URL) | raises (`DatasetError`) | last-good (or empty), marker names `HTTPError` and 404 |
| Body of the wrong shape, empty, or without `licenses` | `Response` → empty | last-good (or empty), copy kept, marker names why |
| Body not JSON | `Response` → empty | last-good (or empty), marker `body not JSON: JSONDecodeError …` |
| Store not writable | — | the good body is still served; a warning is logged |

</intent-contract>

## Binding

- Parent Spec capability: `spec-pyforge-atlas` CAP-64 (FR-72), a `fix`; no `SPEC.md` text changes.
- Dream: `docs/dreams/pyforge-atlas.md` § *Realization log*, the 2026-10-18 entry (atlas fills its own data), R8.
- Epic 34 / Story 34.1 in `planning-artifacts/epics.md`.

## Spec Change Log

- 2026-10-18: written with the implementation (branch `atlas-34-1-raw-json-sources`).
- 2026-10-18: independent review FAIL (1 blocker, 6 should-fix, 5 nits). Resolved: mypy (`write_text` lambdas → typed
  writers; blocker); an empty or key-less body no longer overwrites last-good (`require_key`, S1); no path raises
  (the dead `mkdir` gone, the copy's write and the marker guarded, S2); provenance for the MCP and dashboard read
  surface (S3); the marker names the exception and its cause (S4); recorded-body tests through the real `APIDataset`
  plus corrupt-copy and filesystem-error tests (S5); decode failure reads `body not JSON` (N1); the export sits under
  its own comment (N2); the catalog comment no longer claims a 7 d TTL (N3); the top-level-only check is documented
  (N4); `_exists` reads the copy (N5). S6 (status promotion) happens at the re-review.
- 2026-10-18: re-review PASS; its three nits fixed (`staleness()` keeps the stored `marked_at`; the read-only-store
  marker case is logged and named under Residual risk; tests for a `ConnectionError` cause and for a valid-JSON but
  empty or wrong-shape last-good copy). Promoted to `done`.
