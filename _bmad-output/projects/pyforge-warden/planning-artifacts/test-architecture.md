---
title: "Test Architecture — pyforge-warden"
type: test-architecture
generator: bmad_tea_playwright.py
generator_version: 2.1.0
status: generated
station: warden
source_fingerprint: 61db49da7af356c3
story_count: 43
test_file_count: 64
coverage_target_unit: ">=80%"
coverage_target_integration: ">=70%"
---

# Test Architecture — PyForge Warden

This document is **machine-generated** by `bmad_tea_playwright.py` (v2.1.0). Do not hand-edit; re-run the generator after epics or tests change.

## Executive Summary

- **Station:** `pyforge-warden`
- **Stories parsed:** 43
- **Epics parsed:** 17
- **Test files inventoried:** 64 under `src/shared/packages/pyforge-warden/tests/`
- **Frameworks:** pytest (unit/integration/meta) + Playwright where present
- **Coverage targets:** unit ≥80%, integration ≥70% (gated by Story 19.3)
- **Source fingerprint:** `61db49da7af356c3`

## Risk Assessment

### High-risk epics

- none observed

### Medium-risk epics

- Epic 1: Spine + PyPI engine (walking skeleton)
- Epic 2: The conda/pixi source-manifest wedge
- Epic 3: Policy control + auditable waivers + warn-only
- Epic 4: Machine contract + CycloneDX SBOM
- Epic 5: Fleet-readiness & adoption on-ramp
- Epic 6: Multi-axis expansion — license, currency, KEV/EPSS & adoption (added 2026-07-15; re-baselined 2026-07-16, D12)
- Epic 7: One provenance trail, one eligibility answer
- Epic 8: A web face for the compliance factory
- Epic 9: PR-gate hook specs; scanners are plugins
- Epic 10: Warden owns its skill, persona, and one portal job
- Epic 11: Two advisory lenses beside the gate
- Epic 1: Spine + PyPI engine (walking skeleton)
- Epic 2: The conda/pixi source-manifest wedge
- Epic 3: Policy control + auditable waivers + warn-only
- Epic 4: Machine contract + CycloneDX SBOM
- Epic 5: Fleet-readiness & adoption on-ramp
- Epic 6: Multi-axis expansion — license, currency, KEV/EPSS & adoption (added 2026-07-15; re-baselined 2026-07-16, D12)

### Low-risk epics

- none observed

## Test Inventory

| Relative path | Level | Linked stories |
|---------------|-------|----------------|
| `src/shared/packages/pyforge-warden/tests/conformance/test_axis_producer_ceiling.py` | unit | none observed |
| `src/shared/packages/pyforge-warden/tests/conformance/test_baseline_grandfathering.py` | unit | none observed |
| `src/shared/packages/pyforge-warden/tests/conformance/test_corpus_determinism.py` | unit | none observed |
| `src/shared/packages/pyforge-warden/tests/conformance/test_corpus_egress_counter.py` | unit | none observed |
| `src/shared/packages/pyforge-warden/tests/conformance/test_corpus_regression.py` | unit | none observed |
| `src/shared/packages/pyforge-warden/tests/conformance/test_doctor.py` | unit | none observed |
| `src/shared/packages/pyforge-warden/tests/conformance/test_dogfood.py` | unit | none observed |
| `src/shared/packages/pyforge-warden/tests/conformance/test_engine_parallelism.py` | unit | none observed |
| `src/shared/packages/pyforge-warden/tests/conformance/test_epss_enrichment.py` | unit | none observed |
| `src/shared/packages/pyforge-warden/tests/conformance/test_extraction_oracle.py` | unit | none observed |
| `src/shared/packages/pyforge-warden/tests/conformance/test_fix_pr_actuator.py` | unit | none observed |
| `src/shared/packages/pyforge-warden/tests/conformance/test_kev_enrichment.py` | unit | none observed |
| `src/shared/packages/pyforge-warden/tests/conformance/test_lockfile_oracle.py` | unit | none observed |
| `src/shared/packages/pyforge-warden/tests/conformance/test_osv_engine.py` | unit | none observed |
| `src/shared/packages/pyforge-warden/tests/conformance/test_osv_offline_db_spike.py` | unit | none observed |
| `src/shared/packages/pyforge-warden/tests/conformance/test_perf_overhead.py` | unit | none observed |
| `src/shared/packages/pyforge-warden/tests/conformance/test_report_schema.py` | unit | none observed |
| `src/shared/packages/pyforge-warden/tests/conformance/test_sbom_schema.py` | unit | none observed |
| `src/shared/packages/pyforge-warden/tests/conformance/test_scan_harness.py` | unit | none observed |
| `src/shared/packages/pyforge-warden/tests/meta/test_engine_version_range_sync.py` | meta | none observed |
| `src/shared/packages/pyforge-warden/tests/meta/test_extract_no_execution.py` | meta | none observed |
| `src/shared/packages/pyforge-warden/tests/meta/test_portal_audit_start_get.py` | meta | none observed |
| `src/shared/packages/pyforge-warden/tests/meta/test_pr_gate_plugin_registration.py` | meta | none observed |
| `src/shared/packages/pyforge-warden/tests/meta/test_skf_domain_skill.py` | meta | none observed |
| `src/shared/packages/pyforge-warden/tests/meta/test_socket_deny_alive.py` | meta | none observed |
| `src/shared/packages/pyforge-warden/tests/meta/test_station_persona.py` | meta | none observed |
| `src/shared/packages/pyforge-warden/tests/meta/test_verdict_sole_ownership.py` | meta | none observed |
| `src/shared/packages/pyforge-warden/tests/test_smoke.py` | unit | none observed |
| `src/shared/packages/pyforge-warden/tests/unit/test_actuator.py` | unit | none observed |
| `src/shared/packages/pyforge-warden/tests/unit/test_cli_bypass.py` | unit | none observed |
| `src/shared/packages/pyforge-warden/tests/unit/test_cli_doctor.py` | unit | none observed |
| `src/shared/packages/pyforge-warden/tests/unit/test_cli_sbom.py` | unit | none observed |
| `src/shared/packages/pyforge-warden/tests/unit/test_config.py` | unit | none observed |
| `src/shared/packages/pyforge-warden/tests/unit/test_currency.py` | unit | none observed |
| `src/shared/packages/pyforge-warden/tests/unit/test_default_warden_without_checkmarx.py` | unit | none observed |
| `src/shared/packages/pyforge-warden/tests/unit/test_discovery_extract_cli.py` | unit | none observed |
| `src/shared/packages/pyforge-warden/tests/unit/test_eligibility.py` | unit | none observed |
| `src/shared/packages/pyforge-warden/tests/unit/test_eligibility_sbom.py` | unit | none observed |
| `src/shared/packages/pyforge-warden/tests/unit/test_engine_env_deptry.py` | unit | none observed |
| `src/shared/packages/pyforge-warden/tests/unit/test_environment_yml_extractor.py` | unit | none observed |
| `src/shared/packages/pyforge-warden/tests/unit/test_feeds.py` | unit | none observed |
| `src/shared/packages/pyforge-warden/tests/unit/test_hooks.py` | unit | none observed |
| `src/shared/packages/pyforge-warden/tests/unit/test_hygiene.py` | unit | none observed |
| `src/shared/packages/pyforge-warden/tests/unit/test_identity.py` | unit | none observed |
| `src/shared/packages/pyforge-warden/tests/unit/test_interfaces_and_null_engine.py` | unit | none observed |
| `src/shared/packages/pyforge-warden/tests/unit/test_inventory.py` | unit | none observed |
| `src/shared/packages/pyforge-warden/tests/unit/test_license.py` | unit | none observed |
| `src/shared/packages/pyforge-warden/tests/unit/test_lockfiles_extractor.py` | unit | none observed |
| `src/shared/packages/pyforge-warden/tests/unit/test_mapping.py` | unit | none observed |
| `src/shared/packages/pyforge-warden/tests/unit/test_meta_v0_extractor.py` | unit | none observed |
| `src/shared/packages/pyforge-warden/tests/unit/test_models.py` | unit | none observed |
| `src/shared/packages/pyforge-warden/tests/unit/test_osv_engine_exit_codes.py` | unit | none observed |
| `src/shared/packages/pyforge-warden/tests/unit/test_pixi_extractor.py` | unit | none observed |
| `src/shared/packages/pyforge-warden/tests/unit/test_recipe_v1_extractor.py` | unit | none observed |
| `src/shared/packages/pyforge-warden/tests/unit/test_refresh_endoflife_feed.py` | unit | none observed |
| `src/shared/packages/pyforge-warden/tests/unit/test_refresh_epss_feed.py` | unit | none observed |
| `src/shared/packages/pyforge-warden/tests/unit/test_refresh_kev_feed.py` | unit | none observed |
| `src/shared/packages/pyforge-warden/tests/unit/test_report.py` | unit | none observed |
| `src/shared/packages/pyforge-warden/tests/unit/test_sbom.py` | unit | none observed |
| `src/shared/packages/pyforge-warden/tests/unit/test_scanner_plugins.py` | unit | none observed |
| `src/shared/packages/pyforge-warden/tests/unit/test_sources.py` | unit | none observed |
| `src/shared/packages/pyforge-warden/tests/unit/test_verdict.py` | unit | none observed |
| `src/shared/packages/pyforge-warden/tests/unit/test_vuln.py` | unit | none observed |
| `src/shared/packages/pyforge-warden/tests/unit/test_waiver.py` | unit | none observed |

## Story Coverage Matrix

| Story | Title | Linked test files |
|-------|-------|-------------------|
| 1.1 | Frozen contract, verdict lattice & projection-safety (C0a) | none observed |
| 1.2 | Interfaces, null engine, regression harness & socket-deny (C0c) | none observed |
| 1.3 | deptry as the first engine (hygiene findings) | none observed |
| 1.4 | OSV-DB offline provisioning spike (decision + fixture DB) | none observed |
| 1.5 | osv-scanner as the second engine (vulnerability findings) | none observed |
| 1.6 | Severity gate + verdict composition end-to-end | none observed |
| 1.7 | Typed errors & the no-scan guard (the fail-closed net) | none observed |
| 1.8 | Human & machine report renderers | none observed |
| 1.9 | Manifest discovery, deterministic selection & the resolved scan set (FR1) | none observed |
| 2.1 | conda→pypi map + the ecosystem-identity predicate | none observed |
| 2.2 | Non-rendering extraction (common case) + differential-oracle | none observed |
| 2.3 | The full supported-construct matrix (ratcheted) | none observed |
| 2.4 | Honest split coverage + the indeterminate producer (C0b) | none observed |
| 2.5 | Name-level CVE tier + stale-DB + cross-ecosystem non-merge | none observed |
| 2.6 | Lockfile extraction — the locked-closure vuln hero path (split from 2.1, 2026... | none observed |
| 3.1 | Configurable policy (the ConfigLoader) | none observed |
| 3.2 | Auditable expiring waivers | none observed |
| 3.3 | Waiver expiry + warn-only adoption on-ramp | none observed |
| 4.1 | CycloneDX SBOM emission | none observed |
| 5.1 | Actionable diagnostics & safe-by-default posture | none observed |
| 5.2 | Fleet-scale validation + corpus/oracle maturation | none observed |
| 6.1 | The versioned `ComplianceReport` schema amendment | none observed |
| 6.2 | License axis producer + gate flags (Axis 3) | none observed |
| 6.3 | Currency axis producer + gate flags (Axis 4) | none observed |
| 6.4 | KEV feed provisioning, enrichment & the `--fail-on-kev` gate | none observed |
| 6.5 | Two-mode policy integration (unconfigured visibility + flag-activated gating) | none observed |
| 6.6 | Engine version-range pinning (the distribution gate) | none observed |
| 6.7 | EPSS feed + the `--min-epss` gate | none observed |
| 6.8 | Baseline & grandfathering (gate new findings only) | none observed |
| 6.9 | Fix-PR actuator (opt-in remediation PRs) | none observed |
| 6.10 | Amendment design spike — finding-ID families, verdict encoding, rung-discrimi... | none observed |
| 7.1 | SourceContract adapters + the identity API | none observed |
| 7.2 | The eligibility union carries its provenance | none observed |
| 7.3 | CycloneDX out, the corpus in | none observed |
| 8.1 | Upload runs the real engines, async | none observed |
| 8.2 | Results render with derived progress | none observed |
| 9.1 | Warden publishes the PR-gate hook book | none observed |
| 9.2 | Current scanners become optional plugins | none observed |
| 9.3 | Default Warden stays green without Checkmarx | none observed |
| 10.1 | SKF domain skill and BMAD persona for warden | none observed |
| 10.2 | First portal slice — start/get one audit | none observed |
| 11.1 | `bmad-os-review-pr` and `findings-triage` are warden-wielded advisory lenses | none observed |
| 11.2 | `tea-test-review` is a warden advisory finding | none observed |

## Quality Gates

| Gate | Target | Enforcement |
|------|--------|-------------|
| Unit coverage | ≥80% | Story 19.3 CI gate |
| Integration coverage | ≥70% | Story 19.3 CI gate |
| Forbidden placeholder token | zero occurrences | this generator (hard fail) |
| Idempotent regen | byte-identical on unchanged tree | FR-132 |
| Story-id coverage drift | every epic story id in matrix | `--check` (CAP-5 / Story 19.4) |

## Regeneration

```bash
python _bmad/scripts/bmad_tea_playwright.py --project pyforge-warden
python _bmad/scripts/bmad_tea_playwright.py --all
python _bmad/scripts/bmad_tea_playwright.py --project pyforge-warden --check
python _bmad/scripts/bmad_tea_playwright.py --all --check
```
