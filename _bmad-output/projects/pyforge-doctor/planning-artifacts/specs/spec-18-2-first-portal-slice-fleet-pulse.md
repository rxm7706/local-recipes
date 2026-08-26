---
title: First portal slice — last fleet pulse
type: feature
created: '2026-08-25'
status: done
updated: '2026-08-26'
baseline_revision: c3f75232a15bb3c28730c546e8f955cda59054df
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-doctor/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/change-history/sprint-change-proposal-2026-08-25-station-skill-portal.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-29-1-skf-domain-skills-from-station-packages.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-29-2-personas-act-only-through-grammar-and-mcp.md
warnings: []
deferred:
  - summary: >-
      Existing doctor check 5s budget test flakes on cold worktree starts
      and is not caused by this portal slice.
    evidence: |-
      Full suite 1287 passed + 1 skipped + 1 failed on
      test_doctor_check_completes_within_the_five_second_budget (7.8s / 15.9s).
      Story 18.1 recorded the same flake. New 18.2 tests 7/7 passed.
    location: >-
      src/shared/packages/pyforge-doctor/tests/unit/test_check_speed_budget.py
    severity: low
---

<intent-contract>

## Intent

**Problem:** Empty /stations/doctor/ does not show monitor output.

**Approach:** Show last doctor monitor --fleet summary via PortalClient only.

## Boundaries & Constraints

**Always:** Write artifacts under `_bmad-output/projects/pyforge-doctor/planning-artifacts/` literally. `BMAD_ACTIVE_PROJECT=pyforge-doctor` only — never `scripts/bmad-switch`. Ledger key `18-2-first-portal-slice-fleet-pulse`. Authenticated doctor-role GET `/stations/doctor/` renders the last `monitor --fleet` summary after `PortalClient.emit`. Findings stay advisory.

**Block If:** A change would replace `conda-forge-expert`, add `pyforge.*` under `src/platform/`, or start the paired Wave story this spec does not own.

**Never:** Second PR gate. Raw HTTP. Chrome copy. `import pyforge` / `from pyforge` in django-doctor or `src/platform/`. Live gather-on-GET of `doctor monitor`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Authenticated pulse | doctor-role session; last surface JSON present | `/stations/doctor/` 200; pulse summary counts render; PortalClient.emit used | No error expected |
| Empty last pulse | doctor-role session; no surface file or cache | 200; empty-state copy; still advisory | No error expected |
| Wrong role | warden-only session | 403; no pulse body | Forbidden |
| Portal client-only | django-doctor Python tree | No httpx/requests/urllib.request/http.client; no pyforge.* import; emit via PortalClient | Test fails on offenders |
| Host import gate | `git diff origin/main -- src/platform` | No `import pyforge` / `from pyforge` | Test fails on offenders |

</intent-contract>

## Code Map

- `src/shared/packages/django-doctor/src/django_doctor_portal/views.py` -- `chrome_home`; keep `@require_station_role("doctor")`; pass pulse context
- `src/shared/packages/django-doctor/src/django_doctor_portal/pulse.py` -- emit via `django_pyforge.assertion.client.PortalClient`, verify in-process, load last summary JSON (settings path `DOCTOR_FLEET_SURFACE_PATH` or cache). Do not import `pyforge.*`
- `src/shared/packages/django-doctor/src/django_doctor_portal/templates/doctor_portal/home.html` -- extend `django_pyforge/base.html`; keep `id="doctor-body"`; add `#doctor-fleet-pulse` advisory summary
- `src/shared/packages/django-pyforge/src/django_pyforge/assertion/client.py` -- read-only; `PortalClient.emit` only signs
- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/fleet_surface.py` -- read-only; summary shape `{ok,warn,fail,total}`
- `src/platform/tests/test_station_portal_shells.py` -- read-only host gates (no pyforge import, no raw HTTP, eight-station GET)
- `src/shared/packages/pyforge-doctor/tests/meta/test_portal_fleet_pulse.py` -- station-owned AC tests

## Tasks & Acceptance

**Execution:**
- `src/shared/packages/django-doctor/src/django_doctor_portal/pulse.py` -- last-pulse loader gated by PortalClient.emit -- only sanctioned reach
- `src/shared/packages/django-doctor/src/django_doctor_portal/views.py` -- render pulse on chrome_home -- operator job
- `src/shared/packages/django-doctor/src/django_doctor_portal/templates/doctor_portal/home.html` -- advisory HTMX pulse block -- no chrome copy
- `src/shared/packages/pyforge-doctor/tests/meta/test_portal_fleet_pulse.py` -- fail if ACs violated -- station-owned oracle
- `_bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-18-2-first-portal-slice-fleet-pulse.md` -- keep tracked spec current

**Acceptance Criteria:**
- Given an authenticated doctor-role session, when the operator opens /stations/doctor/, then the pulse summary renders via PortalClient only.
- Given src/platform/, when scanned, then no raw HTTP, no pyforge.* import, no chrome copy.

## Design Notes

Bind to epics.md Story 18.2 and the 2026-08-25 station-skill-portal SCP. PortalClient signs only; django-doctor must not open HTTP or import `pyforge.doctor`. Last pulse is a stored `fleet_surface` document (or empty). Do not run `doctor monitor` on GET.

## Spec Change Log

- 2026-08-25: drafted from epics.md for fleet drain preflight
- 2026-08-26: planned — Code Map and I/O matrix for PortalClient-gated last pulse

## Review Triage Log

### 2026-08-26 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 2: (high 0, medium 1, low 1)
- defer: 1: (high 0, medium 0, low 1)
- reject: 8
- addressed_findings:
  - `[medium]` `[patch]` `last_fleet_pulse` now treats `AssertionRefusedError` as empty advisory pulse so missing host keys do not 500 `/stations/doctor/`
  - `[low]` `[patch]` template summary counts use `|default:0`

## Auto Run Result

Status: done

Summary: `/stations/doctor/` renders the last `doctor monitor --fleet` summary after `PortalClient.emit`. Empty last-pulse is an advisory empty state. django-doctor does not open HTTP or import `pyforge.*`. No chrome copy. Findings stay advisory.

Files:
- `src/shared/packages/django-doctor/src/django_doctor_portal/pulse.py` — PortalClient-gated last-pulse load
- `src/shared/packages/django-doctor/src/django_doctor_portal/pulse_document.py` — pure summary projection
- `src/shared/packages/django-doctor/src/django_doctor_portal/views.py` — chrome_home passes pulse
- `src/shared/packages/django-doctor/src/django_doctor_portal/templates/doctor_portal/home.html` — `#doctor-fleet-pulse`
- `src/shared/packages/pyforge-doctor/tests/meta/test_portal_fleet_pulse.py` — station AC tests
- `planning-artifacts/specs/spec-18-2-….md` — tracked story spec

Review: 2 patches applied (1 medium, 1 low; follow-up score 4 → false). 1 deferred (check-speed flake). 8 rejected.

Verification: 7/7 new meta tests passed. Full doctor suite 1287 passed + 1 skipped; pre-existing 5s `doctor check` budget flake failed (same as 18.1). `git diff origin/main -- src/platform` empty of `pyforge` imports.

Residual: last pulse is a stored surface/cache document (`DOCTOR_FLEET_SURFACE_PATH`), not a live gather. Host eight-station GET still depends on assertion keys in test settings.

## Verification

**Commands:**
- `pixi run -e pyforge-doctor pyforge-doctor-test` -- expected: new tests pass
- `git diff origin/main -- src/platform` -- expected: no `import pyforge` / `from pyforge`
