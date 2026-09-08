---
title: "Test Architecture — pyforge-herald"
type: test-architecture
generator: bmad_tea_playwright.py
generator_version: 2.1.0
status: generated
station: herald
source_fingerprint: d42594ee98f152e7
story_count: 64
test_file_count: 47
coverage_target_unit: ">=80%"
coverage_target_integration: ">=70%"
---

# Test Architecture — PyForge Herald

This document is **machine-generated** by `bmad_tea_playwright.py` (v2.1.0). Do not hand-edit; re-run the generator after epics or tests change.

## Executive Summary

- **Station:** `pyforge-herald`
- **Stories parsed:** 64
- **Epics parsed:** 18
- **Test files inventoried:** 47 under `src/shared/packages/pyforge-herald/tests/`
- **Frameworks:** pytest (unit/integration/meta) + Playwright where present
- **Coverage targets:** unit ≥80%, integration ≥70% (gated by Story 19.3)
- **Source fingerprint:** `d42594ee98f152e7`

## Risk Assessment

### High-risk epics

- Epic 4: Watch — poll, backoff, halt
- Epic 6: Foundation — CLI architecture & shared infrastructure
- Epic 8: Moment 2 — progress visibility
- Epic 9: Moment 3 — success proclamation
- Epic 10: Moment 4 — operations notices
- Epic 11: Integration testing & automation reliability
- Epic 13: The live backend — a ship records itself

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

### Low-risk epics

- Epic 7: Foundation — web surface

## Test Inventory

| Relative path | Level | Linked stories |
|---------------|-------|----------------|
| `src/shared/packages/pyforge-herald/tests/meta/test_portal_deck_status.py` | meta | none observed |
| `src/shared/packages/pyforge-herald/tests/meta/test_release_comms_routing.py` | meta | none observed |
| `src/shared/packages/pyforge-herald/tests/meta/test_skf_skill_and_persona.py` | meta | none observed |
| `src/shared/packages/pyforge-herald/tests/meta/test_slides_generator_routing.py` | meta | none observed |
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
| `src/shared/packages/pyforge-herald/tests/unit/test_cli_watch.py` | unit | none observed |
| `src/shared/packages/pyforge-herald/tests/unit/test_db.py` | unit | none observed |
| `src/shared/packages/pyforge-herald/tests/unit/test_deck_pipeline.py` | unit | none observed |
| `src/shared/packages/pyforge-herald/tests/unit/test_deck_qa.py` | unit | none observed |
| `src/shared/packages/pyforge-herald/tests/unit/test_deck_status.py` | unit | none observed |
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
| `src/shared/packages/pyforge-herald/tests/unit/test_state.py` | unit | none observed |
| `src/shared/packages/pyforge-herald/tests/unit/test_transport_base.py` | unit | none observed |
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
