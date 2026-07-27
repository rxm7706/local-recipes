<!-- RECOVERED 2026-07-25 from Claude Code session transcript 5e5ffa32-3b61-4044-aead-0305c30c98ff.jsonl (~/.claude/projects); this is the ORIGINAL spec incl. its dev/review narrative, not an epics.md regeneration. -->
---
title: 'Story 6.4: KEV feed provisioning, enrichment & the --fail-on-kev gate'
type: 'feature'
created: '2026-07-18'
status: shipped
updated: '2026-07-27 (AUD-WARDEN-030 status sync)'
review_loop_iteration: 0
followup_review_recommended: false
context: []
warnings: [oversized]
---

<intent-contract>

## Intent

**Problem:** The vulnerability axis gates only on CVSS severity today; a CISA-KEV-listed (actively exploited) advisory at a lower CVSS tier can pass silently, and the schema's `kev`/`kev_date`/`kev_data` slots (frozen in Story 6.1) are declared but never populated (FR36).

**Approach:** Add a `feeds.py` skeleton (cache layout + `FeedProvenance` construction + staleness, generic for 6.3/6.7 reuse), consult it from `OsvEngine.run()` to stamp `kev`/`kev_date` on each `vuln:` finding *before* `interfaces.py`'s engine-dedup step, and make a KEV match force `Status.POLICY_VIOLATION` via a new `fail-on-kev` config key (default on) — mirroring the existing stale-vuln-DB → `indeterminate` pattern for an absent/stale KEV feed.

## Boundaries & Constraints

**Always:**
- Enrichment happens inside the vuln producer (`vuln.py`/`engines.py`), never in `interfaces.py` (which only does engine-dedup + rung composition) — F10/architecture.md:138.
- `feeds.py` owns cache layout, `FeedProvenance` shape, and staleness math; no axis (this story's KEV, or the later currency/EPSS) computes its own staleness.
- `fail-on-kev` defaults `true` (FR18 default gate); a KEV match with the policy active forces `POLICY_VIOLATION` regardless of the finding's own CVSS tier, and never *downgrades* an already-critical CVSS status.
- Absent or stale KEV cache **while `fail-on-kev` is active** → one whole-axis `indeterminate:` finding with KEV provenance (mirrors `vuln.py:390` `stale_vuln_data_finding`); `fail-on-kev=false` → KEV consultation is skipped entirely (every finding's `kev` stays `None`, CVSS-only gating, matches AC6's "null slots" wording).
- Ship a hermetic ambient KEV-feed fixture (empty, fresh) wired into `conftest.py` (mirrors `_osv_ambient_db_env`) so the 1265 pre-existing tests don't flip to `indeterminate` now that the KEV policy is on by default.
- The `scan` runtime path opens no socket at any point (NFR-S2) — the "opt-in online" provisioning path lives entirely outside `scan`, in a separate script, never invoked automatically.

**Block If:** none identified — all shape decisions below (TOML key flatness, engine config-injection, provisioning entrypoint, CVE-alias matching) are resolved from established in-repo precedent (cited in Design Notes), not open product questions.

**Never:**
- Never widen `report-schema.json`/`models.py` — Story 6.1 already froze `Finding.kev`/`kev_date`/`epss`, `ComplianceReport.kev_data`/`epss_data`, and `FeedProvenance`; this story populates them, it does not add fields.
- Never build a bespoke online fetcher inside the `pyforge.warden` package or call it from `scan`/`OsvEngine` — the fetch lives in a dev/ops-only script outside the installed package (mirrors `scripts/generate_conda_pypi_map.py`).
- Never add a `--fail-on-kev`/`--no-fail-on-kev` CLI flag — config-only (`fail-on-kev` TOML key), per epics.md:500's retired-flag-family note.
- Never touch `verdict.py` (sole status→exit-code owner; unaffected — it already handles `POLICY_VIOLATION`) or Epic 5/`waiver.py` (out of scope).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| KEV match, policy on | Pinned dep with an OSV advisory whose id or alias is a CVE present in the KEV cache; `fail-on-kev` unset (default true) | Finding carries `kev: true`, `kev_date: <CISA dateAdded>`; status `policy-violation`, exit 1 — even if CVSS tier is MEDIUM/LOW | No error |
| No match, feed fresh | Pinned dep, advisory's CVE not in KEV cache; policy on | `kev: false`; CVSS-tier gating applies as before | No error |
| Policy off | Same as above, `fail-on-kev = false` in `[tool.pyforge-warden]` | `kev` stays `null` on every finding; KEV cache never even opened; CVSS-only gating (byte-identical to pre-6.4) | No error |
| Feed absent, policy on | No file at the resolved KEV cache path; `fail-on-kev` true | Whole vuln axis → `indeterminate`, one `indeterminate:kev-data-unavailable:kev-feed` finding, `kev_data: null` in the report | Never a silent no-op |
| Feed stale, policy on | KEV cache file older than the configured max-age; `fail-on-kev` true | Whole vuln axis → `indeterminate`, `indeterminate:kev-data-stale:kev-feed` finding, `kev_data.max_age_ok: false`; per-finding `kev` matching still runs (informational) | Never a silent no-op |
| No vuln-matchable candidates | Empty/no-op scan | No KEV consultation attempted (mirrors today's empty-candidate short-circuit in `OsvEngine.run`) | No error |

</intent-contract>

## Code Map

- `src/pyforge/warden/feeds.py` (NEW) — cache-dir resolution (`PYFORGE_WARDEN_FEED_CACHE_DIR` env var, no implicit default, mirrors `vuln.py:136` `resolve_cache_dir`), `<cache_dir>/kev/known_exploited_vulnerabilities.json` path helper, KEV JSON loader (cve_id → `dateAdded`), generic `is_feed_stale(snapshot_at, max_age_days, *, now)` (mirrors `vuln.py:365` `is_db_stale` logic, generalized), `DEFAULT_FEED_MAX_AGE_DAYS = 7`, `FeedProvenance` construction helper.
- `src/pyforge/warden/vuln.py` — extend `_findings_for_package`/`parse_osv_output` (vuln.py:698-786) to also capture `group.get("aliases")` per finding (currently read into the docstring but never stored, vuln.py:784) — needed because CISA KEV is CVE-keyed while OSV's primary `ids` are often GHSA/PYSEC; add a KEV-matching helper (checks `{advisory_id, *aliases}` against the loaded catalog) and a `kev_stale_finding(*, unavailable: bool)` pair (mirrors `stale_vuln_data_finding`, vuln.py:390) for the two indeterminate ids in the matrix above; extend `vuln_rung` (vuln.py:894) with a `fail_on_kev: bool` param that forces `POLICY_VIOLATION` on `finding.kev is True`.
- `src/pyforge/warden/engines.py` — `OsvEngine` (engines.py:583): add `__init__(self, *, fail_on_kev: bool = True)` (plain class today, no existing `__init__`); inside `run()`, after `name_level_findings`/`stale_findings` are computed (engines.py:660-663), consult `feeds.py` + `vuln.py`'s KEV helpers when `self.fail_on_kev` and stamp `kev`/`kev_date` on every `vuln:` finding via `dataclasses.replace` before returning `EngineResult`; carry the resulting `FeedProvenance` as a new `EngineResult.kev_data`.
- `src/pyforge/warden/interfaces.py` — `EngineResult` (interfaces.py:144-167): add `kev_data: FeedProvenance | None = None` field (additive, mirrors `vuln_data`). `DefaultPolicy.evaluate`'s `vuln_rung` call (interfaces.py:303-305): thread `fail_on_kev=self._config.fail_on_kev`.
- `src/pyforge/warden/config.py` — `_RECOGNIZED_KEYS` (config.py:81-88): add `"fail-on-kev"` (flat, hyphenated — matches every existing key's shape; see Design Notes). `EffectiveConfig` (config.py:151-279): add `fail_on_kev: bool = True` field + `_coerce_bool`-style validation (mirrors the existing coercion pattern, config.py:301-357) wired in `ConfigLoader._load` (config.py:398-467). TOML-only, no CLI flag (mirrors `dep001-block-confidence`).
- `src/pyforge/warden/report.py` — `assemble_report` (report.py:166-186): add `kev_data: FeedProvenance | None = None` param, thread into `ComplianceReport(...)` (report.py:330-341, alongside the existing `vuln_data=vuln_data`).
- `src/pyforge/warden/cli.py` — engine-construction loop (cli.py:695-696): special-case `OsvEngine` construction with `fail_on_kev=config.fail_on_kev` (mirrors the existing `factory is not DeptryEngine` conditional already in this loop). `assemble_report(...)` call (cli.py:884): pick the first non-`None` `EngineResult.kev_data` across `engine_results` (mirrors the existing `vuln_data` selection cli.py does today) and pass it through.
- `scripts/refresh_kev_feed.py` (NEW) — dev/ops-only provisioning script (NOT part of the installed package, mirrors `scripts/generate_conda_pypi_map.py`'s docstring convention): fetches `https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json` (stdlib `urllib.request`, no new dependency; same URL as `.claude/skills/conda-forge-expert/scripts/cisa_kev_fetcher.py`, pattern-only reuse, no code coupling) and writes it via `feeds.py`'s cache-write helper. This is the entire "opt-in online" surface — never invoked by `scan`.
- `src/shared/packages/pyforge-warden/tests/conftest.py` — new autouse session-scoped `_kev_ambient_feed_env` fixture (mirrors `_osv_ambient_db_env`, conftest.py:264-270): writes an empty-but-fresh KEV cache file and sets `PYFORGE_WARDEN_FEED_CACHE_DIR`.
- `src/shared/packages/pyforge-warden/tests/unit/test_feeds.py` (NEW) — pure-logic coverage for `feeds.py` (cache resolution, staleness math, provenance construction) — mirrors `tests/unit/test_vuln.py`'s structure.
- `src/shared/packages/pyforge-warden/tests/conformance/test_osv_engine.py` (extend) or a new `test_kev_enrichment.py` — end-to-end KEV match/no-match/absent/stale scenarios through `OsvEngine.run()`, using a hermetic OSV fixture advisory whose `id` (or an added `aliases` entry) is CVE-shaped, matched against a hermetic KEV fixture catalog containing that CVE — mirrors `test_osv_offline_db_spike.py`'s hermetic-fixture pattern.

## Tasks & Acceptance

**Execution:**
- [ ] `src/pyforge/warden/feeds.py` -- create the cache/provenance/staleness skeleton -- shared substrate for KEV now, currency/EPSS later (AC2)
- [ ] `src/pyforge/warden/vuln.py` -- capture OSV `aliases`, add KEV-matching + stale/unavailable finding helpers, extend `vuln_rung` with `fail_on_kev` -- makes real-world CVE matching actually work and gates independent of CVSS tier (AC1, AC6)
- [ ] `src/pyforge/warden/engines.py` -- `OsvEngine.__init__(fail_on_kev=True)`, enrich findings inside `run()` before returning `EngineResult` -- enrichment position invariant (AC1, AC3)
- [ ] `src/pyforge/warden/interfaces.py` -- `EngineResult.kev_data` field, thread `fail_on_kev` into `vuln_rung` call -- config reaches the gating decision (AC1)
- [ ] `src/pyforge/warden/config.py` -- `fail-on-kev` TOML key (default true), `EffectiveConfig.fail_on_kev` -- the named, testable opt-out (AC5)
- [ ] `src/pyforge/warden/report.py` -- thread `kev_data` through `assemble_report` into `ComplianceReport` -- report-level KEV provenance (AC1, FR36)
- [ ] `src/pyforge/warden/cli.py` -- construct `OsvEngine` with resolved `fail_on_kev`, select `kev_data` across engine results -- wires config → engine → report
- [ ] `scripts/refresh_kev_feed.py` -- opt-in online provisioning, outside the installed package -- satisfies "opt-in online, never silent" without an in-process fetcher (AC1, NFR-S2)
- [ ] `tests/conftest.py` -- ambient empty-fresh KEV fixture, autouse -- keeps the 1265 pre-existing tests green under the new default-on policy (AC4)
- [ ] `tests/unit/test_feeds.py` -- unit-test `feeds.py`'s cache/staleness/provenance logic -- per template, unit-test every I/O-matrix edge case
- [ ] `tests/conformance/test_kev_enrichment.py` -- end-to-end match/no-match/absent/stale through the real `OsvEngine` -- proves the wiring, not just the units

**Acceptance Criteria:**
- Given a pinned dependency whose advisory (by id or alias) is a CISA-KEV CVE and `fail-on-kev` is unset (default), when the scan runs, then the finding carries `kev: true` + `kev_date`, and the report's status is `policy-violation` with exit 1, regardless of the finding's own CVSS tier.
- Given `fail-on-kev = false` in `[tool.pyforge-warden]`, when the scan runs, then no KEV cache is consulted, every finding's `kev` is `null`, and CVSS-tier gating is byte-identical to pre-6.4 behavior.
- Given an absent or stale KEV cache while `fail-on-kev` is active, when the scan runs, then the vulnerability axis composes `indeterminate` with a KEV-provenance-named driver — never a silent pass, never a crash.
- Given the full existing pyforge-warden test suite, when it runs after this story lands, then all 1265 pre-existing tests still pass unmodified (only the ambient conftest fixture changes globally), plus the new KEV-specific tests.
- Given the report schema (unchanged since 6.1), when a post-6.4 report is validated, then `report-schema.json` still validates it with zero schema edits (this story is a producer, not a schema writer — F6/story 6.1 invariant).

## Design Notes

**TOML key shape — flat, not nested.** Epics.md/PRD prose write `policy.fail_on_kev` as a dotted description of *which policy* it affects, not a literal TOML path. `config.py`'s `_RECOGNIZED_KEYS` (config.py:81-88) is 100% flat hyphenated keys today (`fail-on`, `dep001-block-confidence`, `waiver-default-expiry-days`) with an explicit "no underscore alias" rule; a first nested-table key would need new validation-loop shape work with zero precedent. Using `fail-on-kev` (flat) matches every existing key and the TOML-only/no-CLI-flag treatment `dep001-block-confidence` already established.

**Config reaches `OsvEngine` via constructor, not a `Engine.run()` signature change.** `run(self, target, inventory) -> EngineResult` is a fixed 2-arg `Protocol` shared by `NullEngine`/`DeptryEngine`/`OsvEngine`; widening it would touch every engine. `cli.py`'s engine-construction loop (cli.py:695) already special-cases one engine type (`factory is not DeptryEngine`) — extending that same conditional to construct `OsvEngine(fail_on_kev=...)` only for that one factory keeps `NullEngine`/`DeptryEngine` and the `Engine` protocol untouched, and `OsvEngine()` (zero-arg) still works everywhere else since the new param defaults `True`.

**Provisioning is a standalone script, not a `scan` flag or subcommand.** The OSV-DB decision record deferred *all* online fetching in v1 specifically because NFR-S2 (`scan`'s own process opens no socket`) is incompatible with any in-process default-path fetch; osv-scanner's own binary owns that job for OSV. CISA has no equivalent binary. Rather than build an in-process "opt-in online" branch inside `scan` (which would need careful exclusion from the socket-deny harness), `scripts/refresh_kev_feed.py` sits entirely outside the installed package and outside `scan`'s call graph — identical in spirit to `scripts/generate_conda_pypi_map.py`'s existing "dev-only maintenance script" convention, and it trivially satisfies "opt-in" (a human runs it) and "never silent" (it prints what it fetched) without touching the gate's runtime socket posture at all.

**Why `aliases` capture is in-scope, not a follow-on.** `parse_osv_output`'s own docstring (vuln.py:784) already documents that OSV's `groups[]` carry `aliases` alongside `ids`, but no code path stores them. CISA KEV is CVE-keyed; OSV's primary PyPI advisory ids are frequently `PYSEC-*`/`GHSA-*` with the CVE cross-reference living only in `aliases`. Skipping alias capture would make KEV matching pass its hermetic fixture test (which can freely choose a CVE-shaped primary id) while silently failing to match the vast majority of real-world advisories — a false-green in spirit, not just in a fixture. This is a small, additive extension to an already-tolerant parser (same defensive shape-check style throughout `_findings_for_package`).

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-warden pyforge-warden-test` -- expected: all pre-existing 1265 tests plus new KEV tests pass (plain `pixi run -e pyforge-warden` may try to re-solve an unrelated `bmad-ui` env in this repo; use `--frozen`)
- `pixi run --frozen -e pyforge-warden python -m pyforge.warden.cli scan <fixture-dir> --fail-on-kev` (manual smoke, if a `--fail-on-kev` debug affordance is added) -- otherwise inspect a scan of a fixture with the ambient KEV feed swapped for one containing a seeded match, confirming exit 1 and `kev: true` in the JSON report

**Manual checks (if no CLI):**
- Confirm `report-schema.json` is byte-identical after this story (no edits) via `git diff --stat` on that file.
