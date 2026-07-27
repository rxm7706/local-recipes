---
title: 'Story 5.1: Actionable diagnostics & safe-by-default posture'
type: 'feature'
created: '2026-07-24'
status: shipped
updated: '2026-07-27 (AUD-WARDEN-030 status sync)'
review_loop_iteration: 0
followup_review_recommended: true
baseline_revision: 'f0c7d8d864fec49ba770da98c5f2ebac8ce53cba'
final_revision: 'a4e7a537e242decd6b3731836a96f01f50b930c1'
context: []
warnings: ['oversized']
---

<intent-contract>

## Intent

**Problem:** When a scan exits non-zero, the human report names the finding (`[axis] tier id -- message`) but never tells a maintainer what to actually DO about it — no fixed-version, no manifest+location, no remediation text — pushing them toward disabling the gate instead of fixing the finding (NFR-U1). Separately, the zero-config default posture is mostly already secure (block-critical/KEV, waiver expiry, engine-version fail-loud are all shipped), but there is no `--doctor` self-check, no explicit air-gap framing, and no user-facing install/on-ramp documentation (NFR-U2, D8, P8).

**Approach:** Add remediation content as a `render_text`-only side channel (never touching the frozen `models.py`/`report-schema.json` contract — mirrors the existing `applied_waivers`/`applied_baseline` caller-supplied-param precedent), sourced from data already available upstream (`Component.provenance` for manifest+location) plus one small new addition (osv-scanner's `fixed` version, currently parsed-and-discarded). Add a `--doctor` flag to the single `scan` verb that aggregates the engine-version/OSV-DB/KEV/EPSS health checks already built for Stories 6.4/6.6/6.7, explicitly labeling an absent optional feed as "air-gapped" rather than a failure. Author the install/on-ramp README section from content already decided in `docs/specs/pyforge-warden.md`.

## Boundaries & Constraints

**Always:**
- `models.py`, `data/report-schema.json`, and `REPORT_SCHEMA_VERSION` (`"1.1.0"`) stay byte-for-byte untouched — Story 6.1 was the one sanctioned schema amendment; this story is not a second one. Remediation content lives ONLY in `report.render_text`'s output, via new caller-supplied parameters — the exact shape `applied_waivers`/`applied_baseline` already use (data threaded in by `cli.py`, never stored on `Finding`/`ComplianceReport`). `render_json`'s document is unchanged byte-for-byte by this story.
- `verdict.py` stays the sole exit-code owner. `--doctor` never composes a `Status`/rung and never invents a new exit path — it returns either `0` or `exit_code_for(Status.ERROR)` (the SAME call `cli.py` already makes at its early stat-failure returns, e.g. `cli.py:741`), and NEVER `1` (doctor reports operability, not policy). `130`/SIGINT still applies via `main()`'s existing top-level `except KeyboardInterrupt`.
- `--doctor` is a `store_true` flag on the existing `scan` subparser (mirrors `--warn-only`/`--bypass`'s shape) — never a new subcommand, no interactive prompts. It is dispatched as a sibling branch inside `main()` (`if args.doctor: return _run_doctor(args)` before the existing `return _run_scan(args)` at `cli.py:696`) so it runs inside the SAME SIGINT/SystemExit/last-resort exception nets as a scan — never a parallel entrypoint.
- `--doctor` short-circuits BEFORE discovery/extraction/policy/engine-scan (it is an environment check, not a project scan) and performs read-only local filesystem + `--version` subprocess checks only — NEVER a network call (the autouse socket-deny harness, `tests/meta/test_socket_deny_alive.py`, applies to doctor too).
- `--format {text,json}` continues to apply under `--doctor`; its JSON shape is a NEW small ad-hoc document (NOT `ComplianceReport`, not schema-validated) — still one document on stdout (NFR-I3 preserved).
- License/currency/indeterminate remediation text is derived ONLY from data already in `document["findings"]` (`severity`, `license`, `currency` sub-objects, `id`, `axis`) — no new threading needed for those families. Only vuln's fixed-version and every family's manifest-location need the two new `render_text` parameters.
- Every new remediation-line string passes through the existing `_single_line` sanitizer first (`report.py:468`), exactly like every other free-text field `render_text` already renders.
- A finding whose `subject` has no entry in the manifest-location lookup (e.g. `report.py`'s own synthetic `indeterminate:coverage-floor:<axis>` finding, whose `subject` is an axis name, not a package) omits the manifest+location clause gracefully — never crashes, never fabricates a location.

**Block If:**
- (Design decision recorded, not a HALT): extracting a `fixed` version from an OSV record's `affected[].ranges[].events[]` should take the FIRST well-formed `fixed` event found for that advisory, defensively (mirrors this module's existing "any shape mismatch yields fewer findings, never a crash" ethos throughout `vuln.py`) — do not build a full semver-range resolver correlating the fixed event against the scanned package's own version; that is out of scope for this story.
- No other unattended-unsafe decision identified — the schema/model layer is frozen and this story's design deliberately never touches it.

**Never:**
- No `explain` subcommand (explicitly out of scope per epics.md/PRD wording).
- No change to `models.py`, `report-schema.json`, or `REPORT_SCHEMA_VERSION`.
- No change to `verdict.py`'s lattice, `_EXIT_BY_STATUS`, or `_LEGAL_EXITS_BY_STATUS`.
- `--doctor` never returns exit code `1`.
- No dogfooding task, corpus provisioning, or fleet-scale/parallel-execution validation (that is Story 5.2's scope — confirmed 5.1's own three ACs in epics.md never mention dogfooding).
- No new air-gap CLI flag or config concept — "air-gap explicit" (NFR-U2) is realized entirely as `--doctor`'s diagnostic wording over the SAME already-offline-by-default KEV/EPSS/OSV-DB checks, not a new mechanism.
- Remediation lines apply ONLY to `findings[]`, never `errors[]` — AC1's "not a re-wrap of 1.7's typed errors" scopes this story to finding diagnostics; typed-error messages are unchanged.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|---|---|---|---|
| Non-zero exit, vuln finding, fixed version known | osv record's `affected[].ranges[].events[]` has a `fixed` entry | finding line followed by a remediation line: package, advisory id, severity, fixed-version, manifest+section, "upgrade to >= X" | No error |
| Non-zero exit, vuln finding, no fixed version published | osv record has only `versions:` (no `ranges`/`events`) | remediation line states no fixed version is published yet; suggests waiver/removal | No error |
| Hygiene DEP001 finding | deptry-reported unused dependency | remediation line names the rule + manifest+location + "remove from the manifest" | No error |
| License `denied` finding | `Finding.license.verdict == denied` | remediation line names the SPDX expression + "replace the dependency or waive" | No error |
| Currency `eol` finding | `Finding.currency.verdict == eol` | remediation line names `eol_date` + "upgrade to a supported release" | No error |
| `indeterminate:*` finding, subject not in manifest lookup | synthetic coverage-floor finding | remediation line omits manifest clause; still gives a generic action | No error |
| `warden scan --doctor`, all healthy | deptry+osv-scanner in range, OSV DB present+fresh | exit 0; text and json both report every check `ok`; no discovery/extraction/policy runs | No error |
| `warden scan --doctor`, osv-scanner missing from PATH | binary absent | exit 2; one check reports `ENGINE_UNAVAILABLE`-style message naming osv-scanner; never exit 1 | typed message, no traceback |
| `warden scan --doctor`, KEV/EPSS feed absent, no `--fail-on-kev`/`--min-epss` override | offline, feeds never fetched | that check reports "operating air-gapped" informationally; exit 0 overall | No error |
| `warden scan --doctor --format json` | | one small ad-hoc JSON doc on stdout (not `ComplianceReport`-shaped); pure stdout preserved | No error |
| Zero-config scan, critical vuln / KEV-listed / expired waiver / out-of-range engine | no flags | still composes `policy-violation`/`error` exactly as today (regression guard, no new code) | Unchanged |

</intent-contract>

## Code Map

- `src/pyforge/warden/vuln.py` -- `_findings_for_package`/`parse_osv_output`/`OsvParse` -- extract each advisory's `fixed` version from `affected[].ranges[].events[]` (first well-formed match; `None` on any missing/malformed shape) into a new `OsvParse.fixed_versions: Mapping[str, str]` (`finding.id -> fixed version string`), mirroring `kev_candidates`'s existing "returned alongside findings, never stored ON `Finding`" shape (vuln.py:820-824).
- `src/pyforge/warden/interfaces.py` -- `EngineResult` (interfaces.py:151-207) -- add `fixed_versions: Mapping[str, str] = MappingProxyType({})` (additive/defaulted, mirrors `kev_data`/`epss_data`'s threading precedent, but merged as a dict union across `engine_results` rather than first-non-None, since it is per-finding, not per-feed).
- `src/pyforge/warden/engines.py` -- `OsvEngine.run` (engines.py:1038+) -- thread `parse_osv_output(...).fixed_versions` into the `EngineResult(...)` constructed at the real-parse success site only (other early-return branches keep the default). Add a new public `run_doctor_checks(target: Path) -> tuple[DoctorCheck, ...]` (no config param — every check below is constant-driven, never policy-driven) plus a new small frozen `DoctorCheck(name: str, ok: bool, message: str)` dataclass (engines.py-local, NOT `models.py` — this is not part of the `ComplianceReport` contract). Reuses `_check_engine_version` (engines.py:353) twice — once with `DeptryEngine`'s own `argv=["deptry", "--version"]`/`_DEPTRY_VERSION_PATTERN`/`DEPTRY_VERSION_RANGE`, once with `OsvEngine`'s own `argv=["osv-scanner", "--version"]`/`_OSV_SCANNER_VERSION_PATTERN`/`OSV_SCANNER_VERSION_RANGE` (engines.py:158-166) — plus the OSV-DB presence/staleness check (`vuln.resolve_cache_dir`/`db_zip_path`/`db_snapshot_at`/`is_db_stale`/`vuln.DB_MAX_AGE_DAYS`, mirroring `OsvEngine.run`'s own pre-flight at engines.py:1073) and the KEV/EPSS feed presence/staleness check (`feeds.resolve_cache_dir`/`kev_cache_path`/`epss_cache_path`/`load_kev_catalog`/`load_epss_scores`/`is_feed_stale`/`feeds.DEFAULT_FEED_MAX_AGE_DAYS`) called UNCONDITIONALLY (not gated on `fail_on_kev`/`min_epss`). An absent KEV/EPSS feed is reported `ok=True` with an explicit "operating air-gapped: `<feed>` not present, offline default assumed" message — never a failing check.
- `src/pyforge/warden/report.py` -- `render_text` (report.py:481) -- new caller-supplied `manifest_locations: Mapping[str, tuple[str, ...]] = MappingProxyType({})` and `fixed_versions: Mapping[str, str] = MappingProxyType({})` params. One new remediation line follows each rendered finding line (after report.py:534), built by a new small private `_remediation_line(finding: dict, *, manifest_locations, fixed_versions) -> str | None` templated per id-family/axis (vuln/hygiene DEP-code/license verdict/currency verdict/`indeterminate:` reason token; `None` -> no line emitted). Manifest+location renders each `Provenance` as `f"{manifest} [{section}]"`, joined `"; "` when multiple. `render_json`/`assemble_report`/`REPORT_SCHEMA_VERSION` untouched.
- `src/pyforge/warden/cli.py` -- new `--doctor` `store_true` flag on the `scan` subparser, placed near `--warn-only` (cli.py:595). `main()` (cli.py:696) gains `if args.doctor: return _run_doctor(args)` before the existing `return _run_scan(args)`. New `_run_doctor(args: argparse.Namespace) -> int` -- stats the target the same way `_run_scan` does (no config load needed — doctor is config-independent), calls `engines.run_doctor_checks`, prints one line per check under `--format text` (`  [doctor] <name> ok|problem -- <message>` plus a summary line) or the new small non-schema JSON object under `--format json` (sorted by `name`, still pure stdout), returns `0` if every check is `ok` else `exit_code_for(Status.ERROR)`. In `_run_scan`: once `inventory` is resolved, build `manifest_locations` from `inventory.components` (`name -> tuple(f"{p.manifest} [{p.section}]" for p in component.provenance)`) once; after `engine_results` is assembled, merge `fixed_versions` across all results (first-registration-order-wins on key collision, mirroring `interfaces.DefaultPolicy`'s existing engine-vs-engine dedupe convention). Thread both into the existing `render_text(...)` call (cli.py:1449) only — `assemble_report` is untouched.
- `src/shared/packages/pyforge-warden/README.md` -- new "Installing & adopting Warden" section: local install (`pixi global install`/local channel), the pixi-pack air-gapped bundle path, the nebi push/pull OCI path (marked alpha), the recommended first-contact command (`warden scan . --warn-only`), and `--doctor`'s exit contract (`0`/`2`, never `1`) — distilled from `docs/specs/pyforge-warden.md`'s existing D8/P8 content, not copied verbatim.
- `tests/unit/test_vuln.py` -- fixed-version extraction: present via `ranges`/`events`/`fixed`, absent (bare `versions:` form, today's fixture shape), malformed events, multiple ranges (first wins).
- `tests/fixtures/osv-db/pypi/` -- extend or add one fixture record with a `ranges`/`events`/`fixed` shape (today's fixtures only use the simpler `versions:` form) so the known-fixed-version path is exercisable.
- `tests/unit/test_report.py` -- remediation-line assertions per axis/id-family (vuln w/ and w/o fixed-version, each DEP-code, license denied/unknown, currency eol/over-lag/unknown, an `indeterminate:` reason token, and the manifest-lookup-miss fallback) plus `_single_line` sanitization of the new line.
- `tests/unit/test_cli_doctor.py` (new) -- `--doctor` exit-code matrix (healthy=0; engine missing/out-of-range=2 via a monkeypatched `PATH`/stub binary; never 1), `--format json` shape, air-gapped KEV/EPSS wording when feeds absent, SIGINT/parse-error paths unaffected.
- `tests/conformance/test_doctor.py` (new) -- E2E via `cli.main(["scan", "--doctor", ...])`, both `--format` values, confirms no discovery/extraction/policy side effects occur (e.g. no manifests read).

(All paths above are relative to `src/shared/packages/pyforge-warden/` unless prefixed otherwise.)

## Tasks & Acceptance

**Execution:**
- [x] `src/pyforge/warden/vuln.py` -- add `OsvParse.fixed_versions` -- surface osv-scanner's discarded `fixed` version without touching `Finding`
- [x] `src/pyforge/warden/interfaces.py` -- add `EngineResult.fixed_versions` -- additive/defaulted seam threading, mirrors `kev_data`/`epss_data`
- [x] `src/pyforge/warden/engines.py` -- thread `fixed_versions` through `OsvEngine.run`; add `DoctorCheck` + `run_doctor_checks` -- reuse existing engine-version/OSV-DB/KEV/EPSS detection for the doctor aggregation
- [x] `src/pyforge/warden/report.py` -- `render_text(manifest_locations=..., fixed_versions=...)` + `_remediation_line` -- the actual diagnostic content (AC1)
- [x] `src/pyforge/warden/cli.py` -- `--doctor` flag + `_run_doctor` + `main()` dispatch + `manifest_locations`/`fixed_versions` wiring into `_run_scan`'s `render_text` call
- [x] `src/shared/packages/pyforge-warden/README.md` -- install/on-ramp/air-gap/`--doctor` documentation (AC4)
- [x] `tests/unit/test_vuln.py` + one new/extended osv-db fixture -- fixed-version extraction coverage
- [x] `tests/unit/test_report.py` -- remediation-line coverage per axis/family + sanitization + lookup-miss fallback
- [x] `tests/unit/test_cli_doctor.py` (new) -- `--doctor` exit-code matrix + json shape + air-gapped wording
- [x] `tests/conformance/test_doctor.py` (new) -- E2E proof, no scan side effects under `--doctor`

**Acceptance Criteria:**
- Given a scan composing a non-clean, non-zero-exit status with at least one finding, when the text report renders, then each finding line is followed by a remediation line naming the package, the finding's specific identity (advisory id + severity + fixed-version for vuln, or the DEP-code for hygiene), the declaring manifest(s)+section(s) (when known), and a concrete next action — never merely re-stating `finding.message`.
- Given zero configuration, when a scan runs, then a CRITICAL vulnerability finding still composes `policy-violation`, a KEV-listed finding still forces `policy-violation`, an expired waiver still re-blocks, and an out-of-tested-range engine still composes `error` — all already-shipped zero-config-default behaviors, unregressed by this story.
- Given `warden scan --doctor` on a healthy environment, when it runs, then it exits `0`, performs no discovery/extraction/policy work, and both `--format text`/`--format json` report every check healthy.
- Given `warden scan --doctor` with an unavailable/out-of-range engine or an unreadable OSV DB, when it runs, then it exits `2` naming the specific problem, and never exits `1`.
- Given `warden scan --doctor` with the KEV and/or EPSS feed absent and no gate flag requiring it, when it runs, then that check reports an explicit "operating air-gapped" informational line and the overall exit stays `0`.
- Given the package README, when a maintainer reads its adoption section, then it names the local install path, the pixi-pack air-gapped bundle path, the nebi/OCI path (alpha), the recommended first-contact command, and `--doctor`'s exit contract.

## Spec Change Log

(Empty — no `bad_spec` loopback yet.)

## Review Triage Log

### 2026-07-24 — Review pass

- intent_gap: 0
- bad_spec: 0
- patch: 7: (high 2, medium 2, low 3)
- defer: 5: (medium 1, low 4)
- reject: 0
- addressed_findings:
  - `[high]` `[patch]` Edge Case Hunter found `engines._doctor_check_osv_db` left `db_snapshot_at(zip_path)` unwrapped — a TOCTOU race (the DB vanishing/becoming unreadable between `_db_has_valid_advisory`'s own read and this stat call) would raise an uncaught `OSError` all the way to `main()`'s last-resort net, turning a `--doctor` health-check into a raw traceback instead of a clean typed message. Fixed: wrapped in `try/except OSError`, returning `DoctorCheck(ok=False, ...)` naming the problem (mirrors `_doctor_check_feed`'s own existing TOCTOU guard one function above it).
  - `[high]` `[patch]` Both reviewers independently found `vuln._extract_fixed_version` read `fixed` events from EVERY `affected[]` entry in an OSV record with no filter on which entry's `package.name`/`ecosystem` matches the package actually being processed — a multi-package (monorepo-style) advisory could attribute an unrelated affected package's fixed version to the current finding, producing an actively wrong "upgrade to >= X" remediation. Fixed: `_extract_fixed_version` now takes `pkg_name`/`pkg_ecosystem` and only reads `ranges`/`events` from `affected[]` entries whose own `package` sub-object matches (mirrors `_advisory_targets_pypi_name`'s tolerant per-entry shape). Added `test_parse_osv_output_ignores_fixed_version_from_an_unrelated_affected_package` and `test_parse_osv_output_matches_fixed_version_by_ecosystem_too`; updated the pre-existing malformed-shape parametrize cases and the first-well-formed-wins test to carry a matching `package` block so they keep exercising ranges/events parsing rather than short-circuiting on the new package-match filter.
  - `[medium]` `[patch]` Both reviewers independently found `cli.py`'s `manifest_locations` lookup was a plain dict comprehension keyed only by `component.name` — two components can legitimately share one name at different versions post-merge (`inventory.py`'s own documented "distinct versions ... stay distinct"), so the LAST-iterated component's provenance silently clobbered an earlier one's, letting a remediation line name the wrong manifest/section. Fixed: every same-named component's provenance is now UNIONed (sorted, deduplicated) instead of overwritten — an honest "every place this name is declared" rather than a wrong single guess.
  - `[medium]` `[patch]` Blind Hunter found `_run_doctor` duplicated ~40 lines of `_run_scan`'s early path-stat/validation logic verbatim (empty-path check, `FileNotFoundError`/`NotADirectoryError`/`ValueError`/`OSError` handling, the `S_ISDIR` check) — two call sites to keep in sync for any future fix. Extracted into a shared `_resolve_scan_target(args) -> Path | int` helper both `_run_scan`/`_run_doctor` now call.
  - `[low]` `[patch]` Blind Hunter found `manifest_locations` was keyed only by `component.name`, but vuln findings' `subject` is osv-scanner's own echoed package name (mirroring the synthesized PyPI identity for conda-sourced components), which can differ from `component.name`. Fixed: `manifest_locations` is now additionally keyed by `component.pypi_identity.name` when present, so a conda/PyPI name divergence still resolves the manifest-location clause (folded into the same P1 dict-build edit above).
  - `[low]` `[patch]` Blind Hunter found `engines._doctor_check_feed`'s `cache_path` parameter was typed `Callable[[str], Path]` while the actual functions passed (`feeds.kev_cache_path`/`feeds.epss_cache_path`) are `Callable[[str | Path], Path]` — a harmless-at-runtime but incorrect type-annotation. Fixed: corrected the annotation.
  - `[low]` `[patch]` Blind Hunter found no test exercised the OSV-DB "present but stale" branch of `_doctor_check_osv_db` (`test_doctor_unreadable_osv_db_exits_2_naming_the_problem` only covers the DB-absent branch) — a functionally distinct exit-2 path left uncovered. Added `test_doctor_stale_osv_db_exits_2_naming_the_problem`, building a function-scoped DB cache and backdating its zip past `DB_MAX_AGE_DAYS` (never mutating the session-scoped ambient fixture other tests rely on staying fresh — mirrors `test_osv_engine.py`'s own staleness-test pattern).
- Deferred (5, appended to `deferred-work.md`):
  - `[medium]` A hygiene-axis remediation's manifest-location clause is frequently unavailable because deptry's `module` field is an import name (e.g. `yaml`, `bs4`, `PIL`, `sklearn`), not a distribution name, with no existing correlation table back to the declaring component in this codebase — AC1's own "(when known)" qualifier already scopes this as spec-compliant, but building a real import-name→distribution mapping (a substantially larger effort) would raise the hit rate. Out of this story's scope.
  - `[low]` `--doctor` silently no-ops every other `scan` flag it's combined with, with no warning — low-priority UX polish, not a functional defect.
  - `[low]` `report._remediation_line`'s vuln branch re-derives the advisory id for display by splitting the already-escaped finding id rather than the raw advisory id — practically unreachable (real advisory id formats never contain colons/newlines).
  - `[low]` `tests/conftest.py`'s "ONE seeded advisory" comment is stale (pre-existing, now further out of date after this story's third fixture record).
  - `[low]` Hardcoded `["deptry", "--version"]`/`["osv-scanner", "--version"]` argv literals now exist at three call sites with no shared constant — minor duplication risk, pre-existing pattern this story extends rather than introduces.
- Rejected: none.

All 7 patch fixes applied; full suite re-verified green (1918 passed, was 1915 before this pass, net +3 tests from the two new fixed-version-attribution tests plus the new stale-osv-db doctor test). `models.py`, `data/report-schema.json`, and `verdict.py` remain untouched.

### 2026-07-24 — Review pass (follow-up, fresh Blind Hunter + Edge Case Hunter over `f0c7d8d8..8b06fc79`)

- intent_gap: 0
- bad_spec: 0
- patch: 9: (high 0, medium 6, low 3)
- defer: 2: (medium 1, low 1)
- reject: 3
- addressed_findings:
  - `[medium]` `[patch]` Blind Hunter found the doctor's absent-KEV-feed message ("operating air-gapped: kev feed not present, offline default assumed") factually inverted under the SHIPPED default: `config.EffectiveConfig.fail_on_kev = True`, so `_kev_enrichment` emits the whole-axis `indeterminate:kev-data-unavailable:kev-feed` finding (exit 1) on any default-config scan without the feed — doctor green-lit an environment whose default scan cannot produce a trusted verdict. The intent contract pins ok=True/exit-0 for absent feeds (AC5) but NOT the message text: fixed by giving `_doctor_check_feed` per-feed `absent_hint`/`stale_hint` params — KEV's now truthfully names the default fail-on-kev gate's indeterminate consequence and the two remedies (provision the feed / disable the gate); EPSS's states no gate is active without `--min-epss` (accurate: `min_epss` defaults `None`). The stale-KEV wording ("offline default still applies") had the same defect and got the same treatment. Test updated to pin the per-feed consequence wording.
  - `[medium]` `[patch]` Blind Hunter found a provisioned-but-corrupt feed file misreported as "not present"/air-gapped (`load_kev_catalog` returns `None` for missing and corrupt alike). Fixed: `_doctor_check_feed` now distinguishes via `path.is_file()` after a `None` load — present-but-unloadable is `ok=False` naming the file ("present … but unreadable or invalid -- refresh or remove it", exit 2), mirroring `_doctor_check_osv_db`'s own content-corrupt handling; genuinely-absent (and vanished-mid-check TOCTOU) stays the air-gapped ok. New test `test_doctor_present_but_corrupt_kev_feed_exits_2_naming_the_file`.
  - `[medium]` `[patch]` Blind Hunter found the README's first-contact claim "`--warn-only` … without ever failing the run" false for operational failures (`warn_blocking` downgrades only finding-backed rungs; a fresh machine with no OSV DB exits 2 on the documented on-ramp command). Fixed: scoped the claim to findings and added the operational-error caveat pointing at `--doctor`.
  - `[medium]` `[patch]` Blind Hunter found the README's `--doctor` contract ("exits … 2 when something is missing", with KEV/EPSS caches listed among the verified items) contradicting the implementation (absent feeds exit 0 by design/AC5). Fixed: the section now states absent feeds report an informational air-gapped line at exit 0, and names the default fail-on-kev consequence for default-config scans.
  - `[medium]` `[patch]` Edge Case Hunter found `_extract_fixed_version` read `fixed` events from ranges of ANY type — a `GIT`-typed range's `fixed` is a COMMIT HASH (PYSEC records routinely list the GIT range first), rendering "upgrade to >= <40-hex sha>" nonsense advice. Fixed: only `ECOSYSTEM`/`SEMVER`-typed ranges are read; a missing/unrecognized `type` is skipped as malformed. New fall-through test + two new malformed-shape parametrize cases (missing-range-type, git-only-range); existing extraction tests updated to carry the `type` OSV requires anyway.
  - `[medium]` `[patch]` Both reviewers re-raised (with a sharper CI-gate-disable scenario) the first pass's deferred "`--doctor` silently no-ops every other scan flag": someone appending `--doctor` to an existing CI scan line would disable the compliance gate with no trace — intolerable to leave silent for a product whose contract is "never false-greens". Fixed: `_run_doctor` diffs the parsed args against the scan subparser's own defaults (drift-proof for future flags) and names every ignored non-default flag on stderr; `path`/`--format`/`--doctor` stay honored. New test; the healthy no-extra-flags run keeps stderr empty. (The first pass's ledger entry for this is now resolved-in-code; the entry itself is left to the orchestrator per its ownership rule.)
  - `[low]` `[patch]` Edge Case Hunter found the manifest-location lookup misses when a manifest's declared spelling and the finding subject differ only by PEP-503 normalization (`Foo_Bar` vs `foo-bar`). Fixed: `cli.py` canonicalizes the `manifest_locations` keys and `report._manifest_clause` canonicalizes the lookup with the same new `_canonical_subject_key` (two spellings that collapse together ARE the same PyPI package, so the union is correct). New test.
  - `[low]` `[patch]` Blind Hunter found the doctor text renderer interpolated `check.message` raw — bypassing the very `_single_line` invariant this story extends in `render_text`; a future check message embedding subprocess stderr would forge extra `[doctor]` lines under the `checks=N` header. Fixed: the render site now passes messages through `_single_line`; new test pins header+N physical lines with a crafted newline-bearing message.
  - `[low]` `[patch]` Blind Hunter found `_doctor_check_osv_db`'s env-var message ("… is unset") wrong for the set-but-empty case (`resolve_cache_dir` returns `None` for both). Fixed: "is unset or empty".
- Deferred (2, appended to `deferred-work.md` as NEW entries):
  - `[medium]` First-well-formed-`fixed`-event selection (an intent-contract-recorded decision) picks the OLDEST branch's fix in real multi-branch backport advisories, producing self-contradictory "upgrade to >= X" advice below the installed version; max-fixed would be universally sufficient at identical cost but contradicts the contract's literal wording — a spec-level decision, not a review patch.
  - `[low]` The manifest-location union across same-name different-version components can name a manifest declaring only the non-vulnerable version; version-aware keying would restore precision but needs per-family subject parsing.
- Rejected (3):
  - Blind Hunter's "over-lag remediation can render the literal `None`" — refuted: `models.py`'s `Finding.__post_init__` cross-validates every `currency:eol/over-lag` finding to a non-null `latest`/`lag`/`eol_date` (models.py:437), and `render_text` only consumes `report.to_json_dict()` of model-validated findings; the failure scenario cannot occur. (A guard was drafted, then reverted as dead code once the model guard was verified.)
  - Blind Hunter's doctor/scan-target coupling (`warden scan /typo --doctor` exits 2; reused "vanished after discovery?" message) — the Code Map mandates statting the target; the typo diagnostic names the actual problem; the stale-message scenario requires the target directory to vanish mid-doctor.
  - Edge Case Hunter's canon-match of `affected[].package.name` vs the scanner echo — contradicts the recorded same-source reasoning in `_extract_fixed_version`'s docstring (both names originate from the same osv-scanner/DB output); speculative, and the failure mode is a silently-absent fixed version (graceful), not wrong advice.

All 9 patch fixes applied; full suite green: 1925 passed (was 1918 after the first pass; net +7 tests). `models.py`, `data/report-schema.json`, and `verdict.py` remain untouched; `render_json`'s document is byte-for-byte unchanged.

### 2026-07-24 — Review pass (second follow-up, fresh Blind Hunter + Edge Case Hunter over `f0c7d8d8..72a0ac71`)

- intent_gap: 0
- bad_spec: 0
- patch: 11: (high 0, medium 4, low 7)
- defer: 1: (low 1)
- reject: 3
- addressed_findings:
  - `[medium]` `[patch]` Blind Hunter found the README's `--warn-only` operational-error caveat (itself a pass-2 fix) factually wrong for its OSV-DB half: "an unprovisioned offline OSV database exits `2` even under `--warn-only`" — verified false: `OsvEngine.run`'s pre-flight returns `_withheld_findings` (indeterminate FINDINGS, no `ErrorRecord`), so the state exits 1 by default and 0 under `--warn-only` (`waiver.warn_blocking` deliberately sweeps every INDETERMINATE), leaving the vulnerability axis silently unassessed on the exact on-ramp command the README recommends. Fixed: the caveat now separates the engine case (still exit 2) from the OSV-DB case (indeterminate findings, downgraded under `--warn-only`) and says why `--doctor` matters first.
  - `[medium]` `[patch]` Blind Hunter found a PRESENT-but-stale KEV feed reported `ok=True`/exit 0 by doctor while the same state forces every default-config scan (`fail_on_kev=True`) whole-axis indeterminate/exit 1 — the machine-readable signal (exit code + JSON `status`) green-lit an environment whose default scan cannot produce a trusted verdict, and asymmetrically so (`_doctor_check_osv_db` already treats its own stale state as exit 2). Pass 2 had fixed only the message text. Fixed: `_doctor_check_feed` gained `stale_is_problem` (KEV `True`; EPSS — and the new endoflife check — stay informational, since their gates are off by default); stale-present KEV is now `ok=False`/exit 2. AC5 (ABSENT feeds → exit 0) is untouched. New tests pin stale-KEV=2, stale-EPSS=0, and the problem-state JSON shape (all three previously uncovered — the Blind Hunter's separate coverage finding, folded here).
  - `[medium]` `[patch]` Both reviewers independently found doctor checks KEV/EPSS but not the THIRD sibling under the same feed-cache root — the endoflife.date snapshot the currency axis's tier-2 resolution actually consumes (`feeds.endoflife_cache_path`/`load_endoflife_snapshot`, Story 6.3) — so a corrupt/stale endoflife cache passed doctor exit 0 while a currency-gated scan degrades to `currency:unknown`/indeterminate. Fixed: added the `endoflife-feed` check via the same `_doctor_check_feed` helper with truthful per-feed hints (absent → "no currency gate is active unless --max-lag/--require-lts/--fail-on-eol is passed"); checks 5 → 6 across text/JSON and both test surfaces.
  - `[medium]` `[patch]` Blind Hunter found the vuln no-fix remediation asserting "no fixed version is published yet" when `_extract_fixed_version` returning `None` only means no well-formed ECOSYSTEM/SEMVER `fixed` event exists IN THE RECORD READ (e.g. a GIT-ranges-only PYSEC record or the `versions:`-only form — a fix may well exist upstream) — a false worldwide-absence claim steering users toward a waiver instead of a real upgrade. Fixed: the line now says "no fixed version is recorded in the advisory data … check the advisory upstream, or consider a waiver or removing the dependency" (the I/O matrix row's substance — absence stated + waiver/removal suggested — preserved).
  - `[low]` `[patch]` Edge Case Hunter found a directory (or other non-file) squatting on a feed cache path classified as absent/air-gapped `ok=True` (`is_file()` returns False, loader returns `None`) — a provisioning mistake reported as healthy. Fixed: the present-check uses `exists()`; present-but-unusable now exits 2 naming the path. New test.
  - `[low]` `[patch]` Blind Hunter found `report.py`'s module docstring claiming the new params' "defaults preserve every pre-5.1 caller/test byte-for-byte" — demonstrably false in the same diff (AC1 renders the remediation line unconditionally; the story itself rewrote four pre-existing byte-exact tests). Fixed: the docstring now states defaults are signature-compatible but do NOT reproduce pre-5.1 output.
  - `[low]` `[patch]` Blind Hunter found DEP001/DEP003/DEP004 remediation templates presenting deptry's `module` subject — an IMPORT name (`cv2`, `yaml`, `PIL`) for the imported-side codes — as a manifest-declarable name ("declare cv2 as a dependency" fails resolution or resolves to a squatted package). Fixed: those templates now say "the distribution that provides {subject}"; declared-side DEP002/DEP005 stay direct.
  - `[low]` `[patch]` Blind Hunter found the "the autouse socket-deny harness governs this path too" claim (run_doctor_checks/`_run_doctor` docstrings + conformance test) overclaiming: the harness patches in-process sockets only — the `--version` child processes run outside its reach. Fixed: wording now scopes the harness to the in-process half.
  - `[low]` `[patch]` Blind Hunter found `test_doctor_unreadable_osv_db_exits_2_naming_the_problem` actually exercising the env-UNSET branch (its body delenvs the var), leaving `_doctor_check_osv_db`'s distinct "no usable offline OSV database found" (present-dir, absent/empty/corrupt DB) branch untested at the doctor surface. Fixed: renamed to `test_doctor_unconfigured_osv_db_env_…` (now also pinning "unset or empty") and added `test_doctor_absent_osv_db_under_configured_dir_exits_2`.
  - `[low]` `[patch]` Both reviewers found two defects in the pass-2 ignored-flags mechanism: it ran AFTER `_resolve_scan_target`, so `warden scan /typo --doctor --warn-only` exited 2 with NO trace of the dropped gate flags (reintroducing the silent swallowing it exists to prevent), and its `parse_args([])` defaults probe would raise an uncaught `SystemExit` inside `_run_doctor` if a future scan flag were `required=True`. Fixed: the trace now emits before target resolution and the probe is wrapped (`except SystemExit` → skip the trace, never kill doctor). New test pins the trace surviving an invalid target.
  - `[low]` `[patch]` Edge Case Hunter found the README's doctor exit-2 enumeration omitting the present-but-unloadable feed cause pass 2 introduced (an operator with a truncated KEV feed would expect exit 0 and misread the failure). Fixed: the README's doctor section now enumerates all exit-2 causes — including the stale-KEV one added this pass — and names the endoflife cache among the verified items.
- Deferred (1, appended to `deferred-work.md` as a NEW entry):
  - `[low]` `_canonical_subject_key`'s PEP-503 collapse is applied to conda-native component names too, where separator-twins (`importlib-metadata` vs `importlib_metadata`) are genuinely distinct packages — an environment declaring both unions their declaration sites and a remediation line can name the twin's manifest. A correct fix needs exact-match-first lookup (two-tier seam reshape); low consequence.
- Rejected (3):
  - Blind Hunter's "first-fixed-event selection yields the oldest branch's fix / 'to resolve' overclaims sufficiency" — the same selection-rule root cause the pass-2 ledger entry already records as a spec-level decision (the intent contract's Block If pins first-well-formed-wins); re-deferring would duplicate an entry the orchestrator owns.
  - Blind Hunter's "doctor exits 0 after the entire payload failed to reach stdout (ENOSPC)" — the emission guard deliberately mirrors `_run_scan`'s documented trade-off: `BrokenPipeError` absorption is required for `warden scan --doctor | head -1` to exit 0 correctly, any other stdout failure writes a loud "any partial stdout must not be consumed" stderr diagnostic, and exit-code-only automation receives a health claim that is in fact true.
  - Edge Case Hunter's "canon-match `affected[].package.name` vs the scanner echo" — a re-raise of the finding pass 2 already rejected with recorded same-source reasoning in `_extract_fixed_version`'s docstring; the failure mode is a gracefully-absent fixed version, now rendered truthfully by this pass's no-fix wording fix.

All 11 patch fixes applied; full suite green: 1931 passed (was 1925 after the follow-up pass; net +6 tests). `models.py`, `data/report-schema.json`, and `verdict.py` remain untouched; `render_json`'s document is byte-for-byte unchanged.

## Design Notes

**Why a render_text side channel, not a schema change:** `models.py` is explicitly documented as frozen ("later epics are producers against this contract, never editors"); Story 6.1 was the one sanctioned amendment that pre-allocated the `kev`/`epss`/`license`/`currency` slots on `Finding`. Fixed-version and manifest+location were never reserved slots, so adding them to `Finding` would be an unsanctioned second amendment. The existing `applied_waivers`/`expired_waivers`/`applied_baseline`/`expired_baseline` parameters on `render_text` already establish the sanctioned pattern for exactly this shape of addition: caller-supplied, human-report-only content that never touches `ComplianceReport`/the JSON schema. This story follows that precedent for remediation content too.

**Golden example (vuln, fixed version known):**
```
  [vulnerability] critical vuln:GHSA-xxxx-yyyy:requests@2.25.0 -- requests: GHSA-xxxx-yyyy (severity critical)
      -> fix: upgrade requests to >= 2.31.0 to resolve GHSA-xxxx-yyyy (declared in pyproject.toml [project.dependencies])
```

**Golden example (hygiene DEP001):**
```
  [hygiene] policy-violation hygiene:DEP001:flask -- flask: unused dependency (DEP001)
      -> fix: remove flask from the manifest (declared in pyproject.toml [project.dependencies]) -- looks unused
```

**`--doctor` output shape (text):**
```
warden: doctor status=ok checks=5
  [doctor] deptry ok -- 0.25.3 (within tested range)
  [doctor] osv-scanner ok -- 2.4.1 (within tested range)
  [doctor] osv-db ok -- snapshot 2026-07-20T00:00:00Z (fresh)
  [doctor] kev-feed ok -- operating air-gapped: kev feed not present, offline default assumed
  [doctor] epss-feed ok -- operating air-gapped: epss feed not present, offline default assumed
```

## Verification

**Commands:**
- `pixi run -e pyforge-warden pyforge-warden-test` -- expected: full suite green, no regressions in existing `render_text`/`OsvEngine`/`EngineResult` call sites (every new parameter is additive/defaulted).
- `pixi run -e pyforge-warden pytest src/shared/packages/pyforge-warden/tests/unit/test_cli_doctor.py src/shared/packages/pyforge-warden/tests/conformance/test_doctor.py -q` -- expected: new tests pass, including the never-exit-1 assertion.

**Manual checks (if no CLI):**
- Read the updated README section and confirm it names all four paths (local/pixi-pack/nebi/first-contact) plus `--doctor`'s exit contract, without copying `docs/specs/pyforge-warden.md` verbatim.

## Dev Notes (implementation, 2026-07-24)

- **Deviation from the golden hygiene example's DEP-code labeling.** The Design Notes' "Golden example (hygiene DEP001)" pairs `DEP001` with unused-dependency wording ("remove flask from the manifest ... -- looks unused"). Checked against the installed `deptry` 0.25.1 package's own violation classes (`deptry/violations/dep00{1..5}_*`), the real semantics are: `DEP001` = imported but missing from the dependency declarations (add it); `DEP002` = declared but unused (remove it — the golden example's own wording); `DEP003` = imported but only a transitive dependency (declare it directly); `DEP004` = imported in non-dev code but declared as a dev dependency (move dependency groups); `DEP005` = declared but part of the Python standard library (remove it, redundant). `hygiene.py`'s own pre-existing DEP005 docstring already documents this same "verify against the real deptry package, don't guess" discipline. The implementation follows the verified real semantics per DEP-code (`report._DEP_CODE_ACTIONS`) rather than the golden example's DEP001↔DEP002 mismatch; the example's overall LINE SHAPE (indent, `-> fix:` prefix, trailing manifest-clause parenthetical) is followed exactly.
- **`--doctor` ok-message wording.** `_check_engine_version` (Story 6.6) returns `ErrorRecord | None` with no parsed-version payload on success, and its signature/tests were left untouched (in-scope reuse, not a rewrite) — so a passing engine check's message states `"within tested range <SpecifierSet>"` rather than echoing the live detected version number the Design Notes' illustrative `--doctor` output shows (e.g. `0.25.3 (within tested range)`). The overall shape (header line, one `[doctor] <name> ok|problem -- <message>` line per check, `checks=5`) matches exactly.
- **Fixed-version osv-db fixture.** Added `tests/fixtures/osv-db/pypi/PDOS-FIXTURE-0003.json` (package `pdos-vuln-fixture-fixed`, MEDIUM severity, an `affected[].ranges[].events[]` shape with `fixed: "2.0.0"` — unlike PDOS-FIXTURE-0001/0002's simpler `versions:` enumeration) so `tests/unit/test_vuln.py` exercises the fixed-version extraction against the EXACT shape a real fixture (and the ambient real-osv-scanner-consulted DB) carries, read from disk rather than hand-duplicated. It is also folded into the ambient session-wide offline OSV DB every test in the suite shares; no existing fixture/test references its package name, so it is inert everywhere except the new tests that target it.
- Full suite: `pixi run -e pyforge-warden pyforge-warden-test` -- 1915 passed, 0 failed (baseline before this story: 1882 passed for the pre-existing suite once 4 pre-existing `render_text` byte-exact tests were updated for the new unconditional remediation line -- see below).
- Four pre-existing tests asserted `render_text`'s exact line count/content for a hygiene `warn` finding and had to be updated to include the new remediation line (AC1 makes it unconditional per finding, not opt-in): `tests/conformance/test_scan_harness.py::test_text_format_findings_fixture_emits_driver_and_finding_lines`, `tests/unit/test_discovery_extract_cli.py::test_text_format_emits_a_human_summary_with_driver_and_finding_lines`, `tests/unit/test_report.py::test_render_text_findings_render_in_to_json_dict_sorted_order_with_driver`, `tests/unit/test_report.py::test_render_text_neutralizes_embedded_newlines_in_finding_and_error_messages`.


## Auto Run Result

**Run (2026-07-24, bmad-dev-auto second follow-up review pass over `f0c7d8d8..72a0ac71`):** status `done`. Fresh Blind Hunter + Edge Case Hunter third-pass review; 19 raw findings deduplicated to 15 → 11 patched (0 high, 4 medium, 7 low), 1 deferred (new ledger entry), 3 rejected, 0 intent_gap, 0 bad_spec.

**Summary of changes this pass (commit `a4e7a537e2`):**
- `src/pyforge/warden/engines.py` — `_doctor_check_feed` gains `stale_is_problem` (stale-present KEV now `ok=False`/exit 2 — it blocks every default scan's trusted verdict exactly like a stale OSV DB; EPSS/endoflife stay informational) and uses `exists()` so a directory squatting on a feed path is present-but-unusable, never "air-gapped"; `run_doctor_checks` adds the `endoflife-feed` check (the currency axis's tier-2 source — checks 5 → 6) and stops overclaiming socket-deny-harness coverage of the `--version` subprocesses.
- `src/pyforge/warden/cli.py` — the `--doctor` ignored-flags stderr trace now emits BEFORE target resolution (a typo'd path no longer suppresses it) and its defaults probe is guarded against `SystemExit`.
- `src/pyforge/warden/report.py` — vuln no-fix remediation reworded truthfully ("no fixed version is recorded in the advisory data … check the advisory upstream"); DEP001/DEP003/DEP004 templates say "the distribution that provides {subject}" (deptry subjects are import names for those codes); module docstring no longer claims defaulted `render_text` output is byte-for-byte pre-5.1.
- `src/shared/packages/pyforge-warden/README.md` — corrected the factually wrong `--warn-only` claim (an unprovisioned OSV DB composes indeterminate findings → exit 1 default / exit 0 under `--warn-only`, never exit 2) and completed the `--doctor` exit-2 enumeration (unloadable feed files, stale KEV, endoflife cache listed).
- Tests — `test_cli_doctor.py` +6 (stale-KEV=2, stale-EPSS=0, dir-at-feed-path, problem-state JSON shape, absent-DB-under-configured-dir, trace-survives-invalid-target) plus renamed the mislabeled "unreadable osv db" test; `test_report.py`/`test_doctor.py` (conformance) updated for the new wording and checks=6.

**Verification:** `pixi run --frozen -e pyforge-warden pyforge-warden-test` → **1931 passed, 0 failed** (was 1925; net +6). `models.py`, `data/report-schema.json`, `verdict.py` untouched across all three passes; `render_json` byte-for-byte unchanged; `--doctor` still never exits 1.

**Follow-up review recommended: true** — this pass changed the `--doctor` machine-readable contract (stale-present KEV now exits 2; a sixth check added) and rewrote user-facing README exit-semantics; an independent pass should confirm no new truthfulness gaps in the reworked wording.

**Residual risks:** the deferred conda-namespace canonical-key collapse (new ledger entry) and the previously-ledgered first-fixed-event selection rule remain open, orchestrator-owned; the doctor's endoflife stale hint describes gate-active consequences that are exercised indirectly (via currency-axis tests), not by a dedicated doctor-level gate-active test.
