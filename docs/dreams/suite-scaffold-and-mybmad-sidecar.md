---
title: Module-template stays an authoring tool; mybmad joins as a sidecar, never the console
type: dream
owner: steward
status: specified
---

# Module-template stays an authoring tool; mybmad joins as a sidecar, never the console

## The Dream

The 2026-09-06 suite register left two members at `skip`: `bmad-module-template`
(catalog only) and `mybmad-dashboard` (launcher present, out of the platform).
The campaign now wants both **wielded** — but not the way a module or a
console is wielded.

1. **module-template is an authoring tool.** Steward already authors modules
   through `bmad-builder` beside skill-forge. The template is the scaffold that
   path consumes. It is never `steward provision --module`'d into
   `.claude/skills/`. A placeholder LICENSE is not a reason to copy it into
   the live skill tree.
2. **mybmad is an opt-in sidecar on the estate plane.** Same PostgreSQL as
   the host, **own schema** (`mybmad`). Same Keycloak/OIDC as `/console/`.
   It does not replace `/console/`. `src/platform/` must not grow a second
   login — mybmad is a client of the existing IdP, not a new password store.

## Why mybmad is not the console — estate contract (2026-09-13)

`/console/` is the django-pyforge host. mybmad is a Next.js sidecar, not that
host. Operator ruling: **use our Postgres and our auth; give mybmad its own
schema.**

- **Postgres:** the platform (or BYO) cluster. Prisma `DATABASE_URL` sets
  `schema=mybmad` (or equivalent `search_path`). Liquibase/Django stay on
  their schema. Never a second cluster as the wielded path; never Prisma
  tables in `public` next to Django.
- **Auth:** the same Keycloak/OIDC plane (`COMPONENT_OIDC_*`). No Better Auth
  email/password as the estate login. No second IdP and no new login views
  under `src/platform/`. A Keycloak client for the sidecar is configuration,
  not a second plane.
- **Not `/console/`:** no mount, no replacing Wagtail. `retired-console-check`
  stays green.

The conda launcher's local `pg_ctl` + Better Auth remains a **dev fallback**
when the estate cluster is absent — not the wielded register path.

## Kinships

- `docs/dreams/bmad-suite-lifecycle.md` / `spec-bmad-suite-lifecycle` CAP-1
  (register rows 11 and 13; 2026-09-06 skip verdict)
- `spec-bmad-suite-channel-product` (catalog, not wire-everything)
- `bmad-dashboard` row 12 (opt-in, never `/console/`)
- pap host ADs: one identity plane, `retired-console-check`

## What it looks like when real

The adoption register records row 11 as **wield (authoring tool only)** and
row 13 as **wield (sidecar on estate Postgres + OIDC, schema `mybmad`)**.
`mybmad` is not `/console/` and not a PR gate. The host **shows** it in
django-pyforge chrome (switcher / embed) after the same OIDC session, as a
surface — not station nine. Stations keep talking through `station_port`;
they do not import mybmad. `bmad-spec` re-derives the lifecycle Spec so
Non-goals name this consume contract, not a skip.

## Realization log

- **2026-09-13** — Minted Story 52.1. Operator locked the bridge: same
  PostgreSQL, schema `mybmad`; same Keycloak/OIDC; no second login in
  `src/platform/`; not `/console/`.
