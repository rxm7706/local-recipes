---
title: "Test Architecture — pyforge-doctor"
type: test-architecture
generator: bmad_tea_playwright.py
generator_version: 2.1.0
status: generated
station: doctor
source_fingerprint: c9914e4b1af87b8e
story_count: 144
test_file_count: 93
coverage_target_unit: ">=80%"
coverage_target_integration: ">=70%"
---

# Test Architecture — PyForge Doctor

This document is **machine-generated** by `bmad_tea_playwright.py` (v2.1.0). Do not hand-edit; re-run the generator after epics or tests change.

## Executive Summary

- **Station:** `pyforge-doctor`
- **Stories parsed:** 144
- **Epics parsed:** 41
- **Test files inventoried:** 93 under `src/shared/packages/pyforge-doctor/tests/`
- **Frameworks:** pytest (unit/integration/meta) + Playwright where present
- **Coverage targets:** unit ≥80%, integration ≥70% (gated by Story 19.3)
- **Source fingerprint:** `c9914e4b1af87b8e`

## Risk Assessment

### High-risk epics

- Epic 1: Pre-flight Check (walking skeleton)
- Epic 11: Tracked deferred-work entries get periodically re-verified against live code

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
- Epic 24: The coverage gate ships outside every station it judges (spec-coverage-gate-independence CAP-1..3)
- Epic 25: One chain per station — the sprawl gate, the FR check, and a ledger that survives a rebase (spec-one-chain-per-station CAP-2, CAP-5, CAP-3(g))
- Epic 30: The documentation is right, and refreshing it is repeatable (spec-pyforge-doctor CAP-83, CAP-84)
- Epic 32: The coverage gate diffs against the remote-tracking ref (spec-coverage-gate-independence CAP-4)
- Epic 34: Every capability ships behind a flag — the rule, the gate outside every station, and the retrofit inventory (spec-feature-flag-governance CAP-1, CAP-2, CAP-7; CAP-4's gate clause)
- Epic 36: A fold is proven complete before its file moves, and the sibling check follows the archive (spec-one-chain-per-station CAP-11)
- Epic 41: Phases 4 and 5 of the deferral burn-down: doctor's medium and low deferrals

### Low-risk epics

- Epic 5: The verdict on the Marshal's own row
- Epic 6: Every verdict comes home (Charter §6, generalized)
- Epic 10: Doctor notices when BMAD-METHOD's own installed core falls behind upstream
- Epic 12: The fleet's own hygiene/verification tooling gets its documented sharp edges fixed
- Epic 18: Doctor owns its skill, persona, and one portal job
- Epic 20: Doctor reads the whole suite and guards the estate's two blind spots
- Epic 21: Realization-gate hygiene (fleet readiness 2026-09-09)
- Epic 22: General documentation stops contradicting itself, and stays that way (spec-general-docs-consistency CAP-1..6)
- Epic 23: Leftover docs fold into Diátaxis (spec-docs-shelf-alignment CAP-1..7)
- Epic 26: The map of what no agent can verify without a live proof (spec-pyforge-doctor CAP-77)
- Epic 27: A PR is judged at its merge-base, and a merge subject names its station (spec-pyforge-doctor CAP-78)
- Epic 28: A frontmatter reader that stops at the fence, not at the first dashes (spec-pyforge-doctor CAP-81)
- Epic 29: The sibling drift check records a human acknowledgement and knows where the sibling went (spec-pyforge-doctor CAP-82)
- Epic 31: Doctor names the refs it judges by their full refname (spec-pyforge-doctor CAP-85)
- Epic 33: A recommended follow-up review is carried, checked on every PR (spec-pyforge-doctor CAP-86)
- Epic 35: Capability-ledger's post-PIN check reads only live Specs (spec-pyforge-doctor CAP-87)
- Epic 37: The legacy intake-spec tier retires, and the intake inbox keeps only its README (spec-one-chain-per-station CAP-11)
- Epic 38: Doctor stops letting deferrals and dead checks pile up (spec-pyforge-doctor CAP-29, CAP-88, CAP-42, CAP-1)
- Epic 39: `pr-preflight` runs every step of the Detectors scripts lane (spec-pyforge-doctor CAP-42, CAP-43)
- Epic 40: Phase 2 of the deferral burn-down: doctor's high deferrals

## Test Inventory

| Relative path | Level | Linked stories |
|---------------|-------|----------------|
| `src/shared/packages/pyforge-doctor/tests/meta/test_atlas_sole_mcp_import.py` | meta | none observed |
| `src/shared/packages/pyforge-doctor/tests/meta/test_cli_bridge_sole_subprocess.py` | meta | none observed |
| `src/shared/packages/pyforge-doctor/tests/meta/test_coverage_gate_stays_outside_every_station.py` | meta | none observed |
| `src/shared/packages/pyforge-doctor/tests/meta/test_env_hygiene_no_execution.py` | meta | none observed |
| `src/shared/packages/pyforge-doctor/tests/meta/test_epics_status_tracks_the_ledger.py` | meta | none observed |
| `src/shared/packages/pyforge-doctor/tests/meta/test_flag_gate_stays_outside_every_station.py` | meta | none observed |
| `src/shared/packages/pyforge-doctor/tests/meta/test_hatchling_floor_agrees.py` | meta | none observed |
| `src/shared/packages/pyforge-doctor/tests/meta/test_no_warden_import.py` | meta | none observed |
| `src/shared/packages/pyforge-doctor/tests/meta/test_portal_fleet_pulse.py` | meta | none observed |
| `src/shared/packages/pyforge-doctor/tests/meta/test_preflight_mirrors_scripts_suite.py` | meta | none observed |
| `src/shared/packages/pyforge-doctor/tests/meta/test_prescribe_pure_function.py` | meta | none observed |
| `src/shared/packages/pyforge-doctor/tests/meta/test_read_only_guard.py` | meta | none observed |
| `src/shared/packages/pyforge-doctor/tests/meta/test_refs_are_full_refnames.py` | meta | none observed |
| `src/shared/packages/pyforge-doctor/tests/meta/test_score_pure_function.py` | meta | none observed |
| `src/shared/packages/pyforge-doctor/tests/meta/test_skf_domain_skill.py` | meta | none observed |
| `src/shared/packages/pyforge-doctor/tests/meta/test_source_independence.py` | meta | none observed |
| `src/shared/packages/pyforge-doctor/tests/meta/test_sources_warden_no_subprocess.py` | meta | none observed |
| `src/shared/packages/pyforge-doctor/tests/meta/test_station_persona.py` | meta | none observed |
| `src/shared/packages/pyforge-doctor/tests/meta/test_verdict_narrows_warden.py` | meta | none observed |
| `src/shared/packages/pyforge-doctor/tests/meta/test_verdict_sole_ownership.py` | meta | none observed |
| `src/shared/packages/pyforge-doctor/tests/unit/test_capability_ledger.py` | unit | none observed |
| `src/shared/packages/pyforge-doctor/tests/unit/test_check_speed_budget.py` | unit | none observed |
| `src/shared/packages/pyforge-doctor/tests/unit/test_checks_env_hygiene.py` | unit | none observed |
| `src/shared/packages/pyforge-doctor/tests/unit/test_checks_registry.py` | unit | none observed |
| `src/shared/packages/pyforge-doctor/tests/unit/test_cli_backlog_intake.py` | unit | none observed |
| `src/shared/packages/pyforge-doctor/tests/unit/test_cli_bridge.py` | unit | none observed |
| `src/shared/packages/pyforge-doctor/tests/unit/test_cli_check.py` | unit | none observed |
| `src/shared/packages/pyforge-doctor/tests/unit/test_cli_diagnose.py` | unit | none observed |
| `src/shared/packages/pyforge-doctor/tests/unit/test_cli_monitor.py` | unit | none observed |
| `src/shared/packages/pyforge-doctor/tests/unit/test_detector_incident_log.py` | unit | none observed |
| `src/shared/packages/pyforge-doctor/tests/unit/test_feed_status.py` | unit | none observed |
| `src/shared/packages/pyforge-doctor/tests/unit/test_flag_kill_switch.py` | unit | none observed |
| `src/shared/packages/pyforge-doctor/tests/unit/test_fleet_scan_currency_feeds.py` | unit | none observed |
| `src/shared/packages/pyforge-doctor/tests/unit/test_fleet_scan_pitch_roster.py` | unit | none observed |
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
| `src/shared/packages/pyforge-doctor/tests/unit/test_refs_full_refnames.py` | unit | none observed |
| `src/shared/packages/pyforge-doctor/tests/unit/test_score.py` | unit | none observed |
| `src/shared/packages/pyforge-doctor/tests/unit/test_sources_atlas.py` | unit | none observed |
| `src/shared/packages/pyforge-doctor/tests/unit/test_sources_atlas_watch_axes.py` | unit | none observed |
| `src/shared/packages/pyforge-doctor/tests/unit/test_sources_backlog_intake.py` | unit | none observed |
| `src/shared/packages/pyforge-doctor/tests/unit/test_sources_bmad_config.py` | unit | none observed |
| `src/shared/packages/pyforge-doctor/tests/unit/test_sources_bmad_method.py` | unit | none observed |
| `src/shared/packages/pyforge-doctor/tests/unit/test_sources_board.py` | unit | none observed |
| `src/shared/packages/pyforge-doctor/tests/unit/test_sources_board_chain_completeness.py` | unit | none observed |
| `src/shared/packages/pyforge-doctor/tests/unit/test_sources_board_chain_layers_audit.py` | unit | none observed |
| `src/shared/packages/pyforge-doctor/tests/unit/test_sources_board_check_layout.py` | unit | none observed |
| `src/shared/packages/pyforge-doctor/tests/unit/test_sources_board_dashboard_drift.py` | unit | none observed |
| `src/shared/packages/pyforge-doctor/tests/unit/test_sources_capability_effect_caller_reach.py` | unit | none observed |
| `src/shared/packages/pyforge-doctor/tests/unit/test_sources_capability_effect_verified.py` | unit | none observed |
| `src/shared/packages/pyforge-doctor/tests/unit/test_sources_chain.py` | unit | none observed |
| `src/shared/packages/pyforge-doctor/tests/unit/test_sources_chain_deferred_work.py` | unit | none observed |
| `src/shared/packages/pyforge-doctor/tests/unit/test_sources_chain_dream_chain.py` | unit | none observed |
| `src/shared/packages/pyforge-doctor/tests/unit/test_sources_chain_dreams_hygiene.py` | unit | none observed |
| `src/shared/packages/pyforge-doctor/tests/unit/test_sources_chain_due_for_verification.py` | unit | none observed |
| `src/shared/packages/pyforge-doctor/tests/unit/test_sources_chain_frontmatter_parse.py` | unit | none observed |
| `src/shared/packages/pyforge-doctor/tests/unit/test_sources_chain_source_spec_resolution.py` | unit | none observed |
| `src/shared/packages/pyforge-doctor/tests/unit/test_sources_chain_spec_surface.py` | unit | none observed |
| `src/shared/packages/pyforge-doctor/tests/unit/test_sources_deps_forward_dependency.py` | unit | none observed |
| `src/shared/packages/pyforge-doctor/tests/unit/test_sources_dispatch.py` | unit | none observed |
| `src/shared/packages/pyforge-doctor/tests/unit/test_sources_docs_currency.py` | unit | none observed |
| `src/shared/packages/pyforge-doctor/tests/unit/test_sources_docs_map_hygiene.py` | unit | none observed |
| `src/shared/packages/pyforge-doctor/tests/unit/test_sources_docs_shelf.py` | unit | none observed |
| `src/shared/packages/pyforge-doctor/tests/unit/test_sources_factory.py` | unit | none observed |
| `src/shared/packages/pyforge-doctor/tests/unit/test_sources_frozen_path.py` | unit | none observed |
| `src/shared/packages/pyforge-doctor/tests/unit/test_sources_general_docs_consistency.py` | unit | none observed |
| `src/shared/packages/pyforge-doctor/tests/unit/test_sources_honest_reads_41_2.py` | unit | 41.2 |
| `src/shared/packages/pyforge-doctor/tests/unit/test_sources_hygiene.py` | unit | none observed |
| `src/shared/packages/pyforge-doctor/tests/unit/test_sources_ledger.py` | unit | none observed |
| `src/shared/packages/pyforge-doctor/tests/unit/test_sources_ledger_direction.py` | unit | none observed |
| `src/shared/packages/pyforge-doctor/tests/unit/test_sources_live_proof_surfaces.py` | unit | none observed |
| `src/shared/packages/pyforge-doctor/tests/unit/test_sources_marshal_story_status.py` | unit | none observed |
| `src/shared/packages/pyforge-doctor/tests/unit/test_sources_one_chain.py` | unit | none observed |
| `src/shared/packages/pyforge-doctor/tests/unit/test_sources_one_chain_fold_complete.py` | unit | none observed |
| `src/shared/packages/pyforge-doctor/tests/unit/test_sources_pixi_currency.py` | unit | none observed |
| `src/shared/packages/pyforge-doctor/tests/unit/test_sources_platform_policy.py` | unit | none observed |
| `src/shared/packages/pyforge-doctor/tests/unit/test_sources_registry.py` | unit | none observed |
| `src/shared/packages/pyforge-doctor/tests/unit/test_sources_sibling_dreams.py` | unit | none observed |
| `src/shared/packages/pyforge-doctor/tests/unit/test_sources_status_body_consistency.py` | unit | none observed |
| `src/shared/packages/pyforge-doctor/tests/unit/test_sources_status_body_open_questions.py` | unit | none observed |
| `src/shared/packages/pyforge-doctor/tests/unit/test_sources_status_body_promissory.py` | unit | none observed |
| `src/shared/packages/pyforge-doctor/tests/unit/test_sources_status_body_status_comment.py` | unit | none observed |
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
| 6.12 | bmad-drift counts every pixi environment, table-form ones too | none observed |
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
| 21.1 | `DEFERRED_SPECS` stops reading as a live exemption when it is not one | none observed |
| 21.2 | A Spec with no `status:` line is a finding, not a silent exemption | none observed |
| 21.3 | `sibling-dreams-drift` joins on the key the two trees actually share | none observed |
| 21.4 | `CONSTITUTIVE` is derived from the roster, not hardcoded beside it | none observed |
| 21.5 | The deferred-work verifier resolves a project-relative `source_spec` from the... | none observed |
| 21.6 | `dreams-hygiene` reconciles every Dream file, and README:71 is enforced | none observed |
| 21.7 | The pixi candidate ledgers get their staleness check | none observed |
| 21.8 | Deferred-work intake refuses an entry that cites nothing checkable | none observed |
| 21.9 | A capability with no caller outside its own tests is a finding | none observed |
| 21.10 | A `verified:` line on a capability is read and rendered | none observed |
| 21.11 | The effect check renders beside `story-status-check` | none observed |
| 21.12 | A body that says "3 of 9" under `realized` is a finding | none observed |
| 21.13 | `open_questions: []` over a live memlog question is a finding | none observed |
| 21.14 | Promissory language under a terminal status is measured before it ships | none observed |
| 21.15 | A status comment that contradicts its own ledger is a finding | none observed |
| 21.16 | The status/body check renders where the operator already looks | none observed |
| 22.1 | The 2 identity contradictions are fixed at their source | none observed |
| 22.2 | The 4 cross-cutting decay findings are corrected | none observed |
| 22.3 | A repeatable Doctor detector catches this class of drift going forward | none observed |
| 22.4 | A Diátaxis-adapted information architecture is designed for the general-facin... | none observed |
| 22.5 | The Tutorials/Getting-Started and How-to-Guides quadrants are populated | none observed |
| 22.6 | README.md, CLAUDE.md, and AGENTS.md point cleanly into the reorganized structure | none observed |
| 23.1 | Entry points are indexes; one owner per fact | none observed |
| 23.2 | Fold the getting-started and air-gap cluster; stub the binders | none observed |
| 23.3 | Sunset docs/specs/ by frontmatter status | none observed |
| 23.4 | Empty the intake inbox per its own README | none observed |
| 23.5 | Archive citations for the five already-moved _bmad-output/ files | none observed |
| 23.6 | MAP names publish roots; do not mint an empty vizro/ tree | none observed |
| 23.7 | A new Doctor source flags leftover-shelf occupancy | none observed |
| 24.1 | The evaluator and the thresholds move out of marshal's package, together | none observed |
| 24.2 | An import-linter contract catches the class structurally | none observed |
| 24.3 | The surfaces are reconciled so no file is governed twice or not at all | none observed |
| 25.1 | A new Dream or Spec folder without a declared exemption is a finding | none observed |
| 25.2 | A product requirement minted after the rule date names its source capability | none observed |
| 25.3 | The ledger-regression verdict reads a re-key map, so a rebase moves done rows... | none observed |
| 26.1 | A touched live-proof-only surface gets an advisory Doctor finding naming it | none observed |
| 27.1 | A PR is judged at its merge-base, and a merge subject names its station | none observed |
| 27.2 | `ledger-direction` reads the station's rekey map | none observed |
| 27.3 | A station's legacy-template history stays attributed after its template changes | none observed |
| 27.5 | A bare-form merge is attributed by the paths its diff touches | none observed |
| 28.1 | A frontmatter reader that stops at the fence, not at the first dashes | none observed |
| 29.1 | A per-Dream acknowledgement silences exactly one sibling hash, and the siblin... | none observed |
| 30.1 | The map is enforced within its scope, the stubs are gone, and the new pages a... | none observed |
| 30.2 | docs/map.yaml is the registry, MAP.md is its render, and `docs-currency` reds... | none observed |
| 30.3 | The reference pages are generated — pixi tasks, station CLIs, detectors, skil... | none observed |
| 31.1 | Every Doctor source names the branch it reads by its full refname | none observed |
| 32.1 | The gate's base normalizer names the remote-tracking ref | none observed |
| 33.1 | The deferred-work source reds a done story whose recommended follow-up review... | none observed |
| 34.1 | The flag rule has a closed exemption list, a rule-date baseline and one block... | none observed |
| 34.2 | The flag gate ships in scripts, outside every station, and runs in detectors-ci | none observed |
| 34.3 | The flag gate reads the tree metadata — per-environment defaults and the 90-d... | none observed |
| 34.4 | Each station has a checked-in flag inventory of its runtime capabilities | none observed |
| 34.5 | The flag gate reds a landed flagged story whose test does not run both states | none observed |
| 35.1 | capability-ledger's post-PIN check reads only live Specs | none observed |
| 36.1 | A fold-complete check proves each archived Dream's body is in its station Dream | none observed |
| 36.2 | The sibling-drift check reads acknowledged Dreams under the archive | none observed |
| 37.1 | docs/specs and docs/intake empty, and the legacy tier's index and check retire | none observed |
| 38.1 | A `verified:` line written from now on cites what it read | none observed |
| 38.2 | `spec-surface` names a Spec surface glob that matches nothing | none observed |
| 38.3 | The fleet hygiene sweep runs with the other detectors, warn-only | none observed |
| 38.4 | `doctor check .` completes on the primary checkout | none observed |
| 38.5 | The detector-aggregate tests run where Doctor's run-deps are installed | none observed |
| 39.1 | `pr-preflight` runs the detector-aggregate tests where Doctor's run-deps are ... | none observed |
| 40.1 | Doctor executes no code from the judged tree, and an unresolved head or a fai... | none observed |
| 41.1 | The chain sources measure what they claim: spec-surface, dream-chain, the def... | none observed |
| 41.2 | The ledger, story-status and capability-effect sources degrade honestly, the ... | `src/shared/packages/pyforge-doctor/tests/unit/test_sources_honest_reads_41_2.py` |
| 41.3 | The board, factory, hygiene and status-body sources read frontmatter one way,... | none observed |
| 41.4 | The check CLI, the env and engines checks, the score and the bmad-method sour... | none observed |
| 41.5 | A new story reopens its done epic without reading as a ledger regression | none observed |
| 41.6 | Chain-completeness counts the one-chain fold's citation window again | none observed |

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
