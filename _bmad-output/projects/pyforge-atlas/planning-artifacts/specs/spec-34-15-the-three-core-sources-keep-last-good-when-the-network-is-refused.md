---
title: "34.15: The three core sources keep last-good when the network is refused"
type: 'fix'
created: '2026-11-01'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
context:
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-pyforge-atlas/SPEC.md
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-pyforge-atlas/live-sources.md
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/research/egm-audit-2026-11-01.md
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-34-14-a-plain-run-on-a-fresh-data-root-exits-0.md
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-34-12-a-vulnerability-feed-that-cannot-be-reached-keeps-its-last-good-copy.md
  - src/shared/packages/pyforge-atlas/AGENTS.md
  - src/shared/packages/pyforge-atlas/src/pyforge/atlas/datasets/core_sources.py
  - src/shared/packages/pyforge-atlas/src/pyforge/atlas/datasets/vulnerability_feeds.py
  - src/shared/packages/pyforge-atlas/src/pyforge/atlas/provenance.py
  - src/shared/packages/pyforge-atlas/conf/base/catalog.yml
  - src/shared/packages/pyforge-atlas/tests/conftest.py
deferred: []
---

<intent-contract>

## Intent

**Problem:** with every fetch refused, a plain `pyforge atlas run` over a data root a good run already filled exits 1
at its first node, while CAP-64's success says that, with the network blocked, the same run exits 0 and every public
store keeps its last-good file under a `stale` marker. Line numbers are at `03a7aff5d9`.

- `src/shared/packages/pyforge-atlas/src/pyforge/atlas/datasets/core_sources.py` loads three raw sources through
  `APIDataset` with no fallback: `FeedstockOutputsArchiveDataset` (:535, `core_feedstock_outputs_raw`),
  `CondaRepodataDataset` (:542, `core_repodata_raw`, one `current_repodata.json` per conda-forge subdir) and
  `PyPISimpleIndexDataset` (:811, `pypi_simple_index_raw`). A refused connection raises `DatasetError: ...: Failed
  to connect to the remote server` out of the catalog, and none keeps a copy, whatever the data root holds.
- Story 34.14's exploration (its spec's Auto Run Result, 2026-11-01) measured it: over a root filled by a run with
  recorded responses, a second run with every fetch refused stopped at `core_feedstock_outputs_raw` before any node
  ran; the same second run with only these three URLs still served exited 0, and each vulnerability feed kept
  `last_good.parquet` under `.staleness.json`. These three datasets are the whole gap.
- The session owner's ruling of 2026-11-01 moved Story 34.14's AC3 (the network-blocked run) here, under CAP-64, so
  34.14 keeps its Boundary ("change only what `__default__` sums").

**Approach:**
- Give the three datasets the AD-13 last-good degrade Story 34.12 gave `VulnerabilityFeedDataset`: with `filepath`,
  a good load keeps its frame as `<filepath>/last_good.parquet` and removes `.staleness.json`; a fetch that fails, a
  body that cannot be read, or a body that parses to no rows serves the copy (on a fresh root, the empty frame of the
  dataset's columns) under the marker and never raises. A copy with other columns or no rows is set aside, never
  served; a filesystem error on the copy or the marker is logged, never raised. One private base in `core_sources.py`
  carries the pattern for the three; `VulnerabilityFeedDataset` stays as it is.
- Without `filepath` (the fixtures in `tests/unit/datasets/test_core_sources.py`) each dataset loads and fails as
  before, the way `CfGraphTarballDataset` does.
- `CondaRepodataDataset` keeps its per-subdir rule for a body that is not a JSON object (skipped, logged); a fetch
  failure on any subdir serves the whole copy, so a partial universe never replaces last-good.
- `feedstocks`, a list per row, reads back from the copy as a list, so Phase B.5's `_pick_feedstock` reads the copy
  as it reads a fresh frame.
- The three catalog entries gain `filepath: ${globals:paths.data_root}/raw/<entry>`, so the bootstrap-index-health
  board reads each marker and the Pages job's `data/raw` cache (Story 37.12) keeps each copy. Provenance reports the
  copy's age and the marker's reason, as it does for the vulnerability feeds.
- Prove the run: the integration test Story 34.14 adds runs `__default__` a second time over the root its first run
  filled, with every fetch refused.
- A `fix` under CAP-64: no CAP is minted and no flag is added (`spec-feature-flag-governance` Q1).

Ledger key: `34-15-the-three-core-sources-keep-last-good-when-the-network-is-refused`. Type / Effort / Deps:
fix / M / 34.14.

## Acceptance Criteria

- **AC1 — Each keeps last-good.** For each of `FeedstockOutputsArchiveDataset`, `CondaRepodataDataset` and
  `PyPISimpleIndexDataset` with `filepath` set and a copy on disk: a connect failure, an HTTP error, a body that
  cannot be read, and a body that parses to no rows each return the copy, write `.staleness.json` with `stale` true,
  `last_good_exists` true and a reason that names the failure and "keeping last-good", and raise nothing.
- **AC2 — A fresh root.** With no copy, the same failures return the empty frame of the dataset's columns under the
  marker with `last_good_exists` false.
- **AC3 — A good load.** A good fetch returns its frame, writes it as `last_good.parquet` and removes the marker;
  `feedstocks` reads back from the copy as a list per row; a copy whose columns differ or that holds no rows is set
  aside, never served; a filesystem error on the copy or the marker is logged and the load goes on.
- **AC4 — Fixtures unchanged.** Without `filepath` each dataset loads, skips and raises as before; the existing tests
  in `src/shared/packages/pyforge-atlas/tests/unit/datasets/test_core_sources.py` pass unchanged.
- **AC5 — The catalog.** `core_feedstock_outputs_raw`, `core_repodata_raw` and `pypi_simple_index_raw` in
  `conf/base/catalog.yml` carry `filepath: ${globals:paths.data_root}/raw/<entry>`; `kedro-catalog-check` passes, and
  the bootstrap-index-health board reads each entry `stale` with the marker's reason after a degraded load.
- **AC6 — Provenance.** A fresh fetch resolves `live-fetch`; a degraded load resolves the copy's `file-mtime` with a
  reason starting `stale: `.
- **AC7 — The network-refused run.** Over the root Story 34.14's AC2 run filled, a second run of `__default__` with
  every fetch refused (requests and subprocesses), under the socket guard in `tests/conftest.py`, exits 0, and every
  store that held `last_good.parquet` after the first run, these three and the three vulnerability feeds among them,
  holds the same file under `.staleness.json` with `stale` and `last_good_exists` true.
- **AC8 — Mutation.** AC1 and AC7 each fail when the degrade is taken out (the base's load raises as the fixture path
  does).
- **AC9 — Records.** `pixi run --frozen -e pyforge-atlas pyforge-atlas-test` passes; ruff and mypy pass for the atlas
  package.

## Boundaries & Constraints

**Always:**
- Fetches still compose `kedro_datasets.api.APIDataset`; the no-inline-IO denylist does not change (AD-2).
- Keep every test network-free (recorded responses, the socket guard; AD-11).

**Never:**
- Never change what `__default__` sums (Story 34.14's), `VulnerabilityFeedDataset`, `CfGraphTarballDataset` or any
  other dataset's degrade; never add a flag or a CAP; never change a parser's output columns.

</intent-contract>

## Binding

- Parent capability: `spec-pyforge-atlas` CAP-64 (FR-72): the network-blocked run clause of its success. No CAP is
  minted.

Parent: `spec-pyforge-atlas` CAP-64

- Audit findings carried: ATL-D-R2, ATL-D-C3, the network-blocked clause (EGM audit 2026-11-01, cluster ATL-K2;
  `_bmad-output/projects/pyforge-atlas/planning-artifacts/research/egm-audit-2026-11-01.md`), with Story 34.14.
- Ruling: session owner, 2026-11-01 (Story 34.14's AC3 moves here; 34.14 is amended in place).
- Dream: `docs/dreams/pyforge-atlas.md` § *Realization log*, 2026-10-18 (atlas fills its own data).
- Epic 34 (reopened by Story 34.14 under doctor Story 41.5's rule).
- Ledger key: `34-15-the-three-core-sources-keep-last-good-when-the-network-is-refused`.
- Deps: 34.14 (its registry change and its run test's first run).
- Surface: `src/shared/packages/pyforge-atlas/src/pyforge/atlas/datasets/core_sources.py`,
  `src/shared/packages/pyforge-atlas/src/pyforge/atlas/datasets/__init__.py`,
  `src/shared/packages/pyforge-atlas/src/pyforge/atlas/provenance.py`,
  `src/shared/packages/pyforge-atlas/conf/base/catalog.yml` (the three entries),
  `src/shared/packages/pyforge-atlas/tests/unit/datasets/test_core_sources_last_good.py` (new),
  `src/shared/packages/pyforge-atlas/tests/unit/test_vizro_static_boards.py` (the three classes join the last-good
  types the Pages job's cache covers, Story 37.12),
  `src/shared/packages/pyforge-atlas/tests/integration/test_plain_run_fresh_root.py` (the network-refused run).
- Minted 2026-11-01 in the EGM audit's landing worktree; the landing PR reconciles spec-surface on
  `spec-pyforge-atlas` and its co-governor `spec-pyforge-core`.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-atlas pyforge-atlas-test` — expected: pass (the station's `verify_commands`; AC9).
- `pixi run --frozen -e pyforge-atlas pytest src/shared/packages/pyforge-atlas/tests/unit/datasets/test_core_sources_last_good.py src/shared/packages/pyforge-atlas/tests/unit/datasets/test_core_sources.py -q` — expected: pass (AC1-AC6).
- `pixi run --frozen -e pyforge-atlas pytest src/shared/packages/pyforge-atlas/tests/integration/test_plain_run_fresh_root.py -q` — expected: pass (AC7).
- `pixi run --frozen -e pyforge-atlas kedro-catalog-check` — expected: pass (AC5).
- `pixi run --frozen -e pyforge-guild lint-types` — expected: exit 0 (AC9).

**Run before the push:** AC8's mutation (the base's load raises instead of degrading) and the two named test files
fail; revert.

## Auto Run Result

Status: in-review (built 2026-11-01 in the landing worktree `egm-audit-2026-11`, after Story 34.14's registry change;
not committed).

**What changed:**
- `src/shared/packages/pyforge-atlas/src/pyforge/atlas/datasets/core_sources.py`: a new `LastGoodFrameDataset` base
  carries Story 34.12's pattern for frames: `filepath` is the source's directory; a good load writes
  `last_good.parquet` (`atomic_write_bytes`) and removes `.staleness.json`; a fetch failure ("fetch failed"), a body
  a parser rejects ("body unreadable", with a traceback logged for an error outside the body-error tuple), a body
  with no rows ("body holds no rows") or a frame Parquet cannot hold serves the copy, or on a fresh root the empty
  frame of `COLUMNS`, under the marker, and never raises; a copy with other columns or no rows is renamed
  `.last_good.parquet.rejected`; `LIST_COLUMNS` are turned back into lists on read; an `OSError` on the copy, the
  marker or the rename is logged. Without `filepath` a load is `_parse(_fetch())`, raising as before.
  `FeedstockOutputsArchiveDataset` (`COLUMNS` `conda_name`, `feedstocks`; `feedstocks` a list column),
  `CondaRepodataDataset` (`conda_name`, `version`, `timestamp`, `subdir`) and `PyPISimpleIndexDataset` (`pypi_name`,
  `last_serial`) now subclass it, each with an optional `filepath`; their parsers and output columns are unchanged.
  `CondaRepodataDataset._fetch` still flattens each subdir as it arrives (one payload held at a time) and still skips
  a subdir whose body is not a JSON object; a failed fetch of any subdir serves the whole copy. `_HttpBytesDataset`,
  whose one user was `FeedstockOutputsArchiveDataset`, is removed. `VulnerabilityFeedDataset` is untouched: its tests
  patch `vulnerability_feeds.atomic_write`, so moving its methods onto the new base would have changed them.
- `src/shared/packages/pyforge-atlas/src/pyforge/atlas/datasets/__init__.py`: exports `LastGoodFrameDataset`.
- `src/shared/packages/pyforge-atlas/src/pyforge/atlas/provenance.py`: `LastGoodFrameDataset` joins the marked
  classes, so a fresh fetch reads `live-fetch` and a served copy its mtime with `stale: <reason>` (AC6).
- `src/shared/packages/pyforge-atlas/conf/base/catalog.yml`: `core_repodata_raw`, `core_feedstock_outputs_raw` and
  `pypi_simple_index_raw` gain `filepath: ${globals:paths.data_root}/raw/<entry>` with a Story 34.15 comment (AC5).
- `src/shared/packages/pyforge-atlas/tests/unit/datasets/test_core_sources_last_good.py` (new): each of the three over
  a connect failure, an HTTP 503, a malformed body and a body with no rows, with a copy (AC1) and on a fresh root
  (AC2); a good load after a failure; the fixture path raising `DatasetError` (AC4); `feedstocks` read back as lists
  and Phase B.5's `attribute_feedstocks` giving the same answer on the copy as on the fresh frame; a repodata subdir
  failure serving the whole copy; an unusable copy set aside; refused writes; a frame Parquet cannot hold; a parser
  bug logged with its traceback; provenance (AC6); each catalog path under the data root and the
  bootstrap-index-health board reading each entry `stale` with the marker's reason (AC5).
- `src/shared/packages/pyforge-atlas/tests/unit/test_vizro_static_boards.py`: the three classes join
  `LAST_GOOD_TYPES` (Story 37.12's record of the raw classes whose copies the Pages job's `data/raw` cache keeps);
  the test that reads it went red when the three entries gained a `filepath` under `data/raw/`.
- `src/shared/packages/pyforge-atlas/tests/integration/test_plain_run_fresh_root.py` (Story 34.14's file):
  `test_a_second_run_with_every_fetch_refused_keeps_last_good` runs `__default__` over a fresh root with recorded
  responses, records every `raw/*/last_good.parquet` (these three and the three vulnerability feeds among them),
  refuses every request, runs again, and asserts the second run made refused requests, finished, and left every
  recorded copy byte-identical under a marker with `stale` and `last_good_exists` true; live off and on (AC7).
- `live-sources.md` is not edited: it lists the Epic 34 sources, and these three predate Epic 34 (as the
  vulnerability feeds did when Story 34.12 added their row). The CAP-64 memlog event records the behaviour for the
  next re-derive.

**Commands** (each from the worktree root; exit codes read from `$?`, never through a pipe):
- `pixi run --frozen -e pyforge-atlas pytest src/shared/packages/pyforge-atlas/tests/unit/datasets/test_core_sources_last_good.py src/shared/packages/pyforge-atlas/tests/unit/datasets/test_core_sources.py -q`: exit 0 (73 passed) (AC1-AC6).
- `pixi run --frozen -e pyforge-atlas pytest src/shared/packages/pyforge-atlas/tests/integration/test_plain_run_fresh_root.py -q`: exit 0 (4 passed) (AC7).
- `pixi run --frozen -e pyforge-atlas pytest src/shared/packages/pyforge-atlas/tests/unit/test_retrofit_flags.py src/shared/packages/pyforge-atlas/tests/unit/test_vizro_static_boards.py src/shared/packages/pyforge-atlas/tests/unit/datasets/test_vulnerability_feeds.py -q`: exit 0 (107 passed).
- `pixi run --frozen -e pyforge-atlas kedro-catalog-check`: exit 0 (71 passed) (AC5).
- `TMPDIR=$HOME/.cache/pyforge-preflight-tmp pixi run --frozen -e pyforge-atlas pyforge-atlas-test`: exit 0
  (3316 passed, 17 skipped / 221 passed, 1 skipped / 103 passed) (AC9).
- `pixi run --frozen -e pyforge-guild lint-types`: exit 0; the atlas mypy slice alone: exit 0, 150 files (AC9).
- Touched-module unit coverage from `.steward/coverage/atlas-unit.json`: `datasets/core_sources.py` 91.5%,
  `provenance.py` 96.4% (floor 80%).
- AC8 mutation, as a scratch pytest plugin (`-p atlas_mutant`, the tree never edited) that gives each of the three
  classes a `load` which keeps a good frame's copy but raises on any failure (kedro wraps each subclass's `load` at
  class creation, so each class is patched): exit 1, 27 unit cases and both network-refused integration cases fail,
  the run stopping with `DatasetError: core_feedstock_outputs_raw: Failed to connect to the remote server`; the
  fixture-path and parser tests pass, as they should.
- `pixi run --frozen -e pyforge-guild python _bmad/scripts/bmad_tea_playwright.py --project pyforge-atlas`, then
  `... --check`: exit 0 / exit 0 (160 story ids, 190 test files).

## Spec Change Log

- 2026-11-01: minted by the session owner's ruling of 2026-11-01 from Story 34.14's AC3, which could not be met
  inside 34.14's Boundary (its Auto Run Result names these three datasets as the whole gap); a fix under CAP-64
  (FR-72) with no new CAP and no flag.
- 2026-11-01: built; status `ready-for-dev` -> `in-review` (Auto Run Result above). The Surface names
  `src/shared/packages/pyforge-atlas/tests/unit/test_vizro_static_boards.py`, which the catalog change reaches.

## Review Triage Log

- 2026-11-01 (independent reviewer): **pass**; status `in-review` -> `done`. Judged against this spec's ACs and
  Boundaries, from `git diff HEAD` of `core_sources.py`, `datasets/__init__.py`, `provenance.py`,
  `conf/base/catalog.yml` and `test_vizro_static_boards.py`, and the new
  `tests/unit/datasets/test_core_sources_last_good.py` and `tests/integration/test_plain_run_fresh_root.py` read in
  full; the Auto Run Result was not taken as evidence.
  - AC1: `LastGoodFrameDataset.load` with `filepath` turns a fetch failure, a parser error, a body with no rows and a
    frame Parquet cannot hold into `_degrade`, which serves the copy under `.staleness.json` (`stale` true,
    `last_good_exists` true, reason `<failure> -- keeping last-good[: detail]`) and raises nothing. Tests cover a
    connect failure, an HTTP 503, a malformed body and a no-rows body for each of the three. For repodata and the
    PyPI simple index a malformed body parses to no rows, so its reason reads "body holds no rows"; that is the
    parsers' unchanged behaviour, which the Never boundary keeps. Met.
  - AC2: on a fresh root each of the four failures returns the empty frame of `COLUMNS` with `last_good_exists`
    false. Met.
  - AC3: a good load writes `last_good.parquet` (`atomic_write_bytes`) and removes the marker; `feedstocks` is read
    back as lists and Phase B.5's `attribute_feedstocks` gives the same answer on the copy as on the fresh frame;
    a copy that is garbage, has other columns or holds no rows is renamed `.last_good.parquet.rejected`, never
    served; refused `atomic_write`/`atomic_write_bytes` never fail the load. Met.
  - AC4: without `filepath` a load is `_parse(_fetch())` and a refused fetch raises `DatasetError`; the existing
    `test_core_sources.py` passes unchanged (not in the diff). Met.
  - AC5: the three catalog entries carry `filepath: ${globals:paths.data_root}/raw/<entry>`; `kedro-catalog-check`
    exit 0; the index-health board test reads each entry `stale` with the marker's reason. Met.
  - AC6: `LastGoodFrameDataset` joins provenance's marked classes; the test reads `live-fetch`, then `file-mtime`
    with `stale: fetch failed -- keeping last-good`. Met.
  - AC7: `test_a_second_run_with_every_fetch_refused_keeps_last_good` (live off and on) refuses every request and
    subprocess under the socket guard, finishes, and asserts each `raw/*/last_good.parquet` is byte-identical under
    a `stale`, `last_good_exists` marker. Reviewer check that the glob is the whole set: after the first run the
    data root held exactly six `last_good.parquet` files (these three and the three vulnerability feeds), none
    outside `raw/`. Met.
  - AC8: reviewer's own in-memory mutations (a scratch `-p` pytest plugin; the tree was never edited):
    `LastGoodFrameDataset._degrade` raising `DatasetError` fails 27 unit cases and both network-refused integration
    cases, exit 1, while the fixture-path tests pass; `FeedstockOutputsArchiveDataset.LIST_COLUMNS = ()` fails the
    list read-back test, exit 1. Met.
  - AC9: `TMPDIR=$HOME/.cache/pyforge-preflight-tmp pixi run --frozen -e pyforge-atlas pyforge-atlas-test` exit 0
    (3316 passed, 17 skipped / 221 passed, 1 skipped / 103 passed); package ruff over the touched files from the
    package dir exit 0 / format exit 0; `pixi run --frozen -e pyforge-guild python scripts/lint_types.py ruff`
    exit 0; `pixi run --frozen -e pyforge-guild lint-types` exit 0 (atlas mypy ok). Met.
  - Boundaries: fetches still compose `APIDataset`; `VulnerabilityFeedDataset`, `CfGraphTarballDataset` and
    `__default__` untouched by this story's diff; parser output columns unchanged; no flag, no CAP; every test is
    network-free. `_HttpBytesDataset` is removed; nothing else in `src/` referenced it.
  - Commands, exit codes read from `$?`: the Verification pytest pair, run with `test_pipeline_inventory.py`,
    `test_definitions_dryrun.py`, `test_retrofit_flags.py` and `test_vizro_static_boards.py`: exit 0 (167 passed);
    the integration file: exit 0 (4 passed); touched-module coverage `datasets/core_sources.py` 91.5%,
    `provenance.py` 96.4%.
  - Failures: none.
  - Observations, not failures: a repodata subdir that answers 200 with a body that is not a JSON object is still
    skipped, so a partial universe can replace last-good in that case (the Approach keeps that per-subdir rule); if
    removing the marker fails on a good load, the old marker outlives the fresh frame and provenance reads it stale
    (logged). The epics Status line and the ledger key still read `backlog`; the session owner promotes them.
- 2026-11-01 (independent reviewer, review follow-up atlas-35.5+34.15): **pass**; status stays `done`. Judged from
  `git diff HEAD` of `datasets/core_sources.py`, `datasets/credentials.py`,
  `tests/unit/datasets/test_core_sources_last_good.py`, this spec, spec-35-5 and the `spec-pyforge-atlas` memlog,
  against the task and this spec's ACs and Boundaries; the implementer's Dev Notes were not taken as evidence.
  - Point 1 (Story 35.5): the `credentials.py` module docstring now names the flag-off exception: the legacy VCS host
    and registry branch (`vcs_sources._request_kwargs`) reads `PYFORGE_ATLAS_CREDENTIALED`, so the catalog
    credential rides only with the switch, and without it the request carries `public_sources.request_args` (no
    credential, the no-op auth that keeps `~/.netrc` out). Matches the code; docstring only. Met.
  - Point 2 (this story): with `filepath`, `CondaRepodataDataset._fetch` raises `ValueError` for a subdir whose 200
    body `_api_json` rejects (non-JSON, or JSON that is not an object), so `LastGoodFrameDataset.load` takes it in
    its `_fetch` except as `fetch failed` and serves the whole copy under the marker; without `filepath` the subdir is
    still skipped and logged (AC4). The class docstring follows. Met.
  - Test that fails without the change: reviewer's own in-memory mutants (a scratch `-p` pytest plugin; the tree was
    never edited). Restoring the skip with `filepath` fails 3 cases, exit 1: both cases of
    `test_a_repodata_subdir_that_answers_200_with_no_json_object_serves_the_whole_copy` (a 1-row partial frame
    replaced the 2-row copy) and `test_a_malformed_or_empty_body_keeps_the_last_good_copy[repodata]`. Raising without
    `filepath` too fails `test_core_sources.py::test_conda_repodata_dataset_skips_non_dict_payload`, exit 1, so the
    fixture gate is pinned. Met.
  - Dev note on this spec: present, and spec-35-5 carries its own. The memlog entry names both governed paths;
    `python -m pyforge.doctor.sources spec-surface` exit 0 with no atlas finding.
  - Commands, exit codes read from `$?`: the two `test_core_sources*` files plus `test_credentialed_switch.py` exit 0
    (131 passed); `COVERAGE_FILE=<scratch> TMPDIR=$HOME/.cache/pyforge-preflight-tmp pixi run --frozen -e
    pyforge-atlas pyforge-atlas-test` exit 0 (3318 passed, 17 skipped / 221 passed, 1 skipped / 103 passed); from the
    package dir with the pyforge-guild binaries, `ruff check src tests` exit 0, `ruff format --check src tests` exit
    0, `mypy -p pyforge.atlas` exit 0 (150 files).
  - Scope: no other atlas source, test or planning file changed; the other dirty paths in this worktree carry earlier
    mtimes or other stations' follow-ups.
  - Failures: none.
  - Observations, not failures: the Approach line "keeps its per-subdir rule ... (skipped, logged)" now holds only
    without `filepath`; the Dev Note records the change, and no Spec Change Log line does. A bare `ruff check .` /
    `ruff format --check .` from the package dir exits 1 on `tools/live_artifactory_transport.py` (I001) and
    `wasm/build.py` (format). Neither file is in this diff, and both are outside the lint-types `src tests` trees.
    `credentials.py`'s "one exception" holds for `live_vcs_universe`; Basilisk and identity read the switch under
    their own flags.

## Dev Notes

- Review follow-up 2026-11-01 (the independent review's first observation, EGM audit): a repodata subdir that
  answered 200 with a body that is not a JSON object was skipped, so the subdirs that did answer could replace
  `last_good.parquet` with a partial universe. With `filepath`, `CondaRepodataDataset._fetch` now raises `ValueError`
  for that subdir, so `LastGoodFrameDataset.load` takes it as a failed fetch, the way it takes a refused one: the
  whole copy is served under `.staleness.json` with the reason `fetch failed -- keeping last-good: ValueError: subdir
  <subdir> current_repodata.json is not a JSON object`. Without `filepath` (fixtures) the subdir is still skipped, so
  AC4 holds and `test_conda_repodata_dataset_skips_non_dict_payload` passes unchanged. This replaces the Approach's
  per-subdir skip rule for the `filepath` case. `tests/unit/datasets/test_core_sources_last_good.py` gains
  `test_a_repodata_subdir_that_answers_200_with_no_json_object_serves_the_whole_copy` (a gateway page and a JSON
  list), and the repodata row of `SOURCES` now expects the `fetch failed` verdict for a malformed body. A scratch
  mutant that restores the skip with `filepath` fails three cases: both new cases and the repodata malformed case.
  Commands (exit codes read from `$?`): the two `test_core_sources*` files plus `test_credentialed_switch.py` exit 0
  (131 passed); `COVERAGE_FILE=<scratch> TMPDIR=$HOME/.cache/pyforge-preflight-tmp pixi run --frozen -e pyforge-atlas
  pyforge-atlas-test` exits 0 (3318 passed and 17 skipped, 221 passed and 1 skipped, 103 passed); ruff check and
  format over the atlas package and `mypy -p pyforge.atlas` exit 0 (150 files). Still open, not this follow-up: a
  subdir that answers with a JSON object holding no packages still adds no rows without failing the load.
