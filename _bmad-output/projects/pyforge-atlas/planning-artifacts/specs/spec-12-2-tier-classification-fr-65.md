---
title: 'Tier classification — join trending candidates against atlas signals (S-13.2, FR-65/CAP-2)'
type: 'feature'
created: '2026-08-09'
status: done
baseline_revision: '6c99ac4ae32ba679be856e417658d2663b64370c'
final_revision: 'd9a0796454192186b6017b0c5fcb625a982d300f'
review_loop_iteration: 0
followup_review_recommended: false
context: [
  '{project-root}/_bmad-output/implementation-artifacts/epic-13-context.md',
  '{project-root}/_bmad-output/planning-artifacts/specs/spec-upstream-discovery/SPEC.md',
  '{project-root}/_bmad-output/planning-artifacts/specs/spec-upstream-discovery/tier-taxonomy.md',
]
warnings: [oversized]
---

<intent-contract>

## Intent

**Problem:** Story 13.1 lands `trending_candidates` (raw GitHub-trending repo rows) but
every row is unlabeled — nothing joins it against existing atlas signals to decide whether
it is packageable, so the factory still can't tell a curated gap from an awesome-list.

**Approach:** Add a second, pure Kedro node `classify_trending_candidates` to the same
`pipelines/upstream_discovery/` package (13.1's own doc-comment names this as its landing
spot). It resolves each `trending_candidates` row's `repo_full_name` to a PyPI package name
(PEP-503-normalized match against `pypi_universe`), then joins `pypi_conda_mapping`
(already-on-cf) and `pypi_intelligence_enriched` (`license_spdx`, `packaging_shape`) to
assign `tier` (`"1"`/`"2"`/`"skip"`) + a `reason` to every row, never a silent drop.

## Boundaries & Constraints

**Always:**
- Every input row of `trending_candidates` produces exactly one output row with a non-null
  `tier` and a non-empty `reason` — an empty/malformed `trending_candidates` or any empty
  join-signal table degrades to an empty/all-`unclassified-needs-human` result, never raises
  (mirrors `seed_gaps/nodes.py::_lts_candidates`'s empty-guard style).
- `skip_reason` values are drawn ONLY from `tier-taxonomy.md`'s enumerated set; `tier` is
  stored as a string (`"1"`, `"2"`, `"skip"`) for a single consistent dtype, matching CAP-3's
  own `--tier` flag value shape.
- The classifier reads only already-materialized catalog datasets via ordinary Kedro
  `inputs=[...]` bindings and stays pure pandas/stdlib — no HTTP/parse import, no new
  external fetch (AD-2 applies to CAP-1's fetch, not this join; zero new firewall-blocking
  dependency, per the SPEC's own constraint).
- Every fixture the catalog-check gate cross-checks against reality
  (`EXPECTED_PIPELINE_COUNTS`, `EXPECTED_TOTAL`) and every node's `NODE_TIMEOUTS` entry are
  updated in this same change so `kedro-catalog-check` and `dagster-dryrun` stay green.

**Block If:** None. Repo->PyPI-name resolution, the OSI-license allowlist, and the
currently-unreachable `mega-dep-tree`/`app-with-embedded-lib` skip reasons are resolved
below via documented engineering defaults — no further human input is required to implement
CAP-2's success criterion.

**Never:**
- No CLI/MCP operator surface (Story 13.3), org-audit track (13.4), or Mason handoff (13.5)
  — out of scope here.
- No new scheduled job: `classify_trending_candidates` rides the existing weekly
  `bootstrap_data` job automatically (Kedro resolves execution order from declared
  inputs/outputs; `bootstrap_ops` is computed from the full node set, not a hardcoded list)
  — it only needs a `NODE_TIMEOUTS` entry, not a `SCHEDULED_JOBS` row.
- No real dependency-tree resolution or PyPI `requires_dist` fetch: no atlas signal for a
  not-yet-packaged candidate's dependency tree exists today (confirmed by investigation), so
  `mega-dep-tree` stays enumerated-but-unreachable in v1 (see Design Notes).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Tier-1 happy path | Row resolves to a `pure-python`, OSI-licensed, not-on-cf PyPI package | `tier="1"`, reason cites shape+license | No error |
| Tier-2 happy path | Row resolves to a `c-extension`/`cython`/`rust-pyo3` package, not on cf | `tier="2"`, reason cites shape | No error |
| Already on conda-forge | Resolved `pypi_name` present in `pypi_conda_mapping` | `tier="skip"`, `reason="already-on-conda-forge"` | No error |
| Awesome-list | Repo name/description matches the awesome-list heuristic (no PyPI match) | `tier="skip"`, `reason="awesome-list"` | No error |
| Generic no-PyPI-artifact | No PyPI name match, not awesome-list-shaped | `tier="skip"`, `reason="no-pypi-artifact"` | No error |
| Missing intelligence row | `pypi_name` resolved + not on cf, but absent from `pypi_intelligence_enriched` | `tier="skip"`, `reason="unclassified-needs-human"` | No error |
| Non-OSI/missing license | Intelligence row found, `license_spdx` absent or not in the OSI allowlist | `tier="skip"`, `reason="not-osi-license"` | No error |
| Ambiguous packaging shape | Intelligence row found, `packaging_shape=="unknown"` | `tier="skip"`, `reason="unclassified-needs-human"` | No error |
| Cold-start degradation | `trending_candidates` empty/stale OR all three signal tables empty | Empty/`unclassified-needs-human`-only result with the full output schema | No error, no exception |

</intent-contract>

## Code Map

- `src/pyforge/atlas/pipelines/upstream_discovery/nodes.py` -- CAP-1's existing pure trigger node; add CAP-2's classifier here (its own `__init__.py` docstring already names this package as the Stories 13.2-13.5 landing spot).
- `src/pyforge/atlas/pipelines/upstream_discovery/pipeline.py` -- one-node `Pipeline([...])` list (lines 15-25); append a second `node(...)`.
- `src/pyforge/atlas/pipelines/seed_gaps/nodes.py` -- `report_lts_registry_gap`/`_lts_candidates`/`_classify_lts` (lines 33-156) is the exact dict-join-then-classify-then-DataFrame style template to mirror (empty-guard, per-row classify function returning a reason string, `pd.DataFrame(rows, columns=OUT_COLS)`).
- `src/pyforge/atlas/pipelines/pypi_intelligence/nodes.py` -- `_classify_packaging_shape` (lines 442-457, values `pure-python`/`c-extension`/`cython`/`rust-pyo3`/`unknown`) and `enrich_pypi_intelligence` (lines 503-509, output cols `pypi_name, packaging_shape, license_spdx, license_raw, notes`) define the exact join-signal shape from `pypi_intelligence_enriched`. NOTE: `pypi_intelligence_scored` does NOT carry `license_spdx` (dropped after scoring) — join `pypi_intelligence_enriched`, not `_scored`.
- `conf/base/catalog.yml` -- `upstream_discovery` banner block (lines ~807-828); append `trending_candidates_classified` (derived layer, plain `pandas.ParquetDataset`, no TTL — mirrors `seed_gaps_lts_registry_report` at lines 760-764, not the `# A3:` TTL-gated pattern). Update the header's CAP-2-pending note (lines ~33-34) and the block's own comment.
- `tests/catalog/conftest.py` -- `EXPECTED_PIPELINE_COUNTS["upstream_discovery"]` (currently `1`, line ~85) and `EXPECTED_TOTAL` (currently `87`, line ~88).
- `src/pyforge/atlas/orchestration/definitions.py` -- `NODE_TIMEOUTS` dict, `upstream_discovery` section (line ~259); `test_every_op_has_its_own_timeout` requires an explicit entry per node. No `SCHEDULED_JOBS` change needed (bootstrap picks up new nodes automatically, lines 677/705).
- `tests/pipelines/upstream_discovery/test_nodes.py` -- existing trigger-node test file; extend with classifier tests.

## Tasks & Acceptance

**Execution:**
- [x] `src/pyforge/atlas/pipelines/upstream_discovery/nodes.py` -- add pure helpers: `_normalize_pypi_name(name: str) -> str` (PEP 503: lowercase, collapse runs of `-_.` to one `-`); `_resolve_pypi_name(repo_full_name: str, pypi_universe: pd.DataFrame) -> str | None` (normalize the repo segment after `/`, exact-match against a normalized index built once from `pypi_universe.pypi_name`; `None` on no match or an empty/malformed table); `_is_awesome_list(repo_full_name: str, description) -> bool` (repo segment starts with `awesome` case-insensitive, OR `description` contains `curated list`/`awesome list` case-insensitive); `_OSI_APPROVED_SPDX_IDS` (frozenset of ~15 common OSI-approved SPDX identifiers: MIT, Apache-2.0, BSD-2-Clause, BSD-3-Clause, ISC, GPL-2.0-only, GPL-2.0-or-later, GPL-3.0-only, GPL-3.0-or-later, LGPL-2.1-only, LGPL-2.1-or-later, LGPL-3.0-only, LGPL-3.0-or-later, MPL-2.0, Unlicense, Zlib, PSF-2.0); `_classify_row(row, pypi_name, on_cf, intel) -> tuple[str, str]` implementing the decision tree in that order: not-resolved -> awesome-list else no-pypi-artifact; resolved+on_cf -> already-on-conda-forge; resolved+no `intel` row -> unclassified-needs-human; `license_spdx` not in the allowlist -> not-osi-license; `packaging_shape=="unknown"` -> unclassified-needs-human; `pure-python` -> tier `"1"`; compiled shapes -> tier `"2"`; and `classify_trending_candidates(trending_candidates, pypi_universe, pypi_conda_mapping, pypi_intelligence_enriched) -> pd.DataFrame` (the node — builds the normalized-name index, the on-cf `pypi_name` set, and an `intel`-by-`pypi_name` dict each ONCE, then applies resolution+classification per row; output = original `trending_candidates` columns + `pypi_name`/`tier`/`reason`; empty/malformed input returns an empty DataFrame with the full output schema) -- CAP-2's whole classification contract (FR-65).
- [x] `src/pyforge/atlas/pipelines/upstream_discovery/pipeline.py` -- append `node(func=classify_trending_candidates, inputs=["trending_candidates", "pypi_universe", "pypi_conda_mapping", "pypi_intelligence_enriched"], outputs="trending_candidates_classified", name="classify_trending_candidates")` to the existing `Pipeline([...])` list.
- [x] `conf/base/catalog.yml` -- append `trending_candidates_classified: {type: pandas.ParquetDataset, filepath: data/derived/trending_candidates_classified/trending_candidates_classified.parquet, metadata: {layer: derived}}` after the `upstream_discovery` banner block; update the header's and block's CAP-pending comments to record CAP-2 landed.
- [x] `tests/catalog/conftest.py` -- bump `EXPECTED_PIPELINE_COUNTS["upstream_discovery"]` `1 -> 2` and `EXPECTED_TOTAL` `87 -> 88`.
- [x] `src/pyforge/atlas/orchestration/definitions.py` -- add `"classify_trending_candidates": 120,  # CAP-2 (pure in-memory join, no network)` to `NODE_TIMEOUTS`.
- [x] `tests/pipelines/upstream_discovery/test_nodes.py` -- extend with one test per I/O matrix row above using small fixture DataFrames (never real network/data): tier-1 pure-python, tier-2 compiled, already-on-cf skip, awesome-list skip (CAP-2's own success criterion requires this fixture), generic no-pypi-artifact skip, unclassified-needs-human (missing-intelligence-row AND `unknown`-shape variants), not-osi-license skip, and the empty-`trending_candidates`/empty-signal-table degradation cases.

**Acceptance Criteria:**
- Given a `trending_candidates` snapshot with one repo resolving to a pure-python, MIT-licensed, not-yet-on-conda-forge PyPI package, when `classify_trending_candidates` runs, then that row carries `tier="1"` and a non-empty `reason`.
- Given a repo whose resolved PyPI package is already present in `pypi_conda_mapping`, when the node runs, then that row carries `tier="skip"` and `reason="already-on-conda-forge"`.
- Given a repo shaped like an awesome-list (name/description heuristic match) with no PyPI artifact, when the node runs, then that row carries `tier="skip"` and `reason="awesome-list"`.
- Given `pixi run -e pyforge-atlas kedro-catalog-check`, when run after this change, then it passes (pipeline-count/naming/layer/no-inline-IO conventions hold for the new entry).
- Given `pixi run -e pyforge-atlas dagster-dryrun`, when run after this change, then it passes (`classify_trending_candidates` carries its own `NODE_TIMEOUTS` entry; no new schedule entry needed).

## Spec Change Log

## Review Triage Log

### 2026-08-09 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 6: (high 2, medium 2, low 2)
- defer: 1: (low 1)
- reject: 15
- addressed_findings:
  - `high` `patch` `on_cf_names`/`intel_by_name` were built and queried as raw, un-normalized `pypi_name` strings even though the `pypi_universe` match itself is PEP-503-normalized — a casing/separator mismatch between the three independently-sourced tables silently missed real "already on conda-forge" / intelligence matches. Normalized all three join surfaces consistently.
  - `high` `patch` The blanket `all_signals_empty` cold-start branch (a) discarded the free, join-table-independent awesome-list signal by forcing every row to `unclassified-needs-human`, and (b) never triggered when only ONE of the three tables was empty/unusable (e.g. `pypi_universe` alone), letting the normal path confidently emit `no-pypi-artifact`/`already-on-conda-forge`-eligible calls it had no data to support. Replaced with per-signal `universe_usable`/`mapping_usable` flags threaded into `_classify_row`, with the awesome-list check always evaluated first.
  - `medium` `patch` `license_spdx not in _OSI_APPROVED_SPDX_IDS` would raise `TypeError` on a non-hashable value (e.g. a list from a malformed upstream record), violating the "never raises" invariant. Added an `isinstance(license_spdx, str)` guard.
  - `medium` `patch` The curated OSI-SPDX allowlist omitted common, unambiguous OSI-approved IDs (`0BSD`, `AGPL-3.0-only`/`-or-later`, `BSL-1.0`, `EPL-2.0`, `MIT-0`, `BSD-3-Clause-Clear`), undercounting real Tier-1/2 candidates. Expanded the allowlist.
  - `low` `patch` Any `packaging_shape` other than exactly `"pure-python"` fell through to a confident tier `"2"`, so a malformed/unexpected value (not one of the three known compiled shapes) would be mis-tiered instead of degrading. Added an explicit `_COMPILED_SHAPES` allowlist check.
  - `low` `patch` Design Notes' "enumerated but unreachable in v1" list named `mega-dep-tree`/`app-with-embedded-lib` but omitted `application-not-library`, which is equally unreachable (no library-vs-application signal exists in any joined table). Added it to the list.

### 2026-08-09 — Review pass (follow-up)
- intent_gap: 0
- bad_spec: 0
- patch: 4: (high 0, medium 2, low 2)
- defer: 5: (high 0, medium 3, low 2)
- reject: 8
- addressed_findings:
  - `medium` `patch` `_resolve_pypi_name` was dead code: `classify_trending_candidates`
    inlined the same normalize-and-lookup logic, so the 9 helper test cases exercised a
    copy that never shipped and the two could drift apart silently. Gave the helper an
    optional prebuilt-`index` parameter and routed the node's per-row resolution through
    it — the tested path IS now the shipped path, with the index still built ONCE (this
    also retires the O(rows x universe) rebuild risk the PRIOR pass had deferred; that
    ledger entry was left untouched per the orchestrator's ownership of entry status).
  - `medium` `patch` The catalog comment claimed `trending_candidates_classified` is
    "re-materialized whenever trending_candidates or its join signals change" — false:
    the daily `upstream_discovery_trending` job selects `refresh_trending_candidates`
    alone, so the classification only regenerates in the weekly `bootstrap_data` job and
    trails its own source by up to 6 days. Corrected the comment to state the real
    cadence and name the deferred decision; the schedule change itself is deferred (it
    would couple a self-contained daily job to three other pipelines' outputs, and the
    intent contract scoped scheduling out).
  - `low` `patch` The `universe_usable`/`mapping_usable` flags added by the prior pass
    tested only emptiness and column presence, so a signal table that was non-empty and
    carried `pypi_name` but whose every cell was missing counted as authoritative — a
    confident `no-pypi-artifact` / not-on-cf call off zero searchable keys. Derived both
    flags from the built index/set instead.
  - `low` `patch` The three missing-value guards used `v is None or (isinstance(v, float)
    and pd.isna(v))`, which misses `pd.NA` — the null this project's pandas-3.0 string
    dtypes produce — inserting `str(pd.NA)` -> `"<na>"` as a live join key in the
    universe index, the on-cf set, and the intelligence dict. Added a local scalar-safe
    `_is_missing` mirroring `pypi_intelligence/nodes.py`'s reviewed convention (mirrored,
    not imported: no pipeline package imports another's `nodes` module in this codebase).
  - deferred (5, ledger): weekly-vs-daily cadence of the classified output; the license
    gate's affirmatively-false `not-osi-license` for NULL/unmapped licenses and for PEP
    639 SPDX expressions / unlisted OSI IDs (contract-explicit, so not patched); the
    undocumented FALSE-POSITIVE direction of repo-name -> PyPI-name resolution (no
    zero-fetch corroboration signal exists); `pypi_intelligence_enriched` being a bounded
    top-N slice that structurally excludes freshly-trending packages, making real-world
    tier-1/2 yield likely low and unmeasured; and the up-to-3x duplicate rows per repo
    inherited from CAP-1's three trending windows.
  - Two contract-level findings were deliberately NOT escalated to `intent_gap`: the
    license-reason semantics and the scheduling cadence are both explicit, complete,
    deliberate decisions inside `<intent-contract>` that the code implements faithfully —
    reviewer disagreement with a stated decision is not captured-intent incompleteness.
    Both are recorded in the ledger with full evidence for CAP-3 (Story 13.3) to settle.

## Design Notes

**Repo -> PyPI-name resolution is a documented, lossy v1 heuristic.** No existing atlas
dataset maps a GitHub `owner/repo` to a PyPI name (confirmed by investigation — `vcs_health`
only enriches FROM an already-known feedstock's repo, the opposite direction). PEP-503
exact-normalized-match against the repo's own name segment is the only zero-new-fetch option
available; a PyPI package genuinely published under a different name than its repo (e.g.
`python-requests` repo, `requests` package) will false-negative to `no-pypi-artifact`. This
is an accepted v1 limitation, not a defect — filed as a deferred-work item during review, not
blocking CAP-2's stated success criterion (which only requires an already-on-cf skip and an
awesome-list skip in the fixture).

**`mega-dep-tree`, `application-not-library`, and `app-with-embedded-lib` are enumerated but
unreachable in v1.** No atlas signal exists for a not-yet-packaged candidate's dependency-tree
size, or for distinguishing a plain application from an importable library (`packaging_shape`
only encodes pure-python/compiled, never app-vs-library) — building either requires a new
fetch (e.g. PyPI `requires_dist`, or README/classifier analysis), out of CAP-2's zero-new-fetch
scope. A repo that would ideally earn one of these more specific reasons still correctly
resolves to `no-pypi-artifact` or a tier default (never silently dropped) — just with less
granularity. Revisit if Story 13.4 (org-audit, reusing this classifier) or a later story adds a
real dependency-tree or app-vs-library signal.

**The OSI-approved SPDX allowlist is a small curated set, not the full SPDX list** — the
same accepted scope decision as any other curated-map addition in this codebase (git review
decides, not exhaustive automation).

## Verification

**Commands:**
- `pixi run -e pyforge-atlas kedro-test` — expected: pass (station policy verify command; reconciled 2026-08-30 after policy drifted from this spec's original declaration).
- `pixi run -e pyforge-atlas kedro-catalog-check` — expected: pass (station policy verify command; reconciled 2026-08-30 after policy drifted from this spec's original declaration).

## Auto Run Result

Status: `done` (follow-up review pass over the already-landed story 13.2 implementation).

**Implemented change.** Story 13.2 itself landed in `ee1a257210` (+ surface reconcile
`09dd6f4b05`): a second pure Kedro node `classify_trending_candidates` in
`pipelines/upstream_discovery/`, joining `trending_candidates` against `pypi_universe`
(PEP-503-normalized repo->PyPI-name resolution), `pypi_conda_mapping` (already-on-cf) and
`pypi_intelligence_enriched` (`packaging_shape`, `license_spdx`) to assign a `tier`
(`"1"`/`"2"`/`"skip"`) + a non-empty `reason` to every row, never a silent drop. THIS pass
re-reviewed that diff from the baseline with two independent adversarial reviewers and
landed four hardening patches; no capability, constraint, or non-goal changed.

**Files changed in this pass.**
- `src/pyforge/atlas/pipelines/upstream_discovery/nodes.py` -- `_resolve_pypi_name` gains an
  optional prebuilt-`index` parameter and becomes the node's real resolution path (it was
  dead code with 9 tests on it); new local scalar-safe `_is_missing` (handles `pd.NA`);
  `universe_usable`/`mapping_usable` derived from the built index/set.
- `conf/base/catalog.yml` -- corrected the `trending_candidates_classified` cadence comment
  (weekly via `bootstrap_data`, not "whenever its source changes").
- `tests/pipelines/upstream_discovery/test_nodes.py` -- +7 cases pinning each patch.
- `_bmad-output/.../specs/spec-pyforge-atlas/.memlog.md` + `scripts/.spec-surface-baseline.json`
  -- surface reconcile naming the three changed governed paths, then a scoped re-stamp.
- `_bmad-output/.../implementation-artifacts/deferred-work.md` -- 5 new entries (append-only).

**Review findings.** 4 patches applied (2 medium, 2 low); 5 deferred to the ledger
(3 medium, 2 low); 8 rejected as noise; 0 intent_gap, 0 bad_spec. Two contract-level
findings (license-reason semantics, schedule cadence) were deliberately not escalated to
`intent_gap` — the code implements an explicit, complete, deliberate contract decision in
both cases; reviewer disagreement with a stated decision is not captured-intent
incompleteness. Both carry full evidence in the ledger for CAP-3 (Story 13.3).

**Verification performed** (live, on the landing branch, after the patches):
- `pixi run -e pyforge-atlas kedro-test` -- 987 passed, 19 skipped (+7 over the pre-pass
  980; exactly the new cases).
- `pixi run -e pyforge-atlas kedro-catalog-check` -- 47 passed.
- `pixi run -e pyforge-atlas dagster-dryrun` -- 58 passed.
- `pixi run -e pyforge-atlas pytest .../tests/pipelines/upstream_discovery -q` -- 45 passed.
- `python3 scripts/spec_surface_check.py` -- OK: every tracked file governed or
  allowlisted; no drift (after the memlog entry + scoped `--write-baseline`).

**Residual risks.** All five deferred items are live limitations of the shipped
capability, not of its code: the classified table trails its daily source by up to 6 days;
`not-osi-license` is asserted for licenses that are merely unmapped or expression-shaped;
repo-name resolution can false-POSITIVE onto an unrelated same-named package with no
corroboration signal available; `pypi_intelligence_enriched`'s top-N bound likely makes
real-world tier-1/2 yield low and it is unmeasured by any gate; and each repo can appear up
to 3x from CAP-1's three trending windows. None blocks CAP-2's stated success criterion
(an already-on-cf skip and an awesome-list skip), all are visible to a human via the
`reason` column, and CAP-3 is the first consumer that must settle them.

## Status reconcile 2026-09-20

- frontmatter `status` `shipped` → `done` (ledger row `12-2-tier-classification-fr-65: done`).
