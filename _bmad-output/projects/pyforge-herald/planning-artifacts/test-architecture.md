---
title: "Test Architecture — pyforge-herald"
type: test-architecture
generator: bmad_tea_playwright.py
generator_version: 2.1.0
status: generated
station: herald
source_fingerprint: cc90de9ca00f0211
story_count: 125
test_file_count: 70
coverage_target_unit: ">=80%"
coverage_target_integration: ">=70%"
---

# Test Architecture — PyForge Herald

This document is **machine-generated** by `bmad_tea_playwright.py` (v2.1.0). Do not hand-edit; re-run the generator after epics or tests change.

## Executive Summary

- **Station:** `pyforge-herald`
- **Stories parsed:** 125
- **Epics parsed:** 35
- **Test files inventoried:** 70 under `src/shared/packages/pyforge-herald/tests/`
- **Frameworks:** pytest (unit/integration/meta) + Playwright where present
- **Coverage targets:** unit ≥80%, integration ≥70% (gated by Story 19.3)
- **Source fingerprint:** `cc90de9ca00f0211`

## Risk Assessment

### High-risk epics

- Epic 4: Watch — poll, backoff, halt
- Epic 6: Foundation — CLI architecture & shared infrastructure
- Epic 8: Moment 2 — progress visibility
- Epic 9: Moment 3 — success proclamation
- Epic 10: Moment 4 — operations notices
- Epic 11: Integration testing & automation reliability
- Epic 13: The live backend — a ship records itself
- Epic 19: Herald in effect (fleet readiness 2026-09-09)
- Epic 35: Phase 4+5 of the deferral burn-down: herald's open medium and low deferrals

### Medium-risk epics

- Epic 1: Foundation — package spine & transport
- Epic 2: Deck pull — prototype, marp, bundle
- Epic 3: Deck status & stale-mirror detection
- Epic 5: Export push-back
- Epic 12: Documentation & operator experience
- Epic 14: A deck is proven to look right
- Epic 15: Editable decks — the PowerPoint-native pipeline
- Epic 16: Exporter hook spec
- Epic 17: Herald owns its skill, persona, and one portal job
- Epic 18: Herald renders, announces and slides with the suite
- Epic 21: The whole deck family moves together (spec-deck-family-lockstep)
- Epic 22: The public Pages root is one dossier (spec-pyforge-pages)
- Epic 23: The Design sync loop — one command keeps every twin and its family true (spec-design-sync-loop)
- Epic 25: Herald runs from the Guild env (spec-pyforge-herald CAP-51)
- Epic 26: The dossier states the cutover's control plane (spec-python-foundry-cutover fnd:CAP-14)
- Epic 28: Each deck keeps one current version of each export (spec-pyforge-herald CAP-53)
- Epic 29: Each current export is also kept in object storage (spec-pyforge-herald CAP-54)
- Epic 30: A deck is readable in the browser from its HTML twin (spec-pyforge-herald CAP-55)
- Epic 32: A deck exports as a native, editable .pptx through pptxgenjs-plus (spec-pyforge-herald CAP-57)
- Epic 33: The genesis deck counts archived Dreams where they now live (spec-one-chain-per-station CAP-11)
- Epic 34: Herald cites the deck how-to, not the retiring intake stub (spec-one-chain-per-station CAP-11)

### Low-risk epics

- Epic 7: Foundation — web surface
- Epic 20: The deck family stays current (spec-deck-family-currency)
- Epic 24: What Epic 23's four landings deferred (spec-pyforge-herald CAP-48..50)
- Epic 27: The docs site matches BMAD-METHOD's pattern (spec-pyforge-herald CAP-52)
- Epic 31: The docs site deploys to a second host from the same artifact (spec-pyforge-herald CAP-56)

## Test Inventory

| Relative path | Level | Linked stories |
|---------------|-------|----------------|
| `src/shared/packages/pyforge-herald/tests/meta/test_deck_qa_pixi_task.py` | meta | none observed |
| `src/shared/packages/pyforge-herald/tests/meta/test_deck_registry_sections.py` | meta | none observed |
| `src/shared/packages/pyforge-herald/tests/meta/test_deck_store_import_boundary.py` | meta | none observed |
| `src/shared/packages/pyforge-herald/tests/meta/test_deck_sync_all_pixi_task.py` | meta | none observed |
| `src/shared/packages/pyforge-herald/tests/meta/test_deck_working_set.py` | meta | none observed |
| `src/shared/packages/pyforge-herald/tests/meta/test_docs_site.py` | meta | none observed |
| `src/shared/packages/pyforge-herald/tests/meta/test_portal_deck_status.py` | meta | none observed |
| `src/shared/packages/pyforge-herald/tests/meta/test_release_comms_routing.py` | meta | none observed |
| `src/shared/packages/pyforge-herald/tests/meta/test_skf_skill_and_persona.py` | meta | none observed |
| `src/shared/packages/pyforge-herald/tests/meta/test_slides_generator_routing.py` | meta | none observed |
| `src/shared/packages/pyforge-herald/tests/meta/test_twins_zero_origin.py` | meta | none observed |
| `src/shared/packages/pyforge-herald/tests/unit/test_agent_sdk_transport.py` | unit | none observed |
| `src/shared/packages/pyforge-herald/tests/unit/test_auth.py` | unit | none observed |
| `src/shared/packages/pyforge-herald/tests/unit/test_bridge.py` | unit | none observed |
| `src/shared/packages/pyforge-herald/tests/unit/test_claims.py` | unit | none observed |
| `src/shared/packages/pyforge-herald/tests/unit/test_cli_deck_qa.py` | unit | none observed |
| `src/shared/packages/pyforge-herald/tests/unit/test_cli_dispatch.py` | unit | none observed |
| `src/shared/packages/pyforge-herald/tests/unit/test_cli_epic13.py` | unit | none observed |
| `src/shared/packages/pyforge-herald/tests/unit/test_cli_epic6.py` | unit | none observed |
| `src/shared/packages/pyforge-herald/tests/unit/test_cli_notice_epic10.py` | unit | none observed |
| `src/shared/packages/pyforge-herald/tests/unit/test_cli_progress.py` | unit | none observed |
| `src/shared/packages/pyforge-herald/tests/unit/test_cli_pull.py` | unit | none observed |
| `src/shared/packages/pyforge-herald/tests/unit/test_cli_push.py` | unit | none observed |
| `src/shared/packages/pyforge-herald/tests/unit/test_cli_seed.py` | unit | none observed |
| `src/shared/packages/pyforge-herald/tests/unit/test_cli_status.py` | unit | none observed |
| `src/shared/packages/pyforge-herald/tests/unit/test_cli_success.py` | unit | none observed |
| `src/shared/packages/pyforge-herald/tests/unit/test_cli_sync_all.py` | unit | none observed |
| `src/shared/packages/pyforge-herald/tests/unit/test_cli_watch.py` | unit | none observed |
| `src/shared/packages/pyforge-herald/tests/unit/test_db.py` | unit | none observed |
| `src/shared/packages/pyforge-herald/tests/unit/test_deck_exports_handlers.py` | unit | none observed |
| `src/shared/packages/pyforge-herald/tests/unit/test_deck_pipeline.py` | unit | none observed |
| `src/shared/packages/pyforge-herald/tests/unit/test_deck_publish.py` | unit | none observed |
| `src/shared/packages/pyforge-herald/tests/unit/test_deck_publish_flag.py` | unit | none observed |
| `src/shared/packages/pyforge-herald/tests/unit/test_deck_publish_twins.py` | unit | none observed |
| `src/shared/packages/pyforge-herald/tests/unit/test_deck_qa.py` | unit | none observed |
| `src/shared/packages/pyforge-herald/tests/unit/test_deck_status.py` | unit | none observed |
| `src/shared/packages/pyforge-herald/tests/unit/test_deck_store.py` | unit | none observed |
| `src/shared/packages/pyforge-herald/tests/unit/test_deck_versions.py` | unit | none observed |
| `src/shared/packages/pyforge-herald/tests/unit/test_deck_viewer_publish_flag.py` | unit | none observed |
| `src/shared/packages/pyforge-herald/tests/unit/test_docs_site_shelf_loader.py` | unit | none observed |
| `src/shared/packages/pyforge-herald/tests/unit/test_docsite_build.py` | unit | none observed |
| `src/shared/packages/pyforge-herald/tests/unit/test_dossier_structure.py` | unit | none observed |
| `src/shared/packages/pyforge-herald/tests/unit/test_errors.py` | unit | none observed |
| `src/shared/packages/pyforge-herald/tests/unit/test_evidence.py` | unit | none observed |
| `src/shared/packages/pyforge-herald/tests/unit/test_export_plugins.py` | unit | none observed |
| `src/shared/packages/pyforge-herald/tests/unit/test_export_progress_snapshot.py` | unit | none observed |
| `src/shared/packages/pyforge-herald/tests/unit/test_export_web_snapshot.py` | unit | none observed |
| `src/shared/packages/pyforge-herald/tests/unit/test_integration_epic11.py` | unit | none observed |
| `src/shared/packages/pyforge-herald/tests/unit/test_live_design_spike.py` | unit | none observed |
| `src/shared/packages/pyforge-herald/tests/unit/test_locking.py` | unit | none observed |
| `src/shared/packages/pyforge-herald/tests/unit/test_mcp_transport.py` | unit | none observed |
| `src/shared/packages/pyforge-herald/tests/unit/test_notices.py` | unit | none observed |
| `src/shared/packages/pyforge-herald/tests/unit/test_performance_epic11.py` | unit | none observed |
| `src/shared/packages/pyforge-herald/tests/unit/test_pptx_pipeline.py` | unit | none observed |
| `src/shared/packages/pyforge-herald/tests/unit/test_progress.py` | unit | none observed |
| `src/shared/packages/pyforge-herald/tests/unit/test_registry.py` | unit | none observed |
| `src/shared/packages/pyforge-herald/tests/unit/test_reliability_epic11.py` | unit | none observed |
| `src/shared/packages/pyforge-herald/tests/unit/test_scheduler.py` | unit | none observed |
| `src/shared/packages/pyforge-herald/tests/unit/test_smoke.py` | unit | none observed |
| `src/shared/packages/pyforge-herald/tests/unit/test_stamps.py` | unit | none observed |
| `src/shared/packages/pyforge-herald/tests/unit/test_state.py` | unit | none observed |
| `src/shared/packages/pyforge-herald/tests/unit/test_station_api.py` | unit | none observed |
| `src/shared/packages/pyforge-herald/tests/unit/test_story_19_4_warden_deck.py` | unit | 19.4 |
| `src/shared/packages/pyforge-herald/tests/unit/test_sync_all.py` | unit | none observed |
| `src/shared/packages/pyforge-herald/tests/unit/test_transport_base.py` | unit | none observed |
| `src/shared/packages/pyforge-herald/tests/unit/test_twins.py` | unit | none observed |
| `src/shared/packages/pyforge-herald/tests/unit/test_watch.py` | unit | none observed |
| `src/shared/packages/pyforge-herald/tests/unit/test_webhook.py` | unit | none observed |
| `src/shared/packages/pyforge-herald/tests/unit/test_webhook_host.py` | unit | none observed |
| `src/shared/packages/pyforge-herald/tests/unit/test_webhook_live_smoke.py` | unit | none observed |

## Story Coverage Matrix

| Story | Title | Linked test files |
|-------|-------|-------------------|
| 1.1 | Package scaffold for pyforge herald | none observed |
| 1.2 | Transport port primary mcp client adapter the transport spike | none observed |
| 1.3 | Fallback transport adapter | none observed |
| 1.4 | Bridge core skeleton state errors determinism boundary | none observed |
| 1.5 | Registry module readme design project | none observed |
| 1.6 | Herald deck seed slug | none observed |
| 2.1 | Herald deck pull slug prototype pull with etag short circuit | none observed |
| 2.2 | Commit opt in | none observed |
| 2.3 | Marp source pull | none observed |
| 2.4 | Standalone bundle pull | none observed |
| 3.1 | Herald deck status slug | none observed |
| 3.2 | Stale hand mirror detection | none observed |
| 4.1 | Poll loop with quiescence debounce | none observed |
| 4.2 | Idle backoff | none observed |
| 4.3 | Halt on auth error | none observed |
| 5.1 | Push regenerated exports with etag guard | none observed |
| 5.2 | Conflict refusal on export push | none observed |
| 6.1 | Implement Herald CLI Dispatcher | none observed |
| 6.2 | Implement Shared Argument Conventions | none observed |
| 6.3 | Implement CLI Authentication & Authorization | none observed |
| 6.4 | Implement Evidence Link Validation Protocol (Shared Infrastructure) | none observed |
| 6.5 | CLI Help & First-Day Usability (Inline) | none observed |
| 7.1 | Design & Implement Web Layout (Header, Tabs, Sidebar, Responsive) | none observed |
| 7.2 | Implement Web Tooltips & Inline Help | none observed |
| 8.1 | Implement Progress Data Model & Database Schema | none observed |
| 8.2 | Implement On-Ship Webhook & Weekly Cron Automation | none observed |
| 8.3 | Implement Progress CLI (`herald progress` subcommand) | none observed |
| 8.4 | Implement Progress Web Tab | none observed |
| 9.1 | Implement Claim Data Model & Database Schema | none observed |
| 9.2 | Implement Auto-Extract & Operator Review Gate | none observed |
| 9.3 | Implement Success CLI | none observed |
| 9.4 | Implement Success Web Archive | none observed |
| 9.5 | Implement Evidence Validation (Sync + Async) | none observed |
| 10.1 | Notice Data Model & Archive Storage | none observed |
| 10.2 | Notice Authoring Workflow (CLI) | none observed |
| 10.3 | Notice Archive & Redirects | none observed |
| 10.4 | Notice CLI | none observed |
| 10.5 | Operations Web Tab | none observed |
| 10.6 | Notice Lifecycle | none observed |
| 11.1 | Integration Testing (CLI + Web + Automation) | none observed |
| 11.2 | Automation Reliability | none observed |
| 11.3 | Evidence Linking (Cross-Moment) | none observed |
| 11.4 | Performance Testing | none observed |
| 12.1 | CLI Runbooks & Troubleshooting | none observed |
| 12.2 | Web Surface UX Guide | none observed |
| 12.3 | Operator Runbook | none observed |
| 12.4 | Automation Troubleshooting Guide | none observed |
| 13.1 | The state layer survives a second writer | none observed |
| 13.2 | The serverless-intermediate decision, recorded | none observed |
| 13.3 | DB-backed storage behind the existing seam, with migrations | none observed |
| 13.4 | The webhook endpoint CI calls | none observed |
| 13.5 | The scheduler enforces what was displayed | none observed |
| 13.6 | A ship records itself, end to end | none observed |
| 14.1 | Gate report interface | none observed |
| 14.2 | Headless render gate | none observed |
| 14.3 | Image slot scan | none observed |
| 15.1 | Template-parse-then-fill produces a genuinely editable deck | none observed |
| 15.2 | Dense content renders as shapes that fit | none observed |
| 16.1 | Extract deck/export format plugins | none observed |
| 17.1 | SKF domain skill and BMAD persona for herald | none observed |
| 17.2 | First portal slice — deck status for one slug | none observed |
| 18.1 | The first station video renders from Herald's studio | none observed |
| 18.2 | Release comms go through `bmad-os-changelog` and `-social` | none observed |
| 18.3 | `slides-generator` is herald-wielded | none observed |
| 19.1 | The webhook routes move onto the station API seam | none observed |
| 19.2 | One real ship records itself against a persistent store | none observed |
| 19.3 | The deck-QA gate gets a caller | none observed |
| 19.4 | One real station deck renders through the pptx pipeline | `src/shared/packages/pyforge-herald/tests/unit/test_story_19_4_warden_deck.py` |
| 20.1 | The standard has one home and the deck spec points to it | none observed |
| 20.2 | `deck-facts` derives a per-deck fact ledger and checks a poster against it | none observed |
| 20.3 | PyForge Atlas poster rebuilt to the standard from its ledger | none observed |
| 20.4 | PyForge Doctor poster rebuilt to the standard from its ledger | none observed |
| 20.5 | PyForge Herald poster rebuilt to the standard from its ledger | none observed |
| 20.6 | PyForge Marshal poster rebuilt to the standard from its ledger | none observed |
| 20.7 | PyForge Mason poster rebuilt to the standard from its ledger | none observed |
| 20.8 | PyForge Scribe poster rebuilt to the standard from its ledger | none observed |
| 20.9 | PyForge Steward poster rebuilt to the standard from its ledger | none observed |
| 20.10 | Warden poster rebuilt to the standard from its ledger | none observed |
| 20.11 | PyForge Genesis poster rebuilt to the standard from its ledger | none observed |
| 20.12 | The Canopy poster re-derived and its Design project created | none observed |
| 20.13 | The bridge sees the family — `herald deck status` reports all ten linked | none observed |
| 20.14 | `deck-facts --refresh` rewrites stale marked literals from the ledger | none observed |
| 21.1 | `deck-trio` derives the Infographic head from the standalone | none observed |
| 21.2 | `deck-trio` derives the Infographic Deck from the standalone | none observed |
| 21.3 | `deck-facts` refreshes every marked surface, not just the poster | none observed |
| 21.4 | The ten decks' trios re-derived, refreshed and pushed | none observed |
| 21.5 | The exec summaries and the export set follow the same ledger | none observed |
| 21.6 | unity-data-stack rebuilt to the standard | none observed |
| 21.7 | wasm-analytics-stack rebuilt to the standard | none observed |
| 21.8 | deckcraft rebuilt to the standard | none observed |
| 21.9 | presenton-pixi-image rebuilt to the standard | none observed |
| 21.10 | The registry sees all fourteen decks | none observed |
| 21.11 | One deck proves the Design loop end to end | none observed |
| 21.12 | The transport speaks the `mcp` SDK it actually has pinned | none observed |
| 22.1 | The dossier is the source and Pages is a render | none observed |
| 23.1 | The account is enumerated and reconciled against the registry | none observed |
| 23.2 | Every presentation has a local twin; design systems are mirrored as libraries | none observed |
| 23.3 | The `.potx` path — template-filled PowerPoints, and every derived file stamped | none observed |
| 23.4 | PowerPoints push back, and every push proves itself | none observed |
| 23.5 | The family is browsable and downloadable on Pages | none observed |
| 23.6 | One command, idempotent, reported | none observed |
| 24.1 | The windowed Design read never loops on a stalled window | none observed |
| 24.2 | The docsite has a PR gate | none observed |
| 24.3 | The second `sync-all` run is proven unchanged on a real deck | none observed |
| 25.1 | The deck pipeline runs from the Guild env | none observed |
| 26.1 | The dossier reads the A→B cutover as control-plane fact | none observed |
| 27.1 | The docs shelf builds as a Starlight site in place | none observed |
| 27.2 | One Pages artifact carries the docs site, the dossier and the dashboard | none observed |
| 27.3 | The sidebar is generated from docs/map.yaml order | none observed |
| 27.4 | The docs validators gate every PR | none observed |
| 27.5 | pr-preflight runs the Pages build check only when docsite-check.yml's paths c... | none observed |
| 27.6 | The docs site builds from a clean checkout | none observed |
| 28.1 | Each deck keeps one current version of each export | none observed |
| 28.2 | A new export replaces the version it supersedes | none observed |
| 29.1 | herald deck publish puts each current export in the object store | none observed |
| 29.2 | The published exports are listed and streamed behind the herald role | none observed |
| 30.1 | A deck's HTML twins are self-contained and published | none observed |
| 30.2 | The herald portal shows a deck in the browser from its HTML twin | none observed |
| 31.1 | The Pages artifact builds for the host that deploys it | none observed |
| 31.2 | How to deploy the docs site to GitHub Enterprise Pages | none observed |
| 32.1 | A deck exports as a native, editable pptx through pptxgenjs-plus | none observed |
| 33.1 | deck-facts counts Dreams under the archive too | none observed |
| 34.1 | Herald cites the deck how-to, not the intake stub | none observed |
| 35.1 | The deck transport, sync-all, deck tooling and docs site close their open def... | none observed |
| 35.2 | The docs-site checks and the sync-proof row close on real evidence | none observed |

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
python _bmad/scripts/bmad_tea_playwright.py --project pyforge-herald
python _bmad/scripts/bmad_tea_playwright.py --all
python _bmad/scripts/bmad_tea_playwright.py --project pyforge-herald --check
python _bmad/scripts/bmad_tea_playwright.py --all --check
```
