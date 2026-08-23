---
title: One PyForge web surface strategy — portals, dashboards, and the Guildhall stop competing
type: dream
owner: herald
status: dreamt
---

# One PyForge web surface strategy

## The Dream

An operator (or agent pointing a human) should never wonder *which window is the
truth* for PyForge. Today three station-owned web surfaces plus static tooling
grew for good local reasons and now read as three products:

| Surface | Stack | Job |
|---------|-------|-----|
| Steward dashboard kit | Django (optional extra) | Secure live boards — identity, isolation, audit |
| Atlas dashboard | Vizro + BSL | Domain analytics over atlas data |
| Warden `compliance_face` | Django app on platform | Upload → engines → reports (JSON today) |
| Guildhall / factory console | Static Pages (`docs/dashboard/`) | Program-wide Dream→Code board |

The dream: **one estate strategy** so every new UI chooses a *lane*, reuses
shared security and chrome, and links into the Guildhall — instead of inventing
a fourth stack.

## Lanes (the strategy)

Three lanes, not one monolith:

1. **Guildhall (program board)** — Herald/Marshal visibility. Static or
   lightly-dynamic Pages. Answers: *what is the factory doing?* Never hosts
   upload workflows or row-level tenant data.
2. **Station portals (verbs)** — Django apps on the **platform** host.
   Answers: *do this job* (upload, approve, provision UI). Warden’s compliance
   face (rename toward `warden_portal`) is the prototype. Future marshal/doctor
   operator UIs join this lane only when a verb needs a form, not a chart.
3. **Analytics dashboards (questions)** — Vizro (or steward’s secure-dashboard
   pattern) over station data. Answers: *what does the data say?* Atlas is the
   prototype. Steward’s `pyforge.steward.dashboard` kit is the **security and
   hosting pattern** every analytics board adopts ([[secure-live-dashboards]]),
   not a competing product brand.

**CLI-first stations stay CLI-first** (mason, doctor, scribe, marshal) until a
Dream names a portal verb. Dashboards are not consolation prizes for missing
CLIs.

## What it looks like when real

- A one-page **surface map** (this Dream’s Spec) lists every public URL / Pages
  path, owning station, lane, and auth posture — drift-checked like inventory.
- Shared **chrome**: station name, link home to Guildhall, env badge; no
  per-app snowflake nav.
- Shared **security**: steward dashboard declarations (identity headers, row
  isolation, audit) are mandatory for Lane 3; Lane 2 uses platform auth
  (allauth) + keys-not-blobs for jobs.
- Naming: station portals are `{station}_portal` (e.g. `warden_portal`);
  analytics stay `{station}.dashboard` / Vizro apps; Guildhall keeps its name.
- New UI RFCs answer three questions before code: *which lane? which host?
  which security kit?* Wrong lane is a Spec refusal, not a style nit.

## Constraints / Non-goals

- Not a single SPA that swallows BMAD Method UI (`bmad-dashboard` / MyBMAD stay
  suite tooling).
- Not forcing Atlas Vizro onto Django templates, or Warden upload onto Vizro.
- Not building portals for every station “for symmetry.”
- Not replacing [[factory-console]] / Guildhall; this Dream *governs how
  portals relate to it*.

## Kinships

[[factory-console]] (Guildhall — Lane 1, realized/absorbed into marshal
narrative) · [[secure-live-dashboards]] (Lane 3 security kit — steward) ·
[[atlas-query-dashboards]] / atlas Vizro board (Lane 3 prototype) ·
[[compliance-factory-web-face]] (Lane 2 prototype — warden) ·
[[pyforge-herald]] (stage / proclamation) · [[pyforge-steward]] (deploy &
secure hosting)

## Realization log

- **2026-08-23** — Dreamt after inventory of station web surfaces
  (steward Django kit, atlas Vizro, warden compliance_face, herald static
  Guildhall; four stations CLI-only) and the rename discussion for
  `compliance_face` → `warden_portal`. Strategy: three lanes + surface map +
  shared chrome/security, not one mega-app.
