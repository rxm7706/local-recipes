---
title: 'Module-template is authoring-only and mybmad is an isolated sidecar never the console'
type: 'feature'
created: '2026-09-13'
status: 'done'
context: []
warnings: []
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** The 2026-09-06 adoption register left `bmad-module-template` (row 11)
and `mybmad-dashboard` (row 13) at `skip`. The campaign wants both wielded.
mybmad's conda default (Better Auth passwords + launcher `pg_ctl`) would be a
second login and a second cluster if that were the estate path.

**Approach:** Flip both rows in one Story. module-template is **authoring
tool only** beside `bmad-builder`. mybmad is an opt-in sidecar that **uses
our Postgres and our auth**: same cluster as the host (or Epic 51 BYO),
Prisma confined to schema `mybmad`, same Keycloak/OIDC as `/console/`.
`src/platform/` grows no second login. mybmad is not `/console/`.

## Boundaries & Constraints

**Always:**
- Change rows 11 and 13 through this Story plus memlog on
  `spec-bmad-suite-lifecycle`; re-derive with `bmad-spec` (never hand-edit
  `SPEC.md`).
- Estate `DATABASE_URL` uses `schema=mybmad` (or `search_path=mybmad`).
- Estate login is Keycloak/OIDC (`COMPONENT_OIDC_*` issuer).
- Keep `retired-console-check` green. Keep Epic 44 `blocked` keys untouched.

**Never:**
- Never provision `bmad-module-template` into `.claude/skills/`.
- Never mount mybmad at `/console/` or replace django-pyforge.
- Never add login/allauth/Better Auth under `src/platform/`.
- Never let Prisma migrate Django's schema (`public` or current Liquibase
  schema).
- Never treat launcher-local Postgres + email/password as the wielded path.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Authoring a BMAD module | `bmad-builder` + template | Scaffold off-tree; `.claude/skills/` unchanged | `provision --module` of the template forbidden |
| Estate mybmad | platform/BYO Postgres + Keycloak | Sidecar on `schema=mybmad`; OIDC login | Missing schema or issuer is a named fail |
| Django migrate | existing Liquibase/Django | `public` (or current schema) unchanged | Prisma must not apply here |
| Dev without cluster | `mybmad up` local fallback | Local pg + Better Auth allowed **off** the register path | Must not be documented as wielded |
| `/console/` | browser | django-pyforge + OIDC unchanged | n/a |

</intent-contract>

## Code Map

- `adoption-register.md` rows 11 and 13.
- Lifecycle `.memlog.md` + `bmad-spec` re-derive of `SPEC.md` Non-goals.
- Chart / Liquibase: `CREATE SCHEMA mybmad` only (no Django models).
- `recipes/mybmad-dashboard/wrapper` launcher: overlay env `DATABASE_URL` +
  OIDC client; do not modify `src/platform/` auth adapters.
- Steward / `bmad-builder` docs for the template path.

## Acceptance Criteria

1. Register row 11 is `wield (authoring tool only)`; row 13 is `wield (sidecar: estate Postgres schema mybmad + estate OIDC)`.
2. Lifecycle SPEC Non-goals re-derived to that consume contract.
3. No `/console/` mount; no second login in `src/platform/`; `retired-console-check` green.
4. Prisma applies only in schema `mybmad` on the estate cluster.
5. mybmad estate login is Keycloak/OIDC, not Better Auth passwords.
6. `pipeline-truth` `wired` agrees with the register.
7. django-pyforge chrome can show mybmad (switcher and/or embed) under the same OIDC session; it is not a ninth station and not `/console/`.
8. Ledger key `52-1-module-template-is-authoring-only-and-mybmad-is-an-isolated-sidecar-never-the-console` exists; this Story does not self-close as `done` in the mint commit.

## Auto Run Result

**Status:** done — reconstructed 2026-09-20 from git during the fleet consistency pass before the foundry cutover; no run record survived in this tracked spec.
**Summary:** landed on `main` as `50504e52e9` (2026-09-13, "Merge pull request #1332 from rxm7706/steward-52-1-impl"). Ledger row `52-1-module-template-is-authoring-only-and-mybmad-is-an-isolated-sidecar-never-the-console: done`.
**Verification:** the station's `verify_commands` ran in the landing session; the durable record here is git only — see the landing commit(s) above.
**Files changed:** `_bmad-output/projects/pyforge-steward/planning-artifacts/epics.md`, `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-bmad-suite-install-class-wiring/install-class-playbook.md`, `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-bmad-suite-lifecycle/.memlog.md`, `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-bmad-suite-lifecycle/SPEC.md`, `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-bmad-suite-lifecycle/adoption-register.md`, `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-python-foundry-cutover/.memlog.md`, `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-python-foundry-cutover/SPEC.md`, `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-python-foundry-cutover/cutover.md`, `_bmad-output/projects/pyforge-steward/planning-artifacts/sprint-status-ledger.yaml`, `src/platform/db/changelog/changes/pyforge-mybmad-1-schema.sql`, `src/platform/db/changelog/changes/pyforge-mybmad-2-app-role-grants.sql`, `src/platform/db/changelog/db.changelog-master.yaml` (+9 more)
**Residual risks:** none recorded — no run record survived to carry them.
**Follow-up review recommendation:** false

## Status reconcile 2026-09-20

- frontmatter `status` `backlog` → `done` (ledger row `52-1-module-template-is-authoring-only-and-mybmad-is-an-isolated-sidecar-never-the-console: done`).
- `## Auto Run Result` reconstructed from git (none survived).
