---
title: 'Trending ingest — GitHub-trending discovery pipeline (S-13.1, FR-64/CAP-1)'
type: 'feature'
created: '2026-08-09'
status: done
baseline_revision: '329b7eb19258dcd69387934c0840c82a07a62c3e'
final_revision: 'e569cac396d1a6bb82c10f4f792f69a590077302'
review_loop_iteration: 0
followup_review_recommended: false
context: [
  '{project-root}/_bmad-output/implementation-artifacts/epic-13-context.md',
  '{project-root}/_bmad-output/planning-artifacts/specs/spec-upstream-discovery/SPEC.md',
]
warnings: [oversized]
---

<intent-contract>

## Intent

**Problem:** The factory only packages what a human hand-picks. Epic 13 (Upstream discovery)
starts with CAP-1/FR-64: nothing today ingests GitHub-trending Python repos into the shipped
Kedro/Dagster/DuckDB dataflow — `docs/specs/trendshift-conda-forge.md`'s legacy "Phase T"
never shipped, and `catalog.yml`'s own header still calls it "the unshipped Phase T."

**Approach:** Add an 8th Kedro pipeline, `pipelines/upstream_discovery/`, whose single node
emits a pure `RefreshRequest` trigger; a new `TrendingSnapshotDataset` (subclass of the
existing `ExternalRefreshDataset` — the same base B5 used for `vulnerability_vdb_store`)
owns the injected fetch of 3 `github.com/trending/python?since=<period>` HTML pages + a
GitHub Search API fallback, parses them with two pure functions, and persists the combined
snapshot to `trending_candidates`. A layout break or empty result degrades to WARN +
keep-last-good, never a crash — the exact AD-13 shape every other external-refresh asset in
this codebase already uses.

## Boundaries & Constraints

**Always:**
- All fetch + HTML/JSON parsing lives in `datasets/upstream_discovery.py` (dataset-owned IO,
  AD-2); `pipelines/upstream_discovery/nodes.py` stays a pure `params -> RefreshRequest`
  trigger, mirroring `pipelines/vulnerability/nodes.py::refresh_vdb_store` exactly — no
  HTTP/parse imports there.
- `TrendingSnapshotDataset` subclasses `datasets.refresh.ExternalRefreshDataset` (reuse, do
  not reimplement, its cadence-check / atomic-write / never-clobber / `StalenessMarker`
  machinery). A malformed or empty combined result is rejected by `_write` / `_is_empty`
  exactly like `VDBStoreDataset` — last-good stays on disk, `save()` never raises.
- Both the primary scrape and the Search API fallback route through the EXISTING
  `${globals:endpoint_bases.GITHUB_BASE_URL}` / `GITHUB_API_BASE_URL}` — no new override
  point, and **no `credentials:` key** (unauthenticated GitHub Search API is rate-limited but
  functional; staying uncredentialed keeps this pipeline schedule-eligible without triggering
  AD-11's attended-only-credentialed-run rule).
- Every fixture the catalog-check gate cross-checks against reality
  (`PREFIX_TO_PIPELINE`, `EXPECTED_PIPELINE_COUNTS`, `EXPECTED_TOTAL`, the orphan-`ttls`
  future-consumer regex) is updated in this same change so `kedro-catalog-check` stays green.

**Block If:** None. The SPEC's inherited open questions (which pipeline hosts discovery;
dataset naming; Search-API credential scoping) are resolved in Design Notes below — no
further human input is required to implement CAP-1.

**Never:**
- No tiering/classification, CLI/MCP operator surface, org-audit track, or Mason handoff —
  those are Stories 13.2–13.5, out of scope here.
- No real production HTTP client wired in: the injected `fetcher: Callable[[str], str]`
  defaults to `None` (offline) and is only stubbed in tests — matches every other
  `ExternalRefreshDataset` subclass's DW-B5-2-style deferral (the concrete fetcher lands at
  an attended run, not this story).
- No live Dagster daemon bring-up; the new schedule entry ships `STOPPED`, matching the
  existing DW-G3/DW-C1-1 deferred boundary — do not weaken that gate.
- No `lxml` / `requests` / `httpx` dependency add — `beautifulsoup4` (already used elsewhere
  in this monorepo) with stdlib `html.parser` is the only new dependency.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Happy path | All 3 period URLs return well-formed trending HTML | `save()` persists a non-empty `trending_candidates` snapshot; `is_stale()` False | No error |
| Layout break | All 3 HTML fetches succeed but the parser matches 0 repo cards | Search-API fallback is tried; if it too yields 0 rows, `_write` is never invoked — prior snapshot file untouched | WARN logged; `save()` marks stale, never raises |
| Partial layout break | 2 of 3 periods parse fine, 1 yields 0 rows | The 2 good periods persist; fallback NOT triggered (combined result non-empty) | WARN logged for the broken period only |
| Fetch exception | `fetcher(url)` raises for one period | That period treated as empty; other periods + fallback still attempted | WARN logged, never raises |
| Not due yet | `RefreshRequest.cadence_seconds` not elapsed since last write, `force=False` | `save()` no-ops; snapshot + staleness marker untouched | No error, no fetch attempted |
| Offline / no fetcher | Catalog resolves with default `fetcher=None` (e.g. `kedro-catalog-check`) | `save()` marks stale ("no fetcher wired") + keeps last-good; `load()` returns last-good or empty frame | No error, no network |

</intent-contract>

## Code Map

- `src/pyforge/atlas/datasets/refresh.py` -- base `ExternalRefreshDataset`/`RefreshRequest`/`StalenessMarker` to subclass, and `VDBStoreDataset` as the closest existing template (`_write` rejects malformed data, `load` degrades to empty on a missing/corrupt store).
- `src/pyforge/atlas/pipelines/vulnerability/nodes.py` -- `refresh_vdb_store`/`_coerce_cadence` is the exact trigger-node template to mirror.
- `src/pyforge/atlas/pipelines/derived_artifacts/` -- smallest existing pipeline package; template for `__init__.py`/`pipeline.py` shape.
- `conf/base/catalog.yml` -- lines ~1-32 conventions header (update the "unshipped Phase T" comment); append a new `upstream_discovery` banner block after the `derived_artifacts` block.
- `conf/base/parameters.yml` -- `ttls:` block (add a `trending_candidates` entry; do NOT touch `refresh_cadences:`/`LEGACY_REFRESH_TTLS` — that block is legacy-parity-only per B5, exact-equality-tested).
- `tests/catalog/conftest.py` -- `PREFIX_TO_PIPELINE`, `EXPECTED_PIPELINE_COUNTS`, `EXPECTED_TOTAL`.
- `tests/catalog/test_conventions.py` -- `test_orphan_ttls_name_their_future_consumer`'s regex is hardcoded to legacy `B\d+` story IDs; extend it for post-migration dotted IDs.
- `src/pyforge/atlas/orchestration/definitions.py` -- `SCHEDULED_JOBS` tuple table; add one daily entry (read the file first for the exact current tuple shape before adding).
- `pixi.toml` (member, `src/shared/packages/pyforge-atlas/pixi.toml`) `[package.run-dependencies]` + `pyproject.toml` `[project].dependencies` -- add `beautifulsoup4>=4.15.0` (imported as `bs4`), byte-for-byte in both per AUD-ATLAS-010 doctrine.

## Tasks & Acceptance

**Execution:**
- [x] `src/shared/packages/pyforge-atlas/pixi.toml`, `pyproject.toml` -- add `beautifulsoup4>=4.15.0` to both `[package.run-dependencies]` and `[project].dependencies` (comment: imported as `bs4`) -- new runtime dep for HTML parsing; this package's dependency doctrine (AUD-ATLAS-010) requires both manifests declared byte-for-byte in step.
- [x] `src/pyforge/atlas/datasets/upstream_discovery.py` (new) -- add `TrendingSnapshotDataset(ExternalRefreshDataset)`: constructor takes `filepath`, `daily_url`, `weekly_url`, `monthly_url`, `search_api_url`, `fetcher: Callable[[str], str] | None = None`, `cadence_seconds`, `metadata`; wraps `fetcher` into a bound zero-arg `_do_refresh` passed as `refresher=` to `super().__init__()`. `_do_refresh` calls `self._fetcher(url)` per period, catches exceptions per-period (never aborts the whole run for one bad period), parses via `parse_trending_html`; if the combined per-period result is empty, falls back to `self._fetcher(search_api_url)` + `parse_search_api_response`. Override `_write` (validate `repo_full_name`/`period`/`fetched_at` columns present, atomic-write Parquet, mirrors `VDBStoreDataset._write`'s malformed-column rejection), `_store_exists`/`_store_mtime` (against `STORE_FILENAME = "trending_candidates.parquet"` under `filepath`), and `load()` (read persisted parquet; empty frame + stale marker if absent/corrupt, mirrors `VDBStoreDataset.load`) -- this is CAP-1's whole IO/degradation contract.
- [x] `src/pyforge/atlas/datasets/upstream_discovery.py` -- add pure `parse_trending_html(html: str, *, period: str) -> list[dict]` (BeautifulSoup + stdlib `html.parser`, no lxml; extract `repo_full_name`/`repo_url`/`description`/`language`/`stars_total`/`stars_today`/`forks_total`, tag `period` + `source="html_scrape"`; return `[]` on zero matches, never raise) and `parse_search_api_response(payload: Any) -> list[dict]` (same row shape, `stars_today=None`, `source="search_api_fallback"`; robust to a non-list/malformed payload, returns `[]`) -- the SPEC's explicit "fixture-pinned parser test" requirement; keep these colocated with the dataset class, mirroring `migration_status.py`'s `migration_names()` precedent.
- [x] `src/pyforge/atlas/datasets/__init__.py` -- re-export `TrendingSnapshotDataset`, `parse_trending_html`, `parse_search_api_response` -- required for the `catalog.yml` `type:` reference and for tests to import from `pyforge.atlas.datasets`.
- [x] `src/pyforge/atlas/pipelines/upstream_discovery/__init__.py`, `pipeline.py`, `nodes.py` (new) -- `nodes.py`: `refresh_trending_candidates(ttls: dict) -> RefreshRequest` (pure trigger, own tiny `_coerce_cadence` helper reading `ttls["trending_candidates"]`, default fallback if missing/non-numeric — mirror `vulnerability/nodes.py::refresh_vdb_store`/`_coerce_cadence`). `pipeline.py`: one `node(func=refresh_trending_candidates, inputs="params:ttls", outputs="trending_candidates", name="refresh_trending_candidates")`. `__init__.py`: `from .pipeline import create_pipeline`.
- [x] `conf/base/catalog.yml` -- append an `upstream_discovery` banner block (after `derived_artifacts`) with one entry: `trending_candidates: {type: pyforge.atlas.datasets.TrendingSnapshotDataset, filepath: data/raw/trending_candidates, daily_url: ${globals:endpoint_bases.GITHUB_BASE_URL}/trending/python?since=daily, weekly_url: .../since=weekly, monthly_url: .../since=monthly, search_api_url: ${globals:endpoint_bases.GITHUB_API_BASE_URL}/search/repositories?q=language:python&sort=stars&order=desc, metadata: {layer: raw}}`; update the header's "unshipped Phase T" comment (line ~32) to note S-13.1 landed CAP-1 ingest, CAP-2-5 still pending.
- [x] `conf/base/parameters.yml` -- under `ttls:`, add a `# -- upstream_discovery` sub-header + `trending_candidates: 86400  # 1 d (daily discovery cadence, no legacy equivalent) [future_consumer: 13.1]`. Do not touch `refresh_cadences:`/`LEGACY_REFRESH_TTLS`.
- [x] `tests/catalog/conftest.py` -- add `"trending": "upstream_discovery"` to `PREFIX_TO_PIPELINE`, `"upstream_discovery": 1` to `EXPECTED_PIPELINE_COUNTS`, bump `EXPECTED_TOTAL` 86 -> 87.
- [x] `tests/catalog/test_conventions.py` -- extend `test_orphan_ttls_name_their_future_consumer`'s regex from `\[future_consumer:\s*(B\d+)\b` to `\[future_consumer:\s*(B\d+|\d+\.\d+)\b` (post-migration stories use dotted epic.story IDs, not legacy `B\d+`).
- [x] `src/pyforge/atlas/orchestration/definitions.py` -- read the current `SCHEDULED_JOBS` tuple shape, then add one daily-cadence entry wiring the `upstream_discovery` pipeline's `refresh_trending_candidates` node, `default_status=STOPPED` per existing convention (no live bring-up).
- [x] `tests/datasets/test_upstream_discovery.py` (new) -- one test per I/O matrix row above, stub `fetcher` per case (never real network); plus `parse_trending_html`/`parse_search_api_response` fixture tests (a captured-shape HTML fixture -> expected rows; a "broken layout" HTML fixture -> `[]`).
- [x] `tests/pipelines/upstream_discovery/test_nodes.py` (new) -- pure test of `refresh_trending_candidates` against a `ttls` dict (present / missing / non-numeric key), mirroring `tests/pipelines/vulnerability/test_nodes.py`'s trigger-node test style.

**Acceptance Criteria:**
- Given a fresh `trending_candidates` catalog entry and a stubbed fetcher returning well-formed HTML for all 3 periods, when the `upstream_discovery` pipeline runs, then a non-empty candidates snapshot is persisted and `is_stale()` is False.
- Given a stubbed fetcher whose HTML parses to zero rows across all 3 periods and whose Search-API fallback also yields zero rows, when the pipeline runs, then the prior snapshot file (if any) is byte-identical afterward, a staleness marker is written, and no exception propagates.
- Given `pixi run -e pyforge-atlas kedro-catalog-check`, when run after this change, then it passes (naming/layer/no-inline-IO/AD-1/credential-allowlist/orphan-ttls/pipeline-count conventions all hold for the new entries).

## Spec Change Log

## Review Triage Log

### 2026-08-09 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 6: (high 1, medium 2, low 3)
- defer: 7: (high 0, medium 2, low 5)
- reject: 4
- addressed_findings:
  - `high` `patch` `_STARS_TODAY_RE` only matched the literal "today" phrase; GitHub's trending page phrases the delta as "this week"/"this month" for weekly/monthly views, so `stars_today` came out `None` for 2 of the 3 fetched periods in production (masked in tests by fixture reuse across periods). Widened to `_STARS_DELTA_RE` matching all three phrasings.
  - `medium` `patch` `_REQUIRED_COLUMNS` omitted `source`, so a malformed/missing `source` column (the field distinguishing scrape rows from fallback rows) was accepted and persisted without rejection. Added `"source"` to the tuple.
  - `medium` `patch` No test exercised the Search-API-fallback fetch call itself raising (only "fallback returns empty" and "one HTML period raises" were covered, leaving the already-implemented `except Exception` around `self._fetcher(self._search_api_url)` untested). Added `test_layout_break_search_api_fetch_raises_keeps_last_good`.
  - `low` `patch` A per-period layout break that parsed to zero rows (not an exception) was only logged when ALL 3 periods combined were empty, so one broken period's data could silently vanish from a snapshot with no log trail. Added a per-period WARN in `_do_refresh` when `parse_trending_html` returns zero rows for that period.
  - `low` `patch` `_coerce_cadence`'s `(ttls or {}).get(key)` only substitutes `{}` for a falsy `ttls`; a truthy non-dict `ttls` (list/string) would raise `AttributeError` instead of degrading to the daily default. Guarded with `ttls.get(key) if isinstance(ttls, dict) else None`.
  - `low` `patch` The Search API fallback URL had no `per_page` parameter, silently capping results at GitHub's default page size (30) instead of the achievable 100. Added `&per_page=100`.

### 2026-08-09 — Review pass (follow-up, verification repair)
- intent_gap: 0
- bad_spec: 0
- patch: 6: (high 0, medium 2, low 4)
- defer: 6: (high 0, medium 0, low 6)
- reject: 9
- addressed_findings:
  - `medium` `patch` The prior pass's headline fix (`_STARS_DELTA_RE` widened to match "this week"/"this month", not just "today") shipped with ZERO test coverage of the case it claims to fix — `GOOD_HTML` was reused unchanged across daily/weekly/monthly and the happy-path test never inspected `stars_today` for those rows, so the regression could silently reappear undetected. Added `test_parse_trending_html_stars_delta_matches_all_three_period_phrasings` (parametrized across all three phrasings).
  - `medium` `patch` `repo_full_name` was built by stripping slashes off the scraped `href` assuming it is always the relative `/owner/repo` form; an absolute href would slip past `.strip("/")` unchanged and persist a garbled `repo_full_name`/`repo_url` instead of being skipped. Added `_REPO_FULL_NAME_RE` shape validation + `test_parse_trending_html_skips_card_with_absolute_href`.
  - `low` `patch` Two independently-maintained copies of the same `86_400` cadence literal (`upstream_discovery.py`'s `_DEFAULT_CADENCE_SECONDS` and `nodes.py`'s own `DAILY_SECONDS`) had no shared source, unlike the existing `WEEKLY_SECONDS` precedent both other cadences import. Added a shared `DAILY_SECONDS` to `refresh.py`; both modules now import it.
  - `low` `patch` The per-card skip branch (`if link is None: continue`, a card with no `<h2><a href>` title link) had no direct test coverage. Added `test_parse_trending_html_skips_card_with_no_title_link` (`MIXED_HTML` fixture).
  - `low` `patch` `language` didn't get the same empty-string-to-`None` normalization `description` already has, so an empty-but-present language tag would persist as `""` rather than `None`. Added the `or None` treatment + `test_parse_trending_html_empty_language_tag_normalizes_to_none`.
  - `low` `patch` The widened `future_consumer` regex (prior pass) had no trailing boundary past the dotted-numeric alternative, so a malformed 3-segment ID like `13.1.2` would partial-match as `13.1` instead of failing validation. Added a `(?!\.\d)` negative lookahead.
  - `low` `defer` `_STARS_DELTA_RE` searches the whole card's concatenated text, not a scoped stars-delta element — a description containing a matching phrase could misattribute `stars_today`. Filed to `deferred-work.md` (distinct from the already-deferred first-`<h2>`/first-`<p>` mismatch).
  - `low` `defer` `_DIGITS_RE` doesn't handle abbreviated counts (e.g. "1.2k stars") — would silently truncate if GitHub's trending page ever renders one. Filed to `deferred-work.md`.
  - `low` `defer` `_write`'s malformed-frame guard checks column presence only, not row content — mirrors `VDBStoreDataset._write`'s identical established pattern, so not fixed as a one-file patch. Filed to `deferred-work.md`.
  - `low` `defer` (already tracked, not re-filed) Search-API fallback semantic mismatch ("trending" vs. static most-starred) — matches the existing `deferred-work.md` entry from review pass 1 verbatim.
  - `low` `defer` (already tracked, not re-filed) First-`<h2>`/first-`<p>` tag match fragility (`repo_full_name`/`description` misattribution) — matches the existing `deferred-work.md` entry from review pass 1 verbatim.
  - `low` `defer` (already tracked, not re-filed) `_coerce_cadence` accepts a non-positive cadence unguarded — matches the existing `deferred-work.md` entry from review pass 2 verbatim (same precedent-mirroring rationale).
  - `reject` (9, noise or already-accepted-by-design; see reasoning inline, not filed): `max_retries`/`timeout_seconds` "inert" — `refresh.py` documents this as declarative Dagster-resource metadata, not enforced in-loop, for all three existing external-refresh datasets too; Search-API rate-limit tradeoff — already an explicit, accepted `<intent-contract>` constraint; `future_consumer` tag "mislabeled" as still-pending — verified against existing shipped-story entries (B2/B5) that the tag is attribution, not a pending-work flag; no request backoff/spacing — the live fetcher is explicitly deferred to a future attended run, not this story; no alerting on double scrape+fallback failure — matches the WARN+stale pattern already shipped for all three sibling external-refresh datasets; the memlog's own verification-count claims being "asserted prose" — meta-commentary on review methodology, not a code defect; `parse_trending_html`/`parse_search_api_response` call sites being "unguarded" (x2) — both functions are already internally exception-safe by design, no realistic uncaught path; `pd.DataFrame(fetched)`-on-scalar raising in `_write` — unreachable via this class's actual call path (`_do_refresh` always returns a `DataFrame`), mirrors `VDBStoreDataset` verbatim.

## Design Notes

**Resolving the SPEC's inherited open questions:** (1) *Which pipeline hosts discovery?* A new 8th package, `pipelines/upstream_discovery/` — `catalog.yml`'s own header comment already anticipates this ("the unshipped Phase T" is explicitly named as the reason candidate rows aren't cataloged yet; `find_pipelines()` auto-discovers any package exposing `create_pipeline()`, so adding one is mechanical, not a closed-system violation). Named for the Epic/SPEC (`upstream_discovery`), not just "trending," so Story 13.4's org-audit track can land in the same package later without a rename. (2) *Dataset naming* — `trending_candidates` (raw layer), matching FR-64's own wording ("candidates land in a named dataset"). (3) *Search-API credential scoping* — neither: it stays unauthenticated (rate-limited but functional), which avoids AD-11's attended-only-credentialed-run constraint entirely and keeps the pipeline schedule-eligible. (4) *Cadence source* — `ttls:` (not `refresh_cadences:`, which is a closed, exact-equality-tested legacy-parity fixture for exactly 3 pre-existing stores); `test_orphan_ttls_name_their_future_consumer` already anticipates non-A3-flip `ttls` consumers via its `[future_consumer: ...]` annotation, its regex just needs widening for the new story-ID scheme.

**Why `ExternalRefreshDataset`, not `_StaleAwareStatusSource` (migration_status.py's pattern):** both offer injected-fetcher + keep-last-good, but only `ExternalRefreshDataset` bundles the `RefreshRequest`-trigger-node + cadence-check `save()` shape that gives "Given a schedule" for free (a pure node emits the trigger, the dataset's `save()` decides if a refresh is due) — exactly `refresh_vdb_store`'s shape, reused verbatim.

## Verification

**Commands:**
- `pixi run -e pyforge-atlas kedro-test` — expected: pass (station policy verify command; reconciled 2026-08-30 after policy drifted from this spec's original declaration).
- `pixi run -e pyforge-atlas kedro-catalog-check` — expected: pass (station policy verify command; reconciled 2026-08-30 after policy drifted from this spec's original declaration).

**Manual checks (if no CLI):**
- Confirm `environment.yaml` regen is/isn't required for the new `beautifulsoup4` run-dep (repo CLAUDE.md pixi.toml-change gate is scoped to the root `local-recipes`/`build` env sync check; verify whether this member-package pixi.toml edit trips it). **Verified 2026-08-09:** `pixi project export conda-environment -e build` produces a byte-identical `environment.yaml` — the `build` env does not pull the `pyforge-atlas` feature, so no regen or commit is needed.

## Auto Run Result

**Summary.** Resumed on a verification failure, not a fresh implementation: the prior
session's `57a6cde737` had already landed all 11 tasks + a review pass, but the loop's
own `python scripts/spec_surface_check.py` gate was red — 21 governed paths (this
story's own diff) had changed without `spec-pyforge-atlas`'s `.memlog.md` naming them,
so the drift baseline never moved. Repaired by reconciling that memlog (naming every
changed/added path) and re-stamping the baseline, scoped to `pyforge-atlas/spec-pyforge-atlas`
only — no intent-contract or code change. With the gate green, ran the owed follow-up
review (`followup_review_recommended: true` from the prior pass): independent Blind
Hunter + Edge Case Hunter passes over the full diff, 6 patches applied, 6 findings
deferred (3 newly filed, 3 already tracked from the prior pass), 9 rejected.

**Files changed, this session:**
- `_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-pyforge-atlas/.memlog.md` — two Surface reconcile entries (verification repair; follow-up review patches).
- `scripts/.spec-surface-baseline.json` — re-stamped twice, scoped to `pyforge-atlas/spec-pyforge-atlas` only.
- `src/shared/packages/pyforge-atlas/src/pyforge/atlas/datasets/refresh.py` — added a shared `DAILY_SECONDS` constant.
- `src/shared/packages/pyforge-atlas/src/pyforge/atlas/datasets/upstream_discovery.py` — imports the shared constant; validates `repo_full_name` shape; normalizes empty `language` to `None`.
- `src/shared/packages/pyforge-atlas/src/pyforge/atlas/pipelines/upstream_discovery/nodes.py` — imports the shared constant instead of duplicating it.
- `src/shared/packages/pyforge-atlas/tests/catalog/test_conventions.py` — tightened the `future_consumer` regex against 3-segment IDs.
- `src/shared/packages/pyforge-atlas/tests/datasets/test_upstream_discovery.py` — 4 new tests (6 new test cases via parametrization) closing the coverage/robustness gaps above.
- `_bmad-output/projects/pyforge-atlas/implementation-artifacts/deferred-work.md` — 3 new entries.

**Review findings breakdown (follow-up pass):** patch 6 (0 high, 2 medium, 4 low) — all
applied and verified; defer 6 (3 newly filed, 3 duplicates of already-tracked findings
from the prior pass, not re-filed); reject 9 (matches an already-shipped or already-accepted
pattern elsewhere in this surface — see the Review Triage Log entry for the itemized
reasoning per finding).

**Verification performed:** `pixi run --frozen -e pyforge-atlas kedro-test` (945 passed,
19 skipped, up from 939 — exactly the 6 new cases), `pixi run --frozen -e pyforge-atlas
kedro-catalog-check` (47 passed), `pixi run --frozen -e pyforge-atlas dagster-dryrun` (58
passed), `python scripts/spec_surface_check.py` (clean, exit 0) — all four re-run and
confirmed green after the final commit, against a clean working tree.

**Residual risks.** All genuinely real per-finding risks now live in
`deferred-work.md` (6 entries for this story, 3 new this session): the Search-API
fallback's semantic drift from "trending" to "most-starred," first-tag-match markup
fragility (title/description and, newly, the stars-delta regex), abbreviated-count
truncation, column-presence-only write validation, and non-positive-cadence
misconfiguration. None block CAP-1's stated success criteria; all are pre-existing
patterns or explicitly out-of-scope per the story's own Never-clause.

## Status reconcile 2026-09-20

- frontmatter `status` `shipped` → `done` (ledger row `12-1-trending-ingest-fr-64: done`).
