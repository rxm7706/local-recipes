---
title: A normalized data model and REST API pattern, waiting for a PyForge-native subject
type: dream
owner: atlas
status: dreamt
---

# A normalized data model and REST API pattern, waiting for a PyForge-native subject

## The Dream

The source dream's actual subject — Data Center Entry application-survey data and Technology
Business Management cost-allocation data, normalized across BEAMS/ADS/ITM/BPPA source systems
into a three-tier raw/conformed/curated model, served via JSON:API — has no PyForge analog. This
repo tracks conda-forge feedstocks, PyPI packages, and BMAD fleet state, not enterprise
application inventories or IT cost allocation. What's genuinely reusable is not the domain, it's
the *pattern*: a three-tier normalization discipline plus a DRF-JSON:API-with-audit-history
serving shape, captured here as infrastructure waiting for a subject this repo actually has, not
as a commitment to build anything against DCE/TBM's own domain.

## What it looks like when real

Deliberately left thin — this Dream captures a REUSABLE PATTERN, not a scoped feature, because no
PyForge-native subject has been identified yet that needs it:

- IF a future PyForge capability needs multi-source data normalized into one queryable model with
  full change history (`django-simple-history`-style audit trail) and served as a REST API, this
  Dream is where that pattern's design notes would live — three-tier raw/conformed/curated
  staging, JSON:API response shape, group-based domain permissions.
- The closest current PyForge candidate is atlas's own `cf_atlas.db` — already multi-source
  (PyPI, conda-forge, CVE feeds, GitHub), already normalized into one queryable shape — but atlas
  solves this today with DuckDB + Kedro pipelines, not Django + DRF, and nothing currently asks
  for a REST API surface over it. [[atlas-query-dashboards]] is the nearer, better-evidenced need
  (visualize what's already there) versus this Dream's speculative "expose it over JSON:API."

## What is real

Nothing. This is the most purely speculative Dream in this batch — no PyForge subsystem currently
lacks a normalized model + REST API to the degree that building one would close an observed gap.
Captured for completeness of the source catalog's audit trail, not because investigation found a
real local need.

## Constraints

- **Not to be built against any subject until one is named.** This Dream should not advance past
  `dreamt` without a concrete PyForge-native domain to normalize — building the pattern in the
  abstract, with no real data to validate it against, would violate this repo's own "nothing
  speculative" principle.

## Non-goals

- **Not the DCE/TBM domain itself** — application-survey and cost-allocation data have no
  PyForge equivalent and are explicitly out of scope, not merely deferred.
- **Not GraphQL or gRPC** — JSON:API only, carried from the source dream unchanged (moot until a
  subject exists, but recorded for parity).
- **Not real-time data streaming** — batch/on-demand only, carried unchanged.

## Full feature audit against `enterprise-data-models-and-apis`

Every capability the source dream names, and this Dream's disposition on each:

| Source feature | Disposition | Why |
|---|---|---|
| Three-tier raw/conformed/curated model | **Pattern retained, domain dropped** | The staging discipline is reusable; the DCE/TBM domain it stages is not. |
| DCE application-survey models (27 model classes) | **Omitted, no PyForge analog** | No equivalent enterprise application-survey concept exists here. |
| TBM cost-allocation models (TBM v4.0 taxonomy) | **Omitted, no PyForge analog** | No equivalent IT cost-allocation concept exists here. |
| Django + DRF + JSON:API pattern | **Pattern retained** | Reusable infrastructure shape, independent of the domain it originally served. |
| `django-simple-history` audit trail | **Pattern retained** | Same — a generically useful pattern once ANY Django-backed model exists in this repo (none currently do outside Steward's dashboard). |
| `django-import-export` bulk admin import | **Omitted, no target data** | Nothing to bulk-import without a domain to import into. |
| Custom JSON:API bulk-array parser | **Omitted, no target data** | Same reasoning. |
| Group-based domain permissions | **Pattern retained** | Reusable once a real model exists to permission. |
| `transaction.atomic()` bulk updates | **Omitted, implementation detail** | Not a scoping decision — standard Django practice, assumed if this is ever built, not worth a dedicated line item. |

## Kinships

[[atlas-query-dashboards]] (the better-evidenced near-neighbor — visualizing what atlas already
has, versus this Dream's speculative "build a new normalized model with no named subject") ·
[[pyforge-atlas]] (nominal owner, by the source dream's own label; genuinely unclaimed until a
subject exists)

## Realization log

- **2026-08-14** — Dream captured while porting a sibling org's dream catalog for PyForge fit,
  flagged from the start as the weakest-evidenced Tier-3 candidate. Investigation confirmed no
  PyForge subsystem has an unmet need this pattern would close; kept only as a documented,
  intentionally-thin placeholder distinguishing "the pattern is reusable" from "this domain is
  reusable" — the latter is not. Should not be advanced without a concrete subject named first.
- **2026-08-14** — **Air-gapped realization requirements (operator, from the source original
  enterprise-data-models-and-apis.md):** the source pattern is already the disconnected-friendly
  shape, worth recording so it survives intact if a subject is ever named: data enters as batch
  file drops (18 `django-import-export` CSV/XLSX resource classes loaded via admin and management
  commands; real-time streaming is an explicit non-goal), the Django ORM is the query engine (no
  external ETL service), and the JSON:API surface serves consumers inside the perimeter only.
  A PyForge realization must keep that: the full dependency set (Django, DRF,
  `djangorestframework-jsonapi`, `django-simple-history`, `django-import-export`) resolves from
  Artifactory-mirrored conda/PyPI indexes only (this repo's pixi channels are already swappable
  to internal mirrors); it deploys per today's K8s/OCP+PostgreSQL+Redis decision — image pulled
  from an internal registry, PostgreSQL in-cluster; DB credentials and any group-sync
  configuration reach the process via env/secret-mount only, composing with `_http.py`'s
  runtime-driven enterprise posture (env vars only, never committed config); and admin/browsable-
  API static assets serve WhiteNoise/`collectstatic`-style with zero CDN references — the same
  concern spec-atlas-query-dashboards CAP-4 makes contractual for dashboard surfaces.

- **2026-09-09** — Fleet readiness pass; status corrected `specified` → **`dreamt`** (operator
  batch § 2.2, row atlas-B4). § What is real still reads "Nothing", correctly — no PyForge
  subsystem has surfaced a need for this pattern. `docs/dreams/README.md` § status is explicit
  that "`specified` requires a Spec at `ready` or beyond"; `spec-enterprise-data-models-and-apis`
  is `extension-point`, an explicit park with **zero stories minted** — neither `ready` nor
  beyond. This Dream's own Constraint says the same thing in its own words: it "should not
  advance past `dreamt` without a concrete PyForge-native domain to normalize". The Spec keeps
  `status: extension-point`, unchanged, with its trigger intact; it reverts to `specified` the
  moment a subject is named and the Spec reaches `ready`.
  **The 2026-08-22 extension-point reframe stands, recorded here verbatim now that it no longer
  rides on the `status:` line:** *"reframed as an EXTENSION-POINT (operator): the fleet ships the
  socket/contract; the capability develops separately (incl. air-gapped) — see the spec's
  Extension contract section."* That reframe is sound and the seam is real — but the socket it
  names is steward's shipped AD-17 pluggable-app registry (`config/engine_patterns.py`), which
  belongs to steward, not to this Dream. Under the realization gate this Dream still has nothing
  of its own to exercise. Nearest-need note unchanged: [[atlas-query-dashboards]] remains the
  better-evidenced neighbour (itself retired the same day, batch C1).
  Cross-station residue for steward: `docs/dreams/README.md` should name `extension-point` as a
  recognised parked-Spec state that does NOT satisfy `specified`, and carry this row's corrected
  status.
