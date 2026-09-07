---
title: "Test Architecture — pyforge-doctor"
type: test-architecture
generator: bmad_tea_playwright.py
generator_version: 2.1.0
status: generated
station: doctor
source_fingerprint: af3aa4c83a30e43f
story_count: 73
test_file_count: 61
coverage_target_unit: ">=80%"
coverage_target_integration: ">=70%"
---

# Test Architecture — PyForge Doctor

This document is **machine-generated** by `bmad_tea_playwright.py` (v2.1.0). Do not hand-edit; re-run the generator after epics or tests change.

## Executive Summary

- **Station:** `pyforge-doctor`
- **Stories parsed:** 73
- **Epics parsed:** 23
- **Test files inventoried:** 61 under `src/shared/packages/pyforge-doctor/tests/`
- **Frameworks:** pytest (unit/integration/meta) + Playwright where present
- **Coverage targets:** unit ≥80%, integration ≥70% (gated by Story 19.3)
- **Source fingerprint:** `af3aa4c83a30e43f`

## Risk Assessment

### High-risk epics

- Epic 1: Pre-flight Check (walking skeleton)
- Epic 11: Tracked deferred-work entries get periodically re-verified against live code
- Epic 1: Pre-flight Check (walking skeleton)

### Medium-risk epics

- Epic 2: Fleet Pulse (doctor monitor --fleet)
- Epic 3: Diagnose & Prescribe (doctor diagnose --prescribe)
- Epic 4: The frontier, decomposed (v1.x — added 2026-08-02)
- Epic 7: Deferred-work visibility
- Epic 8: The legacy deferred-work backlog comes home
- Epic 9: The hygiene sweep generalizes, and staleness surfaces itself
- Epic 13: Backlog-intake surfaces deferred entries during story drafting
- Epic 14: The bmad-suite's lag is as visible as the core's
- Epic 15: The suite pipeline's drift is ambient at every stage
- Epic 16: Sibling dreams directories don't drift silently
- Epic 17: Gather/prescribe hook spec
- Epic 19: Suite drift matches the channel catalog (registry-aware upstream)
- Epic 2: Fleet Pulse (doctor monitor --fleet)
- Epic 3: Diagnose & Prescribe (doctor diagnose --prescribe)

### Low-risk epics

- Epic 5: The verdict on the Marshal's own row
- Epic 6: Every verdict comes home (Charter §6, generalized)
- Epic 10: Doctor notices when BMAD-METHOD's own installed core falls behind upstream
- Epic 12: The fleet's own hygiene/verification tooling gets its documented sharp edges fixed
- Epic 18: Doctor owns its skill, persona, and one portal job
- Epic 20: Doctor reads the whole suite and guards the estate's two blind spots

## Test Inventory

| Relative path | Level | Linked stories |
|---------------|-------|----------------|
| `src/shared/packages/pyforge-doctor/tests/meta/test_atlas_sole_mcp_import.py` | meta | none observed |
| `src/shared/packages/pyforge-doctor/tests/meta/test_cli_bridge_sole_subprocess.py` | meta | none observed |
| `src/shared/packages/pyforge-doctor/tests/meta/test_env_hygiene_no_execution.py` | meta | none observed |
| `src/shared/packages/pyforge-doctor/tests/meta/test_no_warden_import.py` | meta | none observed |
| `src/shared/packages/pyforge-doctor/tests/meta/test_portal_fleet_pulse.py` | meta | none observed |
| `src/shared/packages/pyforge-doctor/tests/meta/test_prescribe_pure_function.py` | meta | none observed |
| `src/shared/packages/pyforge-doctor/tests/meta/test_read_only_guard.py` | meta | none observed |
| `src/shared/packages/pyforge-doctor/tests/meta/test_score_pure_function.py` | meta | none observed |
| `src/shared/packages/pyforge-doctor/tests/meta/test_skf_domain_skill.py` | meta | none observed |
| `src/shared/packages/pyforge-doctor/tests/meta/test_source_independence.py` | meta | none observed |
| `src/shared/packages/pyforge-doctor/tests/meta/test_sources_warden_no_subprocess.py` | meta | none observed |
| `src/shared/packages/pyforge-doctor/tests/meta/test_station_persona.py` | meta | none observed |
| `src/shared/packages/pyforge-doctor/tests/meta/test_verdict_narrows_warden.py` | meta | none observed |
| `src/shared/packages/pyforge-doctor/tests/meta/test_verdict_sole_ownership.py` | meta | none observed |
| `src/shared/packages/pyforge-doctor/tests/unit/test_check_speed_budget.py` | unit | none observed |
| `src/shared/packages/pyforge-doctor/tests/unit/test_checks_env_hygiene.py` | unit | none observed |
| `src/shared/packages/pyforge-doctor/tests/unit/test_checks_registry.py` | unit | none observed |
| `src/shared/packages/pyforge-doctor/tests/unit/test_cli_backlog_intake.py` | unit | none observed |
| `src/shared/packages/pyforge-doctor/tests/unit/test_cli_bridge.py` | unit | none observed |
| `src/shared/packages/pyforge-doctor/tests/unit/test_cli_check.py` | unit | none observed |
| `src/shared/packages/pyforge-doctor/tests/unit/test_cli_diagnose.py` | unit | none observed |
| `src/shared/packages/pyforge-doctor/tests/unit/test_cli_monitor.py` | unit | none observed |
| `src/shared/packages/pyforge-doctor/tests/unit/test_detector_incident_log.py` | unit | none observed |
| `src/shared/packages/pyforge-doctor/tests/unit/test_fleet_scan_currency_feeds.py` | unit | none observed |
| `src/shared/packages/pyforge-doctor/tests/unit/test_fleet_surface.py` | unit | none observed |
| `src/shared/packages/pyforge-doctor/tests/unit/test_hooks_plugins.py` | unit | none observed |
| `src/shared/packages/pyforge-doctor/tests/unit/test_hygiene_definitions.py` | unit | none observed |
| `src/shared/packages/pyforge-doctor/tests/unit/test_landing_evidence_conformance.py` | unit | none observed |
| `src/shared/packages/pyforge-doctor/tests/unit/test_main_stub.py` | unit | none observed |
| `src/shared/packages/pyforge-doctor/tests/unit/test_models.py` | unit | none observed |
| `src/shared/packages/pyforge-doctor/tests/unit/test_prescribe_partition.py` | unit | none observed |
| `src/shared/packages/pyforge-doctor/tests/unit/test_prescribe_rank.py` | unit | none observed |
| `src/shared/packages/pyforge-doctor/tests/unit/test_prescribe_root_cause.py` | unit | none observed |
| `src/shared/packages/pyforge-doctor/tests/unit/test_prescribe_safe_upgrade.py` | unit | none observed |
| `src/shared/packages/pyforge-doctor/tests/unit/test_score.py` | unit | none observed |
| `src/shared/packages/pyforge-doctor/tests/unit/test_sources_atlas.py` | unit | none observed |
| `src/shared/packages/pyforge-doctor/tests/unit/test_sources_atlas_watch_axes.py` | unit | none observed |
| `src/shared/packages/pyforge-doctor/tests/unit/test_sources_backlog_intake.py` | unit | none observed |
| `src/shared/packages/pyforge-doctor/tests/unit/test_sources_bmad_method.py` | unit | none observed |
| `src/shared/packages/pyforge-doctor/tests/unit/test_sources_board_chain_completeness.py` | unit | none observed |
| `src/shared/packages/pyforge-doctor/tests/unit/test_sources_board_chain_layers_audit.py` | unit | none observed |
| `src/shared/packages/pyforge-doctor/tests/unit/test_sources_board_check_layout.py` | unit | none observed |
| `src/shared/packages/pyforge-doctor/tests/unit/test_sources_board_dashboard_drift.py` | unit | none observed |
| `src/shared/packages/pyforge-doctor/tests/unit/test_sources_chain_deferred_work.py` | unit | none observed |
| `src/shared/packages/pyforge-doctor/tests/unit/test_sources_chain_dream_chain.py` | unit | none observed |
| `src/shared/packages/pyforge-doctor/tests/unit/test_sources_chain_dreams_hygiene.py` | unit | none observed |
| `src/shared/packages/pyforge-doctor/tests/unit/test_sources_chain_due_for_verification.py` | unit | none observed |
| `src/shared/packages/pyforge-doctor/tests/unit/test_sources_chain_spec_surface.py` | unit | none observed |
| `src/shared/packages/pyforge-doctor/tests/unit/test_sources_deps_forward_dependency.py` | unit | none observed |
| `src/shared/packages/pyforge-doctor/tests/unit/test_sources_dispatch.py` | unit | none observed |
| `src/shared/packages/pyforge-doctor/tests/unit/test_sources_factory.py` | unit | none observed |
| `src/shared/packages/pyforge-doctor/tests/unit/test_sources_hygiene.py` | unit | none observed |
| `src/shared/packages/pyforge-doctor/tests/unit/test_sources_ledger.py` | unit | none observed |
| `src/shared/packages/pyforge-doctor/tests/unit/test_sources_ledger_direction.py` | unit | none observed |
| `src/shared/packages/pyforge-doctor/tests/unit/test_sources_marshal_story_status.py` | unit | none observed |
| `src/shared/packages/pyforge-doctor/tests/unit/test_sources_platform_policy.py` | unit | none observed |
| `src/shared/packages/pyforge-doctor/tests/unit/test_sources_registry.py` | unit | none observed |
| `src/shared/packages/pyforge-doctor/tests/unit/test_sources_sibling_dreams.py` | unit | none observed |
| `src/shared/packages/pyforge-doctor/tests/unit/test_sources_warden.py` | unit | none observed |
| `src/shared/packages/pyforge-doctor/tests/unit/test_testing_kit_import.py` | unit | none observed |
| `src/shared/packages/pyforge-doctor/tests/unit/test_verdict.py` | unit | none observed |

## Story Coverage Matrix

| Story | Title | Linked test files |
|-------|-------|-------------------|
| 1.1 | Package scaffold, frozen Finding/DoctorReport contract & exit-code module | none observed |
| 1.2 | Wrap warden's engine-availability self-check (FR-1) | none observed |
| 1.3 | Tri-state, individually addressable checks (FR-2) | none observed |
| 1.4 | Credential/environment-hygiene check (FR-3) | none observed |
| 1.5 | `doctor check` CLI wiring, `--json`, and the speed budget (FR-9, NFR-4) | none observed |
| 2.1 | Atlas gather filter — staleness axis, MCP-first with CLI fallback (FR-5, AD-6) | none observed |
| 2.2 | cve and abandonment watch axes (FR-4) | none observed |
| 2.3 | `doctor monitor --fleet` CLI wiring, default axis set, `--json` (FR-9) | none observed |
| 3.1 | Partition findings by actionability (FR-6, AD-4) | none observed |
| 3.2 | Rank the actionable partition (FR-7, AD-4) | none observed |
| 3.3 | Root-cause naming (FR-8) | none observed |
| 3.4 | `doctor diagnose --target … --prescribe` CLI wiring, `--json` (FR-9) | none observed |
| 4.1 | Health scoring (FR-10) | none observed |
| 4.2 | Persistent fleet-health surface (FR-11) | none observed |
| 4.3 | Adoption-tracking watch axis (FR-12) | none observed |
| 4.4 | Safe upgrade-path recommendation (FR-13) | none observed |
| 5.1 | Marshal-durability source, independent by construction | none observed |
| 5.2 | Render the verdict through a `doctor` verb | none observed |
| 6.1 | Profile `doctor check` and bring it inside its budget | none observed |
| 6.2 | A source registry Doctor owns | none observed |
| 6.3 | The repo/runtime split survives the move | none observed |
| 6.4 | The ledger verdicts come home | none observed |
| 6.5 | The board verdicts come home | none observed |
| 6.6 | The chain verdicts come home | none observed |
| 6.7 | `forward_dependency` comes home, and the harness coupling is decided | none observed |
| 6.8 | `bmad_drift` comes home without breaking the board | none observed |
| 6.9 | The `scripts/` shims retire | none observed |
| 6.10 | Independence is structural, for every source | none observed |
| 6.11 | The classifier recognizes a spike report *(added 2026-08-11 — FR-16)* | none observed |
| 7.1 | The emitter mints identity at defer time | none observed |
| 7.2 | Grandfather the 470 at a dated cut-off | none observed |
| 7.3 | The detector sees anonymous Tier-3 entries | none observed |
| 7.4 | One severity, both sides | none observed |
| 8.1 | The parser reads every legacy Tier-3 shape | none observed |
| 8.2 | Minting picks the next free suffix per station convention | none observed |
| 8.3 | The fix mode promotes the backlog and refuses on collision | none observed |
| 8.4 | The baseline re-stamps so a second run is a no-op | none observed |
| 8.5 | The detector recognizes content that already reached the ledger by another path | none observed |
| 8.6 | DW-FU-8-4 closes — the collision-abort redesign, plus the parsing gap it surf... | none observed |
| 8.7 | The promoter learns to copy already-identified-but-untracked entries too | none observed |
| 9.1 | The five hygiene finding classes get testable definitions | none observed |
| 9.2 | The sweep runs against all eight stations | none observed |
| 9.3 | Hygiene findings report and never mutate | none observed |
| 9.4 | Loop-home staleness surfaces in the ATTENTION block | none observed |
| 10.1 | The declared floor and the installed core are compared and reported | none observed |
| 10.2 | The installed core is compared against the latest upstream release | none observed |
| 10.3 | The drift surfaces ambiently, never gates | none observed |
| 11.1 | Due-for-verification entries are selected, per project | none observed |
| 11.2 | Churn-based cost filtering skips entries whose code has not moved | none observed |
| 11.3 | Mechanically-checkable claims are verified without an agent | none observed |
| 11.4 | Judgment-requiring entries get an evidence-grounded verdict | none observed |
| 11.5 | Verification reaches across project boundaries | none observed |
| 11.6 | Near-duplicate entries surface as one defect class | none observed |
| 11.7 | Verification staleness surfaces in the ambient fleet report | none observed |
| 12.1 | The hygiene/verification catalog stays a maintained, current artifact | none observed |
| 12.2 | The exemplar standard conformance table is refreshed and re-verified | none observed |
| 12.3 | Chain completeness parses capability ids, not a bare substring match | none observed |
| 12.4 | Dream chain gap count surfaces in the ambient ATTENTION block | none observed |
| 12.5 | The spec surface baseline write race is closed | none observed |
| 13.1 | A drafting session surfaces matching deferred-work entries for an epic | none observed |
| 14.1 | The bmad-suite is compared against upstream, derived not declared | none observed |
| 15.1 | GitHub releases unblind the npm-invisible packages | none observed |
| 15.2 | Channel and recipe staleness are ambient findings | none observed |
| 16.1 | The shared-title diff is an ambient finding | none observed |
| 17.1 | Extract gather/prescribe source plugins | none observed |
| 18.1 | SKF domain skill and BMAD persona for doctor | none observed |
| 18.2 | First portal slice — last fleet pulse | none observed |
| 19.1 | The suite watched set matches the channel catalog and upstream follows recipe... | none observed |
| 20.1 | Suite drift maps every active member, derived from the roster | none observed |
| 20.2 | The render-HALT class has a detector | none observed |
| 20.3 | `frozen-path-changed` exists | none observed |
| 20.4 | `bmad-os-root-cause-analysis` is doctor-wielded | none observed |
| 20.5 | The version-drift Spec's open questions are written back | none observed |

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
python _bmad/scripts/bmad_tea_playwright.py --project pyforge-doctor
python _bmad/scripts/bmad_tea_playwright.py --all
python _bmad/scripts/bmad_tea_playwright.py --project pyforge-doctor --check
python _bmad/scripts/bmad_tea_playwright.py --all --check
```
