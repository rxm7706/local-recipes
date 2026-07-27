---
title: 'Story 1.5: osv-scanner as the second engine (vulnerability findings)'
type: 'feature'
created: '2026-07-16'
status: shipped
updated: '2026-07-27 (AUD-WARDEN-030 status sync)'
baseline_revision: '28a0f9fb68ad10cc9c57e801ffe8cd8a56f39201'
final_revision: '483a97e255e98c70483c2514de24344a5ff8b894'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - '{project-root}/_bmad-output/projects/pyforge-warden/planning-artifacts/osv-db-offline-provisioning-decision.md'
  - '{project-root}/_bmad-output/projects/pyforge-warden/planning-artifacts/architecture.md'
  - '{project-root}/_bmad-output/projects/pyforge-warden/planning-artifacts/epics.md'
  - '{project-root}/_bmad-output/projects/pyforge-warden/implementation-artifacts/epic-1-context.md'
warnings: [oversized]
---

<intent-contract>

## Intent

**Problem:** Story 1.4's spike empirically proved offline osv-scanner mechanics and produced a decision record + hermetic fixture DB, but the tool still ships only `DeptryEngine` — no CVE signal ever reaches the report. Worse, a vuln-matchable component (`cve_match_level=EXACT`, set at extraction) already projects to `clean` via `interfaces.match_level_rung` with **no engine having consulted a DB at all** — a live false-green today.

**Approach:** Add `OsvEngine` (`engines.py`) that synthesizes a sanitized `requirements.txt`-style input from vuln-matchable components, runs `osv-scanner` fully offline through a widened `_engine_env` (adds `extra_env` + surfaces the child's exit code — both required per the decision record's 3-part seam hand-off), applies the decision record §4 **content pre-flight** against `$OSV_SCANNER_LOCAL_DB_CACHE_DIRECTORY` before trusting any result, and parses vulnerabilities into `vuln:` findings + a populated `VulnData`. Reuses the 1.4 fixture DB/builder for tests; does not touch `test_osv_offline_db_spike.py`.

## Boundaries & Constraints

**Always:**
- Content pre-flight (decision record §4) runs **before** invoking `osv-scanner` when ≥1 vuln-matchable component exists: resolve `$OSV_SCANNER_LOCAL_DB_CACHE_DIRECTORY`, open `<dir>/osv-scanner/PyPI/all.zip` (exact case), require ≥1 entry that parses as JSON + has an `affected[]` entry naming a `PyPI` package with a concrete `versions`/`ranges` spec. Missing/unset var, missing/empty/content-corrupt zip → **no osv invocation**; emit one `indeterminate:offline-db-unavailable:<pkg>` finding (axis `vulnerability`) per candidate — reuses the **existing** `interfaces.DefaultPolicy` false-green backstop (any non-hygiene-axis finding → conservative `indeterminate` rung) verbatim, so **`interfaces.py` is untouched**.
- `_engine_env` gains `extra_env: dict[str, str] | None = None` (merged over the copied `os.environ`) and returns a 3-tuple `(text, error, exit_code)` — `exit_code` is `None` on every early-return path (mkstemp/spawn failure, timeout, vanished cwd) and the real `subprocess.run(...).returncode` once the child completes, including the two decode-failure paths. `DeptryEngine` is updated to unpack 3-tuples (still ignores the exit code).
- osv exit `0`→ parse for vulns (none expected); `1`→ parse for vulns (expected); `127` **after a passing pre-flight** → typed `ENGINE_EXECUTION_FAILED`; `128` → same `offline-db-unavailable`-style indeterminate treatment as an unusable DB (coverage-skipped, per decision record); any other code → typed `ENGINE_EXECUTION_FAILED`.
- Synthesized input lines use `component.pypi_identity.{name,version}` (already PEP-503-canonical), one `name==version` per line, **sorted**. Pure-data-projection guard (NFR-S6): a name/version pair that doesn't match a safe `[A-Za-z0-9._-]+` token, or starts with `-`, is **excluded** from the input (never written raw) and instead surfaces as one `indeterminate:unsafe-identity:<pkg>` finding — never silently dropped, never smuggled into argv/file content.
- On a real osv run, one `vuln:<advisory-id>:<pkg>@<version>` `Finding` per `(group.ids[i], package)` pair, axis `vulnerability`, `severity.tier` derived from that group's `max_severity` (CVSS v3.1 §5 qualitative bands: `<0.1`→none, `0.1–3.9`→low, `4.0–6.9`→medium, `7.0–8.9`→high, `≥9.0`→critical; unparsable/absent→`unknown`), `severity.raw` = the matching vulnerability's own `severity[].score` vector (`None` if absent). These reach the report through the same existing findings-pass-through + false-green-backstop path `DeptryEngine`'s findings already use (Story 1.6 wires the real severity→policy-violation mapping later — tighten-only).
- A successful osv run (pre-flight passed, osv completed 0/1) populates `VulnData(source=<resolved all.zip path>, snapshot_at=<all.zip file's own mtime, ISO-8601 UTC>, max_age_ok=None)` — `max_age_ok`'s threshold comparison is Story 2.4's job; `EngineResult` gains a `vuln_data: VulnData | None = None` field (additive, default `None` — `NullEngine`/`DeptryEngine` unaffected) that `cli.py`/`report.assemble_report` thread through, replacing the hardcoded `VulnData(None, None, None)`.
- Coverage claim (`AxisCoverage.deps_assessed`, axis `vulnerability`) = count of vuln-matchable components actually fed to a **successfully completed** osv run; `0`/no claim when the DB was unusable or there were zero candidates.
- `osv-scanner` absent from PATH in a test = hard-fail (`pytest.fail`), never skip — matches the 1.3/1.4 provisioned-engine convention.

**Block If:** none identified — the 1.4 decision record + this story's own empirical run (osv-scanner 2.4.0, verified `results[].packages[].groups[].max_severity` is a numeric-string CVSS base score, sibling to the per-vuln `severity[].score` vector) resolve every open mechanism question.

**Never:** engine-version pin tightening in `pixi.toml`/`pyproject.toml` (a worktree re-solve is toxic — deferred-work.md; owned by Story 1.7); severity→`policy-violation` mapping (Story 1.6); a `--db-path` CLI flag or any config-file DB override (Story 3.1); network-namespace/egress observation of the osv subprocess (Story 5.2); editing `tests/conformance/test_osv_offline_db_spike.py` (Story 1.4's proof — import its sibling `osv_db_builder.py` fixture by path instead, exactly as it does); conda/pixi component vuln matching (Epic 2 — this story only feeds PyPI-ecosystem, already-`vuln_matchable` components).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Vulnerable pin | 1 vuln-matchable component, valid DB seeds a match | `vuln:<id>:<pkg>@<ver>` finding, severity populated, `VulnData` populated, coverage claims 1 | No error |
| Clean pin | Vuln-matchable component, valid DB, no match | No finding for that component (falls through to existing `EXACT→clean` per-component path), `VulnData` populated | No error |
| Zero vuln-matchable components | Inventory has none | osv never invoked; empty `EngineResult`, no `vuln_data` | No error |
| DB env unset | `$OSV_SCANNER_LOCAL_DB_CACHE_DIRECTORY` not set, ≥1 candidate | osv never invoked; one `indeterminate:offline-db-unavailable:<pkg>` finding per candidate | Never `clean` |
| DB present-but-empty / content-corrupt | Pre-flight opens zip, 0 valid entries | Same as DB-absent (pre-flight fails, osv never invoked) | Never `clean` |
| DB container-corrupt / other engine crash | Pre-flight passes (or DB genuinely fine) but osv exits an unexpected code | Typed `ENGINE_EXECUTION_FAILED` → `error` rung | Report still emitted |
| No-packages (128) | Synthesized input somehow empty/unparseable to osv | Treated like DB-unavailable: indeterminate, no silent pass | Never `clean` |
| Hostile identity | A component's `pypi_identity.name`/`.version` fails the safe-token check | Excluded from the input file; `indeterminate:unsafe-identity:<pkg>` finding | Never injected raw |
| osv-scanner absent (test env) | Binary not on PATH | `pytest.fail`, never a skip | N/A |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-warden/src/pyforge/warden/vuln.py` -- NEW: DB-cache resolution + content pre-flight, input synthesis (sanitize + sort), `parse_osv_output` (mirrors `hygiene.parse_deptry_output`'s `OsvParse` dataclass shape), CVSS-score→tier mapping.
- `src/shared/packages/pyforge-warden/src/pyforge/warden/engines.py` -- MODIFY: `_engine_env` gains `extra_env` + 3rd return value (exit code); `DeptryEngine` updated to unpack 3-tuples; new `OsvEngine` registered after `DeptryEngine`.
- `src/shared/packages/pyforge-warden/src/pyforge/warden/interfaces.py` -- MODIFY: `EngineResult` gains `vuln_data: VulnData | None = None` (additive; no behavior change to `DefaultPolicy.evaluate`).
- `src/shared/packages/pyforge-warden/src/pyforge/warden/report.py` -- MODIFY: `assemble_report` takes `vuln_data: VulnData` instead of hardcoding `VulnData(None, None, None)`.
- `src/shared/packages/pyforge-warden/src/pyforge/warden/cli.py` -- MODIFY: derive `vuln_data` from `engine_results` (first non-`None` `.vuln_data`, else all-`None`) and pass it to `assemble_report`.
- `src/shared/packages/pyforge-warden/tests/unit/test_engine_env_deptry.py` -- MODIFY: unpack `_engine_env`'s 3-tuple at all call sites; add `extra_env`-threading + exit-code-surfacing assertions.
- `src/shared/packages/pyforge-warden/tests/unit/test_vuln.py` -- NEW: `parse_osv_output`, pre-flight (valid/absent/empty/content-corrupt/container-corrupt, reusing `tests/fixtures/osv_db_builder.build_offline_db` + hand-built corrupt zips mirroring the 1.4 spike's corruption fixtures), CVSS-tier mapping, input-sanitization edge cases -- all via injected fakes, no real subprocess.
- `src/shared/packages/pyforge-warden/tests/conformance/test_osv_engine.py` -- NEW: `OsvEngine.run()` against the REAL osv-scanner binary + the 1.4 fixture DB (hard-fail if absent, mirroring `test_osv_offline_db_spike.py`'s convention) -- vulnerable/clean/DB-absent end-to-end through production code.

## Tasks & Acceptance

**Execution:**
- [x] `engines.py` -- widen `_engine_env` (`extra_env` param, `(text, error, exit_code)` return) and update `DeptryEngine` -- required by the decision record's seam hand-off #1/#3.
- [x] `vuln.py` -- DB resolution + content pre-flight (`_db_has_valid_advisory`) -- decision record §4, the mandated defense against the empirically-confirmed exit-0 content-corrupt false-green.
- [x] `vuln.py` -- input synthesis (`_synthesize_requirements`) with the safe-token purity guard -- NFR-S6.
- [x] `vuln.py` -- `parse_osv_output` (groups→findings, CVSS tier mapping) -- FR10.
- [x] `engines.py` -- `OsvEngine` wiring all of the above through `_engine_env`, registered via `register_engine` -- FR10/FR11.
- [x] `interfaces.py` + `report.py` + `cli.py` -- thread `vuln_data` end to end, replacing the hardcoded `None` triple -- FR11.
- [x] `tests/unit/test_engine_env_deptry.py`, `tests/unit/test_vuln.py`, `tests/conformance/test_osv_engine.py` -- cover the I/O matrix above.

**Acceptance Criteria** *(from `epics.md`, preserved verbatim):*

**Given** the 1.4 fixture DB, **When** a lockfile with a known-vulnerable pin is scanned, **Then** osv runs offline through `_engine_env()`, its advisory + CVSS severity lands in the inventory (FR10), merged into the **same** `ResolvedInventory` as deptry's findings. **And** the synthesized osv input is a **pure data projection** (NFR-S6): any line starting with `-`, or carrying a URL / VCS ref / path / env-marker we did not author, is rejected or neutralized; manifest-derived values never become CLI flags. **And** osv exit `1` (vulns-found) is read as content, `127`→engine-error, `128`→no-packages — never a silent pass.

**Given** the offline posture, **When** osv runs, **Then** the **C0c socket-deny gate holds** — osv performs **no silent DB fetch** during a scan (explicit NFR-S2 AC on the DB-access surface); the report records the DB source + timestamp (FR11).

## Design Notes

**Why no `interfaces.py` policy change:** `DefaultPolicy.evaluate` already routes any non-hygiene-axis engine finding to a conservative `indeterminate` rung (the "false-green backstop" built in 1.2 for exactly this pre-1.6 gap). Both the "DB unusable" and "real vulnerability found" cases are just `Finding`s on the vulnerability axis — the existing backstop makes both `indeterminate` today; Story 1.6 later tightens real vulnerabilities to `policy-violation`. No new rung-producing code path is needed.

**Empirically verified osv-scanner 2.4.0 output shape** (`osv-scanner scan --offline --format json --output-file … -L requirements.txt:…` against the 1.4 fixture DB, re-run this story): `results[].packages[].groups[]` is osv's own aggregation — `{ids: [...], aliases: [...], max_severity: "9.8"}` (a numeric-string CVSS base score, osv-computed) — while `results[].packages[].vulnerabilities[]` carries the raw OSV record per id, including `severity: [{type, score:"<CVSS vector>"}]`. `max_severity` is per-*group* (aliased ids share one score); attributing the group's max to each of its ids is the conservative choice (never under-claims severity).

**`snapshot_at`** = the resolved `all.zip`'s own filesystem mtime (ISO-8601 UTC) — the only honest timestamp signal available without real provisioning infrastructure (owned by Story 5.1). This is a genuinely volatile field; `--deterministic` is still a documented no-op (`determinism.py` doesn't exist yet), so tests assert format/presence, not an exact value — consistent with how the rest of the report currently carries no pinned volatile fields.

**No implicit default DB path:** if `$OSV_SCANNER_LOCAL_DB_CACHE_DIRECTORY` is unset, `OsvEngine` does **not** fall back to osv-scanner's own built-in per-user cache guess — v1 is explicit-provisioning-only (decision record §5/§10); inventing an implicit default would risk a silent, unaudited DB source.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-warden pyforge-warden-test` -- expected: all prior 1.1–1.4 suites unchanged + new `test_vuln.py` + `test_osv_engine.py` green; sole-ownership / no-execution / socket-deny meta-guards stay green (osv's 127/128 aren't in the guarded `{1,2,130}` exit-literal set, so referencing them in `vuln.py`/`engines.py` does not trip the sole-ownership guard).
- Manual: `git diff --stat` shows zero changes to `pixi.toml`/`pixi.lock`/`pyproject.toml` and zero changes to `tests/conformance/test_osv_offline_db_spike.py`.

## Review Triage Log

### 2026-07-16 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 6 (medium 3, low 3)
- defer: 1 (low)
- reject: 8
- addressed_findings:
  - `medium` `patch` `indeterminate:<reason>:<pkg>` finding ids (both `unsafe-identity` and `offline-db-unavailable` families) carried only the component NAME, no version. Two distinct components sharing a name but differing by version (a legitimate, documented inventory state) withheld for the same reason collided on id; `DefaultPolicy.evaluate`'s engine-finding dedup then silently dropped the second one's finding, losing its per-component traceability (confirmed via direct repro through the real `cli.main()` pipeline: `inventory_count=2`, only 1 finding emitted — the aggregate verdict stayed correctly non-clean via the redundant per-component match-level rung, so this was a completeness/audit gap, NOT a false-green or a crash). Fixed: `_indeterminate_finding` (vuln.py) now mints `indeterminate:<reason>:<pkg>@<version-or-unspecified>`, mirroring the existing `vuln:<id>:<pkg>@<version>` family. Updated the two id-grammar unit tests + both conformance-test assertions to the new format; added a new regression test (`test_indeterminate_finding_id_includes_version_to_avoid_cross_version_collision`).
  - `medium` `patch` `OsvEngine.run()` discarded the already-computed NFR-S6 `excluded_findings` (purity-guard-excluded candidates) on 4 of its 6 return paths — the `mkstemp` `OSError` branch, the `_engine_env`-returned-error branch, the exit-127 branch, and the "any other exit code" branch all returned `findings=()`/`findings=(error,)`, dropping findings the guard had already computed before the subprocess even ran. Direct violation of the intent-contract's explicit "never silently dropped" NFR-S6 constraint. Fixed: all 4 branches now include `excluded_findings` in their returned `findings` tuple.
  - `medium` `patch` Test-coverage gap: neither `test_vuln.py` nor `test_osv_engine.py` exercised `OsvEngine.run()`'s exit-127, exit-128, or "any other exit code" branches (confirmed via grep: zero references to "127"/"128" in either file) despite the story's own Tasks checklist claiming "cover the I/O matrix above" and the Acceptance Criteria explicitly naming `127→engine-error, 128→no-packages — never a silent pass`. Fixed: added `tests/unit/test_osv_engine_exit_codes.py` (4 tests, one parametrized over `{127, 128, other}`) exercising all three branches plus the purity-guard-findings-survive-a-failure invariant, via a real fixture DB (pre-flight passes) + a monkeypatched `subprocess.run`.
  - `low` `patch` Real, confirmed (via `mypy 2.2.0`) type-checking regression at `engines.py:415`: the local name `error` was bound to non-Optional `ErrorRecord` in an earlier `except OSError` branch, then reassigned from `_engine_env`'s `ErrorRecord | None` return — harmless at runtime (the branches are mutually exclusive; the first always returns) but a genuine new mypy error absent on the baseline tree. Fixed: renamed the `except OSError` branch's local to `mkstemp_error`.
  - `low` `patch` `_cvss_score_to_tier` (vuln.py) did not bound-check the parsed `max_severity` score to the valid CVSS `[0.0, 10.0]` range before banding — an out-of-range (e.g. negative) score silently banded to `SeverityTier.NONE` (implying verified-harmless) instead of `UNKNOWN` (implying untrustworthy/unparseable). Zero current functional impact (severity does not drive the verdict/rung until Story 1.6), but a real defensive-correctness gap given the project's fail-closed philosophy. Fixed: added the range check.
  - `low` `patch` `_db_has_valid_advisory`'s per-entry exception guard did not catch `RuntimeError`/`NotImplementedError`, both of which `zipfile.ZipFile.read()` raises for an encrypted or unsupported-compression zip entry — such an entry would abort the WHOLE pre-flight (propagating out to `cli.py`'s generic engine-seam catch-all) instead of being skipped so the rest of the archive's valid entries are still checked, contradicting the function's own documented intent. Fixed: widened the except tuple.
  - `low` `defer` `DefaultPolicy.evaluate` (interfaces.py, untouched by this diff) unconditionally stamps every engine `ErrorRecord`'s rung driver with `axis=AXIS_VULNERABILITY` regardless of source engine/error kind — pre-existing since 1.2/1.3 (already true for `DeptryEngine`'s own hygiene-axis errors), already explicitly tracked in `interfaces.py`'s own docstring as owned by Story 1.7's error-grammar work; `OsvEngine`'s new errors merely ride the same known, pre-existing path. Appended to `deferred-work.md`.
  - `reject` (8, silently dropped): NFR-S6 charset excludes PEP 440 local-version labels (`+cu121`) — faithfully implements the frozen intent-contract's literal `[A-Za-z0-9._-]+` charset and fails CLOSED (`indeterminate`, never `clean`), a coverage/safety tradeoff not a defect; exit-128 reclassifying purity-excluded candidates into `offline-db-unavailable` — the reviewer's own admission this matches the story's sanctioned I/O matrix; `pixi.toml`'s `osv-scanner` pin lacking a `<3` ceiling / version-detection guard — explicitly listed in the intent-contract's own "Never" clause as Story 1.7's job; `conftest.py`'s autouse ambient-DB fixture's blast radius — a deliberate, documented design choice with negligible real-world collision risk; `_synthesize_requirements` non-dedup of identical lines from two components resolving to the same pypi identity — unreachable in the current PyPI-only extraction/mapping scope and harmless even if reached (dedup happens downstream regardless); decision-record-vs-spec "127 semantics" framing tension — a deliberation-doc-vs-final-spec artifact the spec already explicitly resolves and the code correctly implements; `vuln.py` module docstring's duplicated closing sentence — cosmetic; Blind Hunter's "reproducible crash disabling the tool, zero report emitted" framing — EMPIRICALLY REFUTED via a direct repro through the real `cli.main()` pipeline (two same-name-different-version components, DB unset: `inventory_count=2`, exit code 1, a complete, valid, non-clean report was emitted — `DefaultPolicy.evaluate`'s own engine-finding dedup prevents the `ComplianceReport` uniqueness violation their script's apparent bypass of that dedup pass had surfaced); the real, narrower underlying defect their script actually pointed at is the first `patch` item above.

## Auto Run Result

**Summary of implemented change:** Added `OsvEngine` (`engines.py`) — the vulnerability-axis engine running `osv-scanner` fully offline through a widened `_engine_env` seam (`extra_env` param + surfaced exit code). A new `vuln.py` module owns DB-cache resolution, the decision-record §4 content pre-flight, NFR-S6-safe input synthesis, and osv JSON→`vuln:` finding parsing with CVSS-tier mapping. `vuln_data` now threads end-to-end through `EngineResult` → `DefaultPolicy` (untouched) → `assemble_report` → `cli.py`, replacing the hardcoded `VulnData(None, None, None)`. Closes the pre-existing live false-green where a vuln-matchable component projected to `clean` with no engine ever having consulted a DB.

**Files changed:**
- `src/pyforge/warden/engines.py` — `_engine_env` widened (3-tuple return + `extra_env`); `DeptryEngine` updated to unpack 3-tuples; new `OsvEngine` (registered after `DeptryEngine`) implementing the full 0/1/127/128/other exit-code disposition.
- `src/pyforge/warden/vuln.py` (NEW) — DB resolution + content pre-flight, NFR-S6 input synthesis, `parse_osv_output`/`OsvParse`, CVSS-tier mapping.
- `src/pyforge/warden/interfaces.py` — `EngineResult` gains `vuln_data: VulnData | None = None` (additive; `DefaultPolicy.evaluate` untouched).
- `src/pyforge/warden/report.py` — `assemble_report` takes `vuln_data: VulnData` instead of hardcoding it.
- `src/pyforge/warden/cli.py` — derives `vuln_data` from `engine_results` and threads it through.
- `tests/unit/test_engine_env_deptry.py` — 3-tuple unpacking + `extra_env`/exit-code assertions.
- `tests/unit/test_vuln.py` (NEW), `tests/conformance/test_osv_engine.py` (NEW), `tests/unit/test_osv_engine_exit_codes.py` (NEW) — unit + conformance coverage of the full I/O matrix, including the 127/128/other exit-code branches added during review.
- `tests/conftest.py` — session-scoped autouse ambient offline OSV DB so pre-1.5 fixtures scanning ordinary pinned deps through `cli.main` stay genuinely green now that `OsvEngine` is live.
- `tests/conformance/test_scan_harness.py`, `tests/unit/test_interfaces_and_null_engine.py` — mechanical fixes for the same reason (3-tuple unpack; registry-order assertion; coverage assertion now reflects a real osv run).

**Review findings breakdown:** 0 intent_gap, 0 bad_spec, 6 patch (3 medium, 3 low — all applied), 1 defer (appended to `deferred-work.md`), 8 reject (including an empirically-refuted "reproducible crash" claim from one reviewer — verified via direct repro through the real `cli.main()` pipeline before rejecting).

**Follow-up review recommendation:** `false` — 6 localized, mechanically-verified patches (id-grammar fix, findings-completeness fixes, one test-coverage addition, two low-severity defensive-hardening fixes, one type-hygiene rename) across 2 production files already covered by two independent adversarial review passes plus my own empirical verification (a direct `cli.main()` repro, `mypy`, `ruff`). None touched `DefaultPolicy`/`verdict.py` (the C0 false-green-prevention core, confirmed intact both before and after).

**Verification performed:** `pixi run --frozen -e pyforge-warden pyforge-warden-test` — 544 passed (538 pre-patch + 6 new exit-code/collision tests), 0 failed. `mypy 2.2.0` (via `pixi run --frozen -e local-recipes mypy`) — 0 new errors (1 pre-existing, unrelated `cli.py:538` error confirmed present on baseline). `ruff check` — 0 new issues (2 pre-existing, unrelated lint nits confirmed present on baseline via `git show`). `git diff --stat` against baseline — zero changes to `pixi.toml`/`pixi.lock`/`pyproject.toml`/`tests/conformance/test_osv_offline_db_spike.py`. Manual smoke test via a real `cli.main()` invocation against a synthesized two-version-of-one-package manifest, DB unset — confirmed a schema-valid, non-clean report is emitted (no crash), settling a disputed reviewer claim empirically before triage.

**Residual risks:** The `deferred-work.md` entry (pre-existing `AXIS_VULNERABILITY` mislabeling of non-vulnerability-axis engine errors, owned by Story 1.7). The `osv-scanner >=2.4.0` pin has no upper bound and no runtime version-detection guard yet (explicitly deferred to Story 1.7 by the intent-contract's own "Never" clause) — a `pixi update` before 1.7 lands could silently reinterpret the exit-code contract this story's false-green defenses depend on.
