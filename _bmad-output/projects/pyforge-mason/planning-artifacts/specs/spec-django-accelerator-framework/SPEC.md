---
spec: django-accelerator-framework
status: absorbed
owner-dream: docs/dreams/django-accelerator-framework.md
absorbed-into: spec-pyforge-unifying-strategy
surface:
  # `src/platform/**` and the pyforge-steward dashboard glob were DROPPED 2026-09-09: they
  # dual-govern `src/platform/deploy/DR.md` with a steward Spec, so `spec-surface-check`
  # emits the identical drift-presumed finding under both — an INV-2 smell.
  - scripts/emit_wagtailcore_schema_delta.py
companions: []
sources:
  - ../../../../../../docs/dreams/django-accelerator-framework.md
  - ../../../../pyforge-steward/planning-artifacts/specs/spec-python-agent-platform/SPEC.md
open_questions: []
  # CLOSED 2026-09-09: "Does CAP-2's third-surface trigger count Django surfaces repo-wide
  # only, or across the estate?" — answered by the trigger's RETIREMENT, not by scoping it.
  # Counting surfaces, repo-wide or estate-wide, measures the wrong thing.
---

# SPEC — The Django accelerator contract (ABSORBED)

This is a pointer spec, not a contract. Absorbed by operator ruling on **2026-09-09**
(fleet-readiness decision batch § 2.3 C3, evidence row mason-B6).

**Why it was absorbed.** CAP-2's counting trigger is **retired, not scoped**: it watched for a
third or fourth Django surface repeating the copy by hand, and that premise was falsified. The
estate reached **nine** Django faces and did not repeat the copy — it factored a declarative
base class instead. `src/shared/packages/django-pyforge` provides
`django_pyforge.portals.PortalConfig`; eight station portals subclass it with roughly ten
declarative fields each (`django-mason/src/django_mason_portal/apps.py:6-21`) and mount into the
ONE project via `src/platform/config/settings/base.py:27-41` and `:165-183`. The surface count
never moved past two — `find src -name manage.py` returns exactly `src/platform/manage.py`.

**Where the live content goes.** CAP-1's accelerator contract travels with the exemplar, and the
exemplar lives under steward's chain, not mason's. Target: **`spec-pyforge-unifying-strategy`,
its Lane-2 section** — deliberately NOT `spec-python-agent-platform`, because steward Story 48.8
supersedes that Spec.

**Why mason was never the right home.** Mason has no epic and no story for this Dream and never
did; the Dream's own Kinships call mason nominal and "genuinely unclaimed". Absorbing also
resolves mason's only `docs/dreams/README.md:71` vocabulary violation — a Dream at `specified`
over a `draft` Spec.


### The record, as it stood at absorption

*Everything below is the contract as written before 2026-09-09, preserved verbatim so the
absorb loses nothing. It is a record, not a live contract — CAP-1 travels to the Unifying
Spec's Lane-2 section, CAP-2 is retired. CAP-1's own evidence is already stale here:
`SPEC.md` cited `config/urls.py:26` `include(health_check.urls)`; the live route is
`src/platform/config/urls.py:98` via an explicit `HealthCheckView`, with `:50-55` recording
`include(health_check.urls)` as the DEPRECATED path they moved off.*

#### Why (as written)

The dream was captured thin on 2026-08-14 — one hand-built Django surface (Steward's dashboard),
no recurring scaffolding pain, an explicit constraint against building anything until a second
Django-backed surface was actually planned. The same day, three Realization-log entries changed
its standing: the operator directed that the Django/Langflow/DB-GPT family builds on a
cookiecutter-django host with FastAPI integration **based on this dream** ("at that intake this
dream is the basis and should be spec'd with (not after) the family"); the air-gap realization
requirements were carried over from the OpenTeams source original; and the subject project was
named **python-agent-platform**. Story 10.1 then rendered that host into `src/platform/` (landed
on main 2026-08-14): `config/settings/{base,local,production,test}.py` env()-split settings,
`config/urls.py:26` `path("ht/", include("health_check.urls"))`, the `config/asgi.py` FastAPI
seam owning `/api/`, `config/celery_app.py`. So the honest question this spec answers is not
"build the scaffolding engine?" — the dream's own constraint still says no — but "what is the
**named shape** any PyForge Django surface renders to, now that two surfaces exist to name it
from?" This spec closes the "spec'd with the family" obligation: CAP-1 names the contract (real
now); CAP-2 parks the engine on the dream's own trigger.

#### Capabilities (as written)

- **CAP-1 — The accelerator contract (REAL now).**
  - **intent:** A named, documented shape — *the accelerator contract* — that any PyForge Django
    surface renders to: cookiecutter-django base with FastAPI integration (an ASGI seam owning
    the API namespace); `env()`-helper/split-settings configuration; `/ht/` django-health-check
    endpoints wired to K8s liveness/readiness probes; mirror endpoints (conda/pypi/registry)
    parameterized at render time; vendored zero-CDN static assets (Bootstrap 5.3 + HTMX shape);
    auth bound to an internal OIDC IdP. Its **first realization** is python-agent-platform's
    `src/platform/` render (Story 10.1, on main 2026-08-14); its **second reference shape** is
    Steward's dashboard — `middleware.py` identity-at-the-boundary + `declarations.py`
    adopter-declarations — the local precedent the dream names as what a second Django surface
    copies from directly.
  - **success:** The contract is documented in this spec, and both existing surfaces verifiably
    conform to the clauses applicable to each — or carry dated deviations (the steward dashboard
    predates the contract and embodies the identity/declaration clauses, not the full render
    shape; that asymmetry is recorded, not papered over).
- **CAP-2 — The templating engine (CONTINGENT, explicitly parked).**
  - **intent:** A FreeMarker-*style* stamping engine that renders new surfaces from the contract
    mechanically — built **only after** a third/fourth Django surface repeats the copy by hand,
    per the dream's own constraint ("one hand-built Django app doesn't justify a templating
    pipeline; three or four might"). When the trigger fires, the engine's templates are
    **extracted from the proven local shapes** (the 10.1 render + the steward dashboard), never
    imported from the WF source's FreeMarker templates.
  - **success:** The CAP stays parked with its trigger recorded here; no engine code, template
    repo, or pipeline exists before a third surface demonstrates the repeated hand-copy. If the
    trigger fires, the engine work starts from the then-live conforming surfaces, and this spec
    is updated first.

#### Constraints (as written)

- **Always — air-gap parity per the dream's 2026-08-14 air-gap entry:** Artifactory coordinates
  are first-class render-time substitutions across `pyproject.toml`, `pixi.toml`, Helm charts,
  and CI workflows; every pip/conda/pixi install in a rendered surface resolves from mirrored
  indexes only; frontend assets are vendored and bundled locally with zero CDN
  `<script>`/`<link>` references in base templates (applied at template-authoring time, not as a
  later patch); all runtime config flows through env/secret mounts (`env()`-split settings,
  matching `_http.py`'s env-only enterprise routing) — never committed; auth binds to an
  internal OIDC IdP with no external identity callbacks; `/ht/` endpoints are wired to K8s
  liveness/readiness probes.
- **Always — the platform is the living exemplar:** the contract must never drift from what
  `src/platform/` actually ships. When contract and render disagree, either the render gains a
  dated deviation or the contract is amended — never silent divergence.
- **Always — CAP-2 stays parked until its trigger:** building the engine before a third surface
  repeats the copy is a violation of this spec, not initiative.

#### Non-goals (as written)

- **Not** an engine build now — CAP-2 is parked on the dream's own third-surface trigger.
- **Not** an import of the WF source's FreeMarker templates, Jenkins wiring, or three-repo
  pipeline — carried unchanged from the dream's non-goals; local shapes are the only template
  source if CAP-2 ever activates.
- **Not** a new station — this is a mason planning artifact naming a shape two existing surfaces
  already carry; the platform's own build contract stays with `spec-python-agent-platform`.

#### Success signal (as written)

The accelerator contract is documented (this spec); `src/platform/` and Steward's dashboard each
verifiably conform to their applicable clauses or carry dated deviations; CAP-2 remains parked
with its extraction-not-import rule and third-surface trigger recorded; and the owner dream reads
`status: specified` with a Realization-log entry closing the "spec'd with (not after) the family"
obligation.
