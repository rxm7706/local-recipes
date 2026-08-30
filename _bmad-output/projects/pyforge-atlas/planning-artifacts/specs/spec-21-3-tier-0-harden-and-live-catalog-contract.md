---
title: 'Tier 0 harden and --live-catalog contract (Story 21.3, Epic 21)'
type: 'feature'
created: '2026-08-30'
status: 'done'
followup_review_recommended: true
baseline_revision: e631a46a33a58782619645063ea9e9113057d2a8
context:
  - '{project-root}/_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-atlas-kedro-catalog-expansion/SPEC.md'
  - '{project-root}/_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-atlas-kedro-catalog-expansion/verification-matrix.md'
  - '{project-root}/_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-atlas-kedro-catalog-expansion/catalog-sources.md'
  - '{project-root}/_bmad-output/projects/pyforge-atlas/implementation-artifacts/epic-21-context.md'
warnings: []
review_loop_iteration: 1
deferred:
  - summary: >-
      pypi_conda_mapping.parquet's conda_name restriction to enumerated conda
      packages (map_pypi_conda) is not re-applied by match_source_urls()'s
      recipe_source_url tier, so "conda_name is a subset of cf_packages" is not
      strictly true for every row of the final persisted dataset.
    evidence: |-
      Read src/shared/packages/pyforge-atlas/src/pyforge/atlas/pipelines/pypi_intelligence/nodes.py
      L96-136 (match_source_urls): recipe_source_url-tier rows are appended from
      pypi_json_raw without re-checking core_packages_enumerated membership.
      Doesn't change the pypi_name-column decision (independently justified by
      load_parselmouth_pypi_names' pre-existing semantics and the intent's own
      downstream-unchanged-shape requirement), but the code comment justifying
      that decision should not overclaim the subset property universally.
    location: >-
      src/shared/packages/pyforge-atlas/src/pyforge/atlas/pipelines/pypi_intelligence/nodes.py:96-136
    severity: low
  - summary: >-
      When --live-catalog degrades pypi_index to empty (no -only) and
      --verify-mode strict is set, main() falls through to the pre-existing
      per-package pypi_exists() live-HTTP path, in tension with --live-catalog's
      "no duplicate HTTP clients" framing; cf_packages' degrade path has no
      equivalent live-HTTP fallback, so the I/O matrix's "mirrors the
      conda-forge row exactly" claim doesn't fully hold at the
      downstream-consumption level.
    evidence: |-
      Pre-existing mechanism (scripts/conda-forge-packaging-inventory-operations_metrics.py,
      the `if pypi_index: ... elif args.verify_mode == "strict": pypi_exists(...)`
      block), not modified by this story, but --live-catalog is a new way to
      reach it. Confirmed independently by three review layers (blind hunter,
      edge case hunter, intent-alignment auditor).
    location: >-
      scripts/conda-forge-packaging-inventory-operations_metrics.py (pypi_verified loop)
    severity: medium
  - summary: >-
      --strict-fetch has no effect on the three --live-catalog-acquired sets
      (they bypass try_source entirely); --live-catalog-only is the intentional
      analog for this path, but the interaction is undocumented.
    evidence: |-
      Confirmed --strict-fetch exists (argparse) and is checked inside
      try_source() and one other call site, but load_live_catalog()'s three
      acquisitions never call try_source and never check args.strict_fetch.
    location: >-
      scripts/conda-forge-packaging-inventory-operations_metrics.py (main(), live_catalog branch)
    severity: low
  - summary: >-
      load_live_catalog()'s except Exception blocks store only str(exc), no
      traceback -- a genuine bug (e.g. a future Kedro column rename) would look
      identical in the printed warning to an expected degrade (missing file /
      sub-floor count).
    evidence: |-
      Direct read of the (reverted, to-be-re-derived) loader's exception
      handling shape; applies to whatever the re-derived equivalent looks like.
    location: >-
      scripts/conda-forge-packaging-inventory-operations_metrics.py (load_live_catalog)
    severity: low
  - summary: >-
      --help/replay wording says "missing, unreadable, or below its scale
      floor" applies uniformly to "the three required datasets," but
      pypi_conda_mapping has no floor -- could mislead debugging of a
      --live-catalog-only failure on that dataset.
    evidence: |-
      Boundaries & Constraints (this spec) explicitly documents no floor for
      pypi_conda_mapping; the planned --help/replay phrasing doesn't
      distinguish it from the two floored datasets.
    location: >-
      scripts/conda-forge-packaging-inventory-operations_metrics.py (--help text)
    severity: low
  - summary: >-
      --live-catalog's --help text names internal Python variables
      (cf_packages/pypi_index/parselmouth_pypi) rather than the user-facing
      concepts (conda-forge names / PyPI names / Parselmouth mapping) used
      elsewhere in the CLI's own output columns.
    evidence: |-
      Direct read of the planned --help description text vs. the CSV's
      PyPI_Verified/CondaForge_Verified column names. Note (review pass 2):
      the re-derived --help text already uses user-facing concepts, not
      internal variable names -- this item appears already resolved as a
      side effect of the re-derivation, left here as historical record
      rather than pruned (no un-defer mechanism in this workflow).
    location: >-
      scripts/conda-forge-packaging-inventory-operations_metrics.py (--help text)
    severity: low
  - summary: >-
      --live-catalog degrading cf_packages to empty (missing/sub-floor
      core_packages_enumerated.parquet, run without --live-catalog-only)
      makes every already-on-conda-forge AOSS package look "not on
      conda-forge" (cf_or_pm membership test), which poisons the AOSS-Free
      Mason-facing queue output (write_aoss_free_queue) -- documented
      elsewhere as a live/irreversible signal. Not a new code path (the
      aoss_free_candidates gate is pre-existing and unmodified by this
      story) and matches the story's own explicit degrade-and-continue
      design, but the consequence severity isn't called out anywhere in
      --help/replay.md; operators relying on the AOSS-Free queue should use
      --live-catalog-only.
    evidence: |-
      Read scripts/conda-forge-packaging-inventory-operations_metrics.py's
      aoss_free_candidates construction (gated on `pkg not in cf_or_pm`) and
      write_aoss_free_queue's own "live and irreversible" framing. Confirmed
      independently by one review layer (blind hunter, pass 2); not
      corroborated by other layers, but the underlying mechanism (cf_or_pm
      membership) is directly verifiable in the diff.
    location: >-
      scripts/conda-forge-packaging-inventory-operations_metrics.py (aoss_free_candidates / write_aoss_free_queue)
    severity: medium
  - summary: >-
      load_live_catalog()'s scale-floor check counts distinct raw
      pre-normalization values (non_null.nunique()), while the set actually
      returned and consumed downstream is deduplicated post-norm_pkg() --
      a column with many raw variants collapsing to the same normalized
      name could theoretically pass the floor with a materially smaller
      final set. Low real-world likelihood: conda-forge/PyPI catalog names
      are already close to normalized in the source Parquet.
    evidence: |-
      Direct read of load_live_catalog(): `distinct = non_null.nunique()`
      computed before `values = {norm_pkg(str(v)) for v in non_null}`.
      Corroborated by two independent review layers (blind hunter and
      intent-alignment auditor, pass 2), both rating it low-severity/likely
      inert.
    location: >-
      scripts/conda-forge-packaging-inventory-operations_metrics.py (load_live_catalog)
    severity: low
  - summary: >-
      The `subdirs = [s.strip() for s in args.repodata_subdirs.split(",")
      ...]` line was relocated (not behaviorally changed) by this story's
      diff and appears unused elsewhere in the file -- pre-existing
      dead/unused code unrelated to this story's purpose, surfaced
      incidentally by touching nearby lines.
    evidence: |-
      Blind hunter (review pass 2) noted the line is directly touched
      (moved) by this diff but never referenced elsewhere in the file;
      not independently re-verified beyond that report.
    location: >-
      scripts/conda-forge-packaging-inventory-operations_metrics.py (main(), subdirs)
    severity: low
---

<intent-contract>

## Intent

**Problem:** `scripts/conda-forge-packaging-inventory-operations_metrics.py` (the
legacy inventory-quartet runner — NOT part of the `pyforge-atlas` Kedro package)
computes `PyPI_Verified` and `CondaForge_Verified` from live HTTP fetches
(`parse_channeldata_url`, per-package `pypi_exists`) or ad-hoc local snapshot files
(`--cf-channeldata`, `--pypi-simple`, `--parselmouth`, defaulting to `/tmp/ext-src/…`),
duplicating verification work the `pyforge-atlas` Kedro `core`/`pypi_intelligence`
pipelines already do and persist as Parquet. Stories 21.1/21.2 landed the
self-contained Kedro data plane; `verification-matrix.md` (this story's
`spec_checkpoint`) specifies a `--live-catalog` contract so the quartet reads that
Parquet directly instead ("no duplicate HTTP clients when `--live-catalog` is set" —
Decision #8 in the dream, "Direct Parquet reads — no compatibility JSON shim").

**Approach:** Add `--live-catalog PATH` / `--live-catalog-only` to `metrics.py`.
When `--live-catalog` is set, the acquisition of exactly three verification sets —
`cf_packages` (conda-forge names), `pypi_index` (PyPI names), `parselmouth_pypi`
(conda names reachable via the Parselmouth PyPI↔conda mapping) — is replaced by
direct `pandas.read_parquet` reads of three **already-existing, already-populated**
Tier 0 outputs under `PATH` (confirmed live on this baseline:
`intermediate/core_packages_enumerated/core_packages_enumerated.parquet`, 34,098
rows; `intermediate/pypi_universe/pypi_universe.parquet`, 880,710 rows;
`primary/pypi_conda_mapping/pypi_conda_mapping.parquet`, 21,761 rows). Every other
acquisition path (Basilisk/AOSS/Anaconda/about/curated, all workbook parsing, CSV/MD
output shape) is untouched. Scale-sanity floors from `catalog-sources.md`
(conda-forge ~30,000+, PyPI simple index non-empty) are enforced as a loud failure,
not a warn-only path, per the doc's own rule ("sub-threshold = fail, not warn-only").

**Scope discipline (per `invoke_dev_with: "Thin metrics.py only; no Tier 1
fetches"`):** this story does **not** add new `catalog.yml` entries, dataset
classes, or pipeline nodes. The three Parquet outputs it reads already exist and
are regenerated by every `kedro run --pipeline core,pypi_intelligence` — no new
Kedro-side fetch/persistence work is required to satisfy this story's
`done_checkpoint`. See Boundaries & Constraints → Never for the explicit list of
`catalog-sources.md`'s broader Tier-0 "harden" items (AD-13 last-good persistence on
`CondaChanneldataDataset`/`PyPISimpleIndexDataset` themselves, `Source_Repository_URL`
derivation, feedstock-URL correction, `purl_associator_mappings_raw`/
`openteams_project_1_board_raw`) this story deliberately leaves for later stories,
and Design Notes for why.

## Boundaries & Constraints

**Always:**
- `--live-catalog` absent (the default): `metrics.py` behavior is byte-identical to
  today — no new import, no new file read, no output change. This is a hard
  regression guard, not a nice-to-have.
- `--live-catalog PATH` replaces the acquisition of exactly three sets — `cf_packages`,
  `pypi_index`, `parselmouth_pypi` — with `pandas.read_parquet` reads under `PATH`.
  Everything downstream (`source_sets`, `records`, `cf_or_pm`, `pypi_verified`, CSV
  columns, Markdown report sections, the `about:maintainer`/curated/OpenTeams/
  Basilisk/AOSS/Anaconda flows) is unchanged in shape and dict/set key names — only
  the acquisition of those three sets changes.
- `--cf-channeldata` / `--pypi-simple` / `--parselmouth` stay valid CLI flags (never
  removed — other call sites in the replay doc's execution modes don't pass
  `--live-catalog`) but are accepted-and-unused for the three sets above when
  `--live-catalog` is set; do not error on their presence.
- pandas/pyarrow import for the new Parquet-reading path is **lazy** (imported
  inside the new loader, not at module top) — the script's existing zero-external-
  dependency default path (stdlib-only: `argparse`/`csv`/`html`/`json`/`re`/`sys`/
  `urllib`/`xml.etree`/`zipfile`) stays intact for every invocation that does not
  pass `--live-catalog`. `pandas>=3.0.5` / `pyarrow>=24.0.0` are already declared
  under `[feature.local-recipes.dependencies]` in `pixi.toml` (verified on this
  baseline) — no `pixi.toml` change is needed.
- Scale floors (`catalog-sources.md` § Scale sanity gates, the two Tier-0-real
  rows only): `core_packages_enumerated.parquet` distinct `conda_name` count
  `>= 30_000`; `pypi_universe.parquet` distinct `pypi_name` count `>= 1`
  (non-empty). `pypi_conda_mapping.parquet` has no documented floor — existence +
  readability only.
- A missing file, an unreadable/corrupt Parquet file, or a sub-floor row count for
  one of the three datasets degrades **only that one set** to empty and appends one
  entry to the existing `warnings` list (same list/format `try_source` already
  populates, surfaced in the existing "Warnings (fallbacks used)" summary block) —
  the run still completes and still writes CSV/MD/prompt output, UNLESS
  `--live-catalog-only` is set.
- `--live-catalog-only` (only meaningful combined with `--live-catalog`): if ANY of
  the three required datasets is missing, unreadable, or below its floor, `main()`
  returns exit code `2` with a clear one-line stderr message identifying the
  dataset and the reason, **before** opening `--analysis-xlsx` or writing any
  output file — mirrors the existing top-of-`main()` pattern for missing
  `--analysis-xlsx`/`--openteams-tsv`/`--curated-config` (current lines 808-816).
- `--live-catalog-only` without `--live-catalog`: `main()` returns exit code `2`
  with a clear stderr message (argparse-level mutual-requirement, not a silent
  no-op).
- `docs/reference/conda-forge-packaging-inventory-operations_replay.md` is updated
  in the same change per the script's own "Prompt ↔ Script sync contract" docstring
  (`scripts/conda-forge-packaging-inventory-operations_metrics.py` lines 4-8): add
  a fourth execution-mode example (`--live-catalog`) alongside the three existing
  ones, and note under "Verification and classification" that `PyPI_Verified`/
  `CondaForge_Verified` may source from Kedro Parquet via `--live-catalog` instead
  of live HTTP/local snapshot files.
- This PR touches `scripts/`, `docs/reference/`, and a new `scripts/tests/` file —
  none under `recipes/` — so per `CLAUDE.md`'s always-on PR-gate rule, the PR needs
  `gh pr edit <n> --repo rxm7706/local-recipes --add-label maintenance`. `pixi.toml`
  is not touched by this story, so the `environment.yaml` sync check does not apply.

**Block If:** None — every acquisition/behavior choice below is resolved by this
spec, not left to a human decision at dev time.

**Never:**
- Do not add `purl_associator_mappings_raw` or `openteams_project_1_board_raw`
  catalog entries, datasets, or pipeline wiring. `catalog-sources.md`'s Tier 0
  table lists them as "exist today," but `grep -rn "purl_associator\|openteams"
  src/pyforge/atlas/ conf/` on this baseline returns **zero hits** — they do not
  exist yet. Building them is `SPEC.md` CAP-3 / Story 21.6 ("Phase D extends
  `upstream_discovery`"), not this story.
- Do not change `Source_Repository_URL` or `Conda-Forge_FeedStock_URL` derivation.
  `CondaChanneldataDataset`/`core_packages_enumerated` do not carry `dev_url`/
  `home`/`source_url` (only `conda_name`, `latest_version`, `subdirs`), and
  `PyPIJsonFanOutDataset`'s persisted frame (`_PYPI_JSON_FRAME_COLUMNS`,
  `src/pyforge/atlas/datasets/request_datasets.py` L67-84) has no `project_urls`
  column — `Source_Repository_URL` is not derivable from Tier 0 Parquet alone on
  this baseline. `metrics.py`'s existing `git_url_from_channeldata_meta()` /
  `--cf-channeldata` path and the literal `Conda-Forge_FeedStock_URL` template
  stay exactly as they are; `core_feedstock_attribution.parquet` is not read by
  `--live-catalog` in this story.
- Do not add Tier 1 scale gates (Basilisk non-zero, AOSS free ~1,000+, Anaconda
  main ~5,000+) — those catalog entries do not exist yet (`grep -in
  "basilisk_packages_raw\|aoss_free\|aoss_premium\|anaconda_main_channeldata"
  conf/base/catalog.yml` returns nothing on this baseline) and are Story 21.4's
  job (`invoke_dev_with: "no Tier 1 fetches"`).
- Do not add AD-13 last-good/staleness persistence to `CondaChanneldataDataset` /
  `PyPISimpleIndexDataset` themselves (`src/pyforge/atlas/datasets/core_sources.py`
  L375-404, L457-489 — currently plain live-fetch, `save()` raises
  `NotImplementedError`, no last-good store). `catalog-sources.md`'s Tier-0 table
  frames this as part of the epic's broader "harden live-first" aspiration, but
  it is not named in this story's own `done_checkpoint`, and it is not required
  for `--live-catalog` correctness — the derived Parquet this story reads
  (`core_packages_enumerated`, `pypi_universe`) already exists, is independently
  regenerated on every `core`/`pypi_intelligence` pipeline run, and does not
  depend on the raw dataset classes gaining their own persistence. Left as a
  documented candidate for a future story (see Design Notes).
- Do not merge `pypi_json_raw`'s persisted store into the `PyPI_Verified`
  computation. `pypi_universe.parquet` is the full PyPI Simple Index snapshot
  (backed by `pypi_simple_index_raw`) and is already a superset of any name
  `pypi_json_raw`'s targeted per-package fan-out could contribute; folding in a
  second Parquet source adds merge complexity with no verification-set benefit.
- Do not add a `pixi.toml` task for the new test file. No existing pixi task runs
  this script or its tests today (`grep -n
  "conda-forge-packaging-inventory-operations" pixi.toml` returns nothing); mirror
  the existing `.claude/skills/bmad-review/scripts/tests/test_word_metrics.py`
  precedent — a bare `tests/` dir next to `scripts/`, run directly with
  `python3 -m pytest scripts/tests/`.
- Do not change `write_csv`/`write_markdown`/`write_revised_prompt`'s column sets,
  section list, or the terminal `=== MASTER PROMPT V3.0 EXECUTION SUMMARY METRICS
  ===` block format — `--live-catalog` changes acquisition, not output shape.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|-----------------|
| No `--live-catalog` | Any invocation without the flag | Identical to pre-story behavior: `cf_packages`/`pypi_index`/`parselmouth_pypi` acquired via existing `try_source`/local-file/live-HTTP paths | Unchanged — existing `try_source` fallback/warning behavior |
| Fresh bootstrap, `--live-catalog` set, all 3 datasets present and above floor | `PATH` = a real `PYFORGE_ATLAS_DATA_ROOT` post-`pyforge-atlas-bootstrap` | `cf_packages`/`pypi_index`/`parselmouth_pypi` populated from Parquet; zero calls to `fetch_text`/`fetch_json`/`urllib.request` for these three sets; CSV/MD output otherwise identical in shape to a live-HTTP run | None — happy path |
| `core_packages_enumerated.parquet` missing | `PATH` exists but that file is absent | `cf_packages = set()`; one `warnings` entry naming the dataset and reason; run completes, writes output | Never raise; degrade + warn |
| `core_packages_enumerated.parquet` present, 12,000 rows (below 30,000 floor) | Sub-threshold row count | Same as "missing" — degrade `cf_packages` to empty + warn (per `catalog-sources.md`: sub-threshold = fail, not warn-only for the CHECK, but for the plain `--live-catalog` CLI path this is the documented degrade, not a crash) | Never raise; degrade + warn |
| Same sub-floor scenario, `--live-catalog-only` also set | Sub-threshold + fail-fast flag | `main()` returns `2` before opening the analysis workbook; stderr names the dataset, actual count, and floor | Exit 2, no partial output written |
| `pypi_universe.parquet` missing or empty | 0 rows or absent | `pypi_index = set()` + warning (bare `--live-catalog`) or exit 2 (`--live-catalog-only`) — mirrors the conda-forge row exactly | Never raise; degrade + warn, or fail fast under `-only` |
| `pypi_conda_mapping.parquet` missing or unreadable | Absent or corrupt | `parselmouth_pypi = set()` + warning, or exit 2 under `--live-catalog-only` (existence/readability check only — no row-count floor) | Never raise; degrade + warn, or fail fast under `-only` |
| `--live-catalog-only` without `--live-catalog` | Flag combination error | `main()` returns `2` with a clear stderr message | Fail fast, no workbook opened |
| `--live-catalog` set alongside `--cf-channeldata`/`--pypi-simple`/`--parselmouth` (their defaults or explicit paths) | Both old and new flags present | Old flags accepted, silently unused for the three replaced sets | No error, no double-fetch |

</intent-contract>

## Code Map

- `scripts/conda-forge-packaging-inventory-operations_metrics.py` — the file this
  story almost entirely lives in:
  - L1-26 imports (stdlib only today) — add a **lazy** `import pandas as pd` inside
    the new loader function, not here.
  - L768-806 `argparse` block — add `--live-catalog` (`type=Path`, `default=None`,
    `metavar="PATH"`) and `--live-catalog-only` (`action="store_true"`) here,
    alongside the existing `--pypi-simple`/`--cf-channeldata`/`--parselmouth`
    (L791-794).
  - L808-816 existing top-of-`main()` required-file validation (`--analysis-xlsx`/
    `--openteams-tsv`/`--curated-config`, `return 2` pattern) — insert the new
    `--live-catalog` load-and-floor-check call here, BEFORE `xlsx =
    XlsxReader(args.analysis_xlsx)` (L820), so a `--live-catalog-only` failure
    exits before any workbook I/O.
  - L848-853 `cf_packages = try_source("external:conda-forge-channel", …)` — when
    `--live-catalog` is set, replace this call's result with the pre-loaded Parquet
    set instead of invoking `try_source` (keep the `source_sets["external:conda-forge-channel"]
    = cf_packages` assignment immediately after, unchanged, so Markdown/CSV report
    keys are unaffected).
  - L909-913 `parselmouth_pypi = load_parselmouth_pypi_names(args.parselmouth)` /
    `pypi_index = load_pypi_simple_names(args.pypi_simple)` — same replacement
    pattern when `--live-catalog` is set.
  - `load_channeldata_names`/`parse_channeldata_url` (L436-437, L467-470),
    `load_pypi_simple_names` (L440-449), `load_parselmouth_pypi_names` (L452-464) —
    the functions being bypassed for these three sets under `--live-catalog`; do
    not modify their signatures or behavior (still used for the no-flag path).
  - `main()` docstring / `argparse.ArgumentParser(description=…)` (L764-767) —
    mention `--live-catalog` in the one-line description or `--help` epilog.
- `src/shared/packages/pyforge-atlas/conf/base/catalog.yml` L55-59
  (`core_channeldata_raw`), L176-180 (`pypi_simple_index_raw`), L285-289
  (`pypi_conda_mapping`) — **read-only reference**, confirms these Tier 0 entries
  and their downstream persisted outputs; this story does not edit `catalog.yml`.
- `src/shared/packages/pyforge-atlas/src/pyforge/atlas/pipelines/core/nodes.py`
  L50-95 `enumerate_conda_packages` — produces `core_packages_enumerated`
  (`conda_name`, `latest_version`, `subdirs`); confirms the exact column name
  (`conda_name`) this story's loader reads.
- `src/shared/packages/pyforge-atlas/src/pyforge/atlas/pipelines/pypi_intelligence/nodes.py`
  L143-159 `enumerate_pypi_universe` — produces `pypi_universe` (`pypi_name`,
  `last_serial`); confirms `pypi_name` as the read column.
- `src/shared/packages/pyforge-atlas/src/pyforge/atlas/pipelines/pypi_intelligence/pipeline.py`
  L55 — confirms `pypi_conda_mapping` (`pypi_name`, `conda_name`, `match_source`)
  is the persisted primary-layer output the Phase C mapping node writes.
- `src/shared/packages/pyforge-atlas/src/pyforge/atlas/pipelines/pypi_intelligence/nodes.py`
  `map_pypi_conda` (L57-89) — **corrected 2026-08-30 (review pass 1):** this node
  restricts `pypi_conda_mapping_base`'s `conda_name` to values already present in
  `core_packages_enumerated` (L83-87: "restrict to conda_names the core pipeline
  actually enumerated"). Reading `pypi_conda_mapping.parquet`'s `conda_name` column
  (as this spec originally instructed below) would therefore make `parselmouth_pypi`
  a strict subset of `cf_packages`, making the `cf_or_pm = cf_packages |
  parselmouth_pypi` union a no-op — defeating the entire point of adding the
  Parselmouth set. Note `match_source_urls()` (L96-136), which extends
  `pypi_conda_mapping_base` into the final persisted `pypi_conda_mapping` with
  `recipe_source_url`-tier rows sourced from `pypi_json_raw`, does **not**
  re-apply that `core_packages_enumerated` filter — so the "conda_name is a subset"
  property does not strictly hold for every row of the final dataset either. The
  loader must read the `pypi_name` column (see corrected Code Map entry and Tasks
  below), which reproduces the pre-existing `load_parselmouth_pypi_names()`
  semantics (a PyPI name whose Parselmouth mapping resolves to a — possibly
  differently-named — conda-forge package still counts as `CondaForge_Verified =
  Yes`; `docs/dreams/atlas-kedro-catalog-expansion.md`, "CondaForge Yes when PyPI
  name != conda name") and is what the Boundaries → Always "everything downstream
  unchanged in shape" rule requires.
- `docs/reference/conda-forge-packaging-inventory-operations_replay.md` — add the
  fourth execution-mode example + the verification-section note (see Boundaries →
  Always). **Corrected 2026-08-30 (review pass 1):** the new example MUST also pass
  `--cf-channeldata` pointing at a real snapshot. `--cf-channeldata` is not one of
  the three sets `--live-catalog` replaces — it is still read independently for
  `git_url_from_channeldata_meta()`/`has_src` (the `10kClosed`/`10kOpen` tab-drop
  filter, `main()` further down). Omitting `--cf-channeldata` from the example
  leaves `args.cf_channeldata` at its default (`/tmp/ext-src/cf-channeldata.json`,
  almost certainly absent), making `has_src` always `False` and silently changing
  which `10k`-tab rows get dropped compared to an HTTP-based run — a caveat a
  reader following the example verbatim would not discover. Also fix the example's
  prose: `PYFORGE_ATLAS_DATA_ROOT` is not auto-detected — `--live-catalog` is a
  plain `Path` argument the caller supplies explicitly; phrase it as "point
  `--live-catalog` at your `PYFORGE_ATLAS_DATA_ROOT`" rather than implying
  environment-variable auto-detection.
- `docs/reference/conda-forge-packaging-inventory-operations_prompt.md` — auto-
  regenerated by `write_revised_prompt()` (metrics.py L743-761). **Corrected
  2026-08-30 (review pass 1):** the "no manual edit needed" claim below was wrong —
  `write_revised_prompt()` is a hardcoded f-string template over a fixed, explicit
  list of `args.*` fields (`analysis_xlsx`, `openteams_tsv`, `curated_config`,
  `output_csv`, `output_md`, `output_revised_prompt`, `verify_mode`,
  `strict_max_live_checks`) — it does not dynamically echo every parsed argument, so
  it silently drops `--live-catalog`/`--live-catalog-only` today. The template DOES
  need a manual edit: append `--live-catalog "{args.live_catalog}" \` (only when
  `args.live_catalog is not None`) and `--live-catalog-only \` (only when
  `args.live_catalog_only` is set) to the generated command block, so a
  `--live-catalog` run without `--skip-revised-prompt` regenerates
  `conda-forge-packaging-inventory-operations_prompt.md` with a command that still
  matches how it was actually invoked.
- `scripts/tests/test_conda_forge_packaging_inventory_operations_metrics.py`
  (new) — mirrors the existing `.claude/skills/bmad-review/scripts/tests/
  test_word_metrics.py` convention (a bare `tests/` dir next to `scripts/`, no
  pixi task). Covers the I/O & Edge-Case Matrix rows above using small synthetic
  Parquet fixtures (e.g. via `pandas.DataFrame(...).to_parquet(...)` in a pytest
  `tmp_path`), not the real 34,098-row bootstrap output.

## Tasks & Acceptance

**Execution:**
- [ ] Add `--live-catalog PATH` / `--live-catalog-only` to the `argparse` block
  (L768-806). Validate the `-only`-without`--live-catalog` combination and return
  `2` with a clear message before any other work.
- [ ] Add a loader (e.g. `load_live_catalog(root: Path) -> LiveCatalogResult`, a
  small dataclass/tuple of `cf_packages: set[str]`, `pypi_index: set[str]`,
  `parselmouth_pypi: set[str]`, `warnings: list[str]`, `failed: list[str]`) that:
  - Lazily imports `pandas`.
  - Reads `root / "intermediate/core_packages_enumerated/core_packages_enumerated.parquet"`
    column `conda_name`; floor 30,000 distinct values.
  - Reads `root / "intermediate/pypi_universe/pypi_universe.parquet"` column
    `pypi_name`; floor 1 (non-empty).
  - Reads `root / "primary/pypi_conda_mapping/pypi_conda_mapping.parquet"` column
    `pypi_name` (drop nulls); no floor, existence/readability only. **Corrected
    2026-08-30 (review pass 1):** originally specified as `conda_name` — see the
    corrected Code Map entry for `map_pypi_conda`/`match_source_urls` above for why
    that was wrong.
  - For each: missing file / read exception / sub-floor → append that dataset's
    key to `failed`, append a one-line message to `warnings`, and use an empty set
    for that piece — never raise.
- [ ] Wire the loader into `main()` immediately after the existing L808-816
  required-file checks, before `xlsx = XlsxReader(...)` (L820). If
  `args.live_catalog_only` and `result.failed` is non-empty: print the message(s)
  to stderr and `return 2` immediately.
- [ ] Replace the L848-853 `cf_packages = try_source(...)` call and the L909-913
  `parselmouth_pypi`/`pypi_index` acquisition with the loader's results when
  `args.live_catalog` is set; keep every other line in that region (
  `source_sets["external:conda-forge-channel"] = cf_packages`, `cf_or_pm =
  cf_packages | parselmouth_pypi`, the `if not pypi_index: warnings.append(...)`
  guard for the no-flag path) unchanged in shape.
- [ ] Update the `--help` description to mention `--live-catalog`.
- [ ] Update `docs/reference/conda-forge-packaging-inventory-operations_replay.md`
  per the Prompt ↔ Script sync contract (new execution-mode example + verification
  note). The example MUST also pass `--cf-channeldata` (see corrected Code Map
  entry) and must not phrase `PYFORGE_ATLAS_DATA_ROOT` as auto-detected.
- [ ] Update `write_revised_prompt()` (metrics.py L834-851) to append
  `--live-catalog "{args.live_catalog}"` (when set) and `--live-catalog-only`
  (when set) to its generated command block, so a `--live-catalog` run without
  `--skip-revised-prompt` regenerates `..._prompt.md` accurately (see corrected
  Code Map entry).
- [ ] Add `scripts/tests/test_conda_forge_packaging_inventory_operations_metrics.py`
  covering every row of the I/O & Edge-Case Matrix with synthetic `tmp_path`
  Parquet fixtures, including an explicit assertion that no HTTP-fetch function
  (`fetch_text`/`fetch_json`/`urllib.request.urlopen`) is invoked for the three
  replaced sets when `--live-catalog` succeeds, and a regression test that
  omitting `--live-catalog` reaches the exact same `try_source`/local-file code
  path as before this story (e.g. via `unittest.mock.patch` asserting
  `try_source`/`load_pypi_simple_names`/`load_parselmouth_pypi_names` ARE called
  in that mode).
- [ ] Run `python3 -m pytest scripts/tests/` and confirm green.
- [ ] Once the PR is open, apply the `maintenance` label (`gh pr edit <n> --repo
  rxm7706/local-recipes --add-label maintenance`) — every changed file in this
  story sits outside `recipes/`.

**Acceptance Criteria:**
- Given `metrics.py` invoked with no `--live-catalog` flag, when run against the
  same fixture inputs as before this story, then output CSV/MD/prompt files and
  the terminal summary are byte-for-byte identical to the pre-story script (a
  golden-file or mocked-call-count regression test proves this).
- Given `--live-catalog PATH` pointing at a fixture root with all three required
  Parquet files present and above their floors, when `metrics.py` runs, then
  `CondaForge_Verified`/`PyPI_Verified` are computed from those files alone, and no
  HTTP fetch function is called for conda-forge-channel/PyPI-simple/Parselmouth
  acquisition.
- Given `--live-catalog PATH` with `core_packages_enumerated.parquet` either
  absent or below the 30,000-row floor, when `metrics.py` runs WITHOUT
  `--live-catalog-only`, then the run completes, `CondaForge_Verified` for
  affected packages degrades based on an empty conda-forge set, and a warning
  naming the dataset appears in the "Warnings (fallbacks used)" section.
- Given the same sub-floor/missing scenario WITH `--live-catalog-only`, when
  `metrics.py` runs, then it exits `2` before writing any output file, with a
  stderr message identifying the failing dataset.
- Given `--live-catalog-only` passed without `--live-catalog`, when `metrics.py`
  runs, then it exits `2` with a clear message.
- Given `pixi run -e local-recipes python3 scripts/conda-forge-packaging-inventory-operations_metrics.py
  --live-catalog src/shared/packages/pyforge-atlas/data …` against the real,
  already-bootstrapped local data root (34,098/880,710/21,761 rows respectively,
  confirmed present on this baseline), when run, then it completes successfully
  with zero scale-gate warnings.
- Given `python3 -m pytest scripts/tests/`, when run, then all new tests pass and
  no existing test in the repo regresses.

## Spec Change Log

- 2026-08-30: Initial draft, promoted from `stories.yaml` S-21.3 (`spec-atlas-
  kedro-catalog-expansion/SPEC.md` CAP-2/CAP-4, phase C0). Scope narrowed from
  `catalog-sources.md`'s full Tier-0 table (7 entries, including AD-13 hardening
  of the raw dataset classes and the not-yet-built `purl_associator_mappings_raw`/
  `openteams_project_1_board_raw`) to exactly what this story's own
  `done_checkpoint` and `invoke_dev_with` pin — `--live-catalog` reading the three
  Tier 0 outputs that already exist and are already populated on this baseline —
  after confirming via direct codebase investigation that the two PURL/OpenTeams
  entries do not exist yet (Story 21.6 territory) and that `Source_Repository_URL`
  is not derivable from Tier 0 Parquet alone today. See Design Notes for the
  candidate follow-up items this narrowing defers.
- 2026-08-30 (review pass 1, bad_spec repair): a first implementation pass (now
  reverted) surfaced three spec defects via adversarial review, all in this file's
  Code Map / Tasks & Acceptance — never in `<intent-contract>`, which is unchanged:
  1. **`pypi_conda_mapping.parquet` column.** Originally specified as `conda_name`;
     corrected to `pypi_name`. Root cause: `map_pypi_conda()` restricts
     `pypi_conda_mapping_base`'s `conda_name` to values already in
     `core_packages_enumerated`, so reading `conda_name` would make
     `parselmouth_pypi` a strict subset of `cf_packages`, making `cf_or_pm =
     cf_packages | parselmouth_pypi` a no-op. Known-bad state avoided: a
     `--live-catalog` run that silently fails to give any package credit for a
     PyPI-name-differs-from-conda-name Parselmouth match, defeating the set's
     purpose. **KEEP:** the reverted implementation's `load_live_catalog()` had
     already independently arrived at `pypi_name` (with a correct, verified inline
     rationale) — the re-derivation should reproduce that choice, now made
     explicit in the spec itself rather than left to independent re-derivation.
  2. **`write_revised_prompt()` claimed "no manual edit needed."** False —
     confirmed by direct read that it is a hardcoded f-string template, not
     dynamic over `args`. Corrected: added an explicit task to extend the
     template. Known-bad state avoided: a `--live-catalog` run (without
     `--skip-revised-prompt`) regenerating `..._prompt.md` with a command that
     silently omits the flags actually used.
  3. **replay.md's new example omitted `--cf-channeldata`.** `--cf-channeldata`
     is not one of the three sets `--live-catalog` replaces (it still drives
     `has_src`/the `10k`-tab-drop filter); corrected the Code Map/Tasks to require
     the example keep it, and to not phrase `PYFORGE_ATLAS_DATA_ROOT` as
     auto-detected. Known-bad state avoided: a reader following the example
     verbatim getting a different `10k`-tab drop outcome than an HTTP-based run,
     with no indication why.

  Deferred (not required for this story's `done_checkpoint`, tracked in
  frontmatter `deferred`): the `match_source_urls()` caveat on the "conda_name is
  a subset" property; the pre-existing `pypi_index`-empty + `--verify-mode strict`
  live-HTTP fallback interaction; `--strict-fetch` not applying to the
  `--live-catalog` path; unlabeled traceback loss in `load_live_catalog()`'s
  `except` blocks; `--help`/replay wording precision on the no-floor
  `pypi_conda_mapping` dataset and on internal variable-name exposure.

## Design Notes

**Why `core_packages_enumerated`/`pypi_universe`/`pypi_conda_mapping` instead of
the raw `core_channeldata_raw`/`pypi_simple_index_raw` catalog entries directly:**
the two raw dataset classes (`CondaChanneldataDataset`, `PyPISimpleIndexDataset` in
`core_sources.py`) have no `filepath:` in `catalog.yml` and no persistence at all
today (`save()` raises `NotImplementedError`) — they are pure live-fetch-on-`load()`
classes with nothing to read from disk. Their downstream, already-persisted
consumers (`core_packages_enumerated`, an intermediate `pandas.ParquetDataset`
recomputed on every `core` pipeline run; `pypi_universe`, an `IncrementalParquetDataset`
with a 7-day TTL upsert) carry exactly the fields (`conda_name`, `pypi_name`) this
story needs, are verified present and populated on this baseline (34,098 / 880,710
rows), and require zero new Kedro-side code. Decision #8 in the dream
("Direct Parquet reads — no compatibility JSON shim") is satisfied by reading
whatever Tier 0 Parquet already exists, not by inventing a new raw-layer snapshot.

**Deferred candidates for a later story** (not claimed as done here, listed so the
narrowing in the Spec Change Log is auditable): (1) AD-13 last-good/staleness
persistence on `CondaChanneldataDataset`/`PyPISimpleIndexDataset` themselves, so a
transient live-fetch failure during `kedro run --pipeline core` degrades instead of
failing the whole pipeline run — the natural reference pattern is the
`_ParquetRefreshStore` mixin (`src/pyforge/atlas/datasets/vcs_sources.py` L109-219,
already imported cross-module into `request_datasets.py` per Story 21.2's own
deferred-work note; a third consumer in `core_sources.py` would be a good trigger
to relocate it into `refresh.py` alongside `StalenessMarker`). (2) Extending
`channeldata_json_to_rows()` / `PyPIJsonFanOutDataset`'s persisted frame to carry
`dev_url`/`home`/`project_urls` so `Source_Repository_URL` becomes Parquet-derivable.
(3) Joining `core_feedstock_attribution.parquet` into `Conda-Forge_FeedStock_URL`
instead of the current literal `github.com/conda-forge/{pkg}-feedstock` template.

## Verification

**Commands:**
- `python3 -m pytest scripts/tests/` — expected: all new + existing tests pass.
- `pixi run -e local-recipes python3 scripts/conda-forge-packaging-inventory-operations_metrics.py --help`
  — expected: `--live-catalog`/`--live-catalog-only` listed.
- `pixi run -e local-recipes python3 scripts/conda-forge-packaging-inventory-operations_metrics.py
  --analysis-xlsx <existing fixture/workbook> --curated-config
  conf/conda-forge-packaging-inventory-operations_curated_groups.json
  --live-catalog src/shared/packages/pyforge-atlas/data --skip-revised-prompt`
  — expected: exit 0, zero live-catalog warnings (real local data root already
  clears every floor on this baseline).
- Same command with `--live-catalog /tmp/empty-does-not-exist --live-catalog-only`
  — expected: exit 2, no output file written.

## Review Triage Log

### 2026-08-30 — Review pass
- intent_gap: 0
- bad_spec: 3: (high 1, medium 2, low 0)
- patch: 1: (high 0, medium 0, low 1)
- defer: 6: (high 0, medium 2, low 4)
- reject: 6: (high 0, medium 1, low 5)
- addressed_findings:
  - `[high]` `[bad_spec]` `pypi_conda_mapping.parquet` loader column: Code
    Map/Tasks specified `conda_name`; corrected to `pypi_name`. Root cause:
    `map_pypi_conda()` restricts `pypi_conda_mapping_base`'s `conda_name` to
    values already in `core_packages_enumerated`, so `conda_name` would make
    `parselmouth_pypi` a strict, no-op subset of `cf_packages`. Code reverted;
    spec amended (Code Map, Tasks & Acceptance, Design Notes, Spec Change Log);
    re-derivation via step-03 to follow.
  - `[medium]` `[bad_spec]` `write_revised_prompt()`: Code Map claimed "no
    manual edit needed" — false, it's a hardcoded f-string template that never
    echoes `--live-catalog`/`--live-catalog-only`. Spec amended to add an
    explicit task extending the template.
  - `[medium]` `[bad_spec]` replay.md's new `--live-catalog` example omitted
    `--cf-channeldata`, which independently drives `has_src`/the `10k`-tab-drop
    filter and is not one of the three sets `--live-catalog` replaces. Spec
    amended to require the example retain it and to fix the
    `PYFORGE_ATLAS_DATA_ROOT` auto-detection-sounding phrasing.

### 2026-08-30 — Review pass 2
- intent_gap: 0
- bad_spec: 0
- patch: 4: (high 0, medium 2, low 2)
- defer: 3: (high 0, medium 1, low 2)
- reject: 7: (high 0, medium 0, low 7)
- addressed_findings:
  - `[medium]` `[patch]` `load_live_catalog()`'s `path.exists()` check sat
    outside the `try/except` wrapping the Parquet read — a `PermissionError`/
    `OSError` there would have propagated uncaught, violating the "never
    raises" contract. Moved inside the same `try/except`.
  - `[low]` `[patch]` `--live-catalog`'s `--help` text claimed
    `--cf-channeldata`/`--pypi-simple`/`--parselmouth` "stay accepted but
    unused" — inaccurate for `--cf-channeldata` (still drives `has_src`).
    Reworded to distinguish it from the two genuinely-unused flags.
  - `[low]` `[patch]` replay.md's `--live-catalog-only` prose didn't carry
    the "no floor for the Parselmouth mapping" caveat the `--help` text
    already states. Aligned the two.
  - `[medium]` `[patch]` `write_revised_prompt()`'s new
    `--live-catalog`/`--live-catalog-only` echo logic (landed in review pass
    1) had zero test coverage — every `main()`-level test hardcoded
    `--skip-revised-prompt`. Added
    `test_write_revised_prompt_echoes_live_catalog_flags`, which runs
    `main()` without that flag and asserts the regenerated prompt doc
    contains both flags.

  Patches applied directly (the review-pass-1 implementation subagent was
  not addressable via `SendMessage`/`ListAgents` in this session for
  re-engagement with context intact). Re-ran `python3 -m pytest scripts/tests/
  tests/packaging/test_openteams_handoffs.py` after applying: 32/32 pass.
  Re-verified `--help` output and the `--live-catalog-only` fail-fast exit-2
  command from this spec's `## Verification` section — both still pass.

## Auto Run Result

**Summary:** Implemented `--live-catalog PATH` / `--live-catalog-only` in
`scripts/conda-forge-packaging-inventory-operations_metrics.py`: when set, the
acquisition of `cf_packages`/`pypi_index`/`parselmouth_pypi` reads three
already-populated `pyforge-atlas` Kedro Tier 0 Parquet outputs directly
(`pandas.read_parquet`, lazily imported) instead of live HTTP fetches or
`--cf-channeldata`/`--pypi-simple`/`--parselmouth` local snapshots. Every other
acquisition path, and all downstream shape (CSV/MD columns, `source_sets`
keys, `cf_or_pm`), is unchanged. Two adversarial review passes ran: pass 1
found and corrected 3 spec defects (wrong Parquet column, an incorrect "no
edit needed" claim, an incomplete doc example) via a full revert + spec
amendment + re-derivation loop; pass 2 found and applied 4 direct code
patches on the re-derived implementation. `--live-catalog` absent remains
byte-identical to pre-story behavior (regression-guarded by a dedicated test).

**Files changed:**
- `scripts/conda-forge-packaging-inventory-operations_metrics.py` — `--live-catalog`/`--live-catalog-only` flags, `LiveCatalogResult` dataclass, `load_live_catalog()`, wiring into `main()`'s three acquisition sites, `write_revised_prompt()` flag echo.
- `docs/reference/conda-forge-packaging-inventory-operations_replay.md` — fourth execution-mode example (`--live-catalog`, retaining `--cf-channeldata`) + verification-section note, per the script's Prompt ↔ Script sync contract.
- `scripts/tests/test_conda_forge_packaging_inventory_operations_metrics.py` (new) — 16 tests covering every I/O & Edge-Case Matrix row plus the `write_revised_prompt()` echo path; no pixi task (spec Boundaries → Never, mirrors `test_word_metrics.py`).
- `_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-21-3-tier-0-harden-and-live-catalog-contract.md` — this spec, amended across both review passes (Code Map, Tasks & Acceptance, Design Notes, Spec Change Log, frontmatter `deferred`, Review Triage Log).

**Review findings breakdown:**
- Pass 1: 3 bad_spec (all repaired via spec amendment + revert + re-derivation), 1 patch (moot — superseded by re-derivation), 6 defer, 6 reject.
- Pass 2: 0 bad_spec/intent_gap, 4 patch (all applied directly), 3 new defer, 7 reject.
- Total deferred (frontmatter `deferred`, 9 items): `match_source_urls()` subset-claim caveat; pre-existing `--verify-mode strict` + degraded `pypi_index` live-HTTP fallback (medium, cross-confirmed by 3+ review layers across both passes); `--strict-fetch` not applying to `--live-catalog`; untraced exceptions in `load_live_catalog()`; two `--help`/replay wording-precision items (one likely already resolved by pass 2's re-derivation, left as historical record); AOSS-Free Mason-queue poisoning risk on a `cf_packages` degrade without `-only` (medium — the most operationally significant deferred item); pre/post-normalization floor-count discrepancy (low, likely inert); a relocated, pre-existing unused `subdirs` line (low).
- Rejected: everything that matched the spec's own explicit Boundaries text verbatim (no floor on `pypi_conda_mapping`, `pypi_universe` floor of 1, silent-but-warned degrade, unused-old-flags-no-error, `source_sets` key reuse), plus items resolved by pre-existing/unmodified code patterns or judged too low-impact to track (unescaped-quote path interpolation, empty-string `--live-catalog` path, pandas `ImportError` given it's a guaranteed pixi-env dependency, `nunique()` computed-but-unused for the unfloored dataset, marginal test-depth suggestions beyond the I/O matrix's own requirements).
- Follow-up review recommendation: **true** — pass 2's 4 patches score `3×2 (medium) + 1×2 (low) = 8 ≥ 5` (0 high-severity patches).

**Verification performed:**
- `python3 -m pytest scripts/tests/ tests/packaging/test_openteams_handoffs.py` — 32/32 pass (re-run after both the pass-1 re-derivation and the pass-2 patches).
- `--help` lists `--live-catalog`/`--live-catalog-only` with corrected, accurate wording.
- `--live-catalog /tmp/empty-does-not-exist --live-catalog-only` → exit 2, no output file written, before opening the analysis workbook (`XlsxReader` never instantiated) — re-verified after both implementation passes.
- Matrix Test Audit: all 9 I/O & Edge-Case Matrix rows covered by at least one test, all tests ran and passed, both passes.
- Could not run the spec's real-bootstrapped-data verification command (`--live-catalog src/shared/packages/pyforge-atlas/data` against the 34,098/880,710/21,761-row baseline) — this worktree has no bootstrapped `PYFORGE_ATLAS_DATA_ROOT`; synthetic-fixture tests exercise the identical code path.

**Residual risks:** see the 9 `deferred` frontmatter items. The most operationally significant is the AOSS-Free Mason-queue poisoning risk (medium) — an operator running `--live-catalog` without `--live-catalog-only` against a degraded/incomplete data root could push false "not on conda-forge" entries into a queue documented elsewhere as live/irreversible; mitigated today only by using `--live-catalog-only` in automation, not by any code-level guard.

