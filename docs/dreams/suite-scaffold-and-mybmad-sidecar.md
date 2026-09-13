---
title: Module-template stays an authoring tool; mybmad joins as a sidecar, never the console
type: dream
owner: steward
status: dreamt
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
2. **mybmad is an isolated, opt-in sidecar.** The operator can launch the
   upstream BMAD Next.js UI (`mybmad` / feature `bmad-ui`) when they want that
   face. It does not replace `/console/`, does not share OIDC, and does not
   become a second estate identity plane.

## Why mybmad is not the console

`/console/` is the django-pyforge host: Wagtail, Keycloak/OIDC, Liquibase,
`station_port`, the CRC/OCP chart. `src/platform/` never imports `pyforge.*`.
`retired-console-check` exists because a second Guildhall-class console
already failed once.

mybmad is a Next.js app with **its own Postgres and its own auth**. Making it
`/console/` would mean:

- a second login, not Keycloak;
- a second database, not the platform `DATABASE_URL` / BYO overlay;
- a BMAD-native kanban as the estate face (stations, recipes, fleet, CMS);
- re-introducing the retired second-console class.

That is a product substitution, not a suite-adoption. `bmad-dashboard` (member
12) is already the opt-in marshal VS Code surface under the same rule: never
the console. mybmad is the Next.js sibling of that rule.

Honest shift-left: run it **beside** the host, isolated, opt-in. Honest
replacement of `/console/` would be a different Dream that rewrites identity,
datastore, and the host ADs — not this one.

## Kinships

- `docs/dreams/bmad-suite-lifecycle.md` / `spec-bmad-suite-lifecycle` CAP-1
  (register rows 11 and 13; 2026-09-06 skip verdict)
- `spec-bmad-suite-channel-product` (catalog, not wire-everything)
- `bmad-dashboard` row 12 (opt-in, never `/console/`)
- pap host ADs: one identity plane, `retired-console-check`

## What it looks like when real

The adoption register records row 11 as **wield (authoring tool only)** and
row 13 as **wield (isolated opt-in sidecar)**. A documented authoring path
sits beside `bmad-builder`. `mybmad` launches without mounting at `/console/`,
without joining platform OIDC, and without becoming a PR gate. `bmad-spec`
re-derives the lifecycle Spec so Non-goals no longer say "mybmad into the
platform" / "module-template provisioning" as if those were still skips —
they become the sidecar and authoring-tool contracts.

## Realization log

- **2026-09-13** — Operator asked to mint the steward Story that records both
  verdicts and to answer why mybmad is not the console. Seeded here; Spec
  change is memlog + `bmad-spec`, never a silent register edit.
