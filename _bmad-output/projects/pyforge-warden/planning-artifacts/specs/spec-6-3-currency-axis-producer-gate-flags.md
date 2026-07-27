---
title: 'Story 6.3: Currency axis producer + gate flags (Axis 4)'
type: 'feature'
created: '2026-07-23'
status: shipped
updated: '2026-07-27 (AUD-WARDEN-030 status sync)'
baseline_revision: 'fba8410792f4287ce9576c53276093fd474e6835'
final_revision: '18fb8e44a209d2fd760e5553ed60c4f55df9309f'
review_loop_iteration: 0
followup_review_recommended: true
context: []
warnings: ['oversized']
---

<intent-contract>

## Intent

**Problem:** pyforge-warden ships three axes (hygiene, security, license) but no currency/EOL-supportability signal; FR34/FR35 need a fourth axis emitting tiered, age-honest verdicts for every component plus the Python runtime, gateable via CLI flags. Story 6.1 already landed the schema scaffolding (`AXIS_CURRENCY`, `CurrencyVerdict`, `CurrencyInfo`, `report-schema.json` currency sub-object) inert; no producer exists yet.

**Approach:** Add `currency.py` mirroring `license.py`'s shape exactly (axis="currency", `currency_rung` hard-capped at `Status.WARN`, no escalation logic — Story 6.5 solely owns escalation). Resolve verdicts via a tiered ladder: bundled `lts-registry.yaml` (new, `importlib.resources`) → cached endoflife.date snapshot (via new `feeds.py` siblings to the KEV trio) → `unknown`. Wire `--max-lag`/`--require-lts`/`--fail-on-eol` through `config.py`/`cli.py`/`report.py` exactly like Story 6.2's license flags, and register into the existing cross-axis "never exceeds warn" conformance suite.

## Boundaries & Constraints

**Always:**
- `currency_rung` is unconditional `Status.WARN` — never reads `currency_policy`, never escalates.
- Finding-id reason-token precedence is the pinned 3-way total order `eol` > `over-lag` > `unknown` (decision record §2); `<subject>` is `<pkg>` for a component and the reserved sentinel `!python-runtime` for the interpreter finding. The historical report-section name `runtime_python` was **not shipped** (AUD-WARDEN-028) — the finding is the sole runtime signal.
- `lag` is an integer count of releases-behind-latest, never calendar time; when derived from the endoflife.date (date-based) tier it is an approximation, from a release-position tier it would be exact.
- Every bundled-registry-derived verdict carries `snapshot_at` (registry build time) + `max_age_ok` against a 180-day default max-age (NFR-S9); a stale registry never silently reports `supported`.
- The endoflife.date cache reuses `feeds.py`'s `resolve_cache_dir`/`is_feed_stale`/`feed_provenance`/`DEFAULT_FEED_MAX_AGE_DAYS` verbatim — `currency.py` builds no private cache and computes no staleness itself.
- The real online fetch lives ONLY in a new standalone `scripts/refresh_endoflife_feed.py` (stdlib `urllib.request`, never imported by the installed package or any `scan`-path module) — mirrors `scripts/refresh_kev_feed.py` exactly (NFR-S2: `scan` opens no socket).
- `--max-lag <n>` / `--require-lts` / `--fail-on-eol` parse into `EffectiveConfig` (CLI overrides `[tool.pyforge-warden]`, same precedence as every other flag) and flip `currency_gating`; `currency_policy` (`dict[CurrencyVerdict, Status]`, `MappingProxyType`-wrapped default) is defined this story per the decision record but has no caller yet.
- Register a `("currency", currency_rung, (...))` tuple into `tests/conformance/test_axis_producer_ceiling.py`'s `_CEILING_FIXTURES`, plus a currency-specific non-vacuous coverage check (mirrors the license one, covering all 3 reason-eligible verdicts).

**Block If:** the already-landed 6.1 schema (`CurrencyInfo`/`CurrencyVerdict`/`AXIS_CURRENCY`/`report-schema.json` currency sub-object) is found missing, incomplete, or structurally incompatible with this design during implementation — no story after 6.1 may widen the schema, so a genuine gap here is a planning defect, not something to patch around.

**Never:**
- No fleet-mode N/N-1 conda-channel-data source or `inventory-match` integration — out of scope this story. The `tier` enum's `"channel-n-n-1"` value stays schema-valid but is never emitted by this producer; the ADD/UPDATE availability-at-N/N-1 finding is fleet-mode-only and is simply omitted (with a coverage note) in edge mode.
- No escalation logic (`eol`/`over-lag`/`unknown` → `policy-violation`/`indeterminate`) and no new `is_lts`-style schema field for `--require-lts` — both are Story 6.5's sole design/ownership.
- No network access from `currency.py`, `CurrencyEngine`, or `cli.py` — only `scripts/refresh_endoflife_feed.py` may open a socket.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Bundled LTS-registry hit | Component name/alias matches an `lts-registry.yaml` product | `tier="lts-registry"`, verdict from the product's LTS policy vs. resolved version, `snapshot_at`=registry build date, `max_age_ok` per 180-day default | No error |
| Bundled registry stale, no policy flag | `max_age_ok=False`, no `--fail-on-eol`/`--max-lag`/`--require-lts` | Finding still emitted honestly (`max_age_ok:false`); `currency_rung` still WARN (escalation is 6.5's) | No error |
| Endoflife.date cache hit, no registry match | Cached snapshot present + fresh, component not in `lts-registry.yaml` | `tier="endoflife-date"`, `latest`/`eol_date` from the snapshot, `lag` approximated as a release count | No error |
| No tier resolves | Edge mode: no registry match, endoflife cache absent/stale | `tier=unknown`, `verdict=UNKNOWN`, WARN-capped finding, honest `AxisCoverage` | No exception |
| Python runtime, always assessed | Any scan | One finding with id `currency:<reason>:!python-runtime@<ver>` (accepted finding-only shape; no top-level `runtime_python` report field — AUD-WARDEN-028 / FR34) | No error |
| Gate flags set, no other change | `--max-lag 5` / `--require-lts` / `--fail-on-eol` any combination | `currency.gating=true` in the report; `currency_findings()` output otherwise byte-identical to the unconfigured run | No error |
| Malformed `--max-lag` | e.g. `-1`, `"abc"` | Typed `ConfigValidationError` at parse time, mirrors `--fail-under-coverage`'s validator | Typed error, non-zero exit per FR21 |
| `--deterministic`, same fixtures twice | Repeat run | Byte-identical currency section output (NFR-R3b) | No error |

</intent-contract>

## Code Map

- `src/pyforge/warden/data/lts-registry.yaml` (new) -- regenerated bundled copy of `.claude/skills/conda-forge-expert/data/lts-registry.yaml`, loaded via `importlib.resources`.
- `src/pyforge/warden/feeds.py` -- add `endoflife_cache_path`, `load_endoflife_snapshot`, `write_endoflife_cache` siblings to the KEV trio; reuse `resolve_cache_dir`/`is_feed_stale`/`feed_provenance` unchanged.
- `scripts/refresh_endoflife_feed.py` (new) -- standalone stdlib-`urllib` provisioning script, mirrors `scripts/refresh_kev_feed.py`; the entire opt-in-online surface for this feed.
- `src/pyforge/warden/currency.py` (new) -- the axis producer: `currency_findings(...)`, `currency_rung(...)`, tier resolution, `!python-runtime` runtime finding, `DEFAULT_CURRENCY_POLICY` (unused, mirrors `DEFAULT_LICENSE_POLICY`).
- `src/pyforge/warden/interfaces.py` -- add `currency_data: FeedProvenance | None = None` to `EngineResult`; add `AXIS_CURRENCY -> currency_rung` branch in `DefaultPolicy.evaluate`.
- `src/pyforge/warden/config.py` -- `max_lag`/`require_lts`/`fail_on_eol` fields, `currency_gating`/`currency_policy` properties, `_coerce_max_lag`, `_RECOGNIZED_KEYS` + CLI-override wiring (mirrors the license flag pattern exactly).
- `src/pyforge/warden/engines.py` -- new `CurrencyEngine` (mirrors `LicenseEngine`, no subprocess), registered at module bottom.
- `src/pyforge/warden/cli.py` -- `--max-lag`/`--require-lts`/`--fail-on-eol` argparse flags; `CurrencyEngine` special-case in the engine-construction loop; thread `currency_gating`/`currency_data` into `assemble_report(...)`.
- `src/pyforge/warden/report.py` -- `currency_gating`/`currency_data` params on `assemble_report`, threaded the same way `license_gating`/`kev_data` already are.
- `tests/unit/test_currency.py` (new), `tests/unit/test_feeds.py`, `tests/unit/test_refresh_endoflife_feed.py` (new), `tests/unit/test_config.py`, `tests/conformance/test_axis_producer_ceiling.py`, `tests/conformance/test_scan_harness.py` -- unit + conformance + E2E coverage, each mirroring its Story 6.2/6.4 counterpart.

(All paths above are relative to `src/shared/packages/pyforge-warden/`.)

## Tasks & Acceptance

**Execution:**
- [x] `src/pyforge/warden/data/lts-registry.yaml` -- regenerate from the CFE source copy -- bundled tier-1 currency source (FR34)
- [x] `src/pyforge/warden/feeds.py` -- add `endoflife_cache_path`/`load_endoflife_snapshot`/`write_endoflife_cache` -- gives `currency.py` its shared cache layer; no private cache built
- [x] `scripts/refresh_endoflife_feed.py` -- new dev/ops fetch script -- the sole opt-in-online surface (NFR-S2), mirrors `scripts/refresh_kev_feed.py`
- [x] `src/pyforge/warden/currency.py` -- new producer module -- FR34/FR35 core: tiered resolution, hard-WARN cap, runtime finding
- [x] `src/pyforge/warden/interfaces.py` -- `EngineResult.currency_data` field + `AXIS_CURRENCY` policy branch -- wires the new axis into the existing seam (no new interface, OD7)
- [x] `src/pyforge/warden/config.py` -- `--max-lag`/`--require-lts`/`--fail-on-eol` config plumbing + `currency_gating`/`currency_policy` -- mirrors Story 6.2's license flags
- [x] `src/pyforge/warden/engines.py` -- `CurrencyEngine` -- mirrors `LicenseEngine`
- [x] `src/pyforge/warden/report.py` -- `currency_gating`/`currency_data` params on `assemble_report`
- [x] `src/pyforge/warden/cli.py` -- argparse flags + engine special-case + `assemble_report` threading
- [x] `tests/unit/test_currency.py` -- new -- covers every I/O matrix row plus the runtime finding and tier fallback
- [x] `tests/unit/test_feeds.py` -- add endoflife cache-path/load/write coverage
- [x] `tests/unit/test_refresh_endoflife_feed.py` -- new -- mirrors `test_refresh_kev_feed.py`
- [x] `tests/unit/test_config.py` -- add currency flag-parsing coverage
- [x] `tests/conformance/test_axis_producer_ceiling.py` -- append the currency ceiling tuple + non-vacuous coverage check
- [x] `tests/conformance/test_scan_harness.py` -- add an E2E currency-axis fixture scan

**Acceptance Criteria:**
- Given `--max-lag`/`--require-lts`/`--fail-on-eol` all unset, when a scan runs over a mixed fixture (an LTS-registry hit, an endoflife-only hit, and an unresolvable component), then every currency finding composes at `warn` and the report's `currency.gating` is `false`.
- Given any one of the three currency flags set, when the identical fixture set runs, then `currency.gating` is `true` and `currency_findings()`'s own output (ids, verdicts, tiers) is unchanged from the unconfigured run — proving this story adds no escalation logic.
- Given the endoflife.date cache is absent or stale, when the axis runs, then no exception is raised and the affected components degrade to `tier=unknown`/`endoflife-date` with honest `max_age_ok`.
- Given `tests/conformance/test_axis_producer_ceiling.py`'s parametrized suite, when it runs, then the new currency tuple passes identically to the license tuple's assertions (`status is Status.WARN`, `driver.axis == "currency"`, `driver.finding_id == finding.id`).
- Given `--deterministic`, when the same fixture set runs twice, then the currency report section is byte-identical across both runs.

## Spec Change Log

(No bad_spec loopback occurred during this story's review pass — empty.)

## Review Triage Log

### 2026-07-23 — Review pass

- intent_gap: 0
- bad_spec: 0
- patch: 9 (medium 1medium, low 8low)
- defer: 5 (low 5low)
- reject: 1 (low 1low)
- addressed_findings:
  - `[medium]` `[patch]` `_registry_alias_index` silently overwrote on a normalized alias/product-key collision — now raises `ValueError` naming both colliding products; test added.
  - `[low]` `[patch]` Python-runtime `!python-runtime` finding shape was never exercised end-to-end through `report.py` serialization + schema validation (only unit-tested) — added an E2E scan-harness fixture asserting the round-trip.
  - `[low]` `[patch]` `currency.py` module docstring overclaimed that a stale bundled registry skips tier 1 "entirely" — corrected: only the curated `lts_lines` data is gated by freshness; slug/alias routing metadata is consulted regardless (not freshness-sensitive by nature).
  - `[low]` `[patch]` `_best_match`'s exact-length tie-break was undocumented/untested — documented (first-encountered-in-date-sorted-order wins) and covered by a new test.
  - `[low]` `[patch]` `scripts/refresh_endoflife_feed.py` silently "succeeded" with 0 products fetched when the bundled registry was unreadable and no `--product` was given — now warns on stderr in that case.
  - `[low]` `[patch]` `cli.py` comment overstated that `currency_data` is always populated once the registry is "consulted unconditionally" — corrected to note it can legitimately be `None` (absent/unreadable registry or unparsable `updated:` date).
  - `[low]` `[patch]` `test_currency_findings_mixed_fixture_covers_all_three_reasons` used a superset (`>=`) assertion instead of exact equality — tightened to `==`.
  - `[low]` `[patch]` `refresh_endoflife_feed.py` interpolated an unescaped product slug into the fetch URL — now URL-escaped via `urllib.parse.quote`.
  - `[low]` `[patch]` `_resolve_from_cycles` did not filter an empty-string `cycle` value, unlike `_resolve_from_lines`'s equivalent non-empty check on `line` — added the matching filter for consistency.
  - `[low]` `[reject]` "`--require-lts`/`--fail-on-eol` have no CLI negation flag" — matches this codebase's deliberate, documented convention (Story 6.4: "the coarse `--no-fail-on-*` flag family stays retired," TOML is the intended override path) — not a gap.
  - 5 defer findings logged to `deferred-work.md` (pre-existing/out-of-scope): the missing `runtime_python` report-section field (traces to an incomplete Story 6.1 schema amendment, not this story), `refresh_endoflife_feed.py`'s lack of rate-limiting/backoff, `lag`'s strict-`>` tie handling on same-day releases, `currency_policy`'s cross-file hand-duplication (continues an existing Story 6.2 pattern), and the endoflife cache's inherited 7-day staleness default (architecturally required by this story's own boundaries, worth a future cross-axis defaults pass).

All 9 patch fixes applied; full suite re-verified green (1579 passed) after patching.

### 2026-07-23 — Follow-up review pass (independent, post-merge-candidate)

- intent_gap: 0
- bad_spec: 0
- patch: 14 (medium 4medium, low 10low)
- defer: 3 (medium 2medium, low 1low)
- reject: 4 (low 4low)
- addressed_findings:
  - `[medium]` `[patch]` `test_currency_findings_mixed_fixture_covers_all_three_reasons` used wall-clock `datetime.now(UTC)` while its tier-1 leg depends on the bundled registry's 180-day freshness window (`updated: 2026-07-06`) — would deterministically go red ~2027-01-02 with no code change. Pinned to `_NOW`, with the cache file's mtime pinned too (a new `_pin_cache_mtime_to_now` helper — `is_feed_stale` treats a future-dated mtime as stale, which the wall-clock version had silently masked).
  - `[medium]` `[patch]` `refresh_endoflife_feed.py`'s zero-slug default path (registry missing/malformed, no `--product`) atomically overwrote a previously provisioned, still-good cache with `{}` and exited 0 — the most complete-looking partial snapshot possible, violating the script's own fail-loud contract. `refresh()` now raises before any write; `main()` exits 1; tests rewritten to pin cache preservation byte-for-byte.
  - `[medium]` `[patch]` `_resolve_from_cycles` rejected endoflife.date's documented boolean `eol` shapes wholesale, flooding `currency:unknown` warn noise for fully-current components with `eol: false` on real provisioned snapshots. Patched the schema-expressible half (`eol: false` + lag 0 → supported, no finding); `eol: true` and `eol: false`-behind remain degraded because the frozen 6.1 model invariant requires non-null eol_date on eol/over-lag findings (confirmed live at models.py:437) — remainder deferred to the ledger as a schema-amendment candidate.
  - `[medium]` `[patch]` The numeric-cycle `str(3.10)`→`"3.1"` truncation the module docstring dismissed as fixture-hypothetical was live in the writer: the refresh script's `json.loads` float-parsed real API cycles (and `python` — the canonical 3.10 case — is a default-provisioned product). Now parses with `parse_float=str`/`parse_int=str`, preserving lexical numeral forms; docstring rewritten to bound the residual to foreign/hand-built caches; raw-JSON regression test added.
  - `[low]` `[patch]` `default_with_cli_overrides` passed `cli_require_lts`/`cli_fail_on_eol` raw (plain `ValueError` from `__post_init__`, escaping `cli.py`'s `except ConfigValidationError` fallback) while its own docstring claimed coercer parity — routed through `_coerce_require_lts`/`_coerce_fail_on_eol`; parametrized test added.
  - `[low]` `[patch]` Two snapshot keys normalizing to the same product key silently last-won in `currency_findings`'s dict comprehension (the registry alias index raises on the same ambiguity) — colliding keys are now dropped entirely (runtime input degrades honestly; packaged data keeps failing loud); test added.
  - `[low]` `[patch]` `_registry_alias_index` docstring falsely claimed the collision `ValueError` "fires once per process" (only the raw YAML load is cached; the index rebuilds every scan) — corrected to state the real per-scan behavior.
  - `[low]` `[patch]` `interfaces.py`'s `currency_data` docstring overstated "`None` only when `updated:` is unparsable" — corrected to enumerate the full degrade set (absent/unreadable/unparsable/non-mapping registry too), matching `cli.py`'s comment fixed in the prior pass.
  - `[low]` `[patch]` `currency.py`'s tier-1 docstring claimed `lts_lines` is "the `source: manual`/`heuristic-seed` shape," contradicting the registry header (`lts_lines: (manual only)`) and the actual heuristic-seed exemplar (no lines, null slug); the refresh script's docstrings also implied manual entries are never cache-consulted (slug routing is unconditional). Both corrected; the registry data itself untouched (verbatim CFE-source mirror by spec).
  - `[low]` `[patch]` `--max-lag N` help text didn't disclose the threshold value is recorded but unenforced in v1 (over-lag fires for ANY positive lag regardless of N) — help now states it explicitly.
  - `[low]` `[patch]` Ceiling-test currency fixture messages omitted the producer's real "`({tier})`"/"(no registry/feed match)" tails (the license fixtures match their producer exactly) — aligned to the producer format.
  - `[low]` `[patch]` `test_currency_gate_flags_never_change_the_findings_themselves` docstring claimed BYTE-IDENTICAL output while comparing parsed, re-sorted JSON — reworded to the semantic-equality claim it actually proves.
  - `[low]` `[patch]` `--product ''` passed unvalidated and produced a request to the API root's `.json` — `fetch_product_cycles` now rejects empty slugs with a `ValueError` before any request; no-socket test added.
  - `[low]` `[patch]` The hidden two-file invariant between conftest's ambient endoflife snapshot and the fixture-manifest pins (requests 2.31.0 / packaging 24.0) had no enforcement — added a cross-check test that fails naming the real fix (update the snapshot alongside a pin bump) instead of regressing a "must stay clean" fixture with verdict-pointing noise.
  - 3 defer findings appended to `deferred-work.md` as NEW entries (existing entries untouched): the dropped `lts` boolean Story 6.5's `--require-lts` escalation will need; the missing ecosystem discriminator in `currency:`/`license:` finding ids (cross-axis, decision-record-pinned grammar); the frozen 6.1 non-null-eol_date invariant that makes boolean-`eol` shapes partially inexpressible (the un-patchable remainder of the boolean-eol finding).
  - 4 rejects: no CLI negation flags for `--require-lts`/`--fail-on-eol` (deliberate documented convention, rejected in the prior pass too); the 7-day endoflife staleness default (already ledgered by the prior pass — orchestrator owns the entry); registry `lts_lines` entries with unusable `eol` being skipped (curated tier-1 schema mandates dated eol; skip-malformed is the documented degrade posture); `_load_registry`'s lru_cache pinning a transient read failure for the process lifetime (the CLI is one scan per process; no long-lived consumer exists).

All 14 patch fixes applied; full suite re-verified green (1589 passed — net +10 tests) after patching.

### 2026-07-23 — Review pass (second independent follow-up, bmad-dev-auto)

- intent_gap: 0
- bad_spec: 0
- patch: 12 (high 1high, medium 1medium, low 10low)
- defer: 1 (high 1high)
- reject: 3 (low 3low)
- addressed_findings:
  - `[high]` `[patch]` Ecosystem-variant duplicate finding ids crashed the ENTIRE report: `merge_components` keeps `(ecosystem, name, version)` distinct while currency resolution is ecosystem-agnostic, so a dual pyproject+pixi manifest declaring the same dep minted two `currency:unknown:<pkg>@<ver>` findings with one id — `ComplianceReport`'s uniqueness invariant raised through `cli.py`'s last-resort net (internal-error exit, NO report; live-reproduced). Payloads are byte-identical (sanitize is injective, resolution keys on normalized name+version), so `currency_findings` now dedupes by id (keep-first deterministic; the reserved `!python-runtime` id inserted last with overwrite so a sentinel-squatting component can never mask the interpreter finding). Unit test + live E2E re-verification added; the license-axis/model-level residual is a NEW ledger entry.
  - `[medium]` `[patch]` A narrow `--product` refresh silently REPLACED a multi-product cache, dropping every non-fetched product (later scans flood `currency:unknown`). Replace semantics kept deliberately (merging would re-stamp unfetched, possibly-stale products as fresh under the new mtime — a false-green vector), but the shrink is now loud: `refresh()` reports `dropped_products` in its stats, `main()` warns on stderr naming the dropped products and the remedy; docstrings state the replace-not-merge rationale; 3 tests added.
  - `[low]` `[patch]` The `unknown` finding message claimed "(no registry/feed match)" on every degrade path (matched-but-degraded boolean-eol, collision-dropped snapshot keys, stale-tier skip, version-less component) — now "(no usable registry/feed data)" (true for all), with the one cause knowable at the emission site (version-less) getting its own "(component has no version to assess)" tail; ceiling fixture aligned.
  - `[low]` `[patch]` `currency.py`'s "The Python runtime is ALWAYS put through the ladder" docstring contradicted the CLI engine seam's `manifests_parsed > 0` gate (zero-manifest scans run no engines at all, runtime included) — scoped the claim explicitly.
  - `[low]` `[patch]` The `currency_findings`-level tests hard-couple to the bundled registry's volatile facts (a re-copy with `updated:` newer than the frozen `_NOW` flips `registry_fresh` stale — future-dated is stale — and reds the tier-1 legs with no code change) — added a canary test (`test_bundled_registry_facts_the_suite_relies_on`) pinning freshness-at-`_NOW` + the relied-on entries, failing with a message naming the remedy; registry header NOTE added.
  - `[low]` `[patch]` The registry header claimed the bundled copy is "regenerated verbatim" while its own added header block already differs from the CFE canonical source, and no test enforced the sync rule — header reworded (DATA verbatim; header block the only sanctioned difference) and a parsed-equality parity test added (skips outside the monorepo).
  - `[low]` `[patch]` `--max-lag` help said "v1 records the threshold" but N lands only in `EffectiveConfig` and dies there (no report field, no config echo) — help now says "accepts the threshold but neither enforces it nor echoes it into the report".
  - `[low]` `[patch]` The ambient-snapshot guard test enforced only half its claimed invariant (a NEW pin under an uncovered name is skipped via `cycles is None: continue`) — guard docstring + conftest comment now state the one-direction coverage explicitly and name the extend-the-fixture remedy.
  - `[low]` `[patch]` `test_currency_rung_is_always_warn` built its over-lag fixture with `lag=0`, a shape `_classify` can never emit (over-lag fires on lag truthiness) — fixture now producer-realistic (`lag=1`).
  - `[low]` `[patch]` The refresh script wrote snapshot keys as RAW slugs while the reader normalizes and drops collisions — case/separator-variant `--product` values (`Django`/`django`) produced a "successful" refresh no scan could resolve. `refresh()` now imports the reader's own `_normalize_name` and fails loud BEFORE any request on a normalized collision; exact duplicates dedupe; 2 tests added.
  - `[low]` `[patch]` `UnicodeDecodeError` (a `ValueError`, not `OSError`) escaped both `currency._load_registry`'s and `refresh_endoflife_feed.default_product_slugs`'s documented never-raises degrade contracts on invalid UTF-8 — both except tuples widened; 2 tests added.
  - `[low]` `[patch]` `--timeout 0`/negative passed argparse and surfaced as a non-blocking socket / baffling fetch failure (FAILED exit 1) instead of a usage error — new `_timeout_type` validator rejects non-positive values at parse time (usage exit 2); test added.
  - 1 defer finding appended to `deferred-work.md` as a NEW entry (existing entries untouched): the duplicate-finding-id report-killing crash posture (`assemble_report` outside the engine seam) with its license-axis residual and the model-level hard-crash design — sharpens, without modifying, the prior pass's ecosystem-discriminator grammar entry.
  - 3 rejects: the dropped `lts` boolean `--require-lts` cannot act on (already ledgered by the prior pass — orchestrator owns the entry); boolean-`eol` behind-match degradation framed as "producer choice" (refuted: the frozen 6.1 model invariant requires non-null eol_date on over-lag findings, confirmed at models.py; the un-patchable remainder is already ledgered); no CLI negation flags for `--require-lts`/`--fail-on-eol` (deliberate documented convention, rejected in both prior passes).

All 12 patch fixes applied; full suite re-verified green (1600 passed — net +11 tests) after patching, plus a live dual-ecosystem E2E scan confirming the report now emits.

## Design Notes

`currency.py` should mirror `license.py` file-for-file wherever the shapes coincide (module docstring style, `AxisCoverage` reporting, hard-cap rung function, `DEFAULT_*_POLICY` unused-this-story constant) — the only real design work this story owns is the tier ladder and the `!python-runtime` sentinel, both already pinned by the 6.10 decision record (implement, don't redesign).

`scripts/refresh_endoflife_feed.py` follows `scripts/refresh_kev_feed.py`'s structure exactly: stdlib `urllib.request`, atomic write via the new `feeds.write_endoflife_cache`, `--cache-dir`/`--timeout` argparse, `$PYFORGE_WARDEN_FEED_CACHE_DIR` default. The real `endoflife.date` API response shape should be confirmed against the live endpoint during implementation (a bounded implementation detail — a wrong assumption here fails loud in the standalone script's own parse-sanity check, exactly like `refresh_kev_feed.py`'s `ValueError` guard, never silently in the `scan` path).

`--require-lts`'s actual escalation meaning ("block on non-LTS runtimes/deps where an LTS exists") is intentionally NOT implemented by this story beyond flag-parsing + `currency_gating` — Story 6.5 designs how it reads the `tier`/`verdict` fields this story already produces.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-warden pyforge-warden-test` -- expected: full suite green, including new currency/feeds/config/conformance coverage (the canonical `--frozen` form per `deferred-work.md`'s worktree path-length note; unfrozen fails environmentally in bmad-loop worktrees, unrelated to this story's correctness).

## Auto Run Result

**Status:** done (second independent follow-up review pass, 2026-07-23, commit `18fb8e44a2`).

**Summary:** Fresh adversarial + edge-case review of the full story-6.3 diff (baseline `fba8410792`..`067bb3fc19`). 16 raw findings from two parallel hunters triaged to 12 patches (1 high, 1 medium, 10 low), 1 new defer, 3 rejects; 0 intent gaps, 0 bad-spec loopbacks. Headline fix: ecosystem-variant duplicate finding ids crashed the ENTIRE report (dual pyproject+pixi manifests — live-reproduced internal-error exit with no report emitted); `currency_findings` now dedupes by id with the runtime sentinel protected, verified by unit test + live E2E scan.

**Files changed (all under `src/shared/packages/pyforge-warden/`):**
- `src/pyforge/warden/currency.py` — id-level dedupe in `currency_findings` (runtime-sentinel overwrite); truthful unknown-message tails (incl. version-less); `UnicodeDecodeError` degrade in `_load_registry`; "ALWAYS assessed" docstring scoped to the engine gate.
- `scripts/refresh_endoflife_feed.py` — `dropped_products` stats + stderr warning on narrower refreshes (replace-not-merge rationale documented); normalized-slug collision refusal before any request; exact-duplicate dedupe; `UnicodeDecodeError` degrade; positive-integer `--timeout` validator.
- `src/pyforge/warden/cli.py` — `--max-lag` help no longer claims the threshold is recorded anywhere.
- `src/pyforge/warden/data/lts-registry.yaml` — header: "verbatim" scoped to DATA; canary/parity NOTE (comments only; data untouched, parse-equal with the CFE source).
- `tests/unit/test_currency.py` — new: ecosystem-variant dedupe test, bundled-registry canary, CFE parity test (skip outside monorepo), `_load_registry` decode-degrade test; over-lag rung fixture made producer-realistic (`lag=1`); ambient-guard docstring states its one-direction coverage.
- `tests/unit/test_refresh_endoflife_feed.py` — new: dropped-products (refresh + main-warning + no-drop), slug-collision, exact-dedupe, undecodable-registry, timeout-usage-error tests.
- `tests/conformance/test_axis_producer_ceiling.py` — unknown-fixture message aligned to the new producer tail.
- `tests/conftest.py` — ambient-snapshot comment names the extend-on-new-pin obligation.

**Review breakdown:** 12 patched (see triage log), 1 deferred as a NEW ledger entry (duplicate-id report-crash posture: license-axis residual + model-level hard-crash design, cross-axis/orchestrator-owned), 3 rejected (two already-ledgered by prior passes, one deliberate documented convention).

**Follow-up review recommended:** true — the high-severity fix adds new behavior (dedupe semantics) to the core producer and the refresh script gained CLI-visible behavior (stats key, stderr warning, argparse validation), none of it yet independently reviewed.

**Verification:** `pixi run --frozen -e pyforge-warden pyforge-warden-test` → 1600 passed (net +11 tests over the prior pass's 1589). Live E2E: a dual-ecosystem (pyproject+pixi, same pinned dep) scratch project scanned pre-patch crashed with the duplicate-id internal error; post-patch emits a complete report with one deduped `currency:unknown` finding and zero duplicate ids.

**Residual risks:** the license axis retains a narrower reachable duplicate-id crash (per-ecosystem dispatch, same name+version unresolved in both ecosystems) — ledgered, orchestrator-owned; the bundled-registry canary converts future re-copy breakage into a named maintenance task but cannot future-proof fixture expectations against arbitrary data changes; `--require-lts` still gates without an LTS signal in the emitted data (already ledgered for Story 6.5).

