---
title: "34.2: The Phase C mapping fills from the conda-forge bot's name mapping"
type: 'fix'
created: '2026-10-18'
status: 'done'
baseline_revision: 'b78dabd10a'
review_loop_iteration: 1
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-pyforge-atlas/SPEC.md
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-pyforge-atlas/live-sources.md
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/epics.md
  - src/shared/packages/pyforge-atlas/AGENTS.md
  - src/shared/packages/pyforge-atlas/src/pyforge/atlas/datasets/core_sources.py
  - src/shared/packages/pyforge-atlas/src/pyforge/atlas/datasets/request_datasets.py
  - src/shared/packages/pyforge-atlas/src/pyforge/atlas/pipelines/pypi_intelligence/pipeline.py
  - .claude/skills/conda-forge-expert/scripts/conda_forge_atlas.py
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** on a fresh data root the Phase C mapping, and every PyPI-keyed dataset after it, stays empty. Line
numbers are at `b78dabd10a`.

- **Cause 1, circular source (R3).** `pypi_parselmouth_mapping_raw` (`ParselmouthMappingDataset`,
  `datasets/core_sources.py`) read the flat `pypi_conda_map_store` (`${paths.pypi_conda_map}`), which only
  `export_pypi_conda_map` writes, from `pypi_conda_mapping`, the mapping this source feeds. The unattended refresh of
  2026-10-17 left `pypi_conda_mapping`, `pypi_current_versions`, `pypi_intelligence_enriched` and
  `pypi_intelligence_scored` at 0 rows; only the flat file's staleness sidecar existed.
- **Cause 2, the fan-out had no candidates on a fresh root.** `refresh_pypi_json_store` took only `params:ttls`, so
  Kedro ran it before the mapping existed, and `PyPIJsonFanOutDataset._candidate_names` read the same absent flat file:
  "fetch returned no data".
- **Cause 3, found by the first live run (2026-10-18 06:42):** the bot's mapping carries hash-like `pypi_name` values
  PyPI does not serve (`0164e082b2…`, 35 in the first 200 sorted names). `PyPIJsonRequestDataset.load_many` let one
  project's 404 (`DatasetError` from `APIDataset`) raise out of the fan-out and fail the whole `pypi_intelligence`
  run (`PI_EXIT=1`).
- **Legacy reference:** `phase_c_parselmouth_join` (CFA:1744) reads
  `conda_forge_metadata.conda_forge_bot.pypi_to_conda.get_pypi_name_mapping()`, a GET of
  `raw.githubusercontent.com/conda-forge/conda-forge-bot-data/main/mappings/pypi/name_mapping.yaml`, lowercases
  `pypi_name`, and matched 11,005 conda rows on 2026-10-18. Measured live: the YAML is 1.26 MB, a list of 11,023
  entries (10,989 `regro-bot`, 34 `static`), parsed in 1.8 s by PyYAML's pure loader.

**Approach:**
1. `JSONSourceDataset` gains `decode: json | yaml` (YAML through `yaml.CSafeLoader` when built, else `SafeLoader`,
   then round-tripped through JSON so the last-good copy can hold it; a bad body, or one JSON cannot hold, such as a
   bare date or `!!binary`, degrades as `body not YAML`; an object tag is refused by the safe loader).
2. `ParselmouthMappingDataset(url, filepath)` composes a `JSONSourceDataset(expect=list, decode=yaml)` (AD-13
   last-good + marker, no client of its own) and projects legacy's rows: `pypi_name` lowercased, `conda_name`,
   `match_source: parselmouth`; malformed entries dropped; deduplicated. It exposes the source as `.source`, and
   `provenance.py` reads it, so the read surface sees its freshness. The catalog entry points at the bot's YAML through
   the existing `GITHUB_RAW_BASE_URL` override (no new override point) with a `raw/pypi_parselmouth_mapping_raw` store.
   `export_pypi_conda_map` stays the flat file's one writer.
3. `RefreshRequest` gains `pypi_pairs` (the Story 27.2 pattern: identifier batches ride the trigger, never payloads).
   `refresh_pypi_json_store(ttls, pypi_conda_mapping_base)` passes the run's Phase C pairs (deduplicated, real strings
   only); the pipeline wires `pypi_conda_mapping_base` into it (no cycle: the base precedes `pypi_json_raw`, and
   `match_source_urls` follows it). `PyPIJsonFanOutDataset` unites the pairs with the flat cache (which keeps any
   C.5 match from the previous run and wins on a conflict).
4. `PyPIJsonRequestDataset.load_many` records a per-project `DatasetError` (kedro's wrapper for every HTTP and
   connection failure) in `last_failures`, with the HTTP status when there is one, instead of raising; anything else
   (the rate limiter's guard, a programming error) still raises. `fetch_candidates` persists rows only for projects
   that answered (a failed project keeps its last-good row), marks the store stale only when every request in the
   batch failed (an outage), keeping last-good, and advances the rotation offset only after a batch got answers.
   Legacy Phase H also retries 429/503 with `Retry-After`; that belongs to Story 34.10, which lifts the 200 cap.

Ledger key: `34-2-the-phase-c-mapping-fills-from-the-conda-forge-bot-s-name-mapping`.
Type / Effort / Deps: fix / M / none.

### Living CAP citations

- **`spec-pyforge-atlas` CAP-64** (`live-sources.md` row 3): restores a source meant to work; a `fix`, so no flag
  (`spec-feature-flag-governance` Q1).
- **AD-10** (one writer: `export_pypi_conda_map` still writes the flat file), **AD-13**, **AD-2** (public host, no
  credential), **AD-11** (every test network-free; the fan-out's live path is exercised only by the measurement below).
- **Origin.** Dream entry 2026-10-18 (atlas fills its own data), R3.

## Acceptance Criteria

- **AC1 — The source.** `ParselmouthMappingDataset` reads the bot's YAML through `JSONSourceDataset`; a test with a
  recorded-shape YAML returns legacy's projection (lowercased `pypi_name`, `match_source: parselmouth`, malformed
  entries dropped); unreachable → empty frame with no copy, last-good with one, never raises; broken YAML degrades;
  an unknown catalog key raises `TypeError`.
- **AC2 — Same-run candidates.** `refresh_pypi_json_store` carries the run's pairs; a fresh-root fan-out (no flat
  file) fetches those names; pairs unite with the flat cache.
- **AC3 — A missing project is a miss, not an abort.** One project's `DatasetError` leaves the others' rows and lists it
  in `last_failures`; any other exception raises; every request failing keeps last-good under a marker and leaves the
  rotation offset where it was. A pipeline test pins the trigger's inputs and its place between `map_pypi_conda` and
  `match_source_urls`.
- **AC4 — Live, fresh root (recorded 2026-10-18, scratch copy of the data root, `pypi_intelligence` then
  `seed_gaps`):** both runs exit 0. `pypi_conda_mapping` 0 → 10,968 rows (10,965 distinct conda names) against legacy
  Phase C's 11,005 matched rows (99.7 %). `pypi_json_raw`, `pypi_current_versions`, `pypi_intelligence_enriched` and
  `pypi_intelligence_scored` 0 → 165 each: the 200-name batch (`PYPI_JSON_FANOUT_LIMIT`) less 35 real 404s (all
  hash-like names from the bot's mapping, checked one by one). `vcs_release_velocity` 0 → 123 (the `vcs_health` node
  `derive_release_velocity` over those 165 current versions, same scratch root). `seed_gaps_license_map_report`
  0 → 28.
  `seed_gaps_lts_registry_report` 83 → 87 rows over 80 distinct slugs against legacy's 81 (only `neo4j` missing); the
  row gap to legacy's 219 is 133 `airflow-with-*` conda outputs legacy maps to `apache-airflow` through its C.5
  source-URL match, which atlas reaches with Stories 34.3 (node_attrs URLs) and 34.10 (full Phase H coverage).
- **AC5 — Gates.** `pyforge-atlas-test`, `kedro-test`, `kedro-catalog-check`, the coverage gate and `lint-types` exit
  0; governing Specs reconciled and stamped scoped.

## Boundaries & Constraints

**Never:** a second writer of the flat file; a credential on the bot's host; an HTTP client import in the package; a
test that touches the network.

**Residual risk:**
- **Phase H coverage.** `PYPI_JSON_FANOUT_LIMIT` (200 per run, rotating offset) means the ~11k mapped names take about
  55 runs to cover once; legacy Phase H fetches every never-fetched, serial-moved or 30-day-old row. Minted as Story
  34.10 in this change.
- **Bad names upstream.** The bot's mapping carries hash-like `pypi_name` values; they are counted as misses each run
  they come up, not filtered (a filter would hide a real rename).

## I/O & Edge-Case Matrix

| Situation | Before | After |
|---|---|---|
| Fresh data root | mapping empty; PyPI-keyed datasets empty | mapping from the bot's YAML; PyPI-keyed datasets fill in the same run |
| Bot host down, copy present | (read the flat file) | last-good mapping, `stale` marker |
| A mapped name PyPI does not serve | run fails (`DatasetError`) | a miss in `last_failures`; the run goes on |
| PyPI down for the whole batch | run fails | last-good kept, `stale` marker |
| Broken YAML | — | last-good or empty, `body not YAML` |

</intent-contract>

## Binding

- Parent Spec capability: `spec-pyforge-atlas` CAP-64 (FR-72), a `fix`.
- Dream: `docs/dreams/pyforge-atlas.md` § *Realization log*, 2026-10-18 (atlas fills its own data), R3.
- Epic 34 / Story 34.2 in `planning-artifacts/epics.md`; this change also mints Story 34.10 (Phase H coverage).

## Spec Change Log

- 2026-10-18: written with the implementation (branch `atlas-34-2-phase-c-mapping`), including Cause 3, which the
  first live run found.
- 2026-10-18: independent review FAIL (1 blocker, 4 should-fix, 4 nits). Resolved: `ruff format` on the tests
  (blocker); a YAML body JSON cannot hold degrades instead of raising (S1); only `DatasetError` is a miss, with the HTTP
  status recorded, and the 429/503 retry is moved into Story 34.10's Then clause (S2); a pipeline test pins the
  trigger's wiring and order (S3); `vcs_release_velocity` measured, 123 rows (S4); tests for the safe loader's refusal
  and for de-duplication (N2); `last_failures` declared in `__init__` (N3); the offset advances only after answers
  (N4). N1 (the 34-10 ledger row with no feed row) is the feed-leak guard: the key stays out of the shared feed until
  this change merges, then goes back in.
- 2026-10-18: re-review PASS; its two nits fixed (a test pins the `HTTP <status>:` prefix; Story 34.10's Then clause
  says 34.2 counts every `DatasetError` as a miss). Promoted to `done`.
