---
spec: suite-scaffold-and-mybmad-sidecar
status: ready
created: "2026-09-13"
updated: "2026-09-13"
owner-dream: docs/dreams/suite-scaffold-and-mybmad-sidecar.md
surface:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-bmad-suite-lifecycle/adoption-register.md
  - recipes/mybmad-dashboard/wrapper/src/mybmad_dashboard/launcher.py
  - src/shared/packages/django-pyforge
companions: []
sources:
  - ../../../../../../docs/dreams/suite-scaffold-and-mybmad-sidecar.md
  - ../spec-bmad-suite-lifecycle/SPEC.md
assumptions:
  - "Prisma accepts schema=mybmad (or search_path) on the estate DATABASE_URL."
  - "Upstream Better Auth can consume a generic OIDC issuer, or the sidecar sits behind the same Keycloak client at the edge."
open_questions: []
---

> **Canonical contract.** Derived 2026-09-13 from `.memlog.md`. Do not hand-edit.

# SPEC — Template is an authoring tool; mybmad is a sidecar on our Postgres and OIDC

## Why

The 2026-09-06 register left `bmad-module-template` and `mybmad-dashboard`
at `skip`. The campaign wields both without a ninth station, without
`/console/`, and without a second login in `src/platform/`.

## Capabilities

- **CAP-1**
  - **intent:** `bmad-module-template` is an authoring tool beside
    `bmad-builder`.
  - **success:** Register row 11 is `wield (authoring tool only)`.
    `steward provision --module` never installs it into `.claude/skills/`.
- **CAP-2**
  - **intent:** mybmad uses the estate PostgreSQL and estate Keycloak/OIDC.
  - **success:** Prisma applies only in schema `mybmad`. Login is
    `COMPONENT_OIDC_*` / Keycloak. No Better Auth passwords on the
    wielded path. `src/platform/` adds no login views.
- **CAP-3**
  - **intent:** The host can show mybmad after the same OIDC session.
  - **success:** django-pyforge chrome lists or embeds mybmad as a
    surface. Not `/stations/mybmad/`, not `/console/`. The process stays
    the sidecar. `retired-console-check` stays green.

## Constraints

- Do not flip Epic 44 `blocked` keys.
- Do not hand-edit `spec-bmad-suite-lifecycle/SPEC.md`; memlog + `bmad-spec`.
- Launcher-local `pg_ctl` + Better Auth is a dev fallback only.

## Non-goals

- Replacing `/console/` or adding a ninth station.
- Merging Prisma into Django's schema.
- Making mybmad a PR / `detectors-ci` gate.

## Success signal

Row 11 and row 13 match CAP-1..3; an operator signed into the host can
open mybmad without a second password; Django tables are untouched.

## Decomposition

Steward Story 52.1.
