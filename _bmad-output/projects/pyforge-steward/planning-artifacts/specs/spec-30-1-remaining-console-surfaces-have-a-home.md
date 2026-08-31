---
title: Remaining console surfaces have a home
type: feature
created: '2026-08-25'
status: done
updated: '2026-08-25'
baseline_revision: 00eac7961410a61c36fbb5d212bddf942f54fd39
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-unifying-strategy/console-parity-inventory.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/epics.md
warnings:
  - oversized
deferred: []
---

<intent-contract>

## Intent

**Problem:** The Marshal console still exists as a baked `data.js` blob. FR-7 cannot delete that path until every runtime-reproducible and mixed surface has a named Canopy home, or deletion drops a live view.

**Approach:** Encode the 23-surface inventory as a machine-checked map. Give each runtime-reproducible and mixed row a Lane 1 URL or station portal. Cache detector verdicts from a scheduled job with visible age. Keep editorial copy on Wagtail. Keep live run state and timing on the existing supervisor board.

## Boundaries & Constraints

**Always:** Physical writes under `_bmad-output/projects/pyforge-steward/` plus the Code Map. `BMAD_ACTIVE_PROJECT=pyforge-steward`. Homes are Lane 1 or `/stations/<name>/`. Detector page reads cached rows + age, never implies a per-request check. Editorial GET reads published Wagtail pages. Live run chip / in-flight / timing use `query_board` via `/runs/` only. Parent AD-2: no `import pyforge` under `src/platform/`. Tests fail if a runtime-reproducible or mixed inventory row has no named home.

**Block If:** Implementation would delete `pyforge.doctor.sources.fleet_scan`, pixi dashboard tasks, the dashboard workflow trigger, or `docs/dashboard/data.js`; or would start Story 30.2 inbound-ref sweep; or would require MinIO / a fifth PostgreSQL schema.

**Never:** Story 30.2. Kedro-Viz tree edits or deletion. `pyforge.*` under `src/platform/`. Filesystem scrape of `~/.bmad-loops`, tmux, or journals. Presenting detector subprocess output as request-time truth.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Parity map | Inventory of 14 runtime + 3 mixed | Each row has `home_kind` lane1 or portal and a path | Test fails on missing home |
| Directory | GET `/console/` | Lists named homes including health, editorial, runs | Empty map is a test failure, not a silent 200 |
| Detector cache | Scheduled refresh writes verdicts; GET `/console/health/` | Body shows cached state plus visible age | Empty cache shows `never`, not green |
| Editorial CMS | Published ConsoleEditorialPage | GET `/console/editorial/` includes the page body | Missing pages: empty list, not generate.py prose |
| Supervisor live | GET `/runs/` | Live/timing from supervisor only | Unreachable stays unavailable + age (21.5) |
| Generator kept | Repo after this story | `generate.py`, pixi dashboard tasks, `data.js` present | Fail test if they vanished |
| Host boundary | `src/platform/` tree | No `pyforge` import | Existing meta test stays green |

</intent-contract>

## Code Map

- `src/platform/platformapp/front_door/console_parity.py` — frozen 23 surfaces + `HOMES` + `require_parity_homes()`
- `src/platform/platformapp/front_door/models.py` — keep `HomePage`; add `DetectorVerdict`, `ConsoleEditorialPage`
- `src/platform/platformapp/front_door/migrations/0002_console_parity.py` — tables only
- `src/platform/platformapp/front_door/detector_jobs.py` — refresh cache via injectable runner; seed beat task
- `src/platform/platformapp/front_door/runtime_catalog.py` — request-time scans of tracked repo files (dreams, specs, ledgers)
- `src/platform/platformapp/front_door/views.py` — `/console/` directory, health, editorial, catalog pages; keep `runs_board`
- `src/platform/platformapp/front_door/urls.py` — console routes before Wagtail catch-all (already included from `config/urls.py`)
- `src/platform/platformapp/front_door/tasks.py` — Celery `refresh_detector_verdicts`
- `src/platform/platformapp/front_door/apps.py` — post_migrate seed of beat interval task
- `src/platform/platformapp/front_door/templates/front_door/` — console templates
- `src/shared/packages/django-{doctor,herald,steward,marshal}/.../home.html` — `data-console-home` markers
- `src/platform/tests/test_console_parity_homes.py` — I/O matrix
- Read-only: `pyforge.doctor.sources.fleet_scan`, `docs/dashboard/data.js`, `docs/dashboard/kedro-viz/**`, pixi dashboard tasks, `tests/meta/test_no_pyforge_import.py`, supervisor `query_board`

## Tasks & Acceptance

**Execution:**
- `console_parity.py` — 23 rows; require homes for runtime + mixed
- models + migration — detector cache + editorial page type
- detector_jobs + celery task + beat seed — scheduled cache
- views/urls/templates — Lane 1 homes
- portal home templates — named portal homes
- `test_console_parity_homes.py` — matrix + mapping-removal failure

**Acceptance Criteria:**
- Given the 23-surface inventory, when this story completes, then each runtime-reproducible and mixed surface has a named Canopy home
- Given detector verdicts, when the operator opens the health home, then they see a cached result and its age
- Given editorial program copy, when published in the CMS, then the editorial home shows it
- Given live run state and timing, when queried, then they come from the supervisor
- Given the generator and Kedro-Viz, when this story merges, then both still exist

## Design Notes

Inventory ids (23): runtime `dreams`, `specs`, `story_specs`, `campaigns`, `command_center`, `launch_readiness`, `fleet_progress_tracked`, `pitch`, `guild`, `backlog`, `open_work`, `archived`, `fleet_table`, `program_story_status`; mixed `fleet_chain_audit_badge`, `health_ci_overlay`, `in_build_realized_membership`; build-time `running_chip`, `inflight_card`, `fleet_live_overlay`, `detector_verdicts`, `editorial_blocks`, `journal_timing`. The committed-snapshot model is not a view and is not a row. Kedro-Viz is not a row.

## Spec Change Log

## Review Triage Log

### 2026-08-25 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 1: (high 0, medium 0, low 1)
- defer: 0
- reject: 0
- addressed_findings:
  - `[low]` `[patch]` Design Notes listed `last_shipped`/`snapshot_model`; code map uses `program_story_status` and omits snapshot as a non-view

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — expected: pass (station policy verify command; reconciled 2026-08-30 after policy drifted from this spec's original declaration).

## Auto Run Result

Status: done

**Summary:** Named Canopy homes for every runtime-reproducible and mixed console surface. Detector verdicts are a Celery beat job writing `detector_verdict` with visible age. Editorial is Wagtail. Live runs stay on `/runs/`. Generator and Kedro-Viz untouched.

**Verification:** 31 passed under platform-ci-test (`test_console_parity_homes.py`, `test_front_door_queries_supervisor.py`, `test_no_pyforge_import.py`).

