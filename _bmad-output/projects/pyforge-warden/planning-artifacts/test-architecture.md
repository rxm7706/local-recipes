---
title: "Test Architecture — pyforge-warden"
type: test-architecture
date: 2026-08-02
version: 1.0.0
status: draft
scope: "All 31 stories (E1–E6), 3 real test levels (unit/conformance/meta), pytest framework, src/shared/packages/pyforge-warden/tests/"
target_coverage: "Behavioral: C0 zero-false-green across fixtures + the 1,979-file corpus. No %-line-coverage gate is configured for this package (verified against pyproject.toml — no pytest-cov section exists); see § Coverage Gate Reality."
---

# Test Architecture — PyForge Warden

## Executive Summary

This document was authored 2026-08-02 to **replace a fabricated boilerplate placeholder** (the prior 78-line `test-architecture.md`, generic template rows reading "Target Stories: TBD" against no real story references — created in a bulk commit alongside other fabricated content that was found and remediated this session).

Unlike a normal test-architecture document, this one is **retrospective, not prospective**: Warden is **100% code-complete — 31/31 stories shipped across 6 epics** (a pluggable multi-axis Python dependency compliance gate: hygiene via deptry, security via osv-scanner + CISA KEV + FIRST.org EPSS, plus license and currency axes — all flag-activated gates, baseline & grandfathering, and an opt-in fix-PR actuator). The tests already exist and were written story-by-story during implementation; this document **describes the real coverage that is already on disk**, grounded by reading every one of the 54 test files' module docstrings and cross-referencing their explicit `Story N.M` citations against `_bmad-output/projects/pyforge-warden/planning-artifacts/epics.md`. It does not plan work — it maps what shipped.

**Verified facts this document is built on** (all confirmed against the live repo on 2026-08-02):
- **54 test files** under `src/shared/packages/pyforge-warden/tests/`: 30 in `unit/`, 19 in `conformance/`, 4 in `meta/`, 1 root-level `test_smoke.py`.
- **1,947 tests collected** (`pixi run -e pyforge-warden pytest src/shared/packages/pyforge-warden/tests --collect-only`): 1,936 run by default (`pyforge-warden-test`, `-m "not slow"`), 11 deselected as `@pytest.mark.slow` (run separately via `pyforge-warden-test-corpus-oracle`, `-m slow`).
- **30 of 31 stories** have at least one test file whose own docstring or in-body comments cite that exact story number. **Story 6.10 has zero test files** — by design, not gap: it is a decision-record spike whose own acceptance criteria state "this spike changes no code and no schema" (see § Epic 6, Story 6.10 below).
- The real corpus fixture (`tests/fixtures/corpus/recipes/`) contains **1,979** real `recipe.yaml`/`meta.yaml` files harvested from this repo's own `recipes/` tree, plus 9 hand-authored adversarial fixtures — matching the number cited in the conformance test docstrings and in `epics.md`'s NFR-R1 ("corpus 0 uncaught exceptions (~1,950 files)").
- No `pytest-cov` / coverage-percentage gate is configured anywhere in `pyproject.toml` or `pixi.toml` for this package. The project's actual quality gate is **behavioral**: the C0 invariant (never false-green — 0 exit-0 on adversarial fixtures) proven directly by dedicated tests, not inferred from a line-coverage percentage.

**Test taxonomy differs from sibling station Marshal on purpose.** Marshal's test-architecture (the format exemplar for this document) uses Unit/Integration/E2E because its own suite is organized that way. Warden's suite is organized as **`unit/` / `conformance/` / `meta/`** — a different real taxonomy, not a renaming of the same one:
- **`unit/`** — pure-logic tests against a single module, often with `subprocess.run` monkeypatched (no real deptry/osv-scanner) or hand-built `Component`/`ComplianceReport` objects (no CLI). This is Marshal's UT.
- **`conformance/`** — end-to-end tests that invoke `cli.main()` in-process or drive the real `deptry`/`osv-scanner` binaries against a hermetic offline database. This is where Marshal's IT and E2E collapse into one directory for Warden, because the project's own C0 acceptance gate ("never false-green") is inherently an end-to-end property — testing it at the unit level would prove nothing.
- **`meta/`** — architectural invariant guards that AST-scan the installed package itself (not its behavior): the verdict.py sole-ownership guard, the extract/ no-execution denylist, the socket-deny-harness-is-alive check, and the pixi.toml/engines.py version-range sync check. Marshal has no equivalent directory; this is a Warden-specific need driven by the C0/C0a/C0c invariants baked into Story 1.1/1.2.

---

## Methodology (how this document was verified, not just written)

Every story→test claim in this document was built the same way, in this order, so the mapping traces back to something checkable rather than to plausible-sounding prose:

1. Read `_bmad-output/projects/pyforge-warden/planning-artifacts/epics.md` in full (575 lines) for the real story titles, acceptance criteria, and FR/NFR tags.
2. Listed the actual `tests/` tree on disk (`find . -name "*.py"`) and confirmed it matches the 54-file ground-truth list exactly — no more, no fewer.
3. Read the module docstring (first 10–20 lines) of **every one of the 54 test files** — the overwhelming majority explicitly name the story they implement (e.g. `test_license.py`: "Unit tests — per-component SPDX license verdicts (Story 6.2)"), which made this project unusually well-suited to a grounded retrospective mapping.
4. For any story not obviously covered by a docstring-titled file, ran `grep -rn "Story N.M" tests/` to find every file that mentions that exact story number in a comment or nested docstring, then read the surrounding lines to confirm the reference is a real implementation note (not, say, a cross-reference in a different story's rationale).
5. Where a story is genuinely cross-cutting (its behavior is proven a few lines at a time inside several other stories' files, e.g. Story 1.7's typed errors or Story 6.5's escalation mapping), that is reported as cross-cutting explicitly — a table row citing five files each contributing a fragment, not a fabricated single "owning" file.
6. Where no test evidence could be found (Story 6.10), that is reported as no evidence, with the acceptance-criteria text that explains why, rather than inventing a plausible file name.

No story mapping in this document names a test file that was not opened and read during its construction.

## What changed from the fabricated placeholder

The prior `test-architecture.md` (78 lines, git history) is directly checkable against this one. Two concrete, verifiable errors in it, beyond the "TBD" rows already known:

- Its **Framework & Tooling** section claimed the suite was organized as `tests/unit/`, `tests/integration/`, `tests/meta/`. **`tests/integration/` does not exist and has never existed** in this package — the real second directory is `tests/conformance/`. This is not a naming preference; it is a directory that is asserted to exist and does not.
- Every row of its **Test Strategy Overview** table read `Target Stories: TBD` — none of the 31 real stories, epics, or FR numbers from `epics.md` appeared anywhere in the document, despite `epics.md` (575 lines, dated 2026-07-12 through 2026-07-16) having existed since before the placeholder was committed.
- Its fixture/mock examples (`mock_scanner.py`, `mock_manifest.py`, `mock_gate.py` under a `tests/mocks/` directory) describe files that do not exist on disk; Warden has no `tests/mocks/` directory at all (see § Test Fixtures & Corpus).

This document replaces all of that with citations to the 54 real files and their real docstrings, verified 2026-08-02.

---

## Test Strategy by Epic

### Epic 1: Spine + PyPI engine (walking skeleton) — 9 stories

**Scope**: The frozen `Component`/`ComplianceReport` contract, the 7-rung verdict lattice, the plugin/strategy interfaces, deptry as the first engine, the OSV-DB provisioning spike, osv-scanner as the second engine, severity-gate composition, typed errors, both report renderers, and manifest discovery (FR1). Everything downstream is a *producer* against what 1.1/1.2 freeze here.

| Story | Title | U | C | M | Primary test file(s) | Coverage note |
|-------|-------|:-:|:-:|:-:|----------------------|----------------|
| **1.1** | Frozen contract, verdict lattice & projection-safety (C0a) | ✅ | ✅ | ✅ | `unit/test_models.py`, `unit/test_verdict.py`, `unit/test_inventory.py`, `meta/test_verdict_sole_ownership.py`, `conformance/test_report_schema.py` | `test_models.py` proves the frozen enum tokens + full `Component` field shape (now 15 fields post-6.1 amendment); `test_verdict.py` proves C0a directly against the projection (totality over all Status members, the locked `{0,1,2,130}` exit table, the unknown-match-level-never-clean safety rule, the all-clean guard); `test_inventory.py` proves the Gap-B merge/identity rules; `meta/test_verdict_sole_ownership.py` is the AST-scan guard that fails CI if any module but `verdict.py` projects an exit or the rung ordering; `conformance/test_report_schema.py` validates the packaged JSON schema (folds the dissolved Story 4.2 assertion, FR28/NFR-I1/I2). |
| **1.2** | Interfaces, null engine, regression harness & socket-deny (C0c) | ✅ | ✅ | ✅ | `unit/test_interfaces_and_null_engine.py`, `unit/test_discovery_extract_cli.py`, `conformance/test_scan_harness.py`, `meta/test_socket_deny_alive.py`, `meta/test_extract_no_execution.py`, `test_smoke.py` | `test_interfaces_and_null_engine.py` proves the registry holds only the null engine and `DefaultPolicy` derives the withheld→indeterminate finding. `test_scan_harness.py` is the loop's own verify gate: the 2-fixture regression harness (clean→green, false-green-sentinel→≥1 finding) every later story inherits. `meta/test_socket_deny_alive.py` proves the C0c deny-by-default socket harness is itself alive (a dead guard would be a false-green about false-greens). `meta/test_extract_no_execution.py` is the NFR-S1 AST denylist over `extract/`. `test_smoke.py`'s own docstring says "updated for Story 1.2" — the scaffold-era "returns 0 no matter what" contract is retired there. |
| **1.3** | deptry as the first engine (hygiene findings) | ✅ | — | — | `unit/test_engine_env_deptry.py`, `unit/test_hygiene.py` | `test_engine_env_deptry.py` proves the `_engine_env()` seam (argv-only, temp-file output, `NO_COLOR=1`, `stdin=DEVNULL`) against a monkeypatched `subprocess.run` (FR4/FR8). `test_hygiene.py` proves deptry-JSON parsing + the default hygiene→status table (DEP001–005), including the `[tool.deptry]` ignore-honoring AC (FR9). No dedicated conformance file — deptry's real-binary path is instead proven through `test_scan_harness.py`'s end-to-end fixtures. |
| **1.4** | OSV-DB offline provisioning spike (decision + fixture DB) | — | ✅ | — | `conformance/test_osv_offline_db_spike.py` (+ `fixtures/osv_db_builder.py`, the hermetic-DB builder every later OSV-touching test reuses) | The spike's own empirical proof test: drives the real `osv-scanner` binary directly (never `cli.main`, never production `engines.py`) against a hermetic offline DB built at test time from `fixtures/osv-db/`. `osv_db_builder.build_offline_db` is the substrate that `test_osv_engine.py`, `test_kev_enrichment.py`, and `test_epss_enrichment.py` all reuse — the spike's decision record is the template those stories' own feed-provisioning work follows. |
| **1.5** | osv-scanner as the second engine (vulnerability findings) | ✅ | ✅ | — | `conformance/test_osv_engine.py`, `unit/test_osv_engine_exit_codes.py`, `unit/test_vuln.py` | `test_osv_engine.py` runs `OsvEngine.run()` against the real binary (hard-fails, never skips, if `osv-scanner` is absent from PATH — matches the provisioned-engine convention). `test_osv_engine_exit_codes.py` covers the exit-code disposition (127/128/other) that the real-binary suite can't force reliably, via an injected fake `subprocess.run` against a real offline DB. `test_vuln.py` covers the non-subprocess logic: DB-cache resolution, the content pre-flight, `name==version` input synthesis (NFR-S6 purity guard), and `parse_osv_output` (FR10, FR11). |
| **1.6** | Severity gate + verdict composition end-to-end | ✅ | ✅ | — | `unit/test_vuln.py` (severity→rung composition), `unit/test_verdict.py` (compose ordering), `conformance/test_scan_harness.py` | `test_vuln.py`'s own docstring: "Story 1.6 adds the severity->rung composition (`DEFAULT_VULN_SEVERITY_POLICY`, `status_for_severity_tier`, `vuln_rung`)" (FR18/FR20). The synthetic-`indeterminate`-fixture composition AC (indeterminate outranks warn/clean, proven in E1 even though the first real producer is 2.4) is proven in `test_verdict.py`'s projection-totality tests plus exercised end-to-end in `test_scan_harness.py`. |
| **1.7** | Typed errors & the no-scan guard (the fail-closed net) | ✅ | ✅ | — | `conformance/test_scan_harness.py`, `unit/test_discovery_extract_cli.py`, `unit/test_engine_env_deptry.py`, `unit/test_interfaces_and_null_engine.py` | Cross-cutting, no single dedicated file — `test_scan_harness.py` ratifies the two-namespace `finding_id` contract and the constant error-driver-across-every-error-rung rule as "Story 1.7"; `test_discovery_extract_cli.py` covers the error-taxonomy rows (unreadable manifest / unknown kind / internal `ValueError` / discovery `OSError`, KeyboardInterrupt→130, nonexistent/empty target→2); `test_engine_env_deptry.py` has a test explicitly labeled "Story 1.7 fix: `deps_assessed` must count ONLY what actually..."; `test_interfaces_and_null_engine.py` proves the driver's axis is the producing engine's own axis (FR21, NFR-R5). |
| **1.8** | Human & machine report renderers | ✅ | ✅ | — | `unit/test_report.py` (`render_text` in isolation), `conformance/test_scan_harness.py`, `unit/test_discovery_extract_cli.py` | `test_report.py`'s own docstring: "`report.render_text` in isolation (Story 1.8)" — constructs a `ComplianceReport` directly, no CLI, no engines. `test_scan_harness.py` and `test_discovery_extract_cli.py` cover `--format text`/`--format json`, `--version`/`--help` stability, and the NFR-I3 stdout-purity rows (single valid JSON document or empty) end-to-end (FR14/FR17/FR29/FR31). |
| **1.9** | Manifest discovery, deterministic selection & the resolved scan set (FR1) | ✅ | ✅ | — | `unit/test_discovery_extract_cli.py` (dedicated "discovery: recursive multi-directory walk (Story 1.9)" + "environment.yaml (Story 1.9)" + "D2's split (Story 1.9)" sections), `conformance/test_scan_harness.py` (D2(c) rows), `unit/test_models.py`, `conformance/test_report_schema.py` | `test_discovery_extract_cli.py` carries three dedicated Story-1.9 sections covering the recursive multi-dir walk, the environment.yaml discovery path, and the D2 split (misconfiguration guard vs. empty-extraction downgrade). `test_models.py` proves `Status.INDETERMINATE` widened its legal-exit set for this story; `test_report_schema.py` proves the status/exit coherence rule that indeterminate is the one non-error status exiting non-zero without an `error_kind`. |

**Acceptance**: 9/9 stories have direct, story-cited test coverage. Cluster-1 (1.1→1.2) is fully green before cluster-2 (real engines) per the epics.md-mandated internal gate; `test_scan_harness.py`'s harness (built in 1.2) mechanically polices every later story's regression behavior, matching the "loop's own verify gate" role called out in the epics.md execution model.

---

### Epic 2: The conda/pixi source-manifest wedge — 6 stories

**Scope**: The beachhead value — gating a conda/pixi **source** manifest with no resolved environment. The conda→pypi identity map, non-rendering parse-as-data extraction validated against a real renderer (the differential-oracle), the full supported-construct matrix, honest split coverage + the `indeterminate` producer (C0b), the name-level CVE tier, and lockfile extraction (the locked-closure vuln hero path).

| Story | Title | U | C | M | Primary test file(s) | Coverage note |
|-------|-------|:-:|:-:|:-:|----------------------|----------------|
| **2.1** | conda→pypi map + the ecosystem-identity predicate | ✅ | ✅ | — | `unit/test_mapping.py` (primary), `unit/test_hygiene.py`, `unit/test_vuln.py`, `unit/test_osv_engine_exit_codes.py`, `conformance/test_scan_harness.py` | `test_mapping.py` is the dedicated file: the bundled map's real shape plus the TSV→JSON converter script (`scripts/generate_conda_pypi_map.py`, loaded by path). Because the map's confidence tiers gate DEP001 and vuln matching, this story threads secondarily through `test_hygiene.py` ("DEP001 blocks by default (Story 2.1, Gap-A)"), `test_vuln.py` ("Story 2.1's marquee rename fidelity"), `test_osv_engine_exit_codes.py` (a CONDA-ecosystem component with a resolved `pypi_identity`), and `test_scan_harness.py` (the `{pypi_name, match_source, match_confidence}` shape end-to-end). |
| **2.2** | Non-rendering extraction (common case) + differential-oracle | ✅ | ✅ | — | `unit/test_recipe_v1_extractor.py`, `unit/test_meta_v0_extractor.py`, `unit/test_pixi_extractor.py`, `unit/test_environment_yml_extractor.py`, `unit/test_identity.py`, `conformance/test_extraction_oracle.py` | Four extractors, four dedicated unit files, each explicitly "Story 2.2" in its own one-line docstring, each exercising its extractor directly with no CLI. `test_identity.py` covers the shared conda-matchspec exactness discipline (`classify_conda_specifier`/`split_conda_dep_string`) all four extractors depend on. `test_extraction_oracle.py` is the differential-oracle itself: extracted names ⊇ the real `rattler_build`/`conda_build` render, skip-if-renderer-unavailable (FR3). |
| **2.3** | The full supported-construct matrix (ratcheted) | ✅ | ✅ | — | `unit/test_recipe_v1_extractor.py` (complex-construct rows), `unit/test_meta_v0_extractor.py` (complex-construct rows), `conformance/test_extraction_oracle.py` (ratchet) | Same three files as 2.2, extended: `compiler()`/`stdlib()`→build-tool-exclude, `pin_subpackage()`→internal-exclude, selectors→union+mark, expression-logic→degrade (FR5). The oracle ratchets these rows so a matrix regression fails CI. |
| **2.4** | Honest split coverage + the indeterminate producer (C0b) | ✅ | ✅ | — | `unit/test_report.py` (`hygiene_applicable` override, its own docstring: "Story 2.4, AC3"), `unit/test_hygiene.py`, `unit/test_discovery_extract_cli.py`, `conformance/test_scan_harness.py` | `test_report.py` pins the `hygiene_applicable=False` coverage-shape override and the pre-2.4 regression byte-for-byte (FR15/FR16). The `not-applicable`/skipped hygiene-coverage-when-no-Python-source AC and the `indeterminate` `WithholdReason` producer (FR13/C0b) are exercised across `test_hygiene.py`, `test_discovery_extract_cli.py`, and `test_scan_harness.py`. |
| **2.5** | Name-level CVE tier + stale-DB + cross-ecosystem non-merge | ✅ | ✅ | — | `unit/test_vuln.py` ("Story 2.5 adds the stale-DB honesty tier... and the name-level CVE tier"), `conformance/test_osv_offline_db_spike.py`, `conformance/test_osv_engine.py`, `unit/test_discovery_extract_cli.py` | `test_vuln.py` is the dedicated home per its own docstring: `is_db_stale`/`stale_vuln_data_finding` and `cvss_v31_base_score`/`name_level_critical_advisory_ids`/`name_level_critical_cve_finding` (FR12/FR13). The cross-ecosystem non-merge AC (FR7) and the DB-staleness definition consumed from Story 1.4's decision record are exercised through the OSV conformance files. |
| **2.6** | Lockfile extraction — the locked-closure vuln hero path | ✅ | ✅ | — | `unit/test_lockfiles_extractor.py`, `conformance/test_lockfile_oracle.py` | Crystal clear, both files dedicated: `test_lockfiles_extractor.py` covers `PixiLockExtractor`/`CondaLockExtractor` directly (incl. the documented URL-basename pitfall regression). `test_lockfile_oracle.py` is the test-side oracle against `py-rattler`'s own `LockFile` parse — hard-fails (never skips) if `py-rattler` is unimportable, matching the 1.5 provisioned-engine convention. FR3/FR13 substrate per the story's own framing. |

**Acceptance**: 6/6 stories have direct, story-cited test coverage. `test_extraction_oracle.py` is genuinely shared across 2.2 (created it), 2.3 (ratchets it), and 5.2 (matures it to corpus scale) — this is a real, documented progression, not three independent claims on one file.

---

### Epic 3: Policy control + auditable waivers + warn-only — 3 stories

**Scope**: Making E1's `Policy` interface configurable (`ConfigLoader`, dual TOML precedence), auditable expiring waivers (read-not-written, schema-validated), and the warn-only adoption on-ramp with expiry re-blocking.

| Story | Title | U | C | M | Primary test file(s) | Coverage note |
|-------|-------|:-:|:-:|:-:|----------------------|----------------|
| **3.1** | Configurable policy (the ConfigLoader) | ✅ | ✅ | — | `unit/test_config.py` (primary), `conformance/test_scan_harness.py`, `unit/test_interfaces_and_null_engine.py`, `unit/test_report.py` (`fail_under_coverage`) | `test_config.py` is the dedicated file: dual-TOML `[tool.pyforge-warden]` load, per-key precedence (pyproject wins), and the two derived policy knobs — every `ConfigLoader.load` test round-trips real files through the real `tomllib` path, no mocking (FR30). `test_scan_harness.py` proves config-precedence and config-load-failure rows end-to-end; `test_interfaces_and_null_engine.py` proves `EffectiveConfig` threading (`fail_on` escalation, `dep001_block_confidence`); `test_report.py` covers the FR19 coverage-floor knob. |
| **3.2** | Auditable expiring waivers | ✅ | — | — | `unit/test_cli_bypass.py`, `unit/test_waiver.py` | Both files dedicated per their own top docstrings ("Story 3.2, FR24-FR26" and "the waiver suppression engine (Story 3.2)"). `test_cli_bypass.py` covers the `--bypass --reason` CLI surface + real `.warden-waivers.yaml` integration, end-to-end via `main()`. `test_waiver.py` covers schema validation, exact finding-id matching, expiry-awareness, and the emitted-stanza shape (NFR-S3/S4). |
| **3.3** | Waiver expiry + warn-only adoption on-ramp | ✅ | — | — | `unit/test_cli_bypass.py` (expiry rows + dedicated `--warn-only` section, "Story 3.3, FR23/FR25"), `unit/test_waiver.py` (expiry row + `warn_blocking` section), `unit/test_report.py` (embedded-newline forgery guard mirror) | The same two 3.2 files extend additively with explicit "Story 3.3" sections: an expired match no longer silently indistinguishable from a live one, re-blocking on the next scan, plus the `--warn-only` mode (findings surface as `warn`, exit 0). This defends the epics.md-named "`gate-disabled = 0` anti-metric." |

**Acceptance**: 3/3 stories have direct, story-cited test coverage.

---

### Epic 4: Machine contract + CycloneDX SBOM — 1 story

**Scope**: A separate read-only CycloneDX 1.6 projection over the frozen inventory. Story 4.2 was dissolved by the roundtable (schema-conformance folded into 1.1, stdout-purity into 1.8) — E4 is genuinely a single story.

| Story | Title | U | C | M | Primary test file(s) | Coverage note |
|-------|-------|:-:|:-:|:-:|----------------------|----------------|
| **4.1** | CycloneDX SBOM emission | ✅ | ✅ | — | `unit/test_sbom.py`, `unit/test_cli_sbom.py`, `conformance/test_sbom_schema.py` | Three dedicated files, cleanly divided by their own docstrings: `test_sbom.py` covers every I/O-matrix row except the cross-tool round-trip and the CLI write-failure row (G98 purl construction, `cfe:*` property attachment, the `cfe:partial_inventory` flag, NFR-S7 adversarial-name neutralization). `test_cli_sbom.py` covers exactly the two rows `test_sbom.py` excludes (write-success/write-failure via `--sbom-output`). `test_sbom_schema.py` validates hand-built minimal reports against the real CycloneDX 1.6 schema via `JsonStrictValidator` (FR27). |

**Acceptance**: 1/1 story has direct, story-cited test coverage.

---

### Epic 5: Fleet-readiness & adoption on-ramp — 2 stories

**Scope**: Actionable diagnostics + safe-by-default posture (incl. the `--doctor` self-check, D8), and fleet-scale hardening — corpus provisioning, parallel engine fan-out, the corpus-scale differential-oracle, egress counting, byte-identical determinism, and the dogfood gate.

| Story | Title | U | C | M | Primary test file(s) | Coverage note |
|-------|-------|:-:|:-:|:-:|----------------------|----------------|
| **5.1** | Actionable diagnostics & safe-by-default posture | ✅ | ✅ | — | `unit/test_cli_doctor.py`, `conformance/test_doctor.py`, `unit/test_report.py` (dedicated "Story 5.1 (AC1): remediation lines" section), `unit/test_discovery_extract_cli.py`, `conformance/test_scan_harness.py`, `unit/test_vuln.py` | `test_cli_doctor.py`/`test_doctor.py` cover the `--doctor` flag end-to-end (exit-code matrix: healthy=0, engine-missing/out-of-range=2, never 1; the "operating air-gapped" wording; short-circuits before any discovery/extraction — NFR-U2/D8). The NFR-U1 "fail with a fix" remediation-line AC is proven across `test_report.py`'s dedicated section, `test_discovery_extract_cli.py`, `test_scan_harness.py`, and `test_vuln.py` (`OsvParse.fixed_versions` feeds the remediation text). |
| **5.2** | Fleet-scale validation + corpus/oracle maturation | — | ✅ | — | `conformance/test_corpus_regression.py`, `test_corpus_determinism.py`, `test_corpus_egress_counter.py`, `test_engine_parallelism.py`, `test_perf_overhead.py`, `test_dogfood.py`, `test_extraction_oracle.py` (matured) | Seven conformance files, all explicitly citing Story 5.2 in their own docstrings, each proving one distinct NFR at corpus scale (~1,979 files) or under real subprocess timing: `test_corpus_regression.py` (NFR-R1/R2, 0 uncaught exceptions + the ratcheted `unparseable_rate` baseline, marker-free/default-suite), `test_corpus_determinism.py` (NFR-R3b at fleet scale, `@pytest.mark.slow`), `test_corpus_egress_counter.py` (closes a named deferred-work item — observes the real `osv-scanner` subprocess's network from OUTSIDE the process), `test_engine_parallelism.py` (NFR-P-concurrency, `ThreadPoolExecutor` fan-out + registration-order-stable reassembly), `test_perf_overhead.py` (NFR-P-warm, ≤~2s p95 engines-stubbed), `test_dogfood.py` (the epics.md AC3 dogfood gate — warden scanning its own package via `scripts/dogfood_scan.py`), and `test_extraction_oracle.py` matured from fixture scale (2.2/2.3) to full-corpus scale here. |

**Acceptance**: 2/2 stories have direct, story-cited test coverage. `pyforge-warden-test-corpus-oracle` (the `-m slow` pixi task) exists specifically because these corpus-scale proofs are too slow for the default loop — a real, load-bearing split, not an artifact of this document.

---

### Epic 6: Multi-axis expansion — license, currency, KEV/EPSS & adoption — 10 stories

**Scope**: The one sanctioned schema amendment (6.1) unlocking two new axis producers with flag-activated gates (license 6.2, currency 6.3), the CISA-KEV feed + gate (6.4), the two-mode policy wiring that actually performs the escalation (6.5), the engine version-range distribution gate (6.6), the EPSS feed + gate (6.7), baseline & grandfathering (6.8), the opt-in fix-PR actuator (6.9), and the amendment design spike that precedes 6.1 (6.10).

| Story | Title | U | C | M | Primary test file(s) | Coverage note |
|-------|-------|:-:|:-:|:-:|----------------------|----------------|
| **6.1** | The versioned `ComplianceReport` schema amendment | ✅ | ✅ | — | `unit/test_models.py`, `conformance/test_report_schema.py`, `unit/test_inventory.py`, `unit/test_report.py`, `unit/test_interfaces_and_null_engine.py`, `conformance/test_scan_harness.py` | No single dedicated file — by design, per the story's own framing ("producer-agnostic... every later epic is a producer, never an editor"). `test_models.py` proves the widened `Component` field shape (now 15 fields, up from the pre-amendment exact-13) plus the declared-but-unpopulated KEV/EPSS/license/currency slots. `test_report_schema.py` proves `test_additive_extra_fields_still_validate` still holds post-amendment (backward compatibility) and the `schema_version` stays `1.x`. The amendment's real correctness proof is distributed: every 6.2+ producer's own test suite passing against the widened schema IS the amendment's integration proof (FR38). |
| **6.2** | License axis producer + gate flags (Axis 3) | ✅ | ✅ | — | `unit/test_license.py`, `conformance/test_axis_producer_ceiling.py` (delivers the parametrized ceiling meta-test), `unit/test_config.py`, `unit/test_discovery_extract_cli.py`, `conformance/test_scan_harness.py` | `test_license.py` is the dedicated file: conda's `about: license:` pre-build re-read, PyPI `importlib.metadata` resolution (PEP 639→legacy `License`→trove classifiers), SPDX normalization via `license-expression`, verdict classification, and the hard `license_rung` warn-cap (FR32). `test_axis_producer_ceiling.py`'s own docstring names this as "Story 6.2; Story 6.3 appends the currency axis's own entry to the SAME parametrized table" — this suite mechanically proves the axis's own rung function never escalates above `warn` on its own (the actual escalation is 6.5's sole job). `--allow-licenses`/`--deny-licenses` flag parsing into the `ConfigLoader` (FR33) is covered in `test_config.py`. |
| **6.3** | Currency axis producer + gate flags (Axis 4) | ✅ | ✅ | — | `unit/test_currency.py`, `unit/test_feeds.py` (endoflife trio), `unit/test_refresh_endoflife_feed.py`, `conformance/test_axis_producer_ceiling.py` (registers into 6.2's table) | `test_currency.py` mirrors `test_license.py`'s own style per its docstring: the tier ladder (bundled LTS registry → cached endoflife.date → unknown), reason-token precedence (eol > over-lag > unknown), the `!python-runtime` sentinel, and the hard `currency_rung` warn-cap (FR34). `test_feeds.py`'s own docstring: "Story 6.3 adds the endoflife.date trio's own coverage... mirroring the KEV sections one-for-one" — confirming this story consumes 6.4's `feeds.py` skeleton rather than building a private cache. `test_refresh_endoflife_feed.py` covers the opt-in provisioning script (mocked network, no real socket). `--max-lag`/`--require-lts`/`--fail-on-eol` (FR35) parse into `ConfigLoader`, tested in `test_config.py`. |
| **6.4** | KEV feed provisioning, enrichment & the `--fail-on-kev` gate | ✅ | ✅ | — | `unit/test_refresh_kev_feed.py`, `unit/test_feeds.py` (KEV sections, the primary skeleton), `conformance/test_kev_enrichment.py` | `test_feeds.py`'s KEV sections are the dedicated home for the `feeds.py` skeleton itself (cache-dir resolution, the KEV cache path helper, staleness math, `FeedProvenance` construction, the atomic cache writer) that 6.3 and 6.7 both explicitly mirror. `test_refresh_kev_feed.py` covers the opt-in CISA KEV provisioning script (network fully mocked). `test_kev_enrichment.py` is the conformance proof through PRODUCTION code — `OsvEngine.run()` directly AND the full `cli.main()` pipeline — using the hermetic `PDOS-KEV-FIXTURE-0001` fixture advisory (alias-based KEV matching, empirically verified against a real osv-scanner 2.4.0 run) (FR36). |
| **6.5** | Two-mode policy integration (unconfigured visibility + flag-activated gating) | ✅ | ✅ | — | `conformance/test_axis_producer_ceiling.py` (sole owner of the escalation-mapping proof), `conformance/test_scan_harness.py`, `unit/test_license.py`, `unit/test_currency.py`, `unit/test_config.py`, `unit/test_interfaces_and_null_engine.py` | No single dedicated file — this is the correct shape for a story whose entire job is "solely own the escalation mapping" over axes that 6.2/6.3 already built producer-side. `test_axis_producer_ceiling.py` is where the unconfigured-vs-configured proof lives: identical fixture set run in both modes, diffing only the rungs/exit (FR37 + FR33/FR35). `test_scan_harness.py`, `test_license.py`, `test_currency.py`, and `test_config.py` each carry Story-6.5-tagged rows proving `gating: false` → `warn` rung (never silent clean) and `gating: true` → real escalation (`denied`/`eol`→`policy-violation`, `unknown`→`indeterminate`). |
| **6.6** | Engine version-range pinning (the distribution gate) | ✅ | ✅ | ✅ | `meta/test_engine_version_range_sync.py` (primary), `conformance/test_osv_engine.py`, `test_corpus_regression.py`, `unit/test_osv_engine_exit_codes.py`, `unit/test_engine_env_deptry.py` | `meta/test_engine_version_range_sync.py`'s own docstring: "the pixi.toml / engines.py version-range sync guard (Story 6.6, the distribution gate)" — proves `pixi.toml`'s `deptry = ">=0.25.1,<0.26"` / `osv-scanner = ">=2.4.0,<2.5"` run-dep pins never drift from `engines.py`'s `DEPTRY_VERSION_RANGE`/`OSV_SCANNER_VERSION_RANGE` `SpecifierSet` constants, comparing both sides through `packaging.specifiers.SpecifierSet` (never a literal string compare, which would false-fire on canonicalized ordering) — closing the release-gate that both internal JFrog v1 publish and public v1.x publish are blocked on (NFR-C1). The version ranges themselves are exercised functionally by the real-engine conformance/unit suites. |
| **6.7** | EPSS feed + the `--min-epss` gate | ✅ | ✅ | — | `unit/test_refresh_epss_feed.py`, `unit/test_feeds.py` (EPSS trio, mirrors the KEV sections), `conformance/test_epss_enrichment.py` | `test_feeds.py`'s own docstring: "Story 6.7 adds the EPSS trio's own coverage (`epss_cache_path`/`load_epss_scores`/`write_epss_cache`), mirroring the KEV sections one-for-one" — confirming 6.7 consumes 6.4's shared `feeds.py` layer rather than building a private cache (per the story's own AC). `test_refresh_epss_feed.py` covers the FIRST.org provisioning script (gzip-CSV response, fully mocked network). `test_epss_enrichment.py` reuses the same hermetic `PDOS-KEV-FIXTURE-0001` advisory as 6.4's suite, deliberately with a non-critical CVSS score so the forced `--min-epss` block is unambiguous (FR36). |
| **6.8** | Baseline & grandfathering (gate new findings only) | ✅ | ✅ | — | `unit/test_waiver.py` (baseline half, bottom of the file), `unit/test_report.py`, `conformance/test_baseline_grandfathering.py` | `test_waiver.py`'s own docstring: "Story 6.8 adds the baseline & grandfathering half of the SAME engine (`BaselineEntry`/`load_baseline`/`emit_baseline_stanza` + `apply_waivers`'s `baseline=` parameter and its waiver-wins tie-break)" — one suppression engine, not a parallel path, mirroring `test_config.py`'s real-file-round-trip convention. `test_baseline_grandfathering.py` is the CLI-level conformance proof: a matching baseline entry suppresses + echoes `origin="baseline"`, an unlisted finding still gates, an expired entry re-blocks, a waiver on the same finding id wins the tie-break, and `--baseline-emit` never itself changes the verdict (FR39). |
| **6.9** | Fix-PR actuator (opt-in remediation PRs) | ✅ | ✅ | ✅ | `unit/test_actuator.py`, `conformance/test_fix_pr_actuator.py`, `meta/test_socket_deny_alive.py` (carve-out proof) | `test_actuator.py` covers the closed remediation mapping, dry-run (no client, no socket), the injected fake `ForgeClient` path, `resolve_forge` env-reading, and `Actuation.to_json_dict`'s sorted shape — every test still runs under the deny-by-default socket harness. `test_fix_pr_actuator.py` drives `cli.main()` end-to-end against a LOCAL raw-socket fake forge, reachable only because the actuator's `_EGRESS_ACTIVE` marker unlocks the conftest carve-out — `meta/test_socket_deny_alive.py` is where that carve-out's own boundary is proven not to leak into the general case (FR40). |
| **6.10** | Amendment design spike — finding-ID families, verdict encoding, rung-discriminator & fold semantics (decision record) | — | — | — | **None — by design.** | The story's own acceptance criteria state it explicitly: "this spike changes no code and no schema." Unlike Story 1.4 (also a spike, but one whose AC produces an executable artifact — the hermetic fixture DB `osv_db_builder.py` builds, proven by `test_osv_offline_db_spike.py`), 6.10's deliverable is a **markdown decision record** (`_bmad-output/projects/pyforge-warden/planning-artifacts/finding-id-verdict-encoding-decision.md`), consumed by 6.1 as design input. There is nothing to test because there is no runtime behavior to test — the decision record's content is proven correct by 6.1 successfully implementing it "without new design decisions." This is the one story in the 31 with no test-file mapping, and it is the honest, correct state, not a gap. |

**Acceptance**: 9/10 stories have direct, story-cited test coverage; the 10th (6.10) correctly has none, for the reason stated above. The two HARD sprint-order gates epics.md names (6.10 → 6.1 → every other 6.x story) are visible in the test evidence too: every 6.2+ file's tests exercise the widened (post-6.1) schema shape, and none of them predate or duplicate `test_models.py`'s field-shape assertion.

---

## Full Test File Index

All 54 files, one line each, condensed from the module docstring read for each one during construction of this document. Grouped by directory to mirror the real `tests/` layout.

### `tests/unit/` (30 files)

| File | What it proves | Story(ies) |
|------|-----------------|------------|
| `test_actuator.py` | Fix-PR actuator: closed remediation mapping, dry-run, fake `ForgeClient` path, env-credential resolution | 6.9 |
| `test_cli_bypass.py` | `--bypass --reason` CLI + committed `.warden-waivers.yaml` integration, real `tmp_path`/`main()` | 3.2, 3.3 |
| `test_cli_doctor.py` | `--doctor` CLI surface: exit-code matrix, air-gapped wording, short-circuit-before-discovery | 5.1 |
| `test_cli_sbom.py` | `--sbom-output` CLI surface: write-success/write-failure rows | 4.1 |
| `test_config.py` | `EffectiveConfig`/`ConfigLoader`: dual-TOML load, per-key precedence, derived policy knobs | 3.1 |
| `test_currency.py` | Per-component + Python-runtime currency verdicts: tier ladder, `currency_rung` warn-cap | 6.3 |
| `test_discovery_extract_cli.py` | I/O-matrix edges: discovery stub, pyproject extractor, routing, full CLI surface | 1.2, 1.7, 1.9, 2.4, 3.1 |
| `test_engine_env_deptry.py` | `_engine_env()` seam + `DeptryEngine`, injected fakes only | 1.3, 1.5, 1.7, 6.6 |
| `test_environment_yml_extractor.py` | `EnvironmentYmlExtractor` I/O-matrix rows, direct, no CLI | 2.2 |
| `test_feeds.py` | `feeds.py`: cache-dir resolution, KEV/endoflife/EPSS trios, atomic cache writer | 6.4, 6.3, 6.7 |
| `test_hygiene.py` | deptry-output parsing + default hygiene→status table | 1.3, 2.1, 2.4 |
| `test_identity.py` | `extract/_identity.py` conda-matchspec exactness discipline | 2.2 |
| `test_interfaces_and_null_engine.py` | Strategy seam: Protocols, registry, null engine, `DefaultPolicy` | 1.2, 1.7, 3.1, 6.2, 6.3, 6.5, 6.7 |
| `test_inventory.py` | Gap-B identity + merge rules: provenance union, bare-version folding, purl derivation | 1.1, 6.1 |
| `test_license.py` | Per-component SPDX license verdicts, `license_rung` warn-cap | 6.2, 6.5 |
| `test_lockfiles_extractor.py` | `PixiLockExtractor` + `CondaLockExtractor` I/O-matrix rows | 2.6, 2.1 |
| `test_mapping.py` | Bundled conda→pypi map's real shape + TSV→JSON converter script | 2.1 |
| `test_meta_v0_extractor.py` | `MetaV0Extractor` I/O-matrix rows | 2.2, 2.3 |
| `test_models.py` | Frozen enum tokens + report/finding types, full `Component` shape | 1.1, 1.9, 6.1 |
| `test_osv_engine_exit_codes.py` | `OsvEngine.run()` exit-code disposition (127/128/other), injected fake subprocess | 1.5, 2.1, 6.6 |
| `test_pixi_extractor.py` | `PixiTomlExtractor` I/O-matrix rows | 2.2 |
| `test_recipe_v1_extractor.py` | `RecipeV1Extractor` I/O-matrix rows | 2.2, 2.3 |
| `test_refresh_endoflife_feed.py` | `scripts/refresh_endoflife_feed.py`, network fully mocked | 6.3 |
| `test_refresh_epss_feed.py` | `scripts/refresh_epss_feed.py`, gzip-CSV response, network fully mocked | 6.7 |
| `test_refresh_kev_feed.py` | `scripts/refresh_kev_feed.py`, network fully mocked | 6.4 |
| `test_report.py` | `assemble_report`'s `hygiene_applicable` override + `render_text` in isolation | 2.4, 1.8, 3.1, 3.3, 5.1, 6.1, 6.8 |
| `test_sbom.py` | CycloneDX 1.6 SBOM projection: G98 purls, `cfe:*` attachment, NFR-S7 | 4.1 |
| `test_verdict.py` | C0a directly against the projection: totality, exit table, safety rule | 1.1, 1.6 |
| `test_vuln.py` | Vuln engine non-subprocess logic: DB-cache, content pre-flight, CVSS tiers | 1.5, 1.6, 2.1, 2.5, 5.1, 6.4, 6.7 |
| `test_waiver.py` | Waiver suppression engine + baseline & grandfathering half of the same engine | 3.2, 3.3, 6.8 |

### `tests/conformance/` (19 files)

| File | What it proves | Story(ies) |
|------|-----------------|------------|
| `test_axis_producer_ceiling.py` | Producer meta-test: license/currency axes never self-escalate above `warn` | 6.2, 6.3, 6.5 |
| `test_baseline_grandfathering.py` | `--baseline`/`--baseline-emit` CLI surface end-to-end via `cli.main()` | 6.8 |
| `test_corpus_determinism.py` | Corpus-scale `--deterministic` byte-identical proof (`@pytest.mark.slow`) | 5.2 |
| `test_corpus_egress_counter.py` | Observes the real osv-scanner subprocess's network from outside the process | 5.2 |
| `test_corpus_regression.py` | Corpus-scale extraction regression gate: 0 uncaught exceptions, ratcheted rate | 5.2 |
| `test_doctor.py` | `warden scan --doctor` end-to-end against the real provisioned environment | 5.1 |
| `test_dogfood.py` | Warden scans its own package; a seeded new violation must still exit non-zero | 5.2 |
| `test_engine_parallelism.py` | 4-axis engine fan-out runs concurrently via `ThreadPoolExecutor`, order-stable | 5.2 |
| `test_epss_enrichment.py` | FIRST.org EPSS enrichment + `--min-epss` gate through production code | 6.7 |
| `test_extraction_oracle.py` | Differential-oracle: extractor output vs. real `rattler_build`/`conda_build` render | 2.2, 2.3, 5.2 |
| `test_fix_pr_actuator.py` | Fix-PR actuator E2E against a local raw-socket fake forge | 6.9 |
| `test_kev_enrichment.py` | CISA KEV enrichment + `--fail-on-kev` gate through production code | 6.4 |
| `test_lockfile_oracle.py` | `PixiLockExtractor` vs. py-rattler's own `LockFile` parse (hard-fail, never skip) | 2.6 |
| `test_osv_engine.py` | `OsvEngine.run()` against the real `osv-scanner` binary (hard-fail, never skip) | 1.5, 6.6 |
| `test_osv_offline_db_spike.py` | The 1.4 spike's own empirical proof: real binary, hermetic DB, zero network | 1.4, 2.5 |
| `test_perf_overhead.py` | Stubbed-engine orchestration/report overhead benchmark (NFR-P-warm) | 5.2 |
| `test_report_schema.py` | Packaged `ComplianceReport` schema: exit enum, `status.driver`, additive growth | 1.1, 1.9, 6.1 |
| `test_sbom_schema.py` | CycloneDX 1.6 SBOM's own schema validity via `JsonStrictValidator` | 4.1 |
| `test_scan_harness.py` | The loop's own verify gate: 2-fixture regression harness + I/O-matrix edges | 1.2 (+ rows for 1.7, 1.8, 1.9, 2.1, 2.4, 3.1, 3.3) |

### `tests/meta/` (4 files) + root

| File | What it proves | Story(ies) |
|------|-----------------|------------|
| `test_engine_version_range_sync.py` | `pixi.toml`/`engines.py` version-range pins never drift apart | 6.6 |
| `test_extract_no_execution.py` | AST denylist: `extract/` imports no execution primitive (NFR-S1) | 1.2 |
| `test_socket_deny_alive.py` | The C0c socket-deny harness is itself alive, including the 6.9 carve-out boundary | 1.2, 6.9 |
| `test_verdict_sole_ownership.py` | Only `verdict.py` may project an exit code or the rung ordering | 1.1 |
| `test_smoke.py` (root) | Package imports + the real CLI surface answers (post-scaffold contract) | 1.2 |

---

## FR/NFR Coverage Cross-Reference

Every functional requirement from `epics.md` § Requirements Inventory (FR1–FR40), mapped to its owning story and that story's primary test evidence (see the per-epic tables above for the full file list — this table cites the single most-load-bearing file per FR to keep it scannable).

| FR | What it requires | Story | Primary test evidence |
|----|-------------------|:-----:|------------------------|
| FR1 | Discover + classify candidate manifests; deterministic selection; report the resolved scan set | 1.9 | `unit/test_discovery_extract_cli.py` |
| FR2 | Classify each dependency source-section → correct extractor | 1.9 | `unit/test_discovery_extract_cli.py` |
| FR3 | Extract deps from conda/pixi source manifests without a resolved environment | 2.2 (+2.6 lockfile path) | `unit/test_recipe_v1_extractor.py`, `unit/test_lockfiles_extractor.py` |
| FR4 | Delegate to engines' native parsers for PyPI inputs | 1.3 | `unit/test_engine_env_deptry.py` |
| FR5 | Best-effort templating/selector eval; degrade to name-only+marked | 2.3 | `unit/test_recipe_v1_extractor.py`, `conformance/test_extraction_oracle.py` |
| FR6 | Distinguish "no deps present" vs. "deps present but unresolved" | 2.4 | `unit/test_report.py` |
| FR7 | Per-ecosystem attribution; no silent cross-ecosystem merge | 2.5 | `unit/test_vuln.py` |
| FR8 | Hygiene findings (unused/missing/transitive/misplaced), PyPI+conda | 1.3 (+2.2 conda half) | `unit/test_hygiene.py` |
| FR9 | Honor `[tool.deptry]` ignores | 1.3 | `unit/test_hygiene.py` |
| FR10 | Vuln findings (advisory/affected-fixed/severity), actionable | 1.5 | `conformance/test_osv_engine.py` |
| FR11 | Offline/air-gapped vuln DB; records source+timestamp | 1.5 (decision: 1.4) | `unit/test_vuln.py` |
| FR12 | Detect stale DB → degrade verdict | 2.5 | `unit/test_vuln.py` |
| FR13 | Unresolved version → indeterminate + name-level CVE tier; never assume a version | 2.4, 2.5 | `unit/test_discovery_extract_cli.py`, `unit/test_vuln.py` |
| FR14 | Schema-validated report (status/severity/schema_version/coverage/error_kind) | 1.1 | `conformance/test_report_schema.py` |
| FR15 | Per-axis coverage (one dimension per registered axis) | 2.4 (widened by 6.1) | `unit/test_report.py` |
| FR16 | Partial coverage → qualified verdict, never bare "clean" | 2.4 | `unit/test_report.py` |
| FR17 | Human + machine report, every blocking finding actionable | 1.8 | `unit/test_report.py` |
| FR18 | Gate on content+severity (vuln default critical + any KEV-listed) | 1.6 | `unit/test_vuln.py` |
| FR19 | Minimum coverage-floor gate (default OFF) | 3.1 | `unit/test_report.py` |
| FR20 | Verdict-composition lattice + separate exit; indeterminate → non-zero | 1.6 (frozen in 1.1) | `unit/test_verdict.py` |
| FR21 | Detect engine presence/version + typed error_kinds, never silent PASS | 1.7 | `unit/test_discovery_extract_cli.py` |
| FR22 | No-meaningful-scan → non-passing, never clean | 1.7 (+1.9 D2 downgrade) | `conformance/test_scan_harness.py` |
| FR23 | Warn-only mode | 3.3 | `unit/test_cli_bypass.py` |
| FR24 | Auditable expiring waiver (reason/authorizer/expiry) | 3.2 | `unit/test_waiver.py` |
| FR25 | Re-block on expiry + flag for review | 3.3 | `unit/test_waiver.py` |
| FR26 | Validate waiver schema; reject malformed/malicious | 3.2 | `unit/test_waiver.py` |
| FR27 | CycloneDX 1.6 SBOM | 4.1 | `unit/test_sbom.py` |
| FR28 | Stable exit-code contract | 1.1 | `conformance/test_report_schema.py` |
| FR29 | One non-interactive command → one exit code (+ `--doctor` clause) | 1.8 (+5.1) | `unit/test_discovery_extract_cli.py`, `unit/test_cli_doctor.py` |
| FR30 | Dual `[tool.pyforge-warden]` config, per-key precedence | 3.1 | `unit/test_config.py` |
| FR31 | `--version`/`--help` stable contract | 1.8 | `unit/test_discovery_extract_cli.py` |
| FR32 | SPDX license enrichment | 6.2 | `unit/test_license.py` |
| FR33 | `--allow/--deny-licenses` gate | 6.2 (escalation: 6.5) | `unit/test_config.py`, `conformance/test_axis_producer_ceiling.py` |
| FR34 | Tiered currency (LTS registry → endoflife.date → N/N-1 → unknown) | 6.3 | `unit/test_currency.py` |
| FR35 | `--max-lag`/`--require-lts`/`--fail-on-eol` gate | 6.3 (escalation: 6.5) | `unit/test_config.py`, `conformance/test_axis_producer_ceiling.py` |
| FR36 | KEV + EPSS enrichment + `--fail-on-kev`/`--min-epss` gates | 6.4, 6.7 | `conformance/test_kev_enrichment.py`, `conformance/test_epss_enrichment.py` |
| FR37 | Unconfigured-axis visibility (never silent clean) | 6.5 | `conformance/test_axis_producer_ceiling.py` |
| FR38 | The one versioned schema amendment | 6.1 | `unit/test_models.py`, `conformance/test_report_schema.py` |
| FR39 | Baseline & grandfathering (gate NEW findings only) | 6.8 | `conformance/test_baseline_grandfathering.py` |
| FR40 | Fix-PR actuator (opt-in) | 6.9 | `unit/test_actuator.py`, `conformance/test_fix_pr_actuator.py` |

All 40 FRs have at least one grounded test citation. This table's story assignments are copied directly from `epics.md`'s own "FR Coverage Map" line and its "Post-roundtable corrections" parenthetical (FR1→1.9, FR9→1.3 not E3, FR15→2.4 widened in 6.1, FR24→3.2, FR11→also 1.5, FR29's `--doctor` clause→5.1, FR3's lockfile path→2.6) — not re-derived independently.

---

## Test Coverage Summary

| Level | Directory | File count | Stories with a primary file there |
|-------|-----------|:-----------:|-------------------------------------|
| **Unit (U)** | `tests/unit/` | 30 | 24 of 31 stories have at least one dedicated unit file |
| **Conformance (C)** | `tests/conformance/` | 19 | 26 of 31 stories have at least one dedicated conformance file (real `cli.main()` or real-binary end-to-end) |
| **Meta (M)** | `tests/meta/` | 4 | 4 stories (1.1, 1.2 ×2, 6.6) — architectural invariant guards, not per-feature |
| **Smoke** | `tests/test_smoke.py` | 1 | Cross-cutting scaffold test, tied to Story 1.2's CLI-contract retirement of the pre-real-engine stub behavior |
| **Total** | | **54 files / 1,947 tests** | **30 of 31 stories** (96.8%) have at least one story-cited test file; **Story 6.10 has none, correctly** (decision-record spike, no code produced) |

**No %-line-coverage figure is asserted anywhere in this repo for this package** — see § Coverage Gate Reality below for why that is a deliberate choice, not an oversight.

---

## Story Dependencies & Build Order

Warden's real dependency order is documented in `epics.md` itself as the **"recommended wedge-first build order"** (quoted verbatim, not reconstructed):

```
1.1 → 1.2 → 1.3 (deptry) → 1.9 (discovery) → 2.1 (map + pypi_identity → indeterminate
  = the wedge demo) → 2.2 (extraction + oracle) → 1.4 (OSV spike) → 1.5 (osv) →
  2.5 (name-level CVE) → 1.6 (gate) → 1.7/1.8 (report) → 2.3/2.4 → E3 → E4 →
  6.10 (amendment design spike — decision record) → 6.1 (schema amendment —
  HARD gate: no 6.x producer starts before it) → 6.4 (KEV + the feeds.py
  skeleton) → 6.2 (license producer + the producer meta-test) → 6.3 (currency
  producer; registers into 6.2's meta-test, consumes 6.4's feeds.py — ordered,
  not parallel) → 6.5 (escalation, solely owned) → 6.7 (EPSS, consumes
  feeds.py) / 6.8 (baseline, extends the waiver suppression core) →
  6.9 (fix-PR actuator) → 6.6 (engine ranges) → E5
```

Every ordering claim in that sequence is independently visible in the test evidence gathered for this document:

- **1.1 → 1.2 (cluster-1) precedes 1.3+ (cluster-2)**: `meta/test_verdict_sole_ownership.py` and `meta/test_socket_deny_alive.py` exist only after 1.1/1.2 land, and every later story's tests run under both guards without re-litigating them.
- **2.1 before 2.2**: `unit/test_lockfiles_extractor.py` (Story 2.6, a 2.1 offshoot) has a comment "The real bundled map (Story 2.1) now maps 'numpy' -- monkeypatch to a..." — later stories consume 2.1's map as a fixed fact.
- **6.10 → 6.1 HARD gate**: `unit/test_models.py`'s full 15-field `Component` shape and `conformance/test_report_schema.py`'s additive-compat test are the only tests that touch the schema directly; every 6.2+ file consumes that widened shape without re-deriving it, consistent with 6.1 being "the sole schema writer."
- **6.4 before 6.3/6.7**: `unit/test_feeds.py`'s own docstring says 6.3's endoflife trio and 6.7's EPSS trio each "mirror the KEV sections one-for-one" — the KEV sections (6.4) exist first in the file, and the later two stories extend the same file rather than building a parallel cache.
- **6.2 before 6.5**: `conformance/test_axis_producer_ceiling.py`'s docstring: "Story 6.2; Story 6.3 appends the currency axis's own entry to the SAME parametrized table" and "a future edit that lets `license_rung` consult `config.license_policy` (Story 6.5's own job) would fail this test immediately" — the ceiling test is 6.2's, the escalation is explicitly deferred to 6.5 by name.

---

## Test Fixtures & Corpus

Unlike Marshal's suite (which uses hand-written `Mock*` classes in a `tests/mocks/` directory), Warden's suite has **no `mocks/` directory** — it favors real subprocess execution against hermetic, committed fixture data wherever the C0 gate-integrity invariant is load-bearing, and monkeypatches `subprocess.run` only in narrowly-scoped unit tests that isolate a single seam (`test_engine_env_deptry.py`, `test_osv_engine_exit_codes.py`). This is a real, deliberate difference from Marshal's approach, not an omission.

**Shared fixtures** (`tests/conftest.py`, own docstring: "Shared test fixtures (Story 1.1)"):
- `component_factory` (wraps `make_component`) — the single `Component` factory for the whole suite; test modules take the fixture instead of importing across test files.
- `socket_deny_error` — the exception type the C0c harness raises; every socket primitive (`connect`, `connect_ex`, `sendto`, `sendmsg`, `create_connection`, `getaddrinfo`, `gethostbyname[_ex]`, `gethostbyaddr`, `getnameinfo`) is monkeypatched to deny by default, autouse, patched at conftest import time (not via a fixture window).
- Session-scoped ambient environment fixtures: `_osv_ambient_cache_root` / `_osv_ambient_db_env` (provisions the hermetic offline OSV DB once per session), `_feed_cache_root` / `_kev_ambient_feed_env` / `_currency_ambient_feed_env` (same pattern for the KEV and endoflife/currency feed caches).

**Fixture data on disk** (`tests/fixtures/`):
- `projects/` — 23 hand-authored small Python/conda projects, one concern each: `clean`, `deptry_unused`, `deptry_missing`, `deptry_ignore`, `deptry_stdlib`, `vuln_critical`, `vuln_high`, `vuln_kev`, `vuln_kev_fail_on_kev_false`, `vuln_min_epss_toml`, `warn_and_indeterminate`, `config_precedence`, `hygiene_not_applicable`, `hygiene_not_applicable_malformed`, `sentinel` (the false-green sentinel from 1.2's harness), `recipe_common`/`recipe_complex`, `meta_common`/`meta_complex`, `pixi_toml_common`, `environment_yml_common`, `pixi_lock_basic`/`pixi_lock_url_basename_pitfall`, `conda_lock_basic`.
- `osv-db/pypi/` — hermetic OSV advisory JSON records, including the shared `PDOS-KEV-FIXTURE-0001` (package `pdos-kev-fixture`) reused identically by both `test_kev_enrichment.py` and `test_epss_enrichment.py`, and `PDOS-FIXTURE-0001`/`pdos-vuln-fixture` reused by the 1.4 spike proof.
- `lockfiles/osv-vulnerable/` and `lockfiles/osv-clean/` — locked-closure fixtures for 2.6/1.5.
- `corpus/recipes/` — **1,979** real `recipe.yaml`/`meta.yaml` files harvested from this repo's own `recipes/` tree by `scripts/harvest_corpus.py` (verified count, 2026-08-02). `corpus/adversarial/` — 9 hand-pinned adversarial files (exotic selectors, `{% for %}`, unicode, oversized), sourced in part from `prefix-dev/rattler-build-parser-tests`.
- `adversarial_names.json` — the NFR-S7 adversarial-component-name corpus consumed by `test_sbom.py`.
- `osv_db_builder.py` — not a test file but the shared hermetic-DB-building module every OSV-touching suite (1.4, 1.5, 2.5, 6.4, 6.7) imports by path.

---

## Testing Conventions Worth Naming

Three conventions recur across the 54 files and are worth stating once rather than repeating in every table row above:

- **Hard-fail-never-skip for provisioned engines; skip-if-unavailable for renderers.** `test_osv_engine.py` and `test_lockfile_oracle.py` both state explicitly that they hard-fail (never skip) if `osv-scanner` or `py-rattler` is absent from the environment — "a conformance suite for a provisioned engine must not silently green over a broken environment." `test_extraction_oracle.py`, by contrast, explicitly *skips* when `rattler_build`/`conda_build` are unimportable, because — per its own docstring — those two renderers "aren't guaranteed provisioned the way `py-rattler` already was." This is a real, deliberate distinction based on which dependencies are guaranteed present, not an inconsistency.
- **The shared hermetic-fixture-advisory pattern.** `PDOS-KEV-FIXTURE-0001` (package `pdos-kev-fixture`) is defined once in `tests/fixtures/osv-db/pypi/` and reused byte-for-byte by `test_kev_enrichment.py` (Story 6.4) and `test_epss_enrichment.py` (Story 6.7) — the latter's docstring states it reuses the fixture specifically so "the SAME candidate-collection proof KEV's own suite already establishes applies here unchanged." This is why 6.4 and 6.7 are correctly described as sharing test infrastructure rather than duplicating it.
- **Real subprocess by default, monkeypatch only at a named seam.** The large majority of conformance tests drive real `deptry`/`osv-scanner` binaries; unit-level `subprocess.run` monkeypatching is confined to two files that say so explicitly in their own docstrings (`test_engine_env_deptry.py`, `test_osv_engine_exit_codes.py`), each justified by needing to force an exit-code branch (127/128/timeout) that the real binary won't reliably produce on demand.

---

## Cross-Cutting Invariants (Meta-Tests + the C0 Family)

Warden's cross-cutting acceptance gates are named directly in `epics.md` (§ Requirements Inventory → Additional Requirements) as applying to **every story**, not as a separate epic. Each has a real, identifiable test home:

| Invariant | What it means | Test home | Notes |
|-----------|----------------|------------|-------|
| **C0 — Gate-Integrity** | Never false-green; N adversarial fixtures → 0 exit-0 | `conformance/test_scan_harness.py` (the sentinel fixture), `conformance/test_corpus_regression.py`/`test_dogfood.py` at scale | The suite's actual acceptance gate — not a %-coverage number. |
| **C0a — Projection-safety** | The 7-rung lattice projection is total and correctly ordered | `unit/test_verdict.py`, `meta/test_verdict_sole_ownership.py` | Owned outright by Story 1.1. |
| **C0b — Withhold-completeness** | An `indeterminate` component is never dropped or defaulted to clean | `unit/test_discovery_extract_cli.py`, `unit/test_report.py`, `conformance/test_scan_harness.py` | Owned by Story 2.4; producer, not the projection itself. |
| **C0c — No silent egress** | Deny-by-default socket harness; egress during a scan is a hard test failure | `meta/test_socket_deny_alive.py` (the guard is alive), every test file transitively (autouse fixture) | Landed in Story 1.2; the one documented carve-out is Story 6.9's actuator, itself boundary-tested. |
| **verdict.py sole-ownership guard** | Only `verdict.py` may invoke a guarded exit or materialize the rung ordering | `meta/test_verdict_sole_ownership.py` | AST-scans every module in the installed package except `verdict.py`. |
| **NFR-S1 (no execution of untrusted input)** | `extract/` imports no execution primitive, no `jinja2` | `meta/test_extract_no_execution.py` | AST denylist over the whole `extract/` package. |
| **NFR-R1/R2 (0 uncaught exceptions + ratcheted unparseable rate)** | Corpus-wide reliability floor | `conformance/test_corpus_regression.py` | Story 5.2, default-suite (not `slow`-marked — fast enough to run every time). |
| **NFR-R3b (two-tier determinism)** | Byte-identical twice-run under `--deterministic` | `conformance/test_scan_harness.py` (fixture scale), `test_corpus_determinism.py` (corpus scale, `slow`) | |
| **NFR-S9 (bundled-data max-age)** | A stale bundled LTS registry / map never silently reports "supported" | `unit/test_currency.py`, `unit/test_mapping.py` | Added 2026-07-15 alongside Epic 6. |
| **NFR-C1 (engine version-range distribution gate)** | `pixi.toml` and `engines.py` version ranges never drift apart | `meta/test_engine_version_range_sync.py` | Story 6.6, added 2026-07-16 (D12). |

---

## Framework & Tooling

**Pytest** is the sole test runner — no Playwright, no browser automation. This is correct, not a gap: Warden's own PRD is explicit that it is "N/A — non-interactive CI CLI; no human-UI surface" (`epics.md` § UX Design Requirements).

**Real pixi tasks** (`pixi.toml`, root of the repo, `[feature.pyforge-warden.tasks.*]`):
- `pyforge-warden-test` — `pytest src/shared/packages/pyforge-warden/tests -q -m "not slow"`. The default loop; 1,936 tests.
- `pyforge-warden-test-corpus-oracle` — `pytest src/shared/packages/pyforge-warden/tests -q -m slow`. The corpus-scale differential-oracle + full-corpus determinism + egress-counter proofs (Story 5.2); 11 tests; not part of the default loop because it is dominated by real `rattler-build`/`conda-build` renders and a real `osv-scanner` subprocess over ~1,979 recipes.
- `pyforge-warden-dogfood` — `python scripts/dogfood_scan.py`, `cwd = src/shared/packages/pyforge-warden`. Warden scanning its own package (`pyproject.toml` + `src/`, `tests/` excluded) — the epics.md AC3 dogfood gate, also proven inside the test suite by `conformance/test_dogfood.py`.
- `pyforge-warden-build-conda` / `pyforge-warden-build-dist` / `pyforge-warden-build` — the three-artifact build (conda pkg via pixi-build-python, wheel+sdist via hatchling).

**Test-only dependencies** (`pixi.toml`, `[feature.pyforge-warden.dependencies]`, each annotated "NEVER a pyforge-warden runtime dependency"):
- `py-rattler >=0.25.0` — the test-side oracle for `extract/lockfiles.py` (Story 2.6).
- `py-rattler-build >=0.72.2` — the differential-oracle for `extract/recipe_v1.py` (Story 2.2, v1 render).
- `conda-build >=25.3.1` — the differential-oracle for `extract/meta_v0.py` (Story 2.2, v0 render).

**Real production engine version ranges** (the Story 6.6 distribution gate, `pixi.toml` run-deps, kept in sync with `engines.py`'s `SpecifierSet` constants by `meta/test_engine_version_range_sync.py`):
- `deptry = ">=0.25.1,<0.26"`
- `osv-scanner = ">=2.4.0,<2.5"`

**`pytest.ini_options`** (`pyproject.toml`, `src/shared/packages/pyforge-warden/`): a single custom marker, `slow`, defined exactly for the Story 5.2 corpus-scale split described above. No `pytest-cov`, no `addopts` coverage flag, no coverage-threshold plugin configured anywhere in this package.

---

## Coverage Gate Reality

Marshal's own test-architecture document (the format exemplar for this one) states numeric line-coverage targets (`Unit ≥80%`, `Integration ≥70%`) as its acceptance gate. **Warden does not use that model, and this document will not invent numbers to match the exemplar's shape.**

Verified 2026-08-02 against `src/shared/packages/pyforge-warden/pyproject.toml`: the only test configuration present is `[tool.pytest.ini_options]` with a single `markers` declaration for `slow`. There is no `pytest-cov` dependency, no `--cov` flag in any pixi task, and no coverage-percentage threshold anywhere in this package's configuration or in the root `pixi.toml`.

This is a deliberate, documented design choice, not an oversight: Warden's own acceptance gate (`epics.md` § NFR — "C0: never false-green; N adversarial fixtures → 0 exit-0") is a **behavioral** property, proven by dedicated fixtures and a real 1,979-file corpus, not a line-coverage percentage. A module could have 100% line coverage and still false-green on a real adversarial input; conversely, a module with lower line coverage but a passing `test_scan_harness.py` sentinel-fixture row has directly proven the property that actually matters for a security gate. The **real** acceptance evidence for this package is:
- **1,947 tests collected**, 1,936 in the default loop.
- **0 known uncaught exceptions** across the 1,979-file corpus (`test_corpus_regression.py`, part of the default loop — not `slow`-marked, so this runs on every `pyforge-warden-test` invocation).
- **The dogfood gate passes** on Warden's own package (`test_dogfood.py` + the `pyforge-warden-dogfood` pixi task).

If a %-line-coverage gate is wanted in the future, that is a new capability to scope and build (add `pytest-cov`, decide a threshold, wire it into the pixi task) — not something this document should retroactively claim already exists.

---

## Readiness Checklist

- [x] All 31 stories defined in `epics.md`, cross-checked against this document's ground truth story list — verbatim match.
- [x] Every story mapped to real FR/NFR references, read from `epics.md` directly (FR1–FR40, C0/C0a/C0b/C0c, NFR-R1/R2/R3a/R3b/S1–S9/P-warm/cold/concurrency/I1–I3/U1–U2/C1).
- [x] 30 of 31 stories have at least one story-cited test file (unit and/or conformance and/or meta); the 31st (6.10) correctly has none, with the reason stated inline.
- [x] Real test-file inventory verified against the live filesystem 2026-08-02: 54 files, matching the ground-truth list given for this task exactly.
- [x] Real test count verified via `pytest --collect-only`: 1,947 tests (1,936 default + 11 slow-marked).
- [x] Cross-cutting invariants (C0/C0a/C0b/C0c, verdict.py sole-ownership, NFR-S1/R1/R2/R3b/S9/C1) each mapped to a real meta/ or conformance/ test file.
- [x] Fixture and corpus inventory verified against the live filesystem (1,979 corpus recipes, 9 adversarial, 23 hand-authored project fixtures, hermetic OSV/KEV/EPSS fixture data).
- [x] Framework and pixi-task references verified against the live `pixi.toml`/`pyproject.toml`, not recalled from memory.
- [x] No fabricated coverage percentages — the absence of a %-coverage gate is stated explicitly, with the file checked to prove it.
- [x] This document is retrospective (describes shipped, tested code) — no forward-looking "TBD" rows remain.

---

**Status**: DRAFT — descriptive of shipped code; no further BMAD planning action is implied by this document (Warden is code-complete, all 31 stories shipped).

**Last updated**: 2026-08-02
