---
title: The "Corporate Brain" CMS atlas's own WikiSyncer has been waiting to push to
type: dream
owner: atlas
status: specified
---

# The "Corporate Brain" CMS atlas's own WikiSyncer has been waiting to push to

## The Dream

This is not the speculative dream it first appeared to be. Atlas already has a real, tested,
network-injectable CLIENT for an external Wagtail/Django CMS — `factory/lasuite.py`'s
`LaSuiteClient` (create/update/get/list over the Wagtail REST shape) and `WikiSyncer` (idempotent,
content-digest-keyed push of the Karpathy-wiki's report pages), built for Story H3, verified
end-to-end against an in-memory mock with zero network. `resolve_lasuite_config` already defines
the exact contract a live server needs to satisfy: a base URL and an API token, both required or
the client degrades cleanly rather than pushing at a half-configured endpoint. What's missing is
entirely on the SERVER side — an actual running Wagtail instance to receive these pushes — which
this repo's own deferred-work ledger already names and scopes as `DW-H3`, explicitly an ATTENDED
bring-up (an operator's own infrastructure decision, not a code gap this Dream can close by
itself).

## What it looks like when real

Two genuinely different scopes, deliberately kept separate:

- **The narrow, well-evidenced scope**: a minimal live Wagtail/La Suite server satisfying
  `LaSuiteClient`'s already-defined REST contract, with a real httpx-backed opener injected in
  place of the mock — closing DW-H3 exactly as atlas's own deferred-work ledger already frames it.
  This alone would let the Karpathy-wiki's report pages actually reach a real "Corporate Brain"
  destination for the first time.
- **The much larger, genuinely speculative scope**: the source dream's full feature set — four
  custom Wagtail apps (branded reusable tables, interactive charts, brand color picker,
  heading-anchor blocks), OIDC-authenticated multi-author publishing, DRF APIs, embedded
  Panel/Bokeh dashboards (composing with [[atlas-query-dashboards]] if both existed) — none of
  which has a named PyForge audience of non-developer human authors. This repo's own content is
  authored by AI agents editing markdown/code directly; nothing currently needs a WYSIWYG
  publishing workflow.

## What is real

`DW-H3` (`pyforge-atlas`'s own deferred-work ledger): "the live La Suite/Wagtail SERVER +
credential + httpx opener bring-up (ATTENDED) — DEFERRED." Its own text confirms the client half
is complete and tested; only the operator decision to actually stand up a server remains open.
This Dream does not make that decision — it documents the shape it would take if made, and draws
the line between "close DW-H3" (real, scoped, evidenced) and "build a general enterprise CMS"
(speculative, no named audience).

## Constraints

- **Does not decide DW-H3's own attended bring-up.** That remains an operator decision outside
  this Dream's scope, exactly as atlas's own deferred-work ledger already frames it.
- **The narrow scope (closing DW-H3) and the broad scope (a full CMS) must not be conflated.**
  A future Spec against the narrow scope should not silently absorb the broad one's much larger
  surface without a separate, explicit decision.

## Non-goals

- **Not a general enterprise content-authoring platform** for non-developer human authors — no
  such audience has been named in this repo.
- **Not headless/API-only mode** — moot until the broader scope is ever justified.
- **Not multi-site/multi-tenant** — same.

## Full feature audit against `wagtail-cms-content-platform`

| Source feature | Disposition | Why |
|---|---|---|
| A live Wagtail/Django server satisfying `LaSuiteClient`'s REST contract | **Included, closes DW-H3** | The one piece with real, already-built, already-tested client-side evidence — the genuine gap. |
| `wagtailsite` app (base models, DSS models, snippets, hooks, endpoints) | **Omitted, scope depends on decision** | Belongs to the broad-scope decision, not the narrow DW-H3-closing one. |
| `wagtailtables` (branded reusable tables, Handsontable/TipTap editors) | **Omitted, no named author audience** | No non-developer content authors exist to use this. |
| `wagtailcharts` (10 chart types via Chart.js) | **Omitted, overlaps [[atlas-query-dashboards]]** | If interactive charts are ever needed, that Dream's Panel/Bokeh approach is the better-evidenced path, not a Wagtail-block reimplementation. |
| `wagtailcolorpicker` (brand color picker for rich text) | **Omitted, no named author audience** | Same reasoning as `wagtailtables`. |
| OIDC + django-allauth, group RBAC | **Omitted, no target authentication system** | No PyForge-native identity system this would integrate with yet. |
| DRF APIs alongside the CMS | **Omitted, speculative** | No named consumer. |
| `BokehPanelPage` (embed Panel dashboards in CMS pages) | **Omitted, contingent on both the broad CMS scope AND [[atlas-query-dashboards]]** | Real idea, but stacks two unproven dependencies. |

## Kinships

[[pyforge-atlas]] (the estate; DW-H3 lives in its own deferred-work ledger, Story H3 built the
client) · [[atlas-query-dashboards]] (the better-evidenced path to interactive charts/dashboards,
should the need arise, rather than Wagtail-specific blocks) · [[artifactory-download-intelligence]]
(a sibling atlas Dream from the same investigation, unrelated in subject but same "checked real
code before drafting" discipline)

## Realization log

- **2026-08-14** — Dream substantially re-scoped from the source catalog's original "weakest fit"
  tiering. Initial pass (before this batch's deeper investigation) rated this the lowest-priority
  dream of fifteen, reasoning "no non-developer publishing workflow exists to serve." Investigating
  [[atlas-query-dashboards]] surfaced `factory/lasuite.py`'s real, tested `LaSuiteClient`/`WikiSyncer`
  and `DW-H3`'s own deferred-work entry — the CLIENT side of exactly this capability already exists
  and is waiting on a server. Re-titled and re-scoped to distinguish that real, narrow,
  evidence-backed piece (closing DW-H3) from the much larger, still-genuinely-speculative full CMS
  feature set the source dream describes — the original "weakest fit" verdict was wrong for the
  narrow scope, right for the broad one.
- **2026-08-14** — Spec authored (spec-wagtail-corporate-brain, pyforge-atlas) per operator
  decision: spec-first, bring-up later — narrow scope only (live instance satisfying
  LaSuiteClient's existing contract, real httpx opener, round-trip/idempotency verified); the
  attended DW-H3 bring-up is scheduled separately; broad CMS scope stays excluded per the dream's
  own Constraint.
- **2026-08-14** — **Air-gapped realization requirements (operator, from the source original
  wagtail-cms-content-platform.md):** the source platform runs entirely inside a private network,
  and the narrow DW-H3 instance must too. (1) Whichever way the spec's substrate open question
  resolves, installs come from mirrors only: conda-forge `wagtail` + `django-lasuite` resolved
  through an Artifactory-mirrored conda channel (this repo's pixi channels are already swappable
  to internal mirrors), or a container image pulled from an internal registry per today's
  K8s/OCP+PostgreSQL+Redis decision — never Docker Hub, never public PyPI at deploy time.
  (2) All static assets self-hosted: the source serves its CSS from app `static/` dirs
  (`custom.css`, `wagtail_admin.css`) and injects all editor JS (Draftail color picker,
  Handsontable/TipTap/Chart.js StructBlockAdapter media, Bokeh `render_embed()` resource tags)
  from local media — the live instance serves Wagtail admin + site assets
  WhiteNoise/`collectstatic`-style with zero CDN references, the exact concern
  spec-atlas-query-dashboards CAP-4 just made contractual for Panel/Bokeh; any future
  broad-scope chart/table blocks inherit that CAP-4 vendoring precedent rather than re-deriving
  it. (3) Credentials stay env-only: `LASUITE_BASE_URL`/`LASUITE_API_TOKEN` already resolve only
  from env (spec AD-2) — in-cluster that means secret-mounted env vars, matching `_http.py`'s
  truststore + JFrog/GitHub/.netrc chain (env vars only, never committed config); the httpx
  opener trusts the internal CA the same truststore-driven way. (4) The source's production auth
  is an internal OIDC IdP (form login only in DEBUG) — moot for the narrow Bearer-token scope,
  but any separately-decided broad scope inherits "internal IdP, no external auth callbacks."

- **2026-09-09** — Fleet readiness pass (operator batch § 2.3, C16 / row atlas-B6). **DW-H1's
  object-storage half is re-pointed off MinIO** onto the infra-kinds answer — an RWX volume, and
  for a multi-node target the storage class that provides it. `pyforge-unifying-strategy.md:406-408`
  is unambiguous and was re-affirmed on 2026-09-05: "No MinIO as a fourth core kind … Lane 1 media
  is RWX, and a multi-node target names its RWX-capable storage class" — and Wagtail *is* Lane 1,
  exactly the case that ruling anticipates. `spec-wagtail-corporate-brain/SPEC.md:24`, `:135` and
  `:137` re-render accordingly. The Never is **not** re-opened and no scoped exemption is granted;
  DW-H1 itself stays `open` and ATTENDED — only the storage kind it names is corrected. Neither
  this Dream's status nor the Spec's changes: the readiness pass re-confirmed this pair as an
  exemplar (Epic 16 `done`, DW-H3 still `open`, and the Spec correctly refusing to read `shipped`
  on paper alone, exactly as its own Success signal demands).
