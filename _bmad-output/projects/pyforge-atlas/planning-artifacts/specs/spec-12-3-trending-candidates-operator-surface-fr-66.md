---
title: 'trending-candidates operator surface — read-only CLI/MCP query over classified candidates (S-13.3, FR-66/CAP-3)'
type: 'feature'
created: '2026-08-09'
status: done
baseline_revision: '0750df1192dda873082d8b47f863112c920aab3c'
final_revision: '96991f25085b1d647a05b58dba716b06d5a3db73'
review_loop_iteration: 0
followup_review_recommended: true
context: [
  '{project-root}/_bmad-output/implementation-artifacts/epic-13-context.md',
  '{project-root}/_bmad-output/planning-artifacts/specs/spec-upstream-discovery/SPEC.md',
  '{project-root}/_bmad-output/planning-artifacts/specs/spec-upstream-discovery/tier-taxonomy.md',
]
warnings: [oversized]
---

<intent-contract>

## Intent

**Problem:** Story 13.2 materializes `trending_candidates_classified` (every trending repo
tiered + reasoned), but nothing can query it — no CLI, no MCP tool — so the factory's own
"what should I package next?" question has no answer surface (FR-66, CAP-3).

**Approach:** A new `pyforge.atlas.trending_candidates` package exposes one pure
`query_trending_candidates(...)` function (loads the classified dataset via the existing
`_session`/`_provenance` seam, then filters/sorts/caps with pandas). A thin `__main__.py`
CLI and a thin MCP tool both delegate to that ONE function, so identical filters yield
identical output by construction — no parallel filter logic to drift.

## Boundaries & Constraints

**Always:**
- Read-side only: `catalog.load` via `_session.bootstrapped_session`/`_session.loaded_catalog`
  + `_provenance.load_with_provenance` — the exact seam `mcp/tools.py::read_dataset` already
  uses. Zero new fetch; offline-safe and idempotent after ingest (SPEC CAP-3 intent).
- The 6 tier-taxonomy.md flags, exactly: `--period` (`daily`|`weekly`|`monthly`|`all`, default
  `weekly`; `all` is an engineering-default addition beyond the taxonomy's 3 enumerated values
  — see Design Notes), `--tier` (comma-list of `1`/`2`/`skip`, or the literal `all`, default
  `1,2`), `--top` (positive int display cap, default `25`), `--not-on-cf`/`--all` (mutually
  exclusive; default = not-on-cf), `--min-stars` (int floor on `stars_total`, default `500`),
  `--json` (off = table).
- `--not-on-cf` filters out `reason == "already-on-conda-forge"` — no boolean `on_cf` column
  exists in `trending_candidates_classified`, so this is ALWAYS derived from `reason`, never a
  separate stored flag.
- Default sort: `stars_total` descending, ties broken by `repo_full_name` ascending — makes
  `--top`'s cap deterministic and CLI/MCP output byte-comparable for identical filters.
- A row with a null/unparseable `stars_total` fails the `--min-stars` floor (excluded, not an
  error) — never silently passes a filter it cannot actually satisfy.
- `mcp/tools.py`'s new tool body is a single delegate call to `_trending.query_trending_candidates`
  (AD-7) — add `_trending` to `tests/mcp/test_no_business_logic_in_tool_bodies.py`'s
  `ALLOWED_CALL_ROOTS`, mirroring the existing `_nl`/`_provenance` entries.
- An unrecognized `--tier` token, or `--period`/`--top`/`--min-stars` outside their valid
  range, raises a clear `ValueError` (CLI: caught, printed to stderr, exit 1) — fail fast on
  bad input rather than silently returning an empty/wrong result.
- A missing or empty `trending_candidates_classified` dataset degrades to an empty candidate
  list (`count: 0`), never a crash — mirrors CAP-1/CAP-2's never-hard-fail posture.

**Block If:** None — schema, seam, and CLI/MCP precedent are all confirmed present; no
decision here requires human input.

**Never:**
- No new Kedro node, pipeline, or catalog dataset — reads ONLY the already-materialized
  `trending_candidates_classified` from Story 13.2.
- No cadence/schedule change: the weekly-vs-daily trail (`DW` on `spec-13-2-tier-classification.md`)
  stays as-is — this story's read path surfaces `build_stamp`/`build_stamp_newest` so the trail
  is visible, not hidden, which IS the deliberate cadence decision CAP-3 owed (see Design Notes),
  not a scheduling code change.
- No dedup of the underlying dataset's up-to-3x-per-repo rows across periods (same DW item) —
  out of scope for this story's classifier-adjacent data; the default `--period=weekly` shows
  at most one row per repo, and an explicit `--period all` opts into seeing every period's row,
  duplicates included, transparently.
- No Mason handoff (13.5) or fixed-source audit track (13.4) — out of scope.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Happy path, default filters | Classified dataset has tier-1/2 rows across periods | Rows with `period=="weekly"`, `tier` in `{1,2}`, `reason != "already-on-conda-forge"`, `stars_total>=500`, sorted desc by `stars_total`, capped to 25 | No error |
| `--tier all` | Rows across all tiers incl. `skip` | Tier filter is a no-op | No error |
| `--period all` | Dataset has `html_scrape` rows (3 periods) + a `search_api_fallback` row (`period=="all"`) | Every row regardless of period tag, duplicates included | No error |
| `--all` (not `--not-on-cf`) | Rows with `reason=="already-on-conda-forge"` present | Those rows included too | No error |
| Null/unparseable `stars_total` | A row missing `stars_total` | Excluded by `--min-stars` (treated as below floor) | No error |
| Empty/missing dataset | `trending_candidates_classified` absent or zero rows | `count: 0`, empty `candidates` | No error, no exception |
| Invalid `--tier`/`--period`/`--top`/`--min-stars` | e.g. `--tier=5`, `--top=0` | Raises `ValueError` naming the bad value | CLI: stderr + exit 1; MCP: propagates |
| CLI `--json` vs MCP tool, same filters | Identical filter args | Identical `count`/`candidates` payload (both call the same function) | No error |

</intent-contract>

## Code Map

- `src/pyforge/atlas/trending_candidates/__init__.py` -- new package marker.
- `src/pyforge/atlas/trending_candidates/query.py` -- new: `query_trending_candidates(...)` — loads `trending_candidates_classified` via the `_session`/`_provenance` seam (mirrors `mcp/tools.py::read_dataset`), filters/sorts/caps with pandas, returns the envelope dict (`schema_version, dataset, provenance_kind, build_stamp, build_stamp_newest, reason, filters, rows, matched, count, candidates` — `rows`/`matched` added by the third follow-up review pass, see its triage entry).
- `src/pyforge/atlas/trending_candidates/__main__.py` -- new: argparse CLI (mirrors `publish/__main__.py`'s `def main(argv=None) -> int` shape) implementing the 6 flags; renders a table by default, `json.dumps(...)` under `--json`.
- `src/pyforge/atlas/mcp/tools.py` -- add `query_trending_candidates(...)`: one delegate call to `_trending.query_trending_candidates(...)` (mirrors `query_vizro_ai`'s one-line-delegate shape); add `from pyforge.atlas.trending_candidates import query as _trending`.
- `src/pyforge/atlas/mcp/server.py` -- add `@mcp.tool() def query_trending_candidates(...)` wrapping `tools.query_trending_candidates(...)`.
- `tests/mcp/test_no_business_logic_in_tool_bodies.py` -- add `_trending` to `ALLOWED_CALL_ROOTS`.
- `conf/base/catalog.yml` -- update the header's CAP-3-pending note (~lines 36-37) and the `trending_candidates_classified` cadence comment (~lines 831-838) to record CAP-3 landed + the cadence decision.
- `pixi.toml` -- add `[feature.pyforge-atlas.tasks.trending-candidates]` (`cmd = "python -m pyforge.atlas.trending_candidates"`), mirroring the `kedro-test`/atlas-native `publish`-style task shape.
- `tests/trending_candidates/__init__.py`, `tests/trending_candidates/test_query.py` -- new: filter/sort/cap/degradation/validation tests, offline via the `DataCatalog(MemoryDataset(...))` + faked `bootstrapped_session` pattern from `tests/mcp/test_read_surface.py`.
- `tests/trending_candidates/test_main.py` -- new: CLI argument-parsing + `--json` vs table output tests (capture stdout, call `main(argv)` directly).
- `tests/mcp/test_read_surface.py` -- extend: thin-delegate proof that `tools.query_trending_candidates(...)` returns exactly `_trending.query_trending_candidates(...)`'s return (monkeypatched), and that its call root passes the AD-7 AST gate.

## Tasks & Acceptance

**Execution:**
- [x] `src/pyforge/atlas/trending_candidates/__init__.py` -- create empty package marker -- establishes the new top-level sibling package (mirrors `publish/`).
- [x] `src/pyforge/atlas/trending_candidates/query.py` -- implement `query_trending_candidates(*, period="weekly", tier="1,2", top=25, not_on_cf=True, min_stars=500, project_path=None, env=None) -> dict`: validate inputs (raise `ValueError` on an unrecognized `--tier` token or an out-of-range `period`/`top`/`min_stars`); load via `_session.bootstrapped_session`/`_session.loaded_catalog` + `_provenance.load_with_provenance(catalog, "trending_candidates_classified")`; filter by period (unless `"all"`), tier set (unless `"all"`), `not_on_cf`, `min_stars` (nulls excluded); sort by `stars_total` desc / `repo_full_name` asc; `.head(top)`; coerce to `list[dict]` (pandas `.to_dict(orient="records")`); return the envelope -- CAP-3's whole query contract (FR-66).
- [x] `src/pyforge/atlas/trending_candidates/__main__.py` -- implement `main(argv=None) -> int` with `argparse` for the 6 flags (mutually-exclusive `--not-on-cf`/`--all` group); call `query.query_trending_candidates(...)`; on `ValueError` print to stderr and return 1; else print `json.dumps(envelope)` under `--json` or a formatted table (`repo_full_name, tier, reason, stars_total, period`) otherwise; `if __name__ == "__main__": raise SystemExit(main())` -- the CLI half of CAP-3.
- [x] `src/pyforge/atlas/mcp/tools.py` -- add the one-line-delegate `query_trending_candidates` tool body + the `_trending` import -- the MCP half of CAP-3, AD-7-compliant.
- [x] `src/pyforge/atlas/mcp/server.py` -- register `@mcp.tool() def query_trending_candidates(...)` wrapping `tools.query_trending_candidates` -- exposes CAP-3 over MCP.
- [x] `tests/mcp/test_no_business_logic_in_tool_bodies.py` -- add `"_trending"` to `ALLOWED_CALL_ROOTS` -- keeps the AD-7 AST gate green for the new tool.
- [x] `conf/base/catalog.yml` -- update the two CAP-3-pending comments to record CAP-3 landed + the cadence decision -- keeps the catalog's own status narration truthful.
- [x] `pixi.toml` -- add the `trending-candidates` task -- makes the CLI runnable via `pixi run`.
- [x] `tests/trending_candidates/test_query.py` -- one test per I/O matrix row above, using a real `DataCatalog(MemoryDataset(fixture_df))` + faked `bootstrapped_session` (never real network/data) -- pins CAP-3's filter/sort/cap/validation/degradation contract.
- [x] `tests/trending_candidates/test_main.py` -- CLI happy-path `--json` output parses as JSON matching `query_trending_candidates`'s return; a bad `--tier` exits 1 with a stderr message -- pins the CLI wrapper.
- [x] `tests/mcp/test_read_surface.py` -- one test proving `tools.query_trending_candidates(...)` delegates byte-for-byte to `_trending.query_trending_candidates(...)` -- pins CLI/MCP output parity at the seam boundary.

**Acceptance Criteria:**
- Given a classified dataset with tier-1, tier-2, and already-on-cf rows across all three periods, when `query_trending_candidates()` runs with default filters, then the result contains only `period=="weekly"`, tier-1/2, not-already-on-cf rows with `stars_total>=500`, sorted by `stars_total` descending.
- Given the CLI is invoked with `--json` and a given filter set, and the MCP tool is invoked with the identical filter set, when both run against the same materialized dataset, then their `count`/`candidates` payloads are identical.
- Given an empty or absent `trending_candidates_classified` dataset, when either surface is queried, then it returns `count: 0` with an empty `candidates` list and no exception.
- Given `pixi run -e pyforge-atlas kedro-test`, when run after this change, then it passes (new tests included, AD-7 AST gate still green).

## Spec Change Log

## Review Triage Log

### 2026-08-09 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 10: (high 2, medium 3, low 5)
- defer: 1: (medium 1)
- reject: 7: (low 7)
- addressed_findings:
  - `high` `patch` A row surviving the `--min-stars` filter with a numeric-looking STRING `stars_total` (e.g. `"1500"`, which genuinely satisfies `>= min_stars` once coerced) kept its original str value post-filter, leaving `stars_total` a mixed str/int object column — `sort_values` on that raised `TypeError: '<' not supported between instances of 'str' and 'int'` (verified live). Fixed by coercing the column ONCE via `df.assign(stars_total=pd.to_numeric(...))` before both the filter and the sort, so both operate on the identical numeric values.
  - `high` `patch` `to_dict(orient="records")` carried raw `NaN` through for any null optional numeric column (e.g. `stars_today`); `json.dumps` renders `NaN` as a bare, non-RFC-8259-conformant token instead of `null`, breaking CAP-3's own literal success signal ("JSON output validates against a documented schema", SPEC.md) — verified live. Fixed via `capped.where(pd.notna(capped), None)` before the dict conversion.
  - `medium` `patch` `logging.disable(logging.INFO)` on the `--json` path was never reset — process-global state a subsequent in-process `main()` call (e.g. under pytest) would silently inherit. Wrapped the whole body in `try/finally`, resetting via `logging.disable(logging.NOTSET)`.
  - `medium` `patch` `_ALREADY_ON_CF_REASON = "already-on-conda-forge"` duplicated `pipelines/upstream_discovery/nodes.py`'s identical inline literal with no shared source of truth — a wording edit there would silently break this filter. Extracted a named `REASON_ALREADY_ON_CF` constant in `nodes.py`, imported into `query.py`.
  - `medium` `patch` `__main__.py` only caught `ValueError`; any other failure (e.g. a Kedro session/credential bootstrap error) would dump a raw traceback instead of a clean stderr message. Broadened to `except Exception`.
  - `low` `patch` `not_on_cf` had no `_validate_*` guard unlike the other four filters — a non-bool value would silently flip filter semantics via truthiness. Added `_validate_not_on_cf`.
  - `low` `patch` `_validate_tier`'s `"all"` sentinel required an exact unstripped match while comma-list tokens are stripped elsewhere in the same function — a whitespace-padded `" all "` was rejected as an unrecognized token. Stripped before the sentinel comparison.
  - `low` `patch` No test seeded more qualifying rows than `--top`'s default of 25, so the cap's actual truncation behavior was unverified. Added `test_top_actually_truncates` (30 rows, `top=5`).
  - `low` `patch` The catalog.yml comment claims CAP-3 surfaces `build_stamp`/`build_stamp_newest` so staleness is visible, but every test used `MemoryDataset` (always `provenance_kind: "unavailable"`) — untestable as written. Added `seed_parquet_catalog` fixture + `test_build_stamp_propagates_through_a_real_parquet_dataset` against a real `ParquetDataset`.
  - `low` `patch` `test_missing_dataset_degrades_to_empty_no_exception`'s docstring claimed to cover "the realistic never-ingested state" but used an undeclared-catalog-key shortcut, not the real production shape (a declared entry whose backing file is missing). Corrected the docstring's claim and added `test_missing_parquet_file_degrades_to_empty_no_exception` against the same `seed_parquet_catalog` fixture.
  - deferred (1, ledger): `query_trending_candidates`'s session-bootstrap step is unguarded against a bootstrap/credential failure (confirmed live: a missing `conf/local/credentials.yml` raises `KeyError` uncaught) — pre-existing in the shared `_session` seam (`read_dataset` has the identical gap), not introduced by this story; a `_session`-seam-wide fix, not a one-file patch.
  - rejected (7, noise): case-sensitive `--tier`/`--period` (working as contracted, fails clearly rather than silently); `min_stars=0` boundary untested (same code path as any positive int, no distinct behavior to miss); two near-duplicate bad-`--tier` tests (harmless redundancy, not a defect); the "session seam never touched" claim unproven by an explicit spy (the test's assertions already indirectly prove the fail-fast path); `tier` column dtype coercion (protected by CAP-2's own hard invariant that `tier` is always stored as a string); the claim that `test_bad_tier_message_names_the_bad_value` could fail from an unsuppressed kedro import banner (empirically disproven — `test_main.py`'s own top-level `from ... import query` deterministically pre-imports kedro at collection time, before capsys attaches); `_print_table` not sanitizing embedded newlines/tabs (cosmetic-only, and none of `_TABLE_COLUMNS`'s five fields can structurally contain one).

### 2026-08-09 — Review pass (follow-up)
- intent_gap: 0
- bad_spec: 0
- patch: 13: (high 3, medium 7, low 3)
- defer: 2: (medium 1, low 1)
- reject: 9: (low 9)
- addressed_findings:
  - `high` `patch` The NaN→`None` coercion added by the previous pass was a SILENT NO-OP on float columns: `DataFrame.where(cond, None)` does not upcast `float64`, so pandas casts the `None` straight back to `NaN`. It only ever worked on an all-null OBJECT column — exactly the single-row shape the guard test used. Any real frame carrying both a value and a null in one optional column (`stars_today`, null whenever a row lacks a daily delta) leaked the bare non-RFC-8259 `NaN` token into `--json`, defeating CAP-3's own success signal (verified live, and reproduced through a real `ParquetDataset` round-trip). Fixed with `.astype(object)` before the `where`.
  - `high` `patch` `test_null_optional_column_serializes_to_json_safe_none` was a FALSE GREEN guarding the above — its one all-`None` row made the column `object` dtype, the single dtype where the broken code worked. Rewritten to two rows, with an explicit `assert df["stars_today"].dtype == "float64"` so a future fixture edit cannot silently re-green it, and a strict `json.loads(..., parse_constant=reject)` round-trip (plain `json.dumps` happily EMITS `NaN`, so dumping alone proved nothing).
  - `high` `patch` `--json` stdout was not pipeable: kedro's rich handler sits on the ROOT logger writing to STDOUT and the root level is WARNING, so the INFO-only `logging.disable` floor let every WARNING record (e.g. kedro's own "Credentials not found in your Kedro project config.") print into the middle of the envelope (verified live: `json.loads(stdout)` raised). Floor raised to `logging.CRITICAL` on the JSON path only; diagnostics still reach the operator on stderr. The test that took "the LAST non-empty line" — a workaround that tolerated precisely this defect — now parses the WHOLE of stdout.
  - `medium` `patch` The period/tier/reason filters were each guarded by `and "<col>" in df.columns`, so a frame missing a column silently SKIPPED that filter and returned every row while `filters` still reported the value the caller asked for — the exact opposite of the `stars_total` branch and of the Boundaries & Constraints rule it states. Verified live: with no `reason` column, `--not-on-cf` returned an already-on-conda-forge repo, the one row CAP-5's Mason handoff must never be given. Each now empties instead; an un-requested filter (`period="all"`, `tier="all"`, `not_on_cf=False`) still needs no column.
  - `medium` `patch` `__main__.py`'s deferred `from . import query` and its `json.dumps(envelope)` both sat OUTSIDE the `except Exception` guard (the outer `try` carried only a `finally`), so an ImportError or an unencodable cell escaped as a raw traceback despite the module documenting a clean stderr message + exit 1 for any failure. Both moved inside the guard (verified live for each).
  - `medium` `patch` The CLI printed `str(exc)` alone, which is meaningless for several failures on that path — a bootstrap `KeyError` printed the bare line `'atlas'`, and a zero-message exception printed an empty line. Now prefixed with the exception type.
  - `medium` `patch` The `finally` reset `logging.disable` to `NOTSET` unconditionally, CLEARING a floor the calling process had deliberately set (verified live: a host at `disable(WARNING)` came back from one in-process `main(["--json"])` with its own suppression silently lifted). Now saves and restores the prior value.
  - `medium` `patch` The story's central claim is CLI/MCP identity BY CONSTRUCTION, but the filter DEFAULTS are declared FOUR times (`query.py`, `mcp/tools.py`, `mcp/server.py`, argparse) and each forwards its own literals, making `query.py`'s defaults dead code on every other path. Concretely: change a default in `query.py` alone and the existing parity test still passes (both CLI sides move together) while the MCP tool keeps sending the old value — a DEFAULT invocation of the two surfaces returning different results. Added `tests/trending_candidates/test_surface_parity.py` pinning all four declarations to one source of truth (`server.py` via AST, mirroring the AD-7 gate's approach).
  - `medium` `patch` `query_trending_candidates` shipped registered on the MCP server but recorded in NO bucket of `mcp/audit.py`, this package's declared and tested record of its MCP surface — the same omission Story 13.1 avoided (`run_upstream_discovery_pipeline` → `PIPELINE_TRIGGER_TOOLS`) and `query_vizro_ai` avoided (`NL_INTERFACE_TOOLS`), and nothing detected it. Added `TRENDING_SURFACE_TOOLS`, plus tests pinning it and asserting every recorded tool is really registered on the server.
  - `medium` `patch` Table mode printed the rows alone, so "never ingested" and "your filters matched nothing" were byte-identical output (`(no candidates)`, exit 0) — and the staleness the `catalog.yml` comment added by this same story promises the surface always shows ("an operator or agent can always see how stale this table is") was visible only under `--json`, i.e. false for the DEFAULT human path the claim describes. Added a provenance/build_stamp/matched header.
  - `low` `patch` `_validate_period` did not strip whitespace although the previous pass patched `_validate_tier` to — so the same padding was accepted on one flag and rejected on the other (`--tier " all "` worked, `--period " weekly "` raised). Stripped, and the normalized value is what `filters` echoes back.
  - `low` `patch` `pd.to_numeric` widens `stars_total` to `float64` as soon as ANY row is null, so one unrelated null flipped every OTHER row's emitted value from `1200` to `1200.0` — in the operator's table and in the machine-readable envelope alike, making a star count's JSON type depend on unrelated rows. Now uses the nullable `Int64` dtype when the values are integral (whose masking treats NA as False, exactly the contracted "a null `stars_total` fails the floor").
  - `low` `patch` Two factual errors in the durable record this story wrote: the atlas memlog claimed "Baseline scoped-stamped to this spec only" while the same commit re-stamped `pyforge-steward/spec-unified-container` too, and it cited `trending-candidates --json` as landing evidence without noting that run returned `count: 0` (no parquet is materialized in a fresh worktree), so it exercised zero rows — which is precisely why the row-shaped defects above survived to landing. Both corrected in place.
  - deferred (2, ledger): CAP-3's "JSON output validates against a documented schema" success signal has no schema artifact anywhere, and the envelope's `schema_version` is borrowed from `_provenance.SCHEMA_VERSION` so the candidate payload cannot be versioned independently (the output IS now strictly RFC-8259-valid and pinned as such; the *documented schema* half is a new deliverable touching CAP-5's consumer contract). And `build_stamp_newest` is `null` in every real response because `provenance.py` sets it only on the `row-fetched-at` path while this dataset resolves to `file-mtime` — a `provenance`-seam-wide decision predating this story, which only surfaces the field.
  - rejected (9, noise): `count` being post-cap with no `total_matched` (contract-conformant — the operator sets the cap and `filters.top` is in the same envelope); `--min-stars 0` still excluding null-star rows (explicitly contracted in Boundaries & Constraints); `--top` capping rows rather than distinct repos under `--period all` (explicitly contracted in **Never**); the `--period "all"` sentinel reuse making fallback-only rows unreachable by default (a deliberate, reasoned Design Notes decision — and the new table header now makes the "0 of N matched" case visible rather than silent); `tier`-column dtype coercion (the previous pass's rejection premise re-verified as still holding — CAP-2's invariant stores `tier` as a string, and the Edge Case Hunter itself confirmed the classifier writes strings today); argparse usage errors exiting 2 rather than 1 (standard CLI convention; the module's contract covers post-parse failures); `test_bad_tier_exits_1_with_stderr_message`'s name promising more than its body (the previous pass rejected the same redundancy, and the adjacent test carries the stderr assertion); the degradation `reason` embedding absolute host paths (matches the existing `read_dataset` seam's established behaviour, and the paths are non-secret); and `query.py`'s import of `pipelines/upstream_discovery/nodes.py` inverting layering — measured rather than assumed at **116 ms** and one Kedro `Pipeline` construction per process with no correctness impact, where the alternatives (a new module for a single string, or re-duplicating the literal the previous pass deliberately de-duplicated) are both worse against this repo's Simplicity First / Surgical Changes principles.

### 2026-08-09 — Review pass (second follow-up)
- intent_gap: 0
- bad_spec: 0
- patch: 11: (high 0, medium 5, low 6)
- defer: 2: (medium 2)
- reject: 9: (low 9)
- addressed_findings:
  - `medium` `patch` `server.py`'s `@mcp.tool()` wrapper re-declares all five filters and forwards them BY HAND, and nothing exercised it: the parity tests compare only default VALUES and `test_read_surface.py`'s delegation proof stops at `tools.py`. Transposing two kwargs in the wrapper (`period=tier, tier=period`) left the ENTIRE suite green (1027 passed) while an MCP client's `period="daily"` reached the query seam as its `tier` — the exact CLI/MCP drift CAP-3's success signal forbids (verified by mutation). Added an AST guard on the forwarding hop (FastMCP is an optional extra, absent here, so the live tool cannot be called); re-ran the same mutation and it now fails.
  - `medium` `patch` `print(payload)`/`_print_table(envelope)` sat OUTSIDE the `except Exception` guard, in an outer `try` carrying only a `finally`, so a write failure escaped as a raw traceback — and the ordinary `trending-candidates -- --json | head` produced exactly that (`BrokenPipeError`, verified live), the failure class a CLI is most likely to meet and precisely what the module documents can never happen. Both moved inside the guard, plus a dedicated `BrokenPipeError` arm that detaches stdout onto `/dev/null` so the shutdown flush cannot print "Exception ignored in: <_io.TextIOWrapper …>" after a clean exit 1.
  - `medium` `patch` `catalog.yml` contradicted itself about whether CAP-3 exists: the header this story edited says CAP-3 landed, while the `trending_candidates` block (untouched, ~line 823) still read "CAP-3 (operator surface) through CAP-5 … pending". The story retired one of the two CAP-3-pending banners. Corrected the second.
  - `medium` `patch` The previous pass's new audit test asserted only `recorded ⊆ registered` — a direction the very defect it was written for (a tool registered on the server and recorded in NO bucket) satisfies trivially, so the next new tool would ship exactly the same way with the suite green. Added the converse assertion, which needed `audit.py` to state the WHOLE surface: added `GENERIC_SURFACE_TOOLS` (the three read/list primitives were the only registered tools no bucket named) + `registered_surface_tools()`. Mutation-verified: dropping one name now fails. Also replaced a tautological `assert audit.TRENDING_SURFACE_TOOLS == (TOOL_NAME,)` (a constant asserted against its own literal).
  - `medium` `patch` The `--json` block claimed diagnostics "still reach the operator, on stderr, via the handler below" — there is no such handler, and `logging.disable(CRITICAL)` suppresses ERROR too. Re-pointing them is not available from that call site (kedro installs its stdout handler via its own `dictConfig` DURING the bootstrap, after this point). Corrected the comment to state what the code does and where a `--json` operator DOES still see a failure: in-band in the envelope (`provenance_kind`/`reason`), and on stderr from the guard.
  - `low` `patch` A non-finite `stars_total` aborted the WHOLE query: a corrupt cell coercing to ±inf (the literal `"inf"`, or an overflowing `"1e400"` — the same dirty-STRING class the numeric coercion exists for) reached the integral narrowing and raised `OverflowError: cannot convert float infinity to integer` (verified live), where the contract promises ONE excluded row. Folded into NA so it takes the identical never-satisfies-the-floor path a null takes; the narrowing also skips out-of-int64-range values.
  - `low` `patch` The previous pass's NaN→`None` guard used `pd.notna`, which says True for ±inf, so `json.dumps` emitted the bare `Infinity` token — as non-RFC-8259 as the `NaN` that pass fixed, and rejected by any strict parser (verified live). Masked, and pinned by a `parse_constant`-rejecting round-trip.
  - `low` `patch` The previous pass's integral-narrowing fix was applied to `stars_total` ALONE, but `stars_today` is null for 2 of the 3 fetched periods BY CONSTRUCTION and `forks_total` is null whenever the scrape lacks the tag — so those columns widened to `float64` and emitted `7.0` for the rows that DO carry a count, the identical "a count's emitted JSON type depends on unrelated rows" defect one column over (verified live). Generalized into `_narrow_integral_floats`, applied to every float column.
  - `low` `patch` `--period all` made the documented "deterministic tie-break for `--top`'s cap" false: the same repo contributes up to 3 rows tied on BOTH sort keys, so which survived `head(top)` was decided by the parquet file's physical row order — identical data re-materialized in a different order returned different rows (verified live). `period` is now the third sort key, making the ordering total.
  - `low` `patch` The table header labelled the POST-cap count `matched=`, so "25 shown of 400 matched" read as "25 matched". Renamed `shown=`; the header's actual purpose (telling "never ingested" from "your filters matched nothing") is served by the provenance/reason lines either way.
  - `low` `patch` A multi-line degradation `reason` printed its continuation lines with no `#` prefix, dropping an un-prefixed `[Errno 2] …` line between header and rows — visible in the ordinary fresh-worktree run. Now prefixed per line.
  - deferred (2, ledger): the default `--not-on-cf` excludes only the literal `already-on-conda-forge`, while CAP-2 also emits `unclassified-needs-human` for "the mapping was unusable, so on-cf could NOT be determined" — so under `--tier all` an on-conda-forge repo can be returned as a candidate (confirmed live via the real classifier with an empty `pypi_conda_mapping`); the intent contract states the single-literal rule explicitly, every such row is tier `skip`, and both surfaces display `reason`, so this is a CAP-5-consumer contract decision, not a patch. And every session-bootstrapping MCP tool inherits kedro's root-logger stdout handler, which would interleave log lines into FastMCP's stdio JSON-RPC channel — seam-wide (`read_dataset`/`list_datasets` share it), and unreachable today since no stdio launcher exists in-repo.
  - rejected (9, noise): `--top` capping rows rather than distinct repos under `--period all` (prior-pass rejection premise re-verified — explicitly contracted in **Never**); the missing documented JSON schema + borrowed `schema_version` (already on the ledger from the previous pass, no new information); absolute host paths in the degradation `reason` (premise re-verified — matches the `read_dataset` seam, non-secret); `query.py` importing `pipelines/upstream_discovery/nodes.py` for one constant (premise re-verified — measured at 116 ms, and this is the AD-1-permitted direction: consumer→pipelines, never pipelines→orchestration); a non-tabular catalog value raising an opaque `ValueError` (needs a hand-corrupted catalog override, not a production shape); emptying the frame when `repo_full_name` is absent (it is a sort/display column, not a filter — emptying on its absence would be wrong); no pre-cap `total_matched` in the envelope (premise re-verified — the operator sets the cap and `filters.top` rides along; the false `matched=` LABEL was a real defect and is patched above); `test_bad_tier_exits_1_with_stderr_message`'s name promising more than its body (rejected in both prior passes); and three cosmetics (the conftest docstring naming one of its two fixtures, an unused `from __future__ import annotations`, and the CLI's absence from `[project.scripts]` — the Code Map contracts the pixi task).

### 2026-08-10 — Review pass (third follow-up)
- intent_gap: 0
- bad_spec: 0
- patch: 7: (high 0, medium 3, low 4)
- defer: 1: (medium 1)
- reject: 9: (low 9)
- addressed_findings:
  - `medium` `patch` The previous pass's `BrokenPipeError` fix was a NO-OP for the case it was written for. stdout is BLOCK-buffered whenever it is a pipe and no realistic envelope fills that buffer, so `print` returned cleanly and the error surfaced only in the interpreter's SHUTDOWN flush — outside the guard — as `Exception ignored while flushing sys.stdout` and exit 120. That pass verified its fix in a shell exporting `PYTHONUNBUFFERED=1`, ambient here and set by neither `pixi.toml` nor the Containerfile, which is exactly what hid it: under `env -u PYTHONUNBUFFERED … --json | head` the guard never ran (verified live, both ways). An explicit `sys.stdout.flush()` inside the guard fixes it — the same command now exits 1 with empty stderr. The existing test could not catch it: its `StringIO` raises inside `write`, i.e. models only the unbuffered case. Added a real-pipe in-process test and a subprocess test that runs with the variable explicitly unset; removing the flush fails both.
  - `medium` `patch` That guard's `os.dup2` retargeted the descriptor for the WHOLE process with nothing ever undoing it, and leaked the devnull fd — so a host calling `main()` in-process (the same callable API the previous pass added `test_json_restores_the_callers_own_logging_floor` for, on identical reasoning about process-global state) came back with its own stdout pointed at `/dev/null` for good. Now guarded on `sys.stdout is sys.__stdout__` — a host that redirected stdout has no shutdown flush to silence anyway — and the fd is closed. Mutation-verified.
  - `medium` `patch` The envelope carried ONE count, and the two prior passes rejected the adjacent finding partly ON A HEADER THAT DOES NOT EXIST ("the new table header now makes the '0 of N matched' case visible rather than silent"). The rejected scenario is real and production-reachable: `datasets/upstream_discovery.py` falls back to the Search API when the HTML scrape yields zero rows across all THREE windows and stamps every fallback row `period="all"`, so a fully-populated, freshly-refreshed table can consist entirely of rows the DEFAULT `--period weekly` cannot match — answering with a byte-identical `count: 0` / `shown=0  (no candidates)` to a healthy table nothing qualified in, under a fresh `build_stamp` saying all is well. `rows` (loaded) and `matched` (post-filter, pre-cap) now ride in the envelope and the table header, making the degraded state legible (`rows=2  matched=0`) and truncation visible for the first time (`rows=31  matched=30  shown=5`, verified live against a seeded parquet). The Code Map's envelope enumeration is updated to match.
  - `low` `patch` The previous pass's "every registered tool is recorded" guard matched only the CALL form `@mcp.tool()`, so a tool registered with the bare `@mcp.tool` — a spelling FastMCP accepts — was invisible to it and the next unrecorded tool would ship exactly the way `query_trending_candidates` did, suite green, for want of two parentheses (mutation-verified: 13 detected either way with the bare form, 14 with the call form). Both spellings now match, pinned by a mutation test.
  - `low` `patch` `_validate_tier` echoed `" 1 , 2 "` back as `"1 , 2"` while `_validate_period` returns its fully-stripped value — pinned by its own test's "normalized, not echoed padded" — so two callers sending the same tier set got byte-different envelopes for an identical candidate list. Normalized to the joined tokens.
  - `low` `patch` `query.py`'s docstring still documented the two-key sort the previous pass replaced with three: the patch that fixed `--top`'s determinism left its own stated contract behind.
  - `low` `patch` `tier-taxonomy.md`'s "Operator-surface parameters (CAP-3)" table still listed `--period` as `daily|weekly|monthly` and `--tier` as a single value, while `query.py`'s docstring, the CLI's `--help` and the pixi task description all cite that table as the authority for the flag domain. Reconciled to the shipped domain with an explicit as-built note — the same narration fix this story already did for `catalog.yml`.
  - deferred (1, ledger): `mcp/tools.py::read_dataset` — the seam this story was modelled on — returns `to_dict(orient="records")` with no NaN/±inf masking, so every MCP read of a Parquet-backed dataset with a null in a numeric column emits the bare non-RFC-8259 `NaN` token that two passes classed `high` on this story's own path (confirmed live). Pre-existing since B3 and seam-wide; `read_dataset` is deliberately pandas-free for the AD-7 gate, so the fix belongs in the shared coercion layer, not in this file.
  - rejected (9, noise): four dtype/coercion findings whose triggering shapes the writer cannot produce — a finite-but-absurd `stars_total` (`1e19`) ranking first, `_narrow_integral_floats` skipping a whole column on one non-finite cell so a neighbour emits `7.0`, that narrowing running after `head(top)` so `--top` changes a surviving row's JSON type, and a non-JSON-native cell (Timestamp/bytes/decimal) breaking `--json` and the MCP hop — all require a hand-corrupted parquet or a bypass writer: `parse_trending_html`/`parse_search_api_response` emit `int | None` for every count via `_parse_count`/`_safe_int`, matching the prior passes' own "not a production shape" rejection standard, and the CLI already degrades cleanly on the last one; `--period all` truncation being input-order-dependent (re-measured — pandas multi-key `sort_values` IS stable, so this needs two rows tied on all three keys, i.e. the same repo listed twice on one trending page); the `--period all` sentinel making fallback rows unreachable by DEFAULT (the sentinel itself stays — a reasoned Design Notes decision the intent contract states — but the visibility half of the prior rejection's premise was false and is patched above); `build_stamp_newest` missing from the table header (it is `null` in every real response for this dataset type, and that is already on the ledger); and CAP-3's undelivered documented JSON schema (already on the ledger from the previous pass, no new information).

## Design Notes

**Why `--period` gains a 4th value (`all`) beyond the taxonomy's enumerated 3.** The raw
`trending_candidates` dataset tags GitHub Search-API-fallback rows `period="all"` literally
(`datasets/upstream_discovery.py::_SEARCH_API_FALLBACK_PERIOD`). The taxonomy's flag table
only lists `daily`/`weekly`/`monthly` as selectable windows, which would make fallback rows
permanently unreachable through this surface — in tension with the epic's own "never silently
drop a repo" thread running through CAP-1/CAP-2. Reusing the word `all` (already meaningful as
a `--tier` value) as "no period filter" is the minimal, consistent extension: the default
(`weekly`) stays exactly the taxonomy's stated default, and `all` is an explicit opt-in that
also surfaces the multi-period duplicates transparently rather than hiding them.

**The cadence deferred item is settled by decision, not by a schedule change.** Story 13.2's
review flagged that CAP-3, the first consumer, "must decide the cadence deliberately." The
decision: CAP-3 reads whatever is currently materialized and surfaces its own
`build_stamp`/`build_stamp_newest` in every response (mirroring `read_dataset`'s provenance
envelope) — an operator or agent can always see how stale the classified set is. Coupling the
classifier to the daily ingest job remains a cross-pipeline scheduling change out of this
story's scope (unchanged from 13.2's own boundary).

**Why the query module imports `pyforge.atlas.mcp.session` from outside `mcp/`.** `session.py`
has no FastMCP/business-logic dependency (stdlib + kedro only), so reusing it from a new
top-level package avoids inventing a second Kedro-bootstrap path; only `mcp/tools.py` itself is
AST-gated (AD-7), and this module lives outside that gate by design — the same reuse shape
`provenance.py` already has (a plain module, freely importable, that only `mcp/tools.py`'s
*bodies* are restricted from touching directly).

## Verification

**Commands:**
- `pixi run -e pyforge-atlas kedro-test` — expected: pass (station policy verify command; reconciled 2026-08-30 after policy drifted from this spec's original declaration).
- `pixi run -e pyforge-atlas kedro-catalog-check` — expected: pass (station policy verify command; reconciled 2026-08-30 after policy drifted from this spec's original declaration).

## Auto Run Result

Status: `done` — third follow-up review pass on the already-landed CAP-3 surface. No
intent gap, no spec repair; 7 patches applied, 1 finding deferred, 9 rejected.

**Implemented change (this pass).** Two of the three medium patches close defects the
PREVIOUS pass believed it had fixed, both because its live verification ran under an
ambient `PYTHONUNBUFFERED=1` that the repo does not set: the `BrokenPipeError` guard
never ran under block-buffered stdout, and the `os.dup2` it used to silence the shutdown
flush retargeted fd 1 for the whole process. The third makes the CAP-1 Search-API
fallback shape legible instead of silent. The rest are guard-completeness and
documentation-truthfulness fixes.

**Files changed**
- `src/pyforge/atlas/trending_candidates/__main__.py` — `sys.stdout.flush()` inside the
  guard; `dup2` only when `sys.stdout is sys.__stdout__`, with the devnull fd closed; the
  table header now prints `rows`/`matched`/`shown`.
- `src/pyforge/atlas/trending_candidates/query.py` — `rows`/`matched` in the envelope;
  `_validate_tier` echoes normalized tokens; docstring corrected to the three-key sort and
  the three counts.
- `tests/trending_candidates/test_main.py` — real-pipe in-process test (buffered write +
  host-fd survival) and a subprocess test run with `PYTHONUNBUFFERED` explicitly unset;
  fallback-shaped table-header test.
- `tests/trending_candidates/test_query.py` — `rows`/`matched` on the truncation and empty
  paths; fallback-shape test; normalized-`tier` echo test.
- `tests/trending_candidates/test_surface_parity.py` — registry guard matches `@mcp.tool`
  and `@mcp.tool()` alike, pinned by a mutation test.
- `_bmad-output/.../spec-upstream-discovery/tier-taxonomy.md` — CAP-3 parameter table
  reconciled to the shipped flag domain with an as-built note.
- `_bmad-output/.../spec-pyforge-atlas/.memlog.md` + `scripts/.spec-surface-baseline.json`
  — reconciling entry, then a baseline re-stamp scoped to this spec only.

**Review findings breakdown.** patch 7 (medium 3, low 4) — all applied; defer 1 (medium) —
appended to `deferred-work.md` as a NEW entry (`read_dataset` leaks bare `NaN` through the
MCP boundary; seam-wide, pre-existing since B3); reject 9 (low) — four dtype/coercion
findings whose triggering shapes the writer cannot produce (`_parse_count`/`_safe_int` emit
`int | None`), an order-dependence finding re-measured away (pandas multi-key `sort_values`
is stable), the `--period all` sentinel itself (a contracted Design Notes decision — only
the visibility half of the prior rejection's premise was false, and that is patched), and
two already on the ledger. Two prior-pass rejections were re-tested rather than inherited;
one of them (the fallback shape's invisibility) rested on a table header that never existed
and became this pass's third medium patch.

**Verification performed**
- `pixi run --frozen -e pyforge-atlas kedro-test` — **1042 passed, 19 skipped** (1035 before).
- `pixi run --frozen -e pyforge-atlas pytest tests/trending_candidates tests/mcp -q` — **89
  passed** (82 before).
- Mutation-verified both behavioural fixes: removing `sys.stdout.flush()` fails the two new
  pipe tests; removing the `sys.stdout is sys.__stdout__` guard fails the host-fd test.
  Mutation-verified the registry guard: a bare `@mcp.tool` probe is now detected.
- Live against a SEEDED 31-row parquet (the gap that let row-shaped defects survive prior
  passes): table header `rows=31  matched=30  shown=5`; `--json` round-trips through a
  strict parser with integral counts still ints (`1029`, `7`, `null`);
  `env -u PYTHONUNBUFFERED … --json | head -c 0` exits **1 with empty stderr** (it printed
  `Exception ignored while flushing sys.stdout` before this pass). Seeded data removed.
- `python3 scripts/spec_surface_check.py` — `OK: every tracked file governed or allowlisted;
  no drift`.

**Residual risks.** The `--not-on-cf` / `unclassified-needs-human`, documented-JSON-schema,
`build_stamp_newest`, session-bootstrap and stdio-logging items remain open on the ledger,
all owned by seams or stories outside 13.3. The new `rows`/`matched` keys are additive to
the envelope; any consumer written against the previous shape is unaffected.

**Follow-up review recommendation:** `true` — three medium patches, two of which corrected
fixes a previous pass wrongly believed complete, plus an additive change to the envelope
contract and the table's default human output. An independent pass is worth it; the trend
across passes is that each one finds fewer and shallower defects.

## Status reconcile 2026-09-20

- frontmatter `status` `shipped` → `done` (ledger row `12-3-trending-candidates-operator-surface-fr-66: done`).
