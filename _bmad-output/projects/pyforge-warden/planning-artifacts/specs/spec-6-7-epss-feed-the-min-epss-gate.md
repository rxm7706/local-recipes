---
title: 'Story 6.7: EPSS feed + the `--min-epss` gate'
type: 'feature'
created: '2026-07-24'
status: shipped
updated: '2026-07-27 (AUD-WARDEN-030 status sync)'
review_loop_iteration: 0
followup_review_recommended: false
baseline_revision: 'd339757ff821e6aff0c09f3c9b08ee3749e3eede'
final_revision: 'a85d69471f06fc10942e98782fcbdd4779be516e'
context: []
warnings: ['oversized']
---

<intent-contract>

## Intent

**Problem:** `Finding.epss` and `ComplianceReport.epss_data` are declared, schema-validated slots (Story 6.1) that no producer ever populates, and no `--min-epss` gate exists — a security engineer can't prioritize or block on real-world exploit probability the way `--fail-on-kev` already lets them block on known exploitation.

**Approach:** Mirror Story 6.4's KEV mechanism exactly, reusing the shared `feeds.py` cache/provenance/staleness layer and `OsvParse.kev_candidates`: add an EPSS-feed lookup step to `OsvEngine` (`_epss_enrichment`/`_stamp_epss`, paralleling `_kev_enrichment`/`_stamp_kev`), a `min_epss: float | None` escalation param on `vuln_rung` (paralleling `fail_on_kev`), a real two-mode `--min-epss <0..1>` CLI flag (mirrors `--max-lag`, not TOML-only like `--fail-on-kev`), and thread the already-reserved `epss_data` field through `EngineResult`/`assemble_report`. No schema or model changes.

## Boundaries & Constraints

**Always:**
- `feeds.py` owns cache location/lifecycle/staleness math; this story adds ONLY `epss_cache_path`, `load_epss_scores`, `write_epss_cache` as siblings of the existing KEV trio — no new cache-root or staleness logic.
- `_epss_enrichment(min_epss)` is called at engines.py:771 alongside `_kev_enrichment` (same pipeline position — right after DB staleness, before any `vuln:` finding is parsed) and returns a 3-tuple mirroring `_kev_enrichment`'s shape. `_stamp_epss` is called at engines.py:953-955 alongside `_stamp_kev`, BEFORE `EngineResult` returns — the engine-dedup loop must never see an un-stamped finding.
- `epss_stale_finding(*, unavailable: bool)` (vuln.py, mirrors `kev_stale_finding` verbatim) mints `indeterminate:epss-data-unavailable:epss-feed` / `indeterminate:epss-data-stale:epss-feed`, `axis=AXIS_VULNERABILITY`, `severity=None` — emitted ONLY when `min_epss is not None` (gate active), exactly as `kev_stale_finding` gates on `fail_on_kev`.
- `vuln_rung(finding, *, policy=None, fail_on_kev=False, min_epss=None)` gains: when `min_epss is not None and finding.epss is not None and finding.epss.score >= min_epss`, force `Status.POLICY_VIOLATION` — escalate-only (never downgrades an already-stronger status; never fires when `finding.epss is None`).
- `--min-epss` is a real two-mode CLI flag: `_min_epss_type` (argparse `type=`, mirrors `_max_lag_type`) validates `0.0 <= value <= 1.0` (usage error, exit 2, otherwise). `config.py` gets `min_epss: float | None = None`, `_coerce_min_epss` (mirrors `_coerce_fail_under_coverage`'s range-check shape), `"min-epss"` in `_RECOGNIZED_KEYS`, and `cli_min_epss` threaded through `ConfigLoader.load`/`default_with_cli_overrides` exactly where `cli_max_lag` is (config.py:329-390, 741-889).
- `EngineResult` (interfaces.py) gains `epss_data: FeedProvenance | None = None` (mirrors `kev_data`); `assemble_report` (report.py) gains the same param, threaded into `ComplianceReport(...)` at line 417. `report.py` never computes EPSS provenance itself — `cli.py` selects the first non-`None` `EngineResult.epss_data` across `engine_results` (mirrors the existing `kev_data`/`currency_data` selection blocks at cli.py:1077/1091) and passes it in.
- `OsvEngine.__init__` gains `min_epss: float | None = None` alongside `fail_on_kev`; `cli.py`'s existing special-case construction (line 882, `OsvEngine(fail_on_kev=config.fail_on_kev)`) extends to also pass `min_epss=config.min_epss` — no new branch.
- EPSS matching reuses `OsvParse.kev_candidates` (finding.id -> CVE-alias tuple) verbatim — no new candidate-collection mechanism. `epss_match(candidates, scores) -> tuple[float, float] | None` mirrors `kev_match`'s first-hit-wins semantics.
- The real FIRST.org EPSS feed is gzip CSV (`cve,epss,percentile`), unlike KEV's JSON. `scripts/refresh_epss_feed.py` fetches/decodes/normalizes into a cached JSON document (`{"scores": [{"cve": ..., "epss": ..., "percentile": ...}, ...]}`) — never caching raw CSV — following `refresh_kev_feed.py`'s actual shipped pattern (hardcoded URL + `urllib.request`; dev/ops-only, never imported by the installed package, NFR-S2).
- Standing cross-cutting gates hold: zero false-green on fixtures (C0), no schema/model change, the producer-ceiling precedent (`min_epss=None` stays the default so an unconfigured call is unaffected), deny-by-default socket harness, twice-run byte-identical determinism (NFR-R3b).

**Block If:**
- The chosen normalized cache-document shape for EPSS turns out incompatible with how `feed_provenance`/`is_feed_stale` expect a snapshot path to behave — would indicate a `feeds.py` contract gap, not something to patch around blind.

**Never:**
- No schema/model/`report-schema.json` change — `Epss{score,percentile}`, `Finding.epss`, `ComplianceReport.epss_data`, and the schema's `epss`/`epss_data` slots are ALL already shipped (Story 6.1); widening any of them here breaks the "no 6.x producer story may widen the schema" rule.
- No change to `kev_stale_finding`/`_kev_enrichment`/`_stamp_kev`/the KEV cache functions — EPSS additions are new siblings, never edits to the KEV path.
- No fix for the known cross-axis coverage gap (deferred-work.md: `deps_assessed == deps_total` still reports even when a stale-feed finding forces the axis `indeterminate`) — EPSS inherits the identical, already-accepted shape; not this story's fix.
- No `_http.py` module introduction — `refresh_epss_feed.py` follows the actual shipped `urllib.request` + hardcoded-URL pattern, not that planning-doc reference.
- No autouse EPSS-ambient-cache `conftest.py` fixture — `min_epss` defaults `None` (gate off), unlike KEV's default-on `fail_on_kev=True`, so the existing suite needs no ambient EPSS cache to stay green.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|---|---|---|---|
| No `--min-epss` set | any finding, feed present or absent | `epss` populated on a cache hit (informational only); rung/exit byte-identical to pre-6.7 CVSS-only gating | No error |
| `--min-epss 0.5`, feed present, score at/above threshold | cached score 0.7 for the matched CVE | `finding.epss={score:0.7,...}`; rung `policy-violation`, exit 1 | No error |
| `--min-epss 0.5`, feed present, score below threshold | cached score 0.2 | `finding.epss` populated; rung unaffected (CVSS-only gating still applies) | No error |
| `--min-epss` set, feed absent/unreadable | no cache dir / no file / corrupt | whole-axis `indeterminate:epss-data-unavailable:epss-feed`; status `indeterminate`, exit 1 — never a pass | No error |
| `--min-epss` set, feed stale | snapshot older than `feeds.DEFAULT_FEED_MAX_AGE_DAYS` | whole-axis `indeterminate:epss-data-stale:epss-feed`; per-finding matching still attempted against the aged catalog | No error |
| `--min-epss` unset, feed stale/absent | any state | no EPSS consultation at all (mirrors `fail_on_kev=False` skipping `_kev_enrichment`) | No error |
| Both `--fail-on-kev` and `--min-epss` active on the same finding | `kev=true`, `epss.score>=threshold` | both escalate to `policy-violation` (idempotent — already the ceiling) | No error |

</intent-contract>

## Code Map

- `src/pyforge/warden/feeds.py` -- add `_EPSS_FEED_DIR_NAME`/`_EPSS_FEED_FILENAME`, `epss_cache_path(cache_dir)`, `load_epss_scores(path) -> dict[str, tuple[float, float]] | None`, `write_epss_cache(cache_dir, document)` -- siblings of the KEV trio, same shape/error handling
- `src/pyforge/warden/vuln.py` -- `epss_stale_finding(*, unavailable: bool) -> Finding` (mirrors `kev_stale_finding`); `epss_match(candidates, scores) -> tuple[float, float] | None` (mirrors `kev_match`); `vuln_rung(..., min_epss: float | None = None)` gains the threshold-escalation branch
- `src/pyforge/warden/engines.py` -- `_epss_enrichment(min_epss)` (mirrors `_kev_enrichment`, called at line 771 alongside it); `_stamp_epss` (mirrors `_stamp_kev`, called at lines 953-955 alongside it, sets `finding.epss=Epss(...)` via `dataclasses.replace` only on a match); `OsvEngine.__init__` gains `min_epss: float | None = None`
- `src/pyforge/warden/interfaces.py` -- `EngineResult` gains `epss_data: FeedProvenance | None = None` (mirrors `kev_data`)
- `src/pyforge/warden/config.py` -- `EffectiveConfig.min_epss: float | None = None`; `_coerce_min_epss(value) -> float` (range `[0,1]`); `"min-epss"` in `_RECOGNIZED_KEYS`; `cli_min_epss` threaded through `ConfigLoader.load`/`default_with_cli_overrides` (mirrors `cli_max_lag`, config.py:329-390, 741-889)
- `src/pyforge/warden/cli.py` -- `_min_epss_type(value) -> float` (mirrors `_max_lag_type`); `--min-epss` argparse flag; extend the existing special-case at line 882 to `OsvEngine(fail_on_kev=config.fail_on_kev, min_epss=config.min_epss)`; `epss_data` selection block (mirrors `kev_data`'s at lines 1077-1080) threaded into `assemble_report(..., epss_data=epss_data)`
- `src/pyforge/warden/report.py` -- `assemble_report` gains `epss_data: FeedProvenance | None = None` param, threaded into `ComplianceReport(...)` at line 417 (mirrors `kev_data=kev_data`)
- `src/pyforge/warden/scripts/refresh_epss_feed.py` -- **new**, mirrors `refresh_kev_feed.py`'s fetch/validate/cache/exit-code contract, adapted for FIRST.org's gzip-CSV feed, normalizing into the cached JSON `{"scores": [...]}` shape
- `tests/unit/test_feeds.py`, `tests/unit/test_vuln.py`, `tests/unit/test_config.py` -- EPSS-cache-layer, `epss_stale_finding`/`epss_match`/`vuln_rung(min_epss=...)`, and config coercion/threading coverage (mirror the existing KEV/`max_lag` blocks)
- `tests/conformance/test_epss_enrichment.py` -- **new**, mirrors `tests/conformance/test_kev_enrichment.py`'s 10-test structure (match/no-match stamping, gate-off skips consultation entirely, feed-absent/stale forces indeterminate, threshold forces exit 1 regardless of CVSS tier, byte-identical when gate off, E2E `cli.main()` composition)
- `tests/unit/test_refresh_epss_feed.py` -- **new**, mirrors `tests/unit/test_refresh_kev_feed.py`'s fetch/validate/cache/exit-code coverage, adapted for gzip-CSV parsing

(All paths above are relative to `src/shared/packages/pyforge-warden/`.)

## Tasks & Acceptance

**Execution:**
- [x] `src/pyforge/warden/feeds.py` -- `epss_cache_path`/`load_epss_scores`/`write_epss_cache` -- the EPSS cache/provenance sibling trio
- [x] `src/pyforge/warden/vuln.py` -- `epss_stale_finding`, `epss_match`, `vuln_rung(min_epss=...)` -- feed-absence finding + threshold escalation
- [x] `src/pyforge/warden/engines.py` -- `_epss_enrichment`, `_stamp_epss`, `OsvEngine(min_epss=...)` -- wires EPSS consultation + stamping into the vuln producer
- [x] `src/pyforge/warden/interfaces.py` -- `EngineResult.epss_data` -- reserves the cross-engine selection slot (also threads `self._config.min_epss` into `vuln_rung` in `DefaultPolicy.evaluate`, mirroring `fail_on_kev` — required for the gate to have any effect end to end)
- [x] `src/pyforge/warden/config.py` -- `min_epss` field + `_coerce_min_epss` + recognized key + CLI threading -- two-mode gate config surface
- [x] `src/pyforge/warden/cli.py` -- `--min-epss` flag + engine construction + `epss_data` selection + `assemble_report` threading -- gate activation end-to-end
- [x] `src/pyforge/warden/report.py` -- `assemble_report(epss_data=...)` -- report-level provenance threading
- [x] `src/pyforge/warden/scripts/refresh_epss_feed.py` -- new refresh script -- opt-in-online provisioning path
- [x] `tests/unit/test_feeds.py` -- EPSS cache round-trip + malformed-input coverage -- cache-layer correctness
- [x] `tests/unit/test_vuln.py` -- `epss_stale_finding`/`epss_match`/`vuln_rung(min_epss=...)` coverage (escalate at/above, not below, never on `epss=None`) -- escalation correctness
- [x] `tests/unit/test_config.py` -- `min_epss` coercion + CLI-overrides-TOML precedence -- config surface correctness
- [x] `tests/conformance/test_epss_enrichment.py` -- gate-off no-consultation, match/no-match stamping, absent/stale forces indeterminate, threshold forces exit 1, E2E `cli.main()` -- end-to-end proof
- [x] `tests/unit/test_refresh_epss_feed.py` -- fetch/parse/cache/exit-code coverage for the refresh script -- provisioning-path correctness

**Acceptance Criteria:**
- Given a provisioned FIRST EPSS feed, when a security finding's CVE matches a cached score, then the finding carries `epss {score, percentile}` with per-feed provenance, and `--min-epss <threshold>` composes `policy-violation` for any finding whose score is at or above the threshold.
- Given an absent or stale EPSS snapshot while `--min-epss` is set, when the scan runs, then the verdict is `indeterminate` with an EPSS-provenance driver — never a silent no-op; with no `--min-epss` set, a stale/absent snapshot changes nothing.
- Given `--min-epss` unset, when the identical fixtures run, then findings and rungs are byte-identical to the pre-6.7 CVSS/KEV-only gating (no regression to `--fail-on-kev`'s own behavior).
- Given `--deterministic`, when the same fixtures run twice, then the report is byte-identical; `verdict.py`, the schema, and every non-vulnerability axis stay untouched.

## Spec Change Log

(No bad_spec loopback occurred during this story's review pass — empty.)

## Review Triage Log

### 2026-07-24 — Review pass

- intent_gap: 0
- bad_spec: 0
- patch: 8: (high 1, medium 2, low 5)
- defer: 2: (medium 1, low 1)
- reject: 1: (low 1)
- addressed_findings:
  - `[high]` `[patch]` Both reviewers independently found that `engines._stamp_epss` constructed `Epss(score=..., percentile=...)` with no `try/except` — `feeds.load_epss_scores` validates only shape (a non-bool number), never the `[0, 1]` domain `models.Epss.__post_init__` enforces, so a corrupted/out-of-range cached score (e.g. `2.0`) raised an uncaught `ValueError` and crashed the whole scan instead of degrading to the documented `indeterminate` outcome — directly contradicting the "never a silent pass" (and never a crash) design goal. Fixed: the construction is now wrapped, degrading to "no stamp" (same as a non-match) on `ValueError`; added `test_out_of_range_cached_score_degrades_instead_of_crashing`.
  - `[medium]` `[patch]` `_min_epss_type` (the actual argparse `type=` callback wired to `--min-epss`) had zero direct test coverage — every existing test called `ConfigLoader.load`/`EffectiveConfig.default_with_cli_overrides` with an already-parsed float, bypassing argparse entirely, so a wrong `type=` or a misspelled flag string would not have been caught. Added three usage-error tests (`test_min_epss_rejects_a_negative_value_as_a_usage_error`, `..._an_out_of_range_value...`, `..._a_non_numeric_value...`) mirroring `test_max_lag_rejects_*`'s precedent in `test_scan_harness.py`.
  - `[medium]` `[patch]` The realistic out-of-the-box default combination — `fail_on_kev` defaults `True`, so adding `--min-epss` activates BOTH gates simultaneously — was never exercised end-to-end; every new conformance test deliberately isolated EPSS via the `vuln_kev_fail_on_kev_false` fixture. Added `test_default_fail_on_kev_and_min_epss_both_active_on_the_same_finding` (the `vuln_kev` default fixture, one cache dir carrying both a KEV and an EPSS match for the same aliased CVE).
  - `[low]` `[patch]` `epss_stale_finding`'s user-facing message said "the FIRST EPSS feed", inconsistent with every other "FIRST.org EPSS feed" reference in the same diff (and with `kev_stale_finding`'s fully-spelled "the CISA KEV feed" convention it mirrors). Fixed the string; no test asserted the old wording.
  - `[low]` `[patch]` `refresh_epss_feed.py`'s CSV-header check required an EXACT match (`set(reader.fieldnames) != _EXPECTED_FIELDNAMES`) with no forward-compat fallback — a single new column FIRST.org adds to the public feed would hard-fail provisioning. Loosened to a subset check (still fails loud if `cve`/`epss`/`percentile` is missing); added `test_fetch_epss_scores_tolerates_an_extra_column`.
  - `[low]` `[patch]` The same script accepted a CSV row with an empty `cve` but valid numeric fields (asymmetric with `feeds.load_epss_scores`, which does check `cve` is non-empty on the read side), silently inflating the reported `score_count` with an unusable entry. Added a non-empty-`cve` skip (mirrors the read-side tolerance) and `test_fetch_epss_scores_skips_a_row_with_an_empty_cve`.
  - `[low]` `[patch]` `test_min_epss_unset_is_byte_identical_cvss_only_gating`'s name overclaimed a full byte-for-byte report comparison the test never performed (it only asserts specific fields: rc/status/epss/epss_data). Renamed to `test_min_epss_unset_leaves_cvss_only_gating_unaffected`; no test depended on the old name.
- Deferred (2, appended to `deferred-work.md` as NEW entries): `OsvParse.kev_candidates`'s name now serves a second, non-KEV-exclusive purpose (EPSS matching reuses it verbatim per this story's own Boundaries) — a naming-only refactor spanning both the 6.4 and 6.7 code paths, out of this story's single-file-patch scope; the EPSS cache inherits the shared `feeds.DEFAULT_FEED_MAX_AGE_DAYS` (7 days) without a deliberate evaluation of EPSS's own daily-publication cadence — directed by this story's own boundaries ("no new cache-root or staleness logic"), mirrors an identical open tuning question already ledgered for the endoflife.date feed.
- Rejected (1): a reviewer's "no traceability to a spec/FR document in the diff" observation — the diff-only reviewer had no visibility into this project's Tier-2/Tier-3 artifact split (the authoritative spec lives at this very file, tracked through a gitignored `implementation-artifacts` path the diff never touches); not a defect in the change itself.

All 8 patch fixes applied; full suite re-verified green (1726 passed, was 1719, net +7 tests) after patching.

### 2026-07-24 — Follow-up review pass (fresh Blind Hunter + Edge Case Hunter, post-done re-review)

- intent_gap: 0
- bad_spec: 0
- patch: 8: (high 1, medium 3, low 4)
- defer: 3: (medium 1, low 2)
- reject: 4: (low 4)
- addressed_findings:
  - `[high]` `[patch]` A present, fresh, but domain-corrupt EPSS cache entry silently disabled the gate — `feeds.load_epss_scores` validated only shape (its own docstring PROMISED a finiteness check the code never performed, and `json.loads` happily parses `NaN`/`Infinity` tokens and out-of-range numbers), so a matched entry like `epss: 2.0` survived to `_stamp_epss`, whose prior-pass crash-guard silently skipped the stamp — `finding.epss` stayed `None`, `vuln_rung` never fired, exit 0 with no indeterminate signal: a reachable false-green in a gate whose help text promises "never a silent pass". Fixed at the load layer: `load_epss_scores` now skips any entry whose `epss`/`percentile` is non-finite or outside `[0, 1]` (implementing its own documented contract; every surviving catalog entry is trustworthy by construction, mirroring `load_kev_catalog` skipping malformed `cveID` entries); `_stamp_epss`'s `try/except` stays as a last-resort crash-guard, both functions' docstrings re-grounded. Added `test_load_epss_scores_skips_non_finite_and_out_of_domain_entries` (NaN/±Infinity/2.0/-0.1/1.5-percentile all skipped; boundary 0.0/1.0 survives).
  - `[medium]` `[patch]` `refresh_epss_feed.py` performed zero domain validation — `float(row["epss"])` accepts `"nan"`/`"inf"`/`"2.0"`/`"-1"`, so garbage upstream rows were cached as usable (inflating `score_count` and defeating the zero-usable guard), and a cached `NaN` would not even be strict JSON (`json.dump` defaults `allow_nan=True`). The row parse now skips non-finite/out-of-`[0, 1]` values for both fields (mirroring the read-side filter, closing the realistic entry path for the high finding); added `test_fetch_epss_scores_skips_non_finite_and_out_of_domain_rows`.
  - `[medium]` `[patch]` The stale-feed path had no end-to-end coverage (engine-level only) and the `--min-epss` help flatly said a stale feed "composes 'indeterminate'" — leaving unproven which of the two simultaneous outcomes (whole-axis stale-indeterminate vs. a stale-catalog match escalating to policy-violation) wins composition. Added `test_epss_feed_stale_end_to_end_never_composes_a_pass` pinning the full `cli.main()` composition (policy-violation outranks indeterminate per the verdict ladder; exit 1; both findings present; `epss_data.max_age_ok` false) and made the help text precise ("composes at least 'indeterminate' (exit 1; a stale feed's still-matchable scores may escalate further, to 'policy-violation')").
  - `[medium]` `[patch]` The TOML mode of the "real two-mode flag" headline claim was never proven past `ConfigLoader.load` — every E2E test passed `--min-epss` on the CLI, so a cli.py wiring bug reading `args.min_epss` instead of `config.min_epss` in the engine loop would have passed the whole suite. Added fixture project `vuln_min_epss_toml` (`min-epss = 0.5` in its own `[tool.pyforge-warden]`, no CLI flag) + `test_toml_only_min_epss_drives_the_gate_end_to_end` (TOML alone drives consultation, stamping, escalation, exit 1).
  - `[low]` `[patch]` `test_zero_vuln_matchable_candidates_never_consults_epss` overclaimed — it asserted only output shape, which an implementation that DID open the cache but matched nothing would also satisfy. Strengthened with a fail-sentinel monkeypatch on `feeds.load_epss_scores` so "never consulted" is the thing actually proven (the empty-inventory short-circuit at engines.py:858 precedes `_epss_enrichment` at :884 — verified).
  - `[low]` `[patch]` Three `feeds.py` docstrings misattributed the EPSS reader as `vuln.py` (module docstring, `epss_cache_path`, `load_epss_scores`) — `vuln.py` never calls either function; the actual reader is `engines._epss_enrichment` (+ `_stamp_epss` consuming). All three corrected in a codebase whose docstrings are load-bearing architecture records.
  - `[low]` `[patch]` `refresh_epss_feed.py`'s CSV comment-filter comment claimed "skip any leading `#` lines" while the code strips EVERY `#`-prefixed line anywhere in the file. Comment corrected to describe the actual (safe — no CVE id starts with `#`) behavior rather than narrowing the code.
  - `[low]` `[patch]` `--timeout` accepted non-positive values, dying at runtime as a failed refresh (exit 1) instead of a usage error (exit 2) — the exact usage-vs-runtime split this same story's `_min_epss_type` establishes. Added `_positive_int` argparse `type=` + `test_main_rejects_a_non_positive_timeout_as_a_usage_error`.
- Deferred (3, appended to `deferred-work.md` as NEW entries; existing entries untouched per orchestrator directive): the real ~290k-row EPSS feed poured into KEV-sized cache conventions (`indent=2` pretty-print, full `json.loads` per `OsvEngine.run`, ~100MB+ refresh-script peak) — a real-feed performance evaluation invisible at fixture scale; the `feeds.py` atomic-write double-close latent bug, now at its fourth copy — the unified fix spans the KEV/endoflife writers this story's Never-list forbids touching; conformance-helper duplication (`run_scan`/`parse_report` ×3 files, `load_schema` ×4) — consolidation spans pre-existing 1.x/6.4 test files.
- Rejected (4): freshness-gating the `min_epss` escalation (would contradict this spec's explicit "per-finding matching still attempted against the aged catalog" boundary; escalating on stale data is the conservative, never-false-green direction); the load-vs-provenance TOCTOU provenance-attribution race (mirrors `_kev_enrichment`'s shipped ordering; consequence is a marginally misattributed snapshot timestamp in the fail-safe direction); a gzip-bomb/unbounded-read hardening ask against the hardcoded HTTPS FIRST.org URL (dev/ops-only script, trusted origin, mirrors the shipped `refresh_kev_feed.py` pattern); the `_epss_enrichment` TOCTOU downgrade asymmetry (unavailable-not-stale on a vanished file — spec-directed verbatim mirror of `_kev_enrichment`, conservative direction).

All 8 patch fixes applied; full suite re-verified green (1731 passed, was 1726, net +5 tests) after patching.

## Design Notes

The escalation and enrichment seams both already exist and are proven for KEV — copy them structurally, not the KEV path itself:

```python
# vuln.py — mirrors kev_stale_finding; only the reason token/subject differ
def epss_stale_finding(*, unavailable: bool) -> Finding:
    reason = "unavailable" if unavailable else "stale"
    return Finding(
        id=f"indeterminate:epss-data-{reason}:epss-feed",
        axis=AXIS_VULNERABILITY, subject="epss-feed", severity=None,
        message=f"the FIRST EPSS feed is {reason} while --min-epss is active — "
                 "the vulnerability axis cannot be trusted for this scan",
    )

# vuln.py — vuln_rung gains one more escalate-only branch, same shape as fail_on_kev
if min_epss is not None and finding.epss is not None and finding.epss.score >= min_epss:
    status = Status.POLICY_VIOLATION
```

Unlike `kev`/`kev_date` (always stamped `True`/`False` once a catalog loads), `epss` has no boolean equivalent for "no match" — `_stamp_epss` only calls `dataclasses.replace(finding, epss=Epss(...))` on an actual match, leaving `finding.epss` at its existing `None` default otherwise. This is a legitimate, precedent-consistent divergence from the KEV stamp, not an oversight.

`refresh_epss_feed.py` is the one real implementation delta from "direct template": FIRST.org publishes `epss_scores-current.csv.gz` (columns `cve,epss,percentile`), not JSON, so the script must gzip-decompress + CSV-parse before normalizing into the same cached-JSON-document convention `write_kev_cache`/`write_epss_cache` share (`feeds.py` itself stays feed-shape-agnostic — it only ever sees the normalized document).

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-warden pyforge-warden-test` -- expected: full suite green, including new EPSS enrichment/gate/feed-absence coverage, with `--fail-on-kev`-only and CVSS-only gating byte-identical to before. (Canonical `--frozen` form per `deferred-work.md`'s worktree path-length note.)

## Auto Run Result

**Status:** done (follow-up review pass, 2026-07-24, invoked on a `done` spec per orchestrator — fresh review, patches applied, no loopback).

**Summary of implemented change:** Fresh adversarial + edge-case review of the full 6.7 diff (`d339757ff8..d44e4f70af`, 14 files) surfaced one reachable false-green: a present-but-domain-corrupt EPSS cache entry (out-of-range, or a `NaN`/`Infinity` token `json.loads` accepts) passed the shape-only load, then died silently in `_stamp_epss`'s crash-guard — gate never fired, exit 0. Fixed with layered domain validation (load-side filter in `feeds.load_epss_scores` implementing its own already-documented finiteness contract, plus provisioning-side row filtering in `refresh_epss_feed.py`), and closed the two E2E proof gaps the first pass left: stale-feed composition (policy-violation outranks the stale indeterminate — never a pass) and TOML-only `min-epss` activation (new fixture project). Remaining fixes: precise `--min-epss` help wording, a fail-sentinel on the zero-candidates test, three reader-misattribution docstrings, a comment/code mismatch, and `--timeout` usage-error validation.

**Files changed (commit `a85d69471f`):**
- `src/pyforge/warden/feeds.py` — `load_epss_scores` gains the finite+`[0,1]` per-entry domain filter; 3 docstrings corrected (reader is `engines._epss_enrichment`, not `vuln.py`)
- `src/pyforge/warden/engines.py` — `_stamp_epss` docstring re-grounded (try/except is now a crash-guard behind the load filter)
- `src/pyforge/warden/cli.py` — `--min-epss` help made precise about stale-feed composition
- `scripts/refresh_epss_feed.py` — non-finite/out-of-domain row skip; `_positive_int` `--timeout` type; comment-filter comment fixed
- `tests/unit/test_feeds.py`, `tests/unit/test_refresh_epss_feed.py` — domain-filter + timeout-usage-error coverage (+3 tests)
- `tests/conformance/test_epss_enrichment.py` — E2E stale-composition + E2E TOML-mode tests (+2), zero-candidates sentinel, docstring updates
- `tests/fixtures/projects/vuln_min_epss_toml/pyproject.toml` — **new** TOML-mode fixture project

**Review findings breakdown:** 8 patched (1 high, 3 medium, 4 low — all applied), 3 deferred as NEW ledger entries (EPSS real-feed scale vs KEV-sized cache conventions; `feeds.py` atomic-write double-close ×4 copies; conformance-helper duplication ×3–4 files), 4 rejected (freshness-gated escalation contradicting this spec's stale-matching boundary; two TOCTOU-race nits mirroring shipped KEV shapes; gzip-bomb hardening for a trusted-origin dev-only script). 0 intent_gap, 0 bad_spec.

**Follow-up review recommendation:** false — the sole behavior-affecting change is a pair of small, mirrored, individually-tested domain filters in the conservative (fail-closed) direction; everything else is test coverage, help text, and docstrings. Two review passes have now converged (crash → corner-case false-green → closed), and the surviving concerns are ledgered design/tuning questions, not diff defects.

**Verification performed:** `pixi run --frozen -e pyforge-warden pyforge-warden-test` → **1731 passed** (was 1726 at the first pass's close; net +5 tests), zero failures/skips-of-record. Targeted pre-run of the three touched test files (85 passed) confirmed the new E2E stale test's composition assertions (policy-violation, exit 1, `max_age_ok` false) against the real verdict ladder before the full sweep.

**Residual risks:** the three ledgered defers (notably: real-feed EPSS performance is untested at 290k-row scale — fixture-scale tests cannot see it); the `--fail-on-kev` TOML-only asymmetry and cross-axis coverage-vs-indeterminate dissonance remain accepted pre-existing shapes per this spec's Never-list.

