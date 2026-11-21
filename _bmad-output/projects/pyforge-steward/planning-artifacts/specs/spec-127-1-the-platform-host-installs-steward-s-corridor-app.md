---
title: '127.1: The platform host installs steward''s corridor app'
type: 'feature'
created: '2026-11-21'
status: 'done'
story: 127-1-the-platform-host-installs-steward-s-corridor-app
spec: spec-pyforge-steward
difficulty: 'easy'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
flag-exempt: detector-or-gate   # tests, a gate's own module and the scripts a gate runs; a gated gate is a silent green (roster list)
surface:
  - 'src/shared/packages/django-steward/**'
  - 'src/platform/config/settings/base.py'
  - 'src/platform/db/**'
  - 'src/platform/tests/**'
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/SPEC.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/deferred-work-ledger.md
  - docs/dreams/pyforge-steward.md
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** No Django project installs `pyforge.steward.dashboard`, so the corridor's tables exist in no shared database; `src/platform/config/settings/base.py` installs `django_steward_portal`, not the app that owns the corridor models.

**Approach:** The `django-steward` portal package declares the station apps the host installs, and the platform's settings add every portal's declared apps by name.

Ledger key: `127-1-the-platform-host-installs-steward-s-corridor-app`.

### Living CAP citations

- spec-pyforge-steward CAP-139, CAP-141 and CAP-143 (realized, no text change); no FR (the PRD absorbed CAP-141..145 with no requirement of its own); no AD moves.

## Boundaries & Constraints

**Always:**
- Read every verdict from its exit code, never through a pipe.
- Reach station code from the platform only through a portal package or `pyforge.core.station_port`.

**Never:**
- Never import `pyforge.*` from `src/platform/`, move a PostgreSQL or driver pin, or hand-edit a `SPEC.md`, a generated page or `sprint-status-ledger.yaml`.

## Acceptance Criteria

**Given** no Django project installs `pyforge.steward.dashboard`, so the corridor's tables exist in no shared database; `src/platform/config/settings/base.py` installs `django_steward_portal`, not the app that owns the corridor models
**When** the `django-steward` portal package declares the station apps the host installs, and the platform's settings add every portal's declared apps by name
**Then** `pyforge.steward.dashboard` is in the platform's `INSTALLED_APPS` and its eight migrations are in the platform's migration plan; `src/platform/` still imports no `pyforge.*`; a portal that declares nothing changes nothing
**And** the platform's own suite and steward's suite pass

- **AC1 — The story's own check passes.** Expected: exit 0.

  ```bash
  pixi run --frozen -e pyforge-steward pyforge-steward-test && pixi run --frozen -e pyforge-guild platform-ci-local -- --test
  ```

</intent-contract>

## Binding

- Capabilities: spec-pyforge-steward CAP-139, CAP-141 and CAP-143 (realized, no text change); no FR (the PRD absorbed CAP-141..145 with no requirement of its own); no AD moves.
- Dream: `docs/dreams/pyforge-steward.md` § *Realization log*, the 2026-11-21 entry; operator ruling of 2026-11-21 on `DW-steward-126-3-1`: "Platform host".
- Epic: Epic 127, minted with this story.
- Ledger key: `127-1-the-platform-host-installs-steward-s-corridor-app` (`done`).
- Surface: `marshal-policy.toml` `[epic_surfaces]."127"`.

## Verification

**Commands:** the Acceptance Criteria above, each read from its exit code.

## Spec Change Log

- 2026-11-21: minted from the station Dream's 2026-11-21 entry and the operator ruling of 2026-11-21 on `DW-steward-126-3-1`: "Platform host".
- 2026-11-21 (later): done on branch `corridor-platform-host-2026-11-21`; checked against PostgreSQL 17.11 on macOS (migrate, a real Liquibase update, every corridor duty in `-e platform-dev`).
